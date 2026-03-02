import os
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter(prefix="/api/shell")

_cwd = os.getcwd()
_old_cwd = _cwd

class Command(BaseModel):
    command: str

class FileItem(BaseModel):
    name: str
    is_dir: bool
    size: int
    modified: str
    path: str

class SaveFile(BaseModel):
    path: str
    content: str

class Mkdir(BaseModel):
    path: str

class Delete(BaseModel):
    path: str

class Move(BaseModel):
    src: str
    dst: str

def get_current_cwd():
    return _cwd

@router.get("/cwd")
async def get_cwd():
    return {"cwd": _cwd}

@router.post("/execute")
async def execute(cmd: Command):
    global _cwd, _old_cwd
    command = cmd.command.strip()

    if command == "clear" or command == "cls":
        return {"output": "", "error": False, "cwd": _cwd}

    if command.startswith("cd"):
        target = command[2:].strip() or "~"
        try:
            if target == "~":
                new_cwd = Path.home()
            elif target == "-":
                new_cwd, _old_cwd = Path(_old_cwd), _cwd
            else:
                new_cwd = Path(_cwd) / target
            new_cwd = new_cwd.resolve()
            if new_cwd.is_dir():
                _old_cwd = _cwd
                _cwd = str(new_cwd)
                return {"output": f"Changed to {_cwd}", "error": False, "cwd": _cwd}
            return {"output": f"cd: {target}: No such directory", "error": True, "cwd": _cwd}
        except Exception as e:
            return {"output": str(e), "error": True, "cwd": _cwd}

    try:
        use_gitbash = platform.system() == "Windows" and os.path.exists(os.getenv("GITBASH_EXE", ""))
        if use_gitbash:
            exe = os.getenv("GITBASH_EXE")
            shell_cmd = [exe, "-c", command]
        else:
            shell_cmd = ["cmd.exe", "/c", command] if platform.system() == "Windows" else ["/bin/bash", "-c", command]

        result = subprocess.run(shell_cmd, cwd=_cwd, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        return {
            "output": output.strip() or "(no output)",
            "error": result.returncode != 0,
            "cwd": _cwd
        }
    except subprocess.TimeoutExpired:
        return {"output": "Command timed out (60s)", "error": True, "cwd": _cwd}
    except Exception as e:
        return {"output": str(e), "error": True, "cwd": _cwd}

# === FILE MANAGER ROUTES ===
@router.get("/files")
async def list_files(path: str = None):
    target = Path(path) if path else Path(_cwd)
    if not target.is_absolute():
        target = Path(_cwd) / target
    target = target.resolve()
    if not target.exists() or not target.is_dir():
        raise HTTPException(404, "Directory not found")

    items: List[Dict] = []
    for item in target.iterdir():
        try:
            stat = item.stat()
            items.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(item)
            })
        except:
            continue
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {"path": str(target), "items": items, "cwd": _cwd}

@router.get("/files/read")
async def read_file(path: str):
    p = Path(path).resolve()
    if not p.is_file():
        raise HTTPException(404, "File not found")
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        return {"content": content}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/files/save")
async def save_file(data: SaveFile):
    p = Path(data.path).resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data.content, encoding="utf-8")
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/files/mkdir")
async def mkdir(data: Mkdir):
    p = Path(data.path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return {"status": "created"}

@router.post("/files/delete")
async def delete_file(data: Delete):
    p = Path(data.path).resolve()
    if p.is_dir():
        import shutil
        shutil.rmtree(p)
    else:
        p.unlink(missing_ok=True)
    return {"status": "deleted"}

@router.post("/files/move")
async def move_file(data: Move):
    src = Path(data.src).resolve()
    dst = Path(data.dst).resolve()
    src.rename(dst)
    return {"status": "moved"}