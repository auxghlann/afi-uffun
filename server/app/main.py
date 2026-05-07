from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
from app.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown

app = FastAPI(
    title="Emergency Response Hub API",
    description="Backend for the Centralized Emergency Response Hub",
    version="1.0.0",
    lifespan=lifespan
)

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.call import router as call_router
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router

app.include_router(call_router, prefix="/api/call", tags=["Call Simulator"])
app.include_router(admin_router, prefix="/api/admin", tags=["Command Center"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

# Serve static files from the frontend build
# 1. Check ../static (Production/Docker)
# 2. Check ../../client/dist (Local development)
base_dir = os.path.dirname(os.path.dirname(__file__))
static_dir = os.path.join(base_dir, "static")
if not os.path.exists(static_dir):
    static_dir = os.path.join(os.path.dirname(base_dir), "client", "dist")

if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve index.html for all non-API routes to support React Router
        if full_path.startswith("api/"):
            return None # Should be handled by routers above
        
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))
else:
    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Emergency Response Hub API (Static files not found)"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
