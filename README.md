<div align="center">
    
![header](https://capsule-render.vercel.app/api?type=waving&height=300&color=gradient&text=NEOX&desc=Cross%20Platform%20Remote%20Administration%20Tool&descAlignY=52&fontAlignY=40)

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.8-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)
![JWT](https://img.shields.io/badge/JWT-Auth-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)

</div>

## `$ overview`

```python
┌──(neox㉿server)-[~]
└─$ tree
.
├── agent.py                 # Main FastAPI app
├── admin.log                 # Audit log
├── modules/                  # Backend modules
│   ├── filemanager.py        # File operations
│   ├── info.py               # System info
│   ├── settings.py           # .env management
│   ├── shell.py              # Shell + file manager
│   ├── taskmanager.py        # Process control
│   └── tunnel.py             # SSH reverse tunnel
├── static/                   # Frontend
│   └── index.html
├── requirements.txt          # Dependencies
└── .env                      # Config (editable via UI)
```

---

## `$ features`

| Module | Description |
|--------|-------------|
| **Shell** | Execute commands, change directories, view output |
| **System Info** | CPU, RAM, disk, network, OS, processes |
| **File Manager** | Browse, upload, download, delete, rename, edit files |
| **Task Manager** | List, kill, terminate, suspend, resume processes |
| **Tunnel** | SSH reverse tunnel (port forwarding) |
| **Settings** | Edit `.env` via browser UI, view logs |

All modules protected by JWT. Every action logged in `admin.log`.

---

## `$ installation`

```bash
┌──(user㉿host)-[~]
└─$ git clone https://github.com/iNarrow12/NEOX.git
┌──(user㉿host)-[~]
└─$ cd neox

┌──(user㉿host)-[~/neox]
└─$ python -m venv venv
┌──(user㉿host)-[~/neox]
└─$ source venv/bin/activate  # Windows: venv\Scripts\activate

┌──(neox㉿venv)-[~/neox]
└─$ pip install -r requirements.txt
```

### Environment

Create `.env`:

```ini
# Agent Credentials
API_KEY="your_strong_secret_key_here_min_32_chars"
ADMIN_USER="admin"
ADMIN_PASS="your_secure_password"

# SSH Tunnel Settings
TUNNEL_HOST=""
TUNNEL_PORT="2222"
TUNNEL_USER="tunnel"
TUNNEL_PASS="your_tunnel_password"
TUNNEL_LOCAL_PORT="8000"
TUNNEL_REMOTE_PORT="8080"
```

### Run

```bash
┌──(neox㉿venv)-[~/neox]
└─$ python agent.py
# Server starts at http://[::]:8000
```

Open browser → `http://your-server-ip:8000` → login.

> **Note**: Ensure port 8000 is open. For production, use a reverse proxy with SSL.

---

## `$ frontend`

The web interface (`static/index.html`) was crafted with assistance from multiple AI coding tools: **DeepSeek**, **Grok**, **Claude Code**, and **Gemini**. It provides a clean, responsive dashboard to interact with all backend modules without manual API calls.

---

## `$ configuration`

Variables editable via **Settings** UI (changes take effect immediately except `API_KEY`/`ADMIN_USER`/`ADMIN_PASS` – restart required).

| Variable | Description |
|----------|-------------|
| `API_KEY` | JWT signing secret (min 32 chars) |
| `ADMIN_USER` | Login username |
| `ADMIN_PASS` | Login password |
| `TUNNEL_HOST` | SSH server for reverse tunnel |
| `TUNNEL_PORT` | SSH port (default: 2222) |
| `TUNNEL_USER` | SSH username |
| `TUNNEL_PASS` | SSH password |
| `TUNNEL_LOCAL_PORT` | Local port to forward (default: 8000) |
| `TUNNEL_REMOTE_PORT` | Remote port to expose (default: 8080) |

---

## `$ logging`

All actions (logins, commands, file ops, process changes, tunnel events) are logged to `admin.log` in the project root. Example:

```
2025-03-02 15:30:45 - User admin logged in
2025-03-02 15:31:12 - Executed: ls -la
2025-03-02 15:32:01 - Tunnel started to example.com:2222
```

---

## `$ api overview`

All endpoints (except `/login`) require `Authorization: Bearer <token>`.

### Authentication

```
POST /login
{
  "username": "admin",
  "password": "..."
}
→ { "access_token": "..." }
```

### Modules (protected)

| Module | Base Path | Sample Endpoints |
|--------|-----------|------------------|
| Shell | `/api/shell` | `GET /cwd`, `POST /execute`, `GET /files?path=...`, `POST /files/save`, `POST /files/upload` |
| Info | `/api/info` | `GET /all` (full system info), `GET /processes` (top 20) |
| Tasks | `/api/tasks` | `GET /list`, `POST /kill`, `/terminate`, `/suspend`, `/resume` |
| Tunnel | `/api/tunnel` | `GET /status`, `POST /start`, `POST /stop`, `POST /save`, `GET /logs` |
| Settings | `/api/settings` | `GET /env`, `POST /env` |

The frontend UI (served at `/`) provides a user-friendly interface to all these endpoints.

<div align="center">

![footer](https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,20,24&height=100&section=footer)

</div>
