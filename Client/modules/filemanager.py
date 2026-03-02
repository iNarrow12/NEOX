import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/shell")


def _stat(path: str):
    try:
        s = os.stat(path)
        return {
            "name": os.path.basename(path),
            "path": path,
            "is_dir": os.path.isdir(path),
            "size": s.st_size,
            "modified": s.st_mtime,
        }
    except:
        return None


# ── List directory ────────────────────────────────────────────────────────────
@router.get("/files")
async def list_files(path: str = Query(".")):
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        return {"error": "Not a directory", "items": [], "path": path}
    try:
        entries = os.listdir(path)
    except PermissionError:
        return {"error": "Permission denied", "items": [], "path": path}

    items = []
    for name in sorted(entries, key=lambda n: (not os.path.isdir(os.path.join(path, n)), n.lower())):
        full = os.path.join(path, name)
        s = _stat(full)
        if s:
            items.append(s)

    return {"path": path, "items": items}


# ── Read file ─────────────────────────────────────────────────────────────────
@router.get("/files/read")
async def read_file(path: str = Query(...)):
    path = os.path.expanduser(path)
    try:
        with open(path, "r", errors="replace") as f:
            content = f.read()
        return {"path": path, "content": content}
    except PermissionError:
        return {"error": "Permission denied", "content": ""}
    except Exception as e:
        return {"error": str(e), "content": ""}


# ── Save file ─────────────────────────────────────────────────────────────────
class SaveBody(BaseModel):
    path: str
    content: str

@router.post("/files/save")
async def save_file(body: SaveBody):
    path = os.path.expanduser(body.path)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(body.content)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Make directory ────────────────────────────────────────────────────────────
class PathBody(BaseModel):
    path: str

@router.post("/files/mkdir")
async def make_dir(body: PathBody):
    path = os.path.expanduser(body.path)
    try:
        os.makedirs(path, exist_ok=True)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Delete ────────────────────────────────────────────────────────────────────
@router.post("/files/delete")
async def delete_path(body: PathBody):
    path = os.path.expanduser(body.path)
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Move / Rename ─────────────────────────────────────────────────────────────
class MoveBody(BaseModel):
    src: str
    dst: str

@router.post("/files/move")
async def move_path(body: MoveBody):
    src = os.path.expanduser(body.src)
    dst = os.path.expanduser(body.dst)
    try:
        shutil.move(src, dst)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Upload ────────────────────────────────────────────────────────────────────
@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...), path: str = Form(".")):
    dest_dir = os.path.expanduser(path)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, file.filename)
    try:
        with open(dest, "wb") as f:
            content = await file.read()
            f.write(content)
        return {"ok": True, "path": dest}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Download ──────────────────────────────────────────────────────────────────
@router.get("/files/download")
async def download_file(path: str = Query(...)):
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return {"error": "File not found"}
    return FileResponse(path, filename=os.path.basename(path))