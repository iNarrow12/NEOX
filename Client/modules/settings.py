import os
import re
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

router = APIRouter(prefix="/api/settings")

ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

def _parse_env(path: str) -> Dict[str, str]:
    result = {}
    if not os.path.exists(path):
        return result
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip().strip('"').strip("'")
    return result

def _write_env(path: str, data: Dict[str, str]):
    lines = []
    # preserve comments from existing file
    existing_lines = []
    if os.path.exists(path):
        with open(path, "r") as f:
            existing_lines = f.readlines()

    written = set()
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            lines.append(line.rstrip())
            continue
        if "=" in stripped:
            k = stripped.split("=")[0].strip()
            if k in data:
                lines.append(f'{k}="{data[k]}"')
                written.add(k)
                
    for k, v in data.items():
        if k not in written:
            lines.append(f'{k}="{v}"')

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

class EnvData(BaseModel):
    data: Dict[str, str]

@router.get("/env")
async def get_env():
    return {"data": _parse_env(ENV_FILE)}

@router.post("/env")
async def save_env(body: EnvData):
    try:
        _write_env(ENV_FILE, body.data)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}