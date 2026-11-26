import argparse
import http.client
import json
import os
import sqlite3
import sys
from pathlib import Path

from .client import send
from .store import Store
from .web import serve


def parser():
    cli = argparse.ArgumentParser(description="GenBox Open · 本地作品库")
    cli.add_argument("--data-dir", default=os.getenv("GENBOX_DATA_DIR", "~/.genbox-open"),
                     help="本地作品目录（默认 ~/.genbox-open）")
    cmds = cli.add_subparsers(dest="cmd", required=True)
    pub = cmds.add_parser("publish", help="发布或更新一份本地作品")
    pub.add_argument("file", type=Path)
    pub.add_argument("--replace", metavar="SLUG", help="向已有短链追加版本")
    pub.add_argument("--title", help="作品标题")
    cmds.add_parser("list", help="列出本地作品")
    history = cmds.add_parser("history", help="查看版本记录")
    history.add_argument("slug")
    restore = cmds.add_parser("restore", help="将历史版本追加到当前短链")
    restore.add_argument("slug")
    restore.add_argument("version", type=int)
    for cmd in (pub, restore):
        cmd.add_argument("--port", type=int, default=4310, help="输出链接使用的作品库端口")
    web = cmds.add_parser("serve", help="在本机打开只读预览服务")
    web.add_argument("--port", type=int, default=4310, help="作品库端口")
    web.add_argument("--content-port", type=int, default=4311, help="独立内容端口")
    upload = cmds.add_parser("send", help="发送到指定的 GenBox 托管服务")
    upload.add_argument("file", type=Path)
    upload.add_argument("--base-url", required=True, help="目标 GenBox 服务地址")
    upload.add_argument("--visibility", choices=("private", "public"), default="private")
    install = cmds.add_parser("install-skill", help="把本仓的技能链接到本机 Agent 目录")
    install.add_argument("--dir", type=Path, default=Path("~/.agents/skills"), help="技能目录")
    return cli


def install_skill(directory):
    source = Path(__file__).resolve().parents[1] / "skill" / "genbox-open"
    destination = directory.expanduser().resolve() / "genbox-open"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink() and destination.resolve() == source:
        return {"skill": str(destination)}
    if destination.is_symlink() or destination.exists():
        raise ValueError("目标已存在。可用 --dir 选择另一个技能目录。")
    destination.symlink_to(source, target_is_directory=True)
    return {"skill": str(destination)}


def main():
    args = parser().parse_args()
    try:
        if args.cmd == "install-skill":
            result = install_skill(args.dir)
        elif args.cmd == "send":
            result = send(args.file, args.base_url, args.visibility, os.getenv("GENBOX_TOKEN"))
        else:
            ports = [getattr(args, name) for name in ("port", "content_port") if hasattr(args, name)]
            if any(port < 1 or port > 65535 for port in ports):
                raise ValueError("端口范围为 1 至 65535。")
            store = Store(args.data_dir)
            store.initialize()
            if args.cmd == "serve":
                serve(store, args.port, args.content_port)
                return 0
            if args.cmd == "publish":
                result = store.publish(args.file, args.replace, args.title)
            elif args.cmd == "history":
                result = store.history(args.slug)
            elif args.cmd == "restore":
                result = store.restore(args.slug, args.version)
            else:
                result = store.items()
            if args.cmd in ("publish", "restore"):
                origin = f"http://127.0.0.1:{args.port}"
                result.update(url=origin + result["path"], revision_url=origin + result["revision_path"])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error, http.client.HTTPException, OverflowError) as exc:
        print(f"操作失败 · {exc}", file=sys.stderr)
        return 1
