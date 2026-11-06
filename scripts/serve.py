"""Preview changed files locally, with read-only fallback to the current public site."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
import mimetypes

root=Path(__file__).resolve().parents[1]/'site'

class Preview(SimpleHTTPRequestHandler):
    def do_GET(self):
        path=Path(self.translate_path(self.path))
        if path.exists(): return super().do_GET()
        try:
            response=urlopen('https://franckraymond.tech'+self.path,timeout=20)
            data=response.read();self.send_response(200)
            self.send_header('Content-Type',response.headers.get('Content-Type','application/octet-stream'))
            self.end_headers();self.wfile.write(data)
        except HTTPError as exc: self.send_error(exc.code)
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        super().end_headers()

ThreadingHTTPServer(('127.0.0.1',8765),partial(Preview,directory=str(root))).serve_forever()
