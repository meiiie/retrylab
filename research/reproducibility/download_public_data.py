"""Download only the verified public archives; never extract or execute them."""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
ARCHIVES = {
    'accoding': {
        'url': 'https://zenodo.org/api/records/11395043/files/ACcoding-Dataset%20v2.0.0.zip/content',
        'path': 'data/raw/accoding/ACcoding-Dataset-v2.0.0.zip',
        'bytes': 96056846,
        'sha256': '26b5637d2a912ce6ae4824e49e055a060c1162422c4a47508e3eb1017762ac1d',
    },
    'codebench': {
        'url': 'https://codebench.icomp.ufam.edu.br/dataset/files/cb_dataset_2016_1_v1.81.tar.gz',
        'path': 'data/raw/codebench/cb_dataset_2016_1_v1.81.tar.gz',
        'bytes': 174487574,
        'sha256': '777d5d30343575ef007ec92afab4e177969652ba0d730c96aeaa1b8a514d5d13',
    },
    'codebench-2016-2': {
        'url': 'https://codebench.icomp.ufam.edu.br/dataset/files/cb_dataset_2016_2_v1.81.tar.gz',
        'path': 'data/raw/codebench/cb_dataset_2016_2_v1.81.tar.gz',
        'bytes': 58336822,
        'sha256': 'a7792403accd6aadbe47b04f48858a2da42574b98a78a3c245b7eaec4a92075f',
    },
}


def verify(path, specification):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if path.stat().st_size != specification['bytes'] or digest.hexdigest() != specification['sha256']:
        raise ValueError(f'Archive differs from the recorded source: {path}. File retained for inspection.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', choices=[*ARCHIVES, 'all'], default='all')
    parser.add_argument('--verify-only', action='store_true', help='No network; require and verify existing archives.')
    args = parser.parse_args()
    names = list(ARCHIVES) if args.dataset == 'all' else [args.dataset]
    for name in names:
        specification = ARCHIVES[name]
        target = ROOT / specification['path']
        if not target.exists():
            if args.verify_only:
                raise FileNotFoundError(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(target.name + '.part')
            if partial.exists():
                raise FileExistsError(f'Partial download already exists; inspect it before retrying: {partial}')
            request = urllib.request.Request(specification['url'], headers={'User-Agent': 'AAI-reproducibility/1.0'})
            with urllib.request.urlopen(request, timeout=60) as response, partial.open('xb') as output:
                for block in iter(lambda: response.read(1024 * 1024), b''):
                    output.write(block)
            verify(partial, specification)
            partial.rename(target)
        verify(target, specification)
        print(json.dumps({'dataset': name, 'path': specification['path'], 'bytes': target.stat().st_size,
                          'sha256': specification['sha256'], 'verified': True}), flush=True)


if __name__ == '__main__':
    main()
