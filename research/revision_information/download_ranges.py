"""Bounded public HTTP Range download; validate range/ETag/length and gzip CRC."""
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
RAW=ROOT/'data/raw/codebench'
URL='https://codebench.icomp.ufam.edu.br/dataset/files/cb_dataset_2016_2_v1.81.tar.gz'
SIZE=58336822
ETAG='"37a2636-5e60929e77277"'
TARGET=RAW/'cb_dataset_2016_2_v1.81.tar.gz'
PARTS=RAW/'cb_dataset_2016_2_parts'


def part(index,start,end):
    path=PARTS/f'part_{index:02d}.bin'
    size=end-start+1
    for attempt in range(4):
        have=path.stat().st_size if path.exists() else 0
        if have==size:
            return {'part':index,'start':start,'end':end,'bytes':size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        if have>size:
            raise RuntimeError('Oversized partial; preserve for inspection')
        first=start+have
        try:
            request=urllib.request.Request(URL,headers={'Range':f'bytes={first}-{end}','User-Agent':'CodeBench-research-data-audit/1.0'})
            with urllib.request.urlopen(request,timeout=60) as response:
                expected=f'bytes {first}-{end}/{SIZE}'
                if response.status!=206 or response.headers.get('Content-Range')!=expected:
                    raise RuntimeError(f'Unexpected response: {response.status}, {response.headers.get("Content-Range")}')
                if response.headers.get('ETag')!=ETAG or int(response.headers.get('Content-Length','-1'))!=end-first+1:
                    raise RuntimeError('Resource identity or range length changed')
                print(json.dumps({'stage':'range_started','part':index,'start':first,'end':end,'attempt':attempt+1}),flush=True)
                with path.open('ab') as f:
                    last_report=have
                    while True:
                        block=response.read(128*1024)
                        if not block:
                            break
                        f.write(block); have+=len(block)
                        if have>size:
                            raise RuntimeError('Response exceeded requested range')
                        if have-last_report>=4*1024*1024:
                            print(json.dumps({'stage':'range_progress','part':index,'bytes':have,'total':size}),flush=True)
                            last_report=have
            if path.stat().st_size!=size:
                raise RuntimeError('Incomplete response; resume retained partial')
        except Exception as error:
            print(json.dumps({'stage':'range_retry','part':index,'attempt':attempt+1,'error':str(error)}),flush=True)
            if attempt==3:
                raise
            time.sleep(3)
    return {'part':index,'start':start,'end':end,'bytes':size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    PARTS.mkdir(parents=True,exist_ok=True)
    if TARGET.exists():
        raise RuntimeError('Target exists; inspect it instead of overwriting')
    width=(SIZE+3)//4
    ranges=[(i,i*width,min(SIZE-1,(i+1)*width-1)) for i in range(4)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda args:part(*args),ranges))
    temporary=TARGET.with_suffix(TARGET.suffix+'.assembling')
    if temporary.exists():
        raise RuntimeError('Assembly file exists; preserve it for inspection')
    digest=hashlib.sha256()
    with temporary.open('wb') as output:
        for result in sorted(results,key=lambda x:x['part']):
            with (PARTS/f"part_{result['part']:02d}.bin").open('rb') as f:
                for block in iter(lambda:f.read(1024*1024),b''):
                    output.write(block); digest.update(block)
    assert temporary.stat().st_size==SIZE
    decompressed=0
    with gzip.open(temporary,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            decompressed+=len(block)
    if TARGET.exists():
        raise RuntimeError('Target appeared during assembly; do not overwrite')
    temporary.rename(TARGET)
    manifest={'source_page':'https://codebench.icomp.ufam.edu.br/dataset/','download_url':URL,
              'release':'1.81','release_listed_date':'2024-10-24','semester':'2016-2',
              'http_last_modified':'Fri, 12 Aug 2022 10:58:35 GMT','etag':ETAG,'size_bytes':SIZE,
              'sha256':digest.hexdigest(),'gzip_crc_verified':True,'uncompressed_gzip_bytes':decompressed,
              'bounded_parallel_streams':4,'parts':results,'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
              'archive_path':str(TARGET.resolve()),'access':'Public direct download, no authentication or terms acceptance.',
              'license':'No explicit redistribution license established on publisher page; not labeled open-license.',
              'source_code_executed':False,'holdout_performance_evaluated':False}
    (OUT/'source_manifest_2016_2.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'stage':'download_verified','bytes':SIZE,'sha256':digest.hexdigest(),'gzip_crc_verified':True}),flush=True)


if __name__=='__main__':
    main()
