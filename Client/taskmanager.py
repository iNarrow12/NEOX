import psutil
import signal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/tasks")

class PidBody(BaseModel):
    pid: int

@router.get("/list")
async def list_processes():
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent',
                                   'memory_percent', 'memory_info', 'status', 'cmdline']):
        try:
            mem_mb = round((p.info['memory_info'].rss if p.info['memory_info'] else 0) / (1024**2), 1)
            procs.append({
                "pid":     p.info['pid'],
                "name":    p.info['name'] or '—',
                "user":    p.info['username'] or '—',
                "cpu":     round(p.info['cpu_percent'] or 0, 1),
                "mem_pct": round(p.info['memory_percent'] or 0, 1),
                "mem_mb":  mem_mb,
                "status":  p.info['status'] or '—',
                "cmd":     ' '.join(p.info['cmdline'] or [])[:80],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x['cpu'], reverse=True)
    return procs

@router.post("/kill")
async def kill_process(body: PidBody):
    try:
        p = psutil.Process(body.pid)
        p.kill()
        return {"ok": True, "action": "killed", "pid": body.pid}
    except psutil.NoSuchProcess:
        return {"ok": False, "error": "Process not found"}
    except psutil.AccessDenied:
        return {"ok": False, "error": "Access denied — try running NEOX as root"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/terminate")
async def terminate_process(body: PidBody):
    try:
        p = psutil.Process(body.pid)
        p.terminate()
        return {"ok": True, "action": "terminated", "pid": body.pid}
    except psutil.NoSuchProcess:
        return {"ok": False, "error": "Process not found"}
    except psutil.AccessDenied:
        return {"ok": False, "error": "Access denied — try running NEOX as root"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/suspend")
async def suspend_process(body: PidBody):
    try:
        p = psutil.Process(body.pid)
        p.suspend()
        return {"ok": True, "action": "suspended", "pid": body.pid}
    except psutil.NoSuchProcess:
        return {"ok": False, "error": "Process not found"}
    except psutil.AccessDenied:
        return {"ok": False, "error": "Access denied — try running NEOX as root"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/resume")
async def resume_process(body: PidBody):
    try:
        p = psutil.Process(body.pid)
        p.resume()
        return {"ok": True, "action": "resumed", "pid": body.pid}
    except psutil.NoSuchProcess:
        return {"ok": False, "error": "Process not found"}
    except psutil.AccessDenied:
        return {"ok": False, "error": "Access denied — try running NEOX as root"}
    except Exception as e:
        return {"ok": False, "error": str(e)}