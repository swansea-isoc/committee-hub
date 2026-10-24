"""Reproduce the supplied public V2 preview; never read the private setup bundle."""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
PAYLOAD_SHA256 = '17cbc24168fa075988770e06141ff878b0a2d0753767686c7d2090f8f605b8d7'
FILES = {'index.html', 'demo.html', 'hub.js', 'hub.css', 'config.js', '.nojekyll'}
parts = sorted((ROOT / 'tools' / 'preview-payload').glob('*.txt'))
if len(parts) != 6:
    raise RuntimeError('Expected six parts of the public preview bundle')
compressed = base64.b64decode(''.join(p.read_text().strip() for p in parts), validate=True)
if hashlib.sha256(compressed).hexdigest() != PAYLOAD_SHA256:
    raise RuntimeError('Public preview checksum does not match')
files = json.loads(gzip.decompress(compressed))
if set(files) != FILES:
    raise RuntimeError('Unexpected files in the preview bundle')
SITE.mkdir(exist_ok=True)
for name, content in files.items():
    if not isinstance(content, str):
        raise TypeError('Expected text source')
    (SITE / name).write_text(content, encoding='utf-8')
# These are read-only copies of the user's previously supplied artwork at a pinned commit.
# No API writes, settings changes or commits are made to either discount repository.
base = 'https://raw.githubusercontent.com/abubakrmajid1/isoc-discounts/db63f2bfbd4ae61fc31b10113c6e0604f5a5e4a2/'
images = {
    'favicon.png': '181f296f21016aa4c46c1a8746d24ccb45d28f2dd6059d9962a6b038a41c231a',
    'isoc-emblem.png': 'e3f4ca61fad5c18f0d76bac261ed2437cc0aa8678ee0cbefa1367d633f209af2',
    'isoc-logo.png': '6022167b192b1c4aaaa23a11d279392dd382baa19a0779e98166676a93bb7841',
}
assets = SITE / 'assets'
assets.mkdir(exist_ok=True)
for name, expected in images.items():
    target = assets / name
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        continue
    request = urllib.request.Request(base + name, headers={'User-Agent': 'Swansea-ISOC-Committee-Hub'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError('Artwork checksum mismatch: ' + name)
    target.write_bytes(data)
(SITE / 'robots.txt').write_text('User-agent: *\nDisallow: /\n')
print('Imported six public source files and three verified artwork files.')
