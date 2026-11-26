"""Client for GenBox's documented text-upload API."""
import http.client
import json
from urllib.parse import urlencode, urlsplit

from .store import read_source


def send(path, base_url, visibility, token):
    origin = urlsplit(base_url)
    if not origin.hostname or origin.username is not None or origin.password is not None:
        raise ValueError("请输入不带凭据的服务地址。")
    if origin.path not in ("", "/") or origin.query or origin.fragment:
        raise ValueError("服务地址应只包含协议、主机名与可选端口。")
    local = origin.hostname in {"127.0.0.1", "::1", "localhost"}
    if origin.scheme != "https" and not (local and origin.scheme == "http"):
        raise ValueError("远端须使用 HTTPS，本机回环地址可用 HTTP。")
    if not token:
        raise ValueError("请先在当前进程环境设置 GENBOX_TOKEN。")
    if not token.isascii() or not all(33 <= ord(char) <= 126 for char in token):
        raise ValueError("GENBOX_TOKEN 包含无效字符。")
    format_name, body = read_source(path)
    params = urlencode({"format": "md" if format_name == "markdown" else format_name,
                        "visibility": visibility})
    transport = http.client.HTTPSConnection if origin.scheme == "https" else http.client.HTTPConnection
    conn = transport(origin.hostname, origin.port, timeout=20)
    try:
        conn.request("POST", "/api/v1/contents?" + params, body=body.encode("utf-8"),
                     headers={"Content-Type": "text/plain; charset=utf-8",
                              "Authorization": "Bearer " + token})
        response = conn.getresponse()
        if not 200 <= response.status < 300:
            raise ValueError(f"托管服务返回 HTTP {response.status}。")
        raw = response.read(64 * 1024 + 1)
        if len(raw) > 64 * 1024:
            raise ValueError("服务响应过大。")
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not all(isinstance(payload.get(k), str)
                                                   for k in ("slug", "url")):
            raise ValueError("服务响应缺少短链字段。")
        return {k: payload[k] for k in ("slug", "url", "expires_at") if k in payload}
    finally:
        conn.close()
