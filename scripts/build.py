"""Build a minimal deployment overlay from the verified production snapshot."""
import hashlib
import json
import re
import shutil
from pathlib import Path
from bs4 import BeautifulSoup
from menu_labels import rename_menu

root=Path(__file__).resolve().parents[1]
baseline=root/'baseline'; site=root/'site'
site.mkdir(exist_ok=True)
for path in baseline.rglob('*'):
    if path.is_file() and path.suffix not in ('.json',):
        target=site/path.relative_to(baseline);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)

assets=site/'assets';assets.mkdir(exist_ok=True)
(assets/'editorial-tokens.css').write_bytes((root/'src/tokens.css').read_bytes())
(assets/'editorial.css').write_text((baseline/'assets/editorial.css').read_text(encoding='utf-8')+'\n'+(root/'src/modern.css').read_text(encoding='utf-8'),encoding='utf-8')

for name in ['index.html','en/index.html']:
    path=site/name
    soup=BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser')
    title=soup.select_one('.editorial-name')
    intro=soup.select_one('.refresh-intro') or soup.select_one('.home-hero-content')
    intro.insert(0,title.extract())
    if name=='index.html':
        role=soup.select_one('.refresh-role')
        role.clear();role.append('Systèmes & réseaux.');role.append(soup.new_tag('br'))
        accent=soup.new_tag('span',attrs={'class':'role-accent'});accent.string='Des projets, des preuves.';role.append(accent)
        for i,project in enumerate(soup.select('.refresh-project'),1):
            number=soup.new_tag('span',attrs={'class':'project-number','aria-hidden':'true'});number.string=f'{i:02d}'
            project.insert(0,number)
        heading=soup.select_one('#projets-title');holder=soup.new_tag('div',attrs={'class':'modern-section-head'})
        heading.wrap(holder)
        link=soup.select_one('.refresh-library-links a')
        holder.append(link.extract())
    # Keep the original photograph URL and bytes. No generated portrait is used.
    for logo in soup.select('.brand-logo'):
        label=soup.new_tag('span',attrs={'class':'brand-name','aria-hidden':'true'});label.string='Franck Raymond';logo.append(label)
    path.write_text(str(soup),encoding='utf-8')

# Shared styles are used on the case studies too. Refresh only their resource URLs.
version='20261106-modern'
changed=[]
manifest=json.loads((baseline/'manifest.json').read_text(encoding='utf-8'))
for path in site.rglob('*.html'):
    text=path.read_text(encoding='utf-8')
    text=re.sub(r'(editorial(?:-tokens)?\.css)\?v=[^"\s>]+',rf'\1?v={version}',text)
    text=rename_menu(text.encode('utf-8')).decode('utf-8')
    path.write_text(text,encoding='utf-8')
for name,record in manifest.items():
    path=site/name
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
        changed.append(name)
(root/'deployment-manifest.json').write_text(json.dumps({'files':changed,'baseline':{n:manifest[n] for n in changed}},indent=2),encoding='utf-8')
print(f'Built {len(changed)} changed files. Portrait preserved:',(site/'franck.webp').read_bytes()==(baseline/'franck.webp').read_bytes())
