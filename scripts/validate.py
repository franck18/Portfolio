"""Check content preservation and deployment scope before publication."""
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'deployment-manifest.json').read_text(encoding='utf-8'))
checks=0
for name in manifest['files']:
    old=(root/'baseline'/name).read_text(encoding='utf-8')
    new=(root/'site'/name).read_text(encoding='utf-8')
    if not name.endswith('.html'):continue
    before=BeautifulSoup(old,'html.parser');after=BeautifulSoup(new,'html.parser')
    for tag,attribute in [('a','href'),('img','src'),('script','src'),('form','action')]:
        assert Counter(n.get(attribute) for n in before.select(tag))==Counter(n.get(attribute) for n in after.select(tag)),(name,tag,attribute)
        checks+=1
    assert len(after.select('h1'))==len(before.select('h1')),(name,'h1 count')
    assert Counter(n.get('id') for n in before.select('[id]'))==Counter(n.get('id') for n in after.select('[id]')),(name,'IDs')
    checks+=2
    if name not in ['index.html','en/index.html']:
        normalized=re.sub(r'(editorial(?:-tokens)?\.css)\?v=[^"\s>]+',r'\1?v=VERSION',old)
        changed=re.sub(r'(editorial(?:-tokens)?\.css)\?v=[^"\s>]+',r'\1?v=VERSION',new)
        assert normalized==changed,(name,'unexpected content modification')
        checks+=1
assert (root/'site/franck.webp').read_bytes()==(root/'baseline/franck.webp').read_bytes()
assert 'franck.webp' not in manifest['files'],'Portrait must never be uploaded or replaced'
checks+=2
print(f'{checks} preservation checks passed across {len(manifest["files"])} deployment files. Original portrait unchanged and excluded from deployment.')
