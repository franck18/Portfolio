"""Publish only reviewed files over SFTP, backing up and checking each remote file."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from hosting import connect

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'deployment-manifest.json').read_text(encoding='utf-8'))
client=connect();sftp=client.open_sftp()
backup=root/'backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup.mkdir(parents=True,exist_ok=False)
digest=lambda data:hashlib.sha256(data).hexdigest()
try:
    # Check the full lease before making the first change.
    for name in manifest['files']:
        with sftp.open('www/'+name,'rb') as file:data=file.read()
        if digest(data)!=manifest['baseline'][name]['sha256']:
            raise RuntimeError('Hosting changed since snapshot: '+name)
        target=backup/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print(f'Backed up and verified {len(manifest["files"])} remote files: {backup}',flush=True)
    ordered=sorted(manifest['files'],key=lambda n:(n.endswith('.html'),n in ['index.html','en/index.html'],n))
    published=[]
    try:
        for name in ordered:
            remote='www/'+name
            temporary=remote+'.modern-upload'
            sftp.put(str(root/'site'/name),temporary)
            with sftp.open(temporary,'rb') as file:received=file.read()
            if digest(received)!=digest((root/'site'/name).read_bytes()):
                raise RuntimeError('Upload verification failed: '+name)
            sftp.posix_rename(temporary,remote)
            published.append(name)
        (backup/'published.json').write_text(json.dumps(published,indent=2),encoding='utf-8')
        print(f'Published and verified {len(published)} files. Portrait was not transferred.',flush=True)
    except Exception:
        print('Publication failed; restoring already published files.',flush=True)
        for name in reversed(published):sftp.put(str(backup/name),'www/'+name)
        raise
finally:sftp.close();client.close()
