---
name: genbox-open
description: 使用本地 GenBox Open 发布 HTML、Markdown 或 SVG，回看历史并恢复指定版本。用户明确指定托管服务时，可调用公开上传接口。
---

在安装目录定位本技能的 `scripts/genbox.py`。以下命令中的 `CLI` 代表其绝对路径。支持 Python 3.9 及以上版本。

1. 用户要求本地分享或预览时，运行 `python3 CLI publish FILE --title TITLE`。从 JSON 读取 `slug`、`url` 和 `revision_url`。文件上限为 1 MiB，编码为 UTF-8。
2. 在相同数据目录启动 `python3 CLI serve`，或使用用户已经启动的作品库。返回本机链接；用户选用其他端口时，发布命令须传入相同的 `--port`，并告诉用户预览服务需要保持运行。
3. 用户要更新同一短链时，运行 `python3 CLI publish FILE --replace SLUG`。用户指定回到某一版时，先用 `python3 CLI history SLUG` 核对，再执行 `python3 CLI restore SLUG VERSION`。恢复结果会增加一条记录。
4. 仅在用户明确要求向指定托管服务上传时使用 `python3 CLI send FILE --base-url URL`。令牌由用户在进程环境中预设为 `GENBOX_TOKEN`。默认可见性是 private。公开发布需按用户意图显式传入 `--visibility public`。
5. 进程退出码非零时报告错误内容。输出 JSON 后再给出链接，保留用户原文件。
