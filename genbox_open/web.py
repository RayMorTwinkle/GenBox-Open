"""Two loopback-only read servers for the library and sandboxed content."""
import re
import threading
from contextlib import ExitStack, contextmanager
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

STYLE = Path(__file__).with_name("theme.css").read_bytes()
ITEM_PATH = re.compile(r"/s/([A-Za-z0-9_-]{11})(/raw)?")
FORMAT_LABEL = {"html": "HTML", "markdown": "Markdown", "svg": "SVG"}


def markdown_document(text):
    # Deliberately small grammar. Every text node, including code, is escaped.
    blocks, lines = [], []
    mode = "paragraph"

    def flush():
        if not lines:
            return
        if mode == "code":
            blocks.append("<pre><code>" + "\n".join(lines) + "</code></pre>")
        elif mode == "list":
            blocks.append("<ul>" + "".join("<li>" + s + "</li>" for s in lines) + "</ul>")
        else:
            blocks.append("<p>" + "<br>".join(lines) + "</p>")
        lines.clear()

    for line in text.splitlines():
        if line.startswith("```"):
            flush()
            mode = "paragraph" if mode == "code" else "code"
        elif mode == "code":
            lines.append(escape(line))
        else:
            heading = re.match(r"^(#{1,6})\s+(.+)", line)
            if not line.strip() or heading:
                flush()
                mode = "paragraph"
                if heading:
                    level = len(heading[1])
                    blocks.append(f"<h{level}>{escape(heading[2])}</h{level}>")
                continue
            is_list = line.startswith(("- ", "* "))
            next_mode = "list" if is_list else "paragraph"
            if next_mode != mode:
                flush()
                mode = next_mode
            lines.append(escape(line[2:] if is_list else line))
    flush()
    return """<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Markdown 预览</title>
<style>body{margin:0 auto;max-width:44rem;padding:clamp(1.4rem,4vw,4rem);font:16px/1.85 system-ui,sans-serif;color:#252c29;background:#fffdf7;overflow-wrap:anywhere}h1,h2,h3{line-height:1.35}h1{font-size:clamp(1.7rem,4vw,2.6rem)}h2{margin-top:1.8em}pre{padding:1em;background:#e9eee7;overflow:auto}li::marker{color:#8e4c27}</style>
<body>""" + "\n".join(blocks) + "</body></html>"


def layout(title, body):
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/theme.css"><title>{escape(title)} · GenBox Open</title></head>
<body><header><a class="brand" href="/"><span class="mark" aria-hidden="true"></span>GenBox<span>Open</span></a>
<span class="local">本地工作台</span></header><main>{body}</main></body></html>"""


def library(store):
    cards = []
    for item in store.items():
        slug, title = item["slug"], escape(item["title"])
        cards.append(f"""<a class="card" href="/s/{slug}"><span class="tag">{FORMAT_LABEL[item['format']]}</span>
<h2>{title}</h2><footer><code>/{slug}</code><span>版本 {item['version']} →</span></footer></a>""")
    count = len(cards)
    content = '<section class="grid">' + "".join(cards) + "</section>" if cards else """
<section class="empty"><h2>发布第一个文件</h2>
<p>在项目目录运行此命令，然后刷新本页。</p><pre>python3 genbox.py publish examples/field-notes.md</pre></section>"""
    return layout("作品库", f'<div class="intro"><h1>作品库</h1><p>{count} 个作品</p></div>{content}')


def preview(item, history, content_origin):
    slug, version = item["slug"], item["version"]
    title = escape(item["title"])
    options = []
    for rev in history:
        v = rev["version"]
        label = f'版本 {v}'
        if rev["restored_from"]:
            label += f' · 恢复自 v{rev["restored_from"]}'
        attrs = ' aria-current="page"' if v == version else ""
        options.append(f'<li><a{attrs} href="/s/{slug}?v={v}">{label}</a></li>')
    return layout(item["title"], f"""<a class="back" href="/">← 作品库</a>
<div class="intro"><div><span class="tag">{FORMAT_LABEL[item['format']]}</span><h1>{title}</h1></div>
<a class="permalink" href="/s/{slug}?v={version}">本版链接 ↗</a></div>
<div class="stage"><iframe title="{title}" sandbox="allow-scripts" referrerpolicy="no-referrer"
src="{content_origin}/s/{slug}/raw?v={version}"></iframe></div>
<nav aria-label="版本历史"><strong>历史版本</strong><ul>{''.join(options)}</ul></nav>""")


def version_from(query):
    if not query:
        return None
    fields = parse_qs(query, keep_blank_values=True, max_num_fields=2)
    values = fields.get("v", [])
    if set(fields) != {"v"} or len(values) != 1 or not re.fullmatch(r"[1-9][0-9]{0,17}", values[0]):
        raise ValueError("版本号无效。")
    return int(values[0])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def reply(self, status, data, mime="text/plain; charset=utf-8"):
        body = data.encode("utf-8") if isinstance(data, str) else data
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", self.server.policy)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        server = self.server
        if self.headers.get("Host") != f"127.0.0.1:{server.server_port}":
            return self.reply(400, "请使用启动时列出的本机地址。")
        url = urlsplit(self.path)
        if server.role == "library" and url.path == "/":
            return self.reply(200, library(server.store), "text/html; charset=utf-8")
        if server.role == "library" and url.path == "/theme.css":
            return self.reply(200, STYLE, "text/css; charset=utf-8")
        match = ITEM_PATH.fullmatch(url.path)
        if not match or bool(match[2]) != (server.role == "content"):
            return self.reply(404, "找不到这个页面。")
        try:
            version = version_from(url.query)
        except ValueError:
            return self.reply(400, "版本号无效。")
        item = server.store.read(match[1], version)
        if item is None:
            return self.reply(404, "找不到这个作品或版本。")
        if server.role == "library":
            page = preview(item, server.store.history(match[1]), server.content_origin)
            return self.reply(200, page, "text/html; charset=utf-8")
        if item["format"] == "markdown":
            return self.reply(200, markdown_document(item["body"]), "text/html; charset=utf-8")
        mime = "image/svg+xml" if item["format"] == "svg" else "text/html"
        return self.reply(200, item["body"], mime + "; charset=utf-8")

    do_HEAD = do_GET

    def send_error(self, code, message=None, explain=None):
        self.reply(code, "本地 HTTP 服务仅提供作品预览。")


@contextmanager
def servers(store, port, content_port):
    with ExitStack() as stack:
        ui, raw = [stack.enter_context(ThreadingHTTPServer(("127.0.0.1", p), Handler))
                   for p in (port, content_port)]
        ui.role, raw.role = "library", "content"
        ui.store = raw.store = store
        ui_origin = f"http://127.0.0.1:{ui.server_port}"
        ui.content_origin = f"http://127.0.0.1:{raw.server_port}"
        ui.policy = (f"default-src 'none'; style-src 'self'; frame-src {ui.content_origin}; "
                     "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        raw.policy = (f"sandbox allow-scripts; frame-ancestors {ui_origin}; default-src 'none'; "
                      "script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; "
                      "base-uri 'none'; form-action 'none'")
        yield ui, raw


def serve(store, port, content_port):
    with servers(store, port, content_port) as (ui, raw):
        worker = threading.Thread(target=raw.serve_forever, daemon=True)
        worker.start()
        print(f"作品库 http://127.0.0.1:{ui.server_port}/\n内容端 {ui.content_origin}", flush=True)
        try:
            ui.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            raw.shutdown()
            worker.join()
