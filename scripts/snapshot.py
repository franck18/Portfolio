"""Read current public assets and inventory the authorized OVH hosting."""
import ftplib
import json
import os
import ssl
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]

def connect():
    client = ftplib.FTP_TLS(context=ssl.create_default_context(), timeout=40)
    client.connect(os.environ['SITE_FTP_HOST'])
    try:
        client.login(os.environ['SITE_FTP_USER'], os.environ['SITE_FTP_PASSWORD'])
        client.prot_p()
    except ftplib.error_perm as exc:
        if 'security scheme is not implemented' not in str(exc): raise
        client.close()
        client=ftplib.FTP(os.environ['SITE_FTP_HOST'],timeout=40)
        client.login(os.environ['SITE_FTP_USER'], os.environ['SITE_FTP_PASSWORD'])
    client.cwd('/www')
    # OVH's shared control host redirects data transfers to another IPv4 host.
    client.trust_server_pasv_ipv4 = True
    return client

class Assets(HTMLParser):
    def __init__(self):
        super().__init__(); self.paths=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('link','script','img'):
            ref=attrs.get('src') or attrs.get('href','')
            if ref: self.paths.append(ref)

def public_snapshot():
    target=ROOT/'baseline'
    pending=['index.html','en/index.html','projets.html','profil.html','experience.html']
    done=set()
    while pending:
        name=pending.pop(0)
        if name in done: continue
        done.add(name)
        try:
            data=urlopen('https://franckraymond.tech/'+name,timeout=30).read()
            path=target/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
            print(name,len(data),flush=True)
            if name.endswith('.html'):
                parser=Assets(); parser.feed(data.decode())
                for ref in parser.paths:
                    url=urlparse(urljoin('https://franckraymond.tech/'+name,ref))
                    if url.netloc=='franckraymond.tech': pending.append(url.path.lstrip('/'))
        except Exception as exc: print('Failed',name,type(exc).__name__,flush=True)

if __name__=='__main__':
    import sys
    if '--ftp' in sys.argv:
        ftp=connect()
        listing=list(ftp.mlsd())
        (ROOT/'baseline'/'ftp-root-inventory.json').write_text(json.dumps(listing,indent=2))
        print('Authenticated to OVH. Root entries:',len(listing))
        print([name for name,facts in listing if facts.get('type')=='dir'])
        ftp.quit()
    else: public_snapshot()
