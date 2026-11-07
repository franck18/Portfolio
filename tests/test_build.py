"""Exercise snapshot/build cycles locally, without hosting credentials or uploads."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
PHOTO_FILES = {
    'franck.webp': b'original-webp-photo\x00\xff',
    'images/franck-original.jpg': b'original-jpeg-photo\x00\xff',
}
LEGACY_FR = '''<!doctype html><html><head>
<link href="assets/editorial.css?v=old" rel="stylesheet"></head><body>
<a class="brand-logo" href="/">FR</a>
<div class="editorial-name"><h1>Franck Raymond</h1></div>
<div class="refresh-intro"><p class="refresh-role">Ancien rôle</p></div>
<img src="franck.webp" srcset="franck.webp 1x, images/franck-original.jpg 2x">
<section id="projets"><h2 id="projets-title">Trois réalisations à explorer</h2>
<article class="refresh-project"><h3>VMware</h3></article>
<article class="refresh-project"><h3>Extreme Networks</h3></article>
<article class="refresh-project"><h3>Ansible</h3></article>
<div class="refresh-library-links">
<a href="schema-reseau.html">Démonstrateur réseau</a>
<a href="projets.html">Toute la bibliothèque</a></div></section>
</body></html>'''
LEGACY_EN = '''<!doctype html><html><body>
<a class="brand-logo" href="/en/index.html">FR</a>
<div class="editorial-name"><h1>Franck Raymond</h1></div>
<div class="home-hero-content"><p>Systems and networks</p></div>
<img src="../franck.webp"><h2 id="projets-title">Three projects to explore</h2>
</body></html>'''


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ('scripts', 'src'):
            shutil.copytree(ROOT / directory, self.root / directory)
        self.baseline = self.root / 'baseline'
        self.site = self.root / 'site'

    def snapshot(self, source=None):
        if self.baseline.exists():
            shutil.rmtree(self.baseline)
        if source is None:
            (self.baseline / 'en').mkdir(parents=True)
            (self.baseline / 'assets').mkdir()
            (self.baseline / 'index.html').write_text(LEGACY_FR, encoding='utf-8')
            (self.baseline / 'en/index.html').write_text(LEGACY_EN, encoding='utf-8')
            (self.baseline / 'assets/editorial.css').write_text('/* original CSS */', encoding='utf-8')
        else:
            shutil.copytree(source, self.baseline)
        for name, data in PHOTO_FILES.items():
            path = self.baseline / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        manifest = {
            str(path.relative_to(self.baseline)): {
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in self.baseline.rglob('*')
            if path.is_file() and path.name != 'manifest.json'
        }
        (self.baseline / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')

    def run_script(self, name):
        result = subprocess.run(
            [sys.executable, str(self.root / 'scripts' / name)],
            cwd=self.root, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_home_structure(self):
        french = BeautifulSoup((self.site / 'index.html').read_text(encoding='utf-8'), 'html.parser')
        projects = french.select('.refresh-project')
        self.assertEqual(len(projects), 3)
        for project, expected in zip(projects, ('01', '02', '03')):
            self.assertEqual([n.get_text() for n in project.select('.project-number')], [expected])
        holders = french.select('.modern-section-head')
        self.assertEqual(len(holders), 1)
        self.assertEqual(len(holders[0].select('#projets-title')), 1)
        self.assertEqual([n['href'] for n in holders[0].select('a')], ['projets.html'])
        self.assertEqual([n['href'] for n in french.select('.refresh-library-links a')], ['schema-reseau.html'])
        for name in ('index.html', 'en/index.html'):
            soup = BeautifulSoup((self.site / name).read_text(encoding='utf-8'), 'html.parser')
            self.assertEqual(len(soup.select('#projets-title')), 1)
            self.assertEqual(len(soup.select('.editorial-name')), 1)
            for logo in soup.select('.brand-logo'):
                self.assertEqual([n.get_text() for n in logo.select('.brand-name')], ['Franck Raymond'])
        manifest = json.loads((self.root / 'deployment-manifest.json').read_text())
        for name, data in PHOTO_FILES.items():
            self.assertEqual((self.site / name).read_bytes(), data)
            self.assertNotIn(name, manifest['files'])

    def test_rebuild_from_modernized_snapshot_preserves_html_structure(self):
        self.snapshot()
        self.run_script('build.py')
        self.assert_home_structure()
        expected = {name: (self.site / name).read_bytes() for name in ('index.html', 'en/index.html')}
        for cycle in range(2):
            with self.subTest(cycle=cycle + 2):
                self.snapshot(self.site)
                shutil.rmtree(self.site)
                self.run_script('build.py')
                self.assert_home_structure()
                for name, data in expected.items():
                    self.assertEqual((self.site / name).read_bytes(), data)
                self.run_script('validate.py')

    def test_rebuild_does_not_append_the_modern_styles_again(self):
        self.snapshot()
        self.run_script('build.py')
        expected = (self.site / 'assets/editorial.css').read_bytes()
        self.snapshot(self.site)
        self.run_script('build.py')
        self.assertEqual((self.site / 'assets/editorial.css').read_bytes(), expected)

    def test_current_portfolio_snapshot_survives_two_rebuilds(self):
        self.snapshot(ROOT / 'franckraymond-tech')
        expected = None
        for cycle in range(2):
            with self.subTest(cycle=cycle + 1):
                self.run_script('build.py')
                self.assert_home_structure()
                self.run_script('validate.py')
                actual = {str(p.relative_to(self.site)): p.read_bytes()
                          for p in self.site.rglob('*') if p.is_file()}
                if expected is not None:
                    self.assertEqual(actual, expected)
                    manifest = json.loads((self.root / 'deployment-manifest.json').read_text())
                    self.assertEqual(manifest['files'], [])
                expected = actual
                self.snapshot(self.site)
                shutil.rmtree(self.site)


if __name__ == '__main__':
    unittest.main()
