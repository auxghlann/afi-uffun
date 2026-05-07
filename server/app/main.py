from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
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

@app.get("/")
def read_root():
    return {"message": "Welcome to the Emergency Response Hub API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
