"""Verify public deployment hashes without submitting forms or changing data."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen
import hashlib
import json

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'deployment-manifest.json').read_text())
def check(name):
    data=urlopen('https://franckraymond.tech/'+name+'?verify=20261106-modern',timeout=30).read()
    expected=(root/'site'/name).read_bytes()
    if hashlib.sha256(data).digest()!=hashlib.sha256(expected).digest():
        raise AssertionError('Public content differs: '+name)
    return name
with ThreadPoolExecutor(max_workers=6) as pool:
    verified=list(pool.map(check,manifest['files']+['franck.webp']))
print(f'Public HTTPS hashes verified for {len(verified)} files, including the unchanged original portrait.')
