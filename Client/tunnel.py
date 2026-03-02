import paramiko
import threading
import socket
import time
import logging
import select
import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from dotenv import dotenv_values, set_key

router = APIRouter(prefix="/api/tunnel")
logger = logging.getLogger("tunnel")

ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

# ── State ─────────────────────────────────────────────────────────────────────
_state = {
    "running": False,
    "error": "",
    "connected_at": None,
    "host": "",
    "server_port": 2222,
    "username": "tunnel",
    "remote_port": 8000,
    "local_port": 8000,
    "logs": [],
}
_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None

# ── Model ─────────────────────────────────────────────────────────────────────
class TunnelConfig(BaseModel):
    server_host: str
    server_port: int = 2222
    username: str = "tunnel"
    password: str = ""
    local_host: str = "127.0.0.1"
    local_port: int = 8000
    remote_port: int = 8000

# ── .env helpers ──────────────────────────────────────────────────────────────
def _load_config() -> dict:
    vals = dotenv_values(ENV_FILE)
    return {
        "server_host": vals.get("TUNNEL_HOST", ""),
        "server_port": int(vals.get("TUNNEL_PORT", 2222)),
        "username":    vals.get("TUNNEL_USER", "tunnel"),
        "password":    vals.get("TUNNEL_PASS", ""),
        "local_host":  "127.0.0.1",
        "local_port":  int(vals.get("TUNNEL_LOCAL_PORT", 8000)),
        "remote_port": int(vals.get("TUNNEL_REMOTE_PORT", 8000)),
    }

def _save_config(cfg: TunnelConfig):

    pairs = [
        ("TUNNEL_HOST",        cfg.server_host),
        ("TUNNEL_PORT",        str(cfg.server_port)),
        ("TUNNEL_USER",        cfg.username),
        ("TUNNEL_PASS",        cfg.password),
        ("TUNNEL_LOCAL_PORT",  str(cfg.local_port)),
        ("TUNNEL_REMOTE_PORT", str(cfg.remote_port)),
    ]
    for key, val in pairs:
        set_key(ENV_FILE, key, val)

def _log(msg: str, level: str = "info"):
    _state["logs"].append(msg)
    if len(_state["logs"]) > 200:
        _state["logs"] = _state["logs"][-200:]
    getattr(logger, level)(msg)

def _forward_tunnel(chan, local_host, local_port):
    try:
        af = socket.AF_INET6 if ':' in local_host else socket.AF_INET
        sock = socket.socket(af, socket.SOCK_STREAM)
        sock.connect((local_host, local_port))
    except Exception as e:
        _log(f"Could not connect to local:{local_port} — {e}", "error")
        chan.close()
        return
    try:
        while not _stop_event.is_set():
            r, _, _ = select.select([sock, chan], [], [], 5)
            if sock in r:
                data = sock.recv(4096)
                if not data: break
                chan.sendall(data)
            if chan in r:
                data = chan.recv(4096)
                if not data: break
                sock.sendall(data)
    except Exception:
        pass
    finally:
        try: sock.close()
        except: pass
        try: chan.close()
        except: pass

def _handle_reverse_tunnel(transport, local_host, local_port, remote_port):
    transport.request_port_forward("", remote_port)
    _log(f"[+] Tunnel active → server:{remote_port} -> local:{local_port}")
    _state["running"] = True
    _state["error"] = ""
    _state["connected_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    while transport.is_active() and not _stop_event.is_set():
        chan = transport.accept(timeout=1)
        if chan is None:
            continue
        t = threading.Thread(target=_forward_tunnel, args=(chan, local_host, local_port), daemon=True)
        t.start()

def _tunnel_thread(cfg: TunnelConfig):
    attempt = 0
    while not _stop_event.is_set():
        attempt += 1
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            _log(f"[*] Connecting to {cfg.server_host}:{cfg.server_port} (attempt {attempt})…")
            addr_infos = socket.getaddrinfo(cfg.server_host, cfg.server_port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            ipv6 = [a for a in addr_infos if a[0] == socket.AF_INET6]
            ipv4 = [a for a in addr_infos if a[0] == socket.AF_INET]
            chosen = (ipv6 or ipv4)[0]
            af, _, _, _, sockaddr = chosen
            resolved_ip = sockaddr[0]
            _log(f"[*] Resolved {cfg.server_host} → {resolved_ip} ({'IPv6' if af==socket.AF_INET6 else 'IPv4'})")
            sock = socket.socket(af, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect(sockaddr)
            transport = paramiko.Transport(sock)
            transport.start_client()
            transport.auth_password(cfg.username, cfg.password)
            if not transport.is_authenticated():
                raise paramiko.AuthenticationException("Authentication failed")
            transport.set_keepalive(30)
            _log(f"[+] SSH connected to {cfg.server_host}")
            _handle_reverse_tunnel(transport, cfg.local_host, cfg.local_port, cfg.remote_port)
            transport.close()
            sock.close()
        except paramiko.AuthenticationException:
            _state["error"] = "Authentication failed — check username/password"
            _log(f"[-] {_state['error']}", "error")
            _state["running"] = False
            break
        except Exception as e:
            _state["error"] = str(e)
            _log(f"[-] Connection failed: {e}", "error")
            _state["running"] = False
        if _stop_event.is_set():
            break
        _log(f"[~] Reconnecting in 5s…")
        _stop_event.wait(5)
    _state["running"] = False
    _log("[*] Tunnel stopped.")

# ── API Routes ────────────────────────────────────────────────────────────────
@router.get("/status")
async def tunnel_status():
    saved = _load_config()
    return {
        "running": _state["running"],
        "host": _state["host"],
        "server_port": _state["server_port"],
        "username": _state["username"],
        "remote_port": _state["remote_port"],
        "local_port": _state["local_port"],
        "error": _state["error"],
        "connected_at": _state["connected_at"],
        "logs": _state["logs"][-30:],
        "saved": saved,
    }

@router.get("/ping")
async def tunnel_ping():
    return {"ok": True, "routes": "tunnel router active"}

@router.post("/save")
async def tunnel_save(cfg: TunnelConfig):
    try:
        if not cfg.password:
            existing = _load_config()
            cfg.password = existing.get("password", "")
        _save_config(cfg)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/start")
async def tunnel_start(cfg: TunnelConfig):
    global _thread, _stop_event
    if _state["running"]:
        return {"ok": False, "error": "Tunnel already running"}
    if _thread and _thread.is_alive():
        return {"ok": False, "error": "Tunnel thread still active, try again"}
    _stop_event = threading.Event()
    _state.update({
        "host": cfg.server_host, "server_port": cfg.server_port,
        "username": cfg.username, "remote_port": cfg.remote_port,
        "local_port": cfg.local_port, "error": "", "connected_at": None,
        "running": False, "logs": [],
    })
    _thread = threading.Thread(target=_tunnel_thread, args=(cfg,), daemon=True)
    _thread.start()
    for _ in range(16):
        time.sleep(0.5)
        if _state["running"] or _state["error"]:
            break
    if _state["running"]:
        return {"ok": True, "message": f"Tunnel active → {cfg.server_host}:{cfg.remote_port}"}
    return {"ok": False, "error": _state["error"] or "Timed out — check logs"}

@router.post("/stop")
async def tunnel_stop():
    _stop_event.set()
    _state["running"] = False
    _state["error"] = ""
    _state["connected_at"] = None
    return {"ok": True}

@router.get("/logs")
async def tunnel_logs():
    return {"logs": _state["logs"]}