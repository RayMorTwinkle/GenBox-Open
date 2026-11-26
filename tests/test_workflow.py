import concurrent.futures
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import ExitStack, closing, contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from genbox_open.client import send
from genbox_open.store import MAX_BYTES, Store
from genbox_open.web import servers

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def running(server):
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
    worker.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        worker.join()


def request(port, path, method="GET"):
    with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=3)) as client:
        client.request(method, path)
        response = client.getresponse()
        return response.status, dict(response.getheaders()), response.read().decode()


class Workflow(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.dir = Path(workspace.name)
        self.store = Store(self.dir / "db")
        self.store.initialize()
        self.file = self.dir / "笔记.md"
        self.file.write_text("# 初稿\n\n- 潮汐\n", encoding="utf-8")

    def test_restore_survives_reopen_and_preserves_history(self):
        original = self.store.publish(self.file)
        slug = original["slug"]
        self.file.write_text("# 再版", encoding="utf-8")
        current = self.store.publish(self.file, slug)
        self.assertEqual((current["path"], current["version"]), (original["path"], 2))
        restored = self.store.restore(slug, 1)
        self.assertEqual(restored["version"], 3)
        reopened = Store(self.store.directory)
        self.assertEqual(reopened.read(slug)["body"], reopened.read(slug, 1)["body"])
        self.assertEqual(reopened.read(slug, 2)["body"], "# 再版")
        self.assertEqual([r["version"] for r in reopened.history(slug)], [3, 2, 1])
        self.assertEqual(reopened.history(slug)[0]["restored_from"], 1)
        self.assertEqual(reopened.items()[0]["version"], 3)

    def test_concurrent_writers_get_distinct_versions(self):
        slug = self.store.publish(self.file)["slug"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            versions = list(pool.map(lambda _: self.store.publish(self.file, slug)["version"], range(8)))
        self.assertEqual(sorted(versions), list(range(2, 10)))
        self.assertEqual(len(self.store.history(slug)), 9)

    def test_invalid_write_rolls_back(self):
        slug = self.store.publish(self.file)["slug"]
        with self.assertRaises(ValueError):
            self.store.publish(self.file, slug, title="  ")
        with self.assertRaises(ValueError):
            self.store.restore(slug, 55)
        self.file.write_bytes(b"x" * (MAX_BYTES + 1))
        with self.assertRaises(ValueError):
            self.store.publish(self.file, slug)
        self.assertEqual(len(self.store.history(slug)), 1)
        self.assertEqual(len(self.store.items()), 1)

    def test_http_pins_content_version_and_preserves_sandbox_headers(self):
        slug = self.store.publish(self.file)["slug"]
        self.store.publish(ROOT / "examples" / "tide.html", slug)
        with ExitStack() as stack:
            ui, raw = stack.enter_context(servers(self.store, 0, 0))
            ui_port, raw_port = [stack.enter_context(running(s)) for s in (ui, raw)]
            status, _, home = request(ui_port, "/")
            self.assertEqual(status, 200)
            self.assertIn(slug, home)
            status, _, page = request(ui_port, f"/s/{slug}")
            self.assertEqual(status, 200)
            self.assertIn('sandbox="allow-scripts"', page)
            self.assertIn(f"http://127.0.0.1:{raw_port}/s/{slug}/raw?v=2", page)
            status, headers, raw_md = request(raw_port, f"/s/{slug}/raw?v=1")
            self.assertEqual(status, 200)
            self.assertIn("<h1>初稿</h1>", raw_md)
            self.assertIn("sandbox allow-scripts;", headers["Content-Security-Policy"])
            self.assertIn(f"frame-ancestors http://127.0.0.1:{ui_port};",
                          headers["Content-Security-Policy"])
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(request(ui_port, f"/s/{slug}/raw")[0], 404)
            self.assertEqual(request(raw_port, "/")[0], 404)
            self.assertEqual(request(ui_port, f"/s/{slug}?v=text")[0], 400)
            self.assertEqual(request(ui_port, f"/s/{slug}?v=3")[0], 404)
            self.assertEqual(request(ui_port, "/", "POST")[0], 501)
            self.assertEqual(request(ui_port, f"/s/{slug}", "HEAD")[2], "")

    def test_svg_content_type_and_exact_body(self):
        svg = self.dir / "sample.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><title>海</title></svg>',
                       encoding="utf-8")
        slug = self.store.publish(svg)["slug"]
        with servers(self.store, 0, 0) as (_, raw), running(raw) as port:
            status, headers, body = request(port, f"/s/{slug}/raw")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/svg+xml; charset=utf-8")
        self.assertEqual(body, svg.read_text(encoding="utf-8"))

    def test_hosted_client_uses_documented_text_contract(self):
        captured = {}

        class Receiver(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                captured.update(path=self.path, auth=self.headers["Authorization"],
                                body=self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(201)
                self.end_headers()
                payload = {"slug": "example", "url": "/c/example", "manage_url": "/test-only"}
                self.wfile.write(json.dumps(payload).encode())

        with HTTPServer(("127.0.0.1", 0), Receiver) as server, running(server) as port:
            result = send(self.file, f"http://127.0.0.1:{port}", "private", "fixture")
        path = urlsplit(captured["path"])
        self.assertEqual((path.path, parse_qs(path.query)),
                         ("/api/v1/contents", {"format": ["md"], "visibility": ["private"]}))
        self.assertEqual(captured["auth"], "Bearer fixture")
        self.assertEqual(captured["body"], self.file.read_bytes())
        self.assertEqual(result, {"slug": "example", "url": "/c/example"})

    def test_install_skill_and_use_its_entrypoint_from_another_directory(self):
        dest = self.dir / "skills"
        program = [sys.executable, str(ROOT / "genbox.py"), "install-skill", "--dir", str(dest)]
        env = dict(os.environ, GENBOX_DATA_DIR=str(self.dir / "skill-library"))
        for _ in range(2):
            subprocess.run(program, cwd=self.dir, env=env, capture_output=True, check=True)
        script = dest / "genbox-open" / "scripts" / "genbox.py"
        result = subprocess.run([sys.executable, str(script), "publish", str(self.file)],
                                cwd=self.dir, env=env, capture_output=True, check=True)
        published = json.loads(result.stdout)
        self.assertEqual(published["version"], 1)
        self.assertEqual(published["url"], "http://127.0.0.1:4310" + published["path"])
        self.assertTrue((dest / "genbox-open" / "SKILL.md").is_file())
