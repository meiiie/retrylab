"""Verify a bounded set of raw CODE snapshots against dated event provenance."""
import ast
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import tokenize

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
HEADER=re.compile(r'^==[ \t]*(TEST|SUBMITION)[ \t]*\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\)[ \t]*\r?$',re.M)
SECTION=re.compile(r'^-- (CODE|EXECUTION TIME|OUTPUT|ERROR|GRADE|TEST CASE \d+):[ \t]*\r?$',re.M)


def norm_tokens(code):
    result=[]
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type in (tokenize.COMMENT,tokenize.NL,tokenize.ENCODING,tokenize.ENDMARKER):
                continue
            value='' if t.type in (tokenize.INDENT,tokenize.DEDENT,tokenize.NEWLINE) else t.string
            result.append((t.type,value))
        return hashlib.sha256(repr(result).encode()).hexdigest(),True,len(result)
    except (tokenize.TokenError,IndentationError,SyntaxError):
        return None,False,len(result)


def main():
    examples=json.loads((OUT/'selected_examples.json').read_text(encoding='utf-8'))
    wanted={s['source_path'] for e in examples.values() for s in (e['first'],e['last'])}
    records={}
    with gzip.open(ROOT/'data/raw/codebench/cb_dataset_2016_1_v1.81.tar.gz','rb') as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
        for member in tar:
            if member.name not in wanted:
                continue
            text=tar.extractfile(member).read().decode('utf-8')
            headers=list(HEADER.finditer(text))
            for index,h in enumerate(headers):
                body=text[h.end():headers[index+1].start() if index+1<len(headers) else len(text)]
                sections=list(SECTION.finditer(body))
                code_sections=[i for i,s in enumerate(sections) if s.group(1)=='CODE']
                assert len(code_sections)==1
                pos=code_sections[0]
                code=body[sections[pos].end():sections[pos+1].start() if pos+1<len(sections) else len(body)].strip('\r\n')
                token_hash,token_valid,token_count=norm_tokens(code)
                try:
                    tree=ast.parse(code)
                    ast_hash=hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest()
                except (SyntaxError,ValueError,RecursionError):
                    ast_hash=None
                records[(member.name,index)]={'event_type':h.group(1),'timestamp':h.group(2),'CODE_sections':len(code_sections),
                    'code_chars':len(code),'code_sha256':hashlib.sha256(code.encode()).hexdigest(),
                    'record_sha256':hashlib.sha256(body.encode()).hexdigest(),'token_hash':token_hash,'token_valid':token_valid,
                    'token_count':token_count,'ast_hash':ast_hash}
            wanted.remove(member.name)
            if not wanted:
                break
    assert not wanted
    verified={}
    for category,example in examples.items():
        pair=[]
        for side in ('first','last'):
            expected=example[side]
            actual=records[(expected['source_path'],expected['file_event_index'])]
            for key in ('event_type','timestamp','code_sha256','record_sha256','code_chars'):
                assert actual[key]==expected[key],(category,side,key)
            pair.append(actual)
        a,b=pair
        assert a['timestamp']<b['timestamp']<example['target_timestamp']
        verified[category]={'source_path':example['first']['source_path'],
                            'first_event_index':example['first']['file_event_index'],'last_event_index':example['last']['file_event_index'],
                            'first_timestamp':a['timestamp'],'last_timestamp':b['timestamp'],'future_target_timestamp':example['target_timestamp'],
                            'raw_record_hashes_match_processed':True,'raw_code_hashes_match_processed':True,
                            'both_full_CODE_sections_present':True,'text_changed':a['code_sha256']!=b['code_sha256'],
                            'both_tokenizable':a['token_valid'] and b['token_valid'],
                            'normalized_tokens_changed':a['token_hash']!=b['token_hash'] if a['token_valid'] and b['token_valid'] else None,
                            'both_ast_parseable':a['ast_hash'] is not None and b['ast_hash'] is not None,
                            'normalized_AST_changed':a['ast_hash']!=b['ast_hash'] if a['ast_hash'] and b['ast_hash'] else None,
                            'number_of_SUBMITION_snapshots_in_episode':example['submissions'],'distinct_code_hashes_in_episode':example['distinct_code_hashes']}
    result={'status':'Bounded raw verification only; no raw code text exported or executed.',
            'examples':verified,'scope':'These four examples are deliberately selected schema checks, not a representative estimate of normalized token/AST change rates.',
            'final_codes_py_used':False,'editor_keystroke_reconstruction_used':False}
    (OUT/'raw_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
