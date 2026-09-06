#!/usr/bin/env python3
"""
CSF1 Viewer v0.1
Host GUI / CLI to open JCkernel raw (.img/.bin) or QEMU (.qcow2) disks
read-only, detect CSF1 at LBA 4096, and browse as a tree.

Inspect CLI prints one token (no extra English on that line):
  NO_SUPERBLOCK | WRONG_MAGIC | WRONG_VERSION | MOUNT_OK
"""

from __future__ import annotations

import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

APP_NAME = "CSF1 Viewer"
APP_VER = "v0.1"

# allow running from this folder
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from csf1_core import CSF1Volume  # noqa: E402
from qcow2io import open_disk  # noqa: E402

STATE = {
    "vol": None,
    "path": "",
    "order": "az",
    "status": "No disk mounted.",
    "ok": False,
}


def inspect_path(path: str) -> str:
    """Open PATH rb-only and classify the LBA 4096 superblock.

    Does not import / export / remove. Does not scan the first 64 MiB.
    """
    path = os.path.abspath(path.strip().strip('"'))
    dev = open_disk(path, writable=False)
    try:
        vol = CSF1Volume(dev)
        return vol.inspect()
    finally:
        try:
            dev.close()
        except Exception:
            pass


def inspect_cli(path: str) -> int:
    token = inspect_path(path)
    print(token)
    return 0 if token == "MOUNT_OK" else 1


def mount_path(path: str) -> dict:
    path = os.path.abspath(path.strip().strip('"'))
    if not os.path.isfile(path):
        return {"ok": False, "message": f"File not found: {path}"}
    try:
        if STATE["vol"] and STATE["vol"].dev:
            STATE["vol"].dev.close()
    except Exception:
        pass
    try:
        dev = open_disk(path, writable=False)
        vol = CSF1Volume(dev)
        ok = vol.detect_and_mount()
        STATE["vol"] = vol
        STATE["path"] = path
        STATE["ok"] = ok
        STATE["status"] = vol.message
        return {
            "ok": ok,
            "message": vol.message,
            "path": path,
            "kind": "qcow2" if path.lower().endswith(".qcow2") else "raw",
            "sb": _sb_dict(vol) if ok else None,
        }
    except Exception as e:
        STATE["ok"] = False
        STATE["status"] = str(e)
        return {"ok": False, "message": str(e)}


def _sb_dict(vol: CSF1Volume):
    s = vol.sb
    return {
        "disk_name": s.disk_name,
        "version": s.version,
        "created_at": s.created_at,
        "layout_id": s.layout_id,
        "total_size_mb": s.total_size_mb,
        "file_count": s.file_count,
        "folder_count": s.folder_count,
        "max_files": s.max_files,
        "max_folders": s.max_folders,
        "origin_lba": s.origin_lba,
        "data_start_sector": s.data_start_sector,
    }


def tree_payload(order: str = None):
    vol = STATE["vol"]
    if not vol or not STATE["ok"]:
        return {"ok": False, "rows": [], "message": STATE["status"]}
    order = order or STATE["order"]
    STATE["order"] = order
    rows = []
    for path, e in vol.tree_rows(order):
        rows.append({
            "path": path,
            "name": e.name,
            "kind": e.kind,
            "size": e.size,
            "owner": e.owner,
            "created": e.created_at,
            "modified": e.modified_at,
            "deleted": e.deleted_at,
            "index": e.index,
        })
    return {"ok": True, "rows": rows, "order": order, "sb": _sb_dict(vol), "message": STATE["status"]}
