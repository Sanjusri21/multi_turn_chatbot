import sys
from pathlib import Path

# Add backend directory to sys.path so 'app' can be imported cleanly from anywhere
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import init_db
from app.core.logging_config import logger
from app.api.health_routes import router as health_router
from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router
from app.api.conversation_routes import router as conversation_router
from app.api.memory_routes import router as memory_router
from app.api.settings_routes import router as settings_router
from app.api.file_routes import router as file_router
from app.api.voice_routes import router as voice_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multi-Turn AI Chatbot with Persistent Memory, Authentication, and Modern UI"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.exceptions import HTTPException as StarletteHTTPException

@app.on_event("startup")
def on_startup():
    db_path = settings.RESOLVED_DB_PATH
    print(f"\nMemoryBot database:\n{db_path}\n", flush=True)
    logger.info(f"MemoryBot database: {db_path}")
    logger.info("Initializing database tables...")
    init_db()
    logger.info(f"MemoryBot backend started successfully! Provider: {settings.LLM_PROVIDER}")
    logger.info(f"GEMINI configured: {bool(settings.GEMINI_API_KEY)}")
    logger.info(f"XAI configured: {bool(settings.XAI_API_KEY)}")
    logger.info(f"Primary provider: {settings.LLM_PROVIDER}")
    logger.info(f"Grok model: {settings.XAI_MODEL}")
    logger.info(f"Grok base URL: {settings.XAI_BASE_URL}")
    print(f"GEMINI configured: {bool(settings.GEMINI_API_KEY)}", flush=True)
    print(f"XAI configured: {bool(settings.XAI_API_KEY)}", flush=True)
    print(f"Primary provider: {settings.LLM_PROVIDER}", flush=True)
    print(f"Grok model: {settings.XAI_MODEL}", flush=True)
    print(f"Grok base URL: {settings.XAI_BASE_URL}", flush=True)

# Include Routers with /api prefix
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(conversation_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(file_router, prefix="/api")
app.include_router(voice_router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "MemoryBot API is running 🤖",
        "docs_url": "/docs",
        "version": settings.VERSION
    }

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None)
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    tb = traceback.format_exc()
    error_msg = f"\n[MemoryBot ERROR]\nEndpoint: {request.url.path}\nException: {exc}\nTraceback:\n{tb}"
    print(error_msg, flush=True)
    logger.error(error_msg)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
