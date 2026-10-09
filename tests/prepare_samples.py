"""Restore test fixtures from the bundled HTML without network access.
Run before verify.py when using the source-only package. Requires Pillow.
"""
from pathlib import Path
import base64,json,re
from PIL import Image
p=Path(__file__).resolve().parents[1]
s=p.joinpath('index.html').read_text(encoding='utf-8')
data=json.loads(re.search(r'<script id="samplesData" type="application/json">(.*?)</script>',s,re.S).group(1))
p.joinpath('samples').mkdir(exist_ok=True)
p.joinpath('evidence').mkdir(exist_ok=True)
for name,url in data.items():
 target=p/'samples'/(name+'.png')
 if not target.exists():target.write_bytes(base64.b64decode(url.split(',',1)[1]))
print('Test fixtures restored from embedded samples; no network used.')
