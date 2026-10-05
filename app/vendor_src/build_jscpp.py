"""Rebuild app/static/vendor/jscpp/jscpp.js: the JSCPP 2.0.9 C interpreter (MIT) bundled for a browser Web Worker.

The app's Content-Security-Policy forbids eval. JSCPP uses eval only to decode C escape sequences inside character and
string literals and to implement system(); this script replaces those calls with a plain decoder / an error before
bundling, then records hashes in manifest.json.

Requires Node.js with npm and network access. Usage:  python -X utf8 app/vendor_src/build_jscpp.py <empty work dir>
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'app/static/vendor/jscpp'
VERSION = '2.0.9'
TARBALL_SHA256 = 'fa83b3ef9eefb1ee496eb06a70bbb96012d9004bf4529313001fd2ab07d629f6'

DECODER = r"""
function __cEscape(t) {
  var m = t.slice(1), c = m.charAt(0);
  var simple = { n: '\n', t: '\t', r: '\r', a: '\x07', b: '\b', f: '\f', v: '\v', '\\': '\\', "'": "'", '"': '"', '?': '?' };
  if (c === 'x') return String.fromCharCode(parseInt(m.slice(1), 16));
  if (c === 'u' || c === 'U') return String.fromCodePoint(parseInt(m.slice(1), 16));
  if (/[0-7]/.test(c)) return String.fromCharCode(parseInt(m, 8));
  if (Object.prototype.hasOwnProperty.call(simple, c)) return simple[c];
  return c;
}
"""

PATCHES = {
    'lib/ast.js': [
        ("return eval('\"\\\\u' + a.join('') + '\"');", "return __cEscape('\\\\u' + a.join(''));"),
        ("return eval('\"\\\\U' + a.join('') + b.join('') + '\"');", "return __cEscape('\\\\U' + a.join('') + b.join(''));"),
        ("return eval('\"' + a + b +'\"');", "return __cEscape(a + b);"),
        ("return eval(ret);", "return __cEscape(ret.slice(1, -1));"),
        ("return eval('\"'+a+b.join('')+'\"');", "return __cEscape(a + b.join(''));"),
    ],
    'lib/prepast.js': [
        ("return eval('\"' + a + b +'\"');", "return __cEscape(a + b);"),
        ("return eval(ret);", "return __cEscape(ret.slice(1, -1));"),
        ("return eval('\"'+a+b.join('')+'\"');", "return __cEscape(a + b.join(''));"),
    ],
    'lib/includes/cstdlib.js': [
        ("const ret = eval(s);", "const ret = (function () { throw new Error('system() is not supported'); })();"),
    ],
}
SHIMS = {
    'util.js': "module.exports = { inspect: function (v) { try { return JSON.stringify(v); } catch (e) { return String(v); } } };\n",
    'stream.js': "function Stream() {}\nmodule.exports = { Stream: Stream };\n",
}


def run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, shell=(sys.platform == 'win32'))


def main():
    work = Path(sys.argv[1]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    run(['npm', 'init', '-y'], work)
    run(['npm', 'install', '--no-audit', '--no-fund', f'JSCPP@{VERSION}', 'esbuild@0.24.0'], work)
    run(['npm', 'pack', f'JSCPP@{VERSION}'], work)
    actual = hashlib.sha256((work / f'JSCPP-{VERSION}.tgz').read_bytes()).hexdigest()
    if actual != TARBALL_SHA256:
        raise SystemExit(f'JSCPP tarball hash mismatch: {actual}')
    pkg = work / 'node_modules/JSCPP'
    for rel, pairs in PATCHES.items():
        path = pkg / rel
        text = path.read_text(encoding='utf-8')
        for old, new in pairs:
            if old not in text:
                raise SystemExit(f'patch target not found in {rel}: {old}')
            text = text.replace(old, new)
        if rel != 'lib/includes/cstdlib.js':
            text = DECODER + text
        if 'eval(' in text:
            raise SystemExit(f'eval left in {rel}')
        path.write_text(text, encoding='utf-8')
    shims = work / 'shims'
    shims.mkdir(exist_ok=True)
    for name, body in SHIMS.items():
        (shims / name).write_text(body, encoding='utf-8')
    OUT.mkdir(parents=True, exist_ok=True)
    run(['npx', 'esbuild', 'node_modules/JSCPP/lib/commonjs.js', '--bundle', '--format=iife', '--global-name=JSCPP',
         '--platform=browser', '--minify', '--alias:util=./shims/util.js', '--alias:stream=./shims/stream.js',
         f'--outfile={OUT / "jscpp.js"}'], work)
    bundle = (OUT / 'jscpp.js').read_text(encoding='utf-8')
    if 'eval(' in bundle:
        raise SystemExit('eval found in the bundle')
    licenses = {'JSCPP': 'node_modules/JSCPP/LICENSE', 'lodash': 'node_modules/lodash/LICENSE',
                'printf': 'node_modules/printf/LICENSE'}
    for name, rel in licenses.items():
        shutil.copyfile(work / rel, OUT / f'LICENSE-{name}.txt')
    files = sorted(p for p in OUT.iterdir() if p.name != 'manifest.json')
    manifest = {'package': 'JSCPP', 'version': VERSION, 'tarball_sha256': TARBALL_SHA256,
                'patches': 'eval-free C escape decoding; system() disabled; util/stream shims',
                'files': [{'name': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'built {OUT / "jscpp.js"} ({len(bundle)} bytes)')


if __name__ == '__main__':
    main()
