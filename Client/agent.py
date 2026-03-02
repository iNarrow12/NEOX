import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import jwt
import uvicorn

load_dotenv()

app = FastAPI(title="NEOX", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("API_KEY")
ALGORITHM = "HS256"
ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASS")

security = HTTPBearer()

class LoginData(BaseModel):
    username: str
    password: str

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != ADMIN_USER:
            raise Exception("Invalid user")
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/login")
async def login(data: LoginData):
    if data.username == ADMIN_USER and data.password == ADMIN_PASS:
        expire = datetime.utcnow() + timedelta(hours=24)
        token = jwt.encode({"sub": ADMIN_USER, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# ── Import all module routers ──────────────────────────────────────────────────
from modules.shell import router as shell_router
from modules.info import router as info_router
from modules.filemanager import router as files_router
from modules.taskmanager import router as tasks_router
from modules.tunnel import router as tunnel_router
from modules.settings import router as settings_router

# ── Register all routers BEFORE static mount ──────────────────────────────────
app.include_router(shell_router,    dependencies=[Depends(get_current_user)])
app.include_router(info_router,     dependencies=[Depends(get_current_user)])
app.include_router(files_router,    dependencies=[Depends(get_current_user)])
app.include_router(tasks_router,    dependencies=[Depends(get_current_user)])
app.include_router(tunnel_router,   dependencies=[Depends(get_current_user)])
app.include_router(settings_router, dependencies=[Depends(get_current_user)])

logging.basicConfig(filename='admin.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# ── Debug: print all registered routes on startup ─────────────────────────────
@app.on_event("startup")
async def print_routes():
    for route in app.routes:
        if hasattr(route, "methods"):
            print(f"  {route.methods} {route.path}")

# ── Static files MUST be last ─────────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="::", port=8000, log_level="info")