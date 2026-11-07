"""Back up current HTML and shared styling before editing any hosting files."""
import hashlib
import json
import stat
from pathlib import Path
from hosting import connect

root=Path(__file__).resolve().parents[1]
baseline=root/'baseline'
client=connect()
sftp=client.open_sftp()
pending=['www']
paths=[]
try:
    while pending:
        directory=pending.pop()
        for item in sftp.listdir_attr(directory):
            path=f'{directory}/{item.filename}'
            if stat.S_ISDIR(item.st_mode):
                if path in ['www/en','www/pages','www/en/pages']:
                    pending.append(path)
            elif item.filename.endswith('.html'):
                paths.append(path.removeprefix('www/'))
    records={}
    shared=['assets/editorial.css','assets/editorial-tokens.css','assets/editorial-theme.js']
    for path in paths+shared:
        target=baseline/path;target.parent.mkdir(parents=True,exist_ok=True)
        sftp.get('www/'+path,str(target))
        data=target.read_bytes()
        records[path]={'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)}
    (baseline/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(f'Backed up {len(paths)} HTML files and {len(shared)} shared assets.')
finally:
    sftp.close();client.close()
