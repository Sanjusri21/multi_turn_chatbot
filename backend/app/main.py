# USE: Access system-specific parameters, interpreter configuration, and runtime environment paths in Python.
# WHY: Required here to modify Python's module search path (sys.path) dynamically at startup so relative project imports work cleanly.
# HOW: sys provides sys.path (a list of directory strings) which the Python interpreter traverses sequentially to locate imported modules.
import sys

# USE: Provide object-oriented filesystem paths with cross-platform compatibility across Windows, Linux, and macOS.
# WHY: Needed to compute the exact absolute path to the backend directory relative to this main.py file without hardcoded paths.
# HOW: Path(__file__).resolve() inspects this file's path on disk and resolves symlinks, while .parent ascends directories.
from pathlib import Path

# USE: Compute the root filesystem directory path of the backend folder.
# WHY: Resolves the backend directory reliably regardless of the current working directory from which python was launched.
# HOW: Path(__file__).resolve() gets absolute path of main.py, .parent gets backend/app, and .parent.parent gets backend root.
backend_dir = Path(__file__).resolve().parent.parent

# USE: Guard check to determine if the backend root directory is already present inside Python's module search list.
# WHY: Prevents adding duplicate path entries to sys.path if this file is imported or reloaded multiple times.
# HOW: Evaluates whether the stringified representation of backend_dir exists as a member in sys.path.
if str(backend_dir) not in sys.path:
    # USE: Insert the backend root directory at the highest search priority position in sys.path.
    # WHY: Ensures local modules like 'app' are found and loaded first before any similarly-named system packages.
    # HOW: sys.path.insert(0, ...) places the path at index 0 of the list, making it the primary search target for imports.
    sys.path.insert(0, str(backend_dir))

# USE: Import FastAPI application class and incoming HTTP Request model object.
# WHY: FastAPI is the core web framework powering the REST API, and Request represents incoming HTTP client requests.
# HOW: FastAPI manages route registration, OpenAPI docs, and ASGI dispatch; Request gives access to HTTP headers, URL, and body.
from fastapi import FastAPI, Request

# USE: Import Cross-Origin Resource Sharing (CORS) ASGI middleware.
# WHY: Enables the frontend application (e.g. running on Vite localhost:5173) to send AJAX/Fetch requests to this API without browser blocks.
# HOW: Intercepts incoming requests and appends Access-Control-Allow-* response headers required by browser security policies.
from fastapi.middleware.cors import CORSMiddleware

# USE: Import standard JSON HTTP response generator class from FastAPI.
# WHY: Allows custom exception handlers to return structured JSON error payloads with specific HTTP status codes.
# HOW: Serializes Python dictionaries into formatted application/json HTTP response bytes sent over the network socket.
from fastapi.responses import JSONResponse

# USE: Import application-wide configuration settings singleton instance.
# WHY: Provides centralized access to environment variables, API keys, database paths, and model names.
# HOW: Reads validated configuration values loaded from .env and environment variables via Pydantic BaseSettings.
from app.core.config import settings

# USE: Import database schema initialization and table creation routine.
# WHY: Ensures all necessary relational database tables (users, conversations, messages, memories) exist before handling traffic.
# HOW: Calls SQLAlchemy metadata.create_all() and executes automatic migration checks on the active SQLite or PostgreSQL database.
from app.core.database import init_db

# USE: Import configured logger instance for structured application logging.
# WHY: Replaces raw print statements with timestamped, level-tagged log records for better debugging and production monitoring.
# HOW: Emits formatted log strings to stdout according to the logging configuration set up in logging_config.py.
from app.core.logging_config import logger

# USE: Import the system health and connectivity check routing module.
# WHY: Exposes monitoring and liveness probes at /api/health for system diagnostic verification.
# HOW: APIRouter grouping endpoints that return server status, uptime, and database connectivity.
from app.api.health_routes import router as health_router

# USE: Import authentication and user identity routing module.
# WHY: Exposes registration, login, token refresh, and user profile endpoints to secure the application.
# HOW: APIRouter handling password hashing, credential validation, and JWT access token issuance.
from app.api.auth_routes import router as auth_router

# USE: Import primary conversational AI and streaming chat routing module.
# WHY: Powers multi-turn conversational interactions, real-time web search augmentation, and LLM completions.
# HOW: APIRouter accepting chat prompts, retrieving conversation context, querying Gemini/Grok, and streaming responses.
from app.api.chat_routes import router as chat_router

# USE: Import conversation session management routing module.
# WHY: Allows users to create, list, rename, and delete conversation threads/histories.
# HOW: APIRouter querying and mutating conversation records in the database scoped to the authenticated user.
from app.api.conversation_routes import router as conversation_router

# USE: Import long-term persistent memory management routing module.
# WHY: Enables viewing, searching, creating, and removing user-specific persistent facts and knowledge.
# HOW: APIRouter interacting with the Memory repository to store structured facts across conversation boundaries.
from app.api.memory_routes import router as memory_router

# USE: Import user preferences and system settings routing module.
# WHY: Allows retrieving and updating user-specific configuration such as preferred AI models, system prompts, and themes.
# HOW: APIRouter persisting user setting overrides in the database and returning current system configuration.
from app.api.settings_routes import router as settings_router

# USE: Import file attachment and document upload routing module.
# WHY: Handles uploading, parsing, and context injection of text documents, PDFs, and data files.
# HOW: APIRouter processing multipart/form-data file uploads, extracting text content, and saving file metadata.
from app.api.file_routes import router as file_router

# USE: Import voice transcription and speech-to-text / text-to-speech routing module.
# WHY: Supports multimodal audio interactions allowing users to speak queries and receive audio responses.
# HOW: APIRouter accepting audio recordings, transcribing them, or synthesizing speech audio streams.
from app.api.voice_routes import router as voice_router

# USE: Import administrator user management and approval routing module.
# WHY: Exposes /api/admin endpoints for approving, rejecting, suspending, and monitoring users.
# HOW: APIRouter handling admin user reviews and role-based permissions.
from app.api.admin_routes import router as admin_router

# USE: Instantiate the primary FastAPI application instance with project metadata.
# WHY: Serves as the central ASGI application entrypoint where routers, middleware, and event handlers are bound.
# HOW: Configures the OpenAPI title, version, and description metadata rendered on the interactive Swagger docs at /docs.
app = FastAPI(
    # USE: Set the human-readable project title for Swagger documentation.
    # WHY: Identifies the API in documentation interfaces and OpenAPI specifications.
    # HOW: Retrieves PROJECT_NAME property from validated application settings.
    title=settings.PROJECT_NAME,
    # USE: Set the semver version string of the API.
    # WHY: Informs clients and tooling of the active API specification version.
    # HOW: Retrieves VERSION property from validated application settings.
    version=settings.VERSION,
    # USE: Set descriptive overview text for the API.
    # WHY: Provides background context to API consumers inspecting Swagger UI docs.
    # HOW: Displays this string at the top of the generated /docs and /redoc pages.
    description="Multi-Turn AI Chatbot with Persistent Memory, Authentication, and Modern UI"
)

# USE: Register CORS middleware on the FastAPI application instance.
# WHY: Permissive CORS configuration is required during development to allow frontend clients from other ports to make API requests.
# HOW: Wraps ASGI request handling pipeline to inspect origins and attach matching CORS response headers.
app.add_middleware(
    # USE: Specify the middleware class to register.
    # WHY: CORSMiddleware is Starlette's standard implementation for Cross-Origin Resource Sharing.
    # HOW: Intercepts incoming HTTP requests and handles HTTP OPTIONS preflight checks automatically.
    CORSMiddleware,
    # USE: Configure allowed origin domains that can make cross-origin requests.
    # WHY: Wildcard ["*"] permits access from any frontend host during development and demo environments.
    # HOW: Compares the incoming Origin header against the list and returns Access-Control-Allow-Origin header.
    allow_origins=["*"],
    # USE: Indicate whether cookies, authorization headers, or TLS client certificates are supported across origins.
    # WHY: Set to True so Authorization: Bearer <token> headers are accepted on cross-origin requests.
    # HOW: Sets the Access-Control-Allow-Credentials header to true on HTTP responses.
    allow_credentials=True,
    # USE: List HTTP methods permitted for cross-origin client requests.
    # WHY: Allows all standard HTTP methods (GET, POST, PUT, DELETE, OPTIONS, PATCH) needed by the REST endpoints.
    # HOW: Populates the Access-Control-Allow-Methods header in response to preflight OPTIONS requests.
    allow_methods=["*"],
    # USE: List HTTP request headers permitted from cross-origin clients.
    # WHY: Allows Authorization, Content-Type, Accept, and custom client headers without restriction.
    # HOW: Populates the Access-Control-Allow-Headers response header during CORS handshake.
    allow_headers=["*"],
)

# USE: Import Starlette's base HTTP exception class.
# WHY: Allows capturing and customizing responses for standard HTTP error statuses thrown across routes and middleware.
# HOW: Base class from which FastAPI's HTTPException inherits, allowing unified interception of client errors.
from starlette.exceptions import HTTPException as StarletteHTTPException

# USE: Decorator registering an event listener for application startup.
# WHY: Triggers critical initialization logic (e.g. database schema migrations) before accepting HTTP traffic.
# HOW: FastAPI's event system invokes this callable once when the ASGI server boots up.
@app.on_event("startup")
# USE: Startup lifecycle callback function definition.
# WHY: Contains all boot-up checks, database bootstrapping, and diagnostic configuration logs.
# HOW: Executed synchronously by the server runtime before binding incoming socket listeners.
def on_startup():
    # USE: Retrieve the absolute path to the active database file.
    # WHY: Needed for diagnostic logging to verify which SQLite database file or PostgreSQL instance is targeted.
    # HOW: Accesses the RESOLVED_DB_PATH computed property from settings.
    db_path = settings.RESOLVED_DB_PATH
    # USE: Print database path to stdout with immediate buffer flushing.
    # WHY: Guarantees visible terminal output immediately on server start without buffering delays.
    # HOW: Writes string to standard output stream and invokes flush() immediately.
    print(f"\nMemoryBot database:\n{db_path}\n", flush=True)
    # USE: Log the resolved database location to the application logger.
    # WHY: Preserves a persistent log entry indicating the database storage location.
    # HOW: Sends an INFO level formatted string to the configured logging stream.
    logger.info(f"MemoryBot database: {db_path}")
    # USE: Log the initiation of database schema synchronization.
    # WHY: Provides progress visibility in logs during startup sequence.
    # HOW: Emits INFO level record to logger before invoking init_db().
    logger.info("Initializing database tables...")
    # USE: Execute database table creation and schema migration.
    # WHY: Guarantees that tables, indexes, and required columns exist before requests query them.
    # HOW: Calls SQLAlchemy create_all() and runs column migration helper checks against the database connection.
    init_db()
    # USE: Log confirmation of successful startup along with active LLM provider.
    # WHY: Quickly confirms server readiness and indicates which AI provider (gemini, openai, xai) is configured.
    # HOW: Emits formatted string containing LLM_PROVIDER setting value to INFO log.
    logger.info(f"MemoryBot backend started successfully! Provider: {settings.LLM_PROVIDER}")
    # USE: Log boolean status indicating whether Gemini API key is configured.
    # WHY: Helps developers diagnose missing API key configuration without exposing raw secret keys in logs.
    # HOW: Converts GEMINI_API_KEY string to bool (True if non-empty, False if empty) and logs it.
    logger.info(f"GEMINI configured: {bool(settings.GEMINI_API_KEY)}")
    # USE: Log boolean status indicating whether xAI / Grok API key is configured.
    # WHY: Helps developers diagnose whether Grok fallback capabilities are operational without logging secrets.
    # HOW: Converts XAI_API_KEY string to bool and logs the result.
    logger.info(f"XAI configured: {bool(settings.XAI_API_KEY)}")
    # USE: Log the primary configured LLM provider name.
    # WHY: Explicitly documents routing target for conversational AI generation.
    # HOW: Writes settings.LLM_PROVIDER value to the logger output.
    logger.info(f"Primary provider: {settings.LLM_PROVIDER}")
    # USE: Log the configured xAI model name.
    # WHY: Verifies which Grok model architecture is active (e.g. grok-4.1-fast).
    # HOW: Retrieves and logs settings.XAI_MODEL.
    logger.info(f"Grok model: {settings.XAI_MODEL}")
    # USE: Log the base URL configured for the xAI endpoint.
    # WHY: Verifies routing destination for xAI requests (e.g. https://api.x.ai/v1).
    # HOW: Retrieves and logs settings.XAI_BASE_URL.
    logger.info(f"Grok base URL: {settings.XAI_BASE_URL}")
    # USE: Print Gemini configuration status directly to stdout.
    # WHY: Guarantees terminal visibility even if file-based logging is redirected.
    # HOW: Prints boolean flag with flush=True to avoid stdout buffer stalls.
    print(f"GEMINI configured: {bool(settings.GEMINI_API_KEY)}", flush=True)
    # USE: Print xAI configuration status directly to stdout.
    # WHY: Guarantees terminal visibility of xAI readiness during boot.
    # HOW: Prints boolean flag with flush=True.
    print(f"XAI configured: {bool(settings.XAI_API_KEY)}", flush=True)
    # USE: Print primary LLM provider directly to console.
    # WHY: Informs operator which AI engine will answer incoming questions.
    # HOW: Writes provider name string directly to sys.stdout.
    print(f"Primary provider: {settings.LLM_PROVIDER}", flush=True)
    # USE: Print Grok model name directly to console.
    # WHY: Informs operator of fallback model configuration.
    # HOW: Writes model name string directly to sys.stdout.
    print(f"Grok model: {settings.XAI_MODEL}", flush=True)
    # USE: Print Grok base URL directly to console.
    # WHY: Confirms target API gateway in terminal output.
    # HOW: Writes URL string directly to sys.stdout with flush=True.
    print(f"Grok base URL: {settings.XAI_BASE_URL}", flush=True)

# USE: Mount health check routes into the main application.
# WHY: Exposes /api/health endpoint for uptime probes and monitoring agents.
# HOW: Includes health_router endpoints under the "/api" URL prefix.
app.include_router(health_router, prefix="/api")

# USE: Mount user authentication routes into the main application.
# WHY: Exposes /api/auth/register, /api/auth/login, and /api/auth/me endpoints.
# HOW: Includes auth_router endpoints under the "/api" URL prefix.
app.include_router(auth_router, prefix="/api")

# USE: Mount chat and streaming generation routes into the main application.
# WHY: Exposes /api/chat endpoints for AI chat completions and streaming responses.
# HOW: Includes chat_router endpoints under the "/api" URL prefix.
app.include_router(chat_router, prefix="/api")

# USE: Mount conversation session routes into the main application.
# WHY: Exposes /api/conversations endpoints for managing chat threads.
# HOW: Includes conversation_router endpoints under the "/api" URL prefix.
app.include_router(conversation_router, prefix="/api")

# USE: Mount long-term memory routes into the main application.
# WHY: Exposes /api/memory endpoints for querying and manipulating stored user facts.
# HOW: Includes memory_router endpoints under the "/api" URL prefix.
app.include_router(memory_router, prefix="/api")

# USE: Mount settings routes into the main application.
# WHY: Exposes /api/settings endpoints for managing user configurations and model preferences.
# HOW: Includes settings_router endpoints under the "/api" URL prefix.
app.include_router(settings_router, prefix="/api")

# USE: Mount file and document attachment routes into the main application.
# WHY: Exposes /api/files endpoints for document uploading and retrieval.
# HOW: Includes file_router endpoints under the "/api" URL prefix.
app.include_router(file_router, prefix="/api")

# USE: Mount voice and audio processing routes into the main application.
# WHY: Exposes /api/voice endpoints for speech-to-text transcription and audio generation.
# HOW: Includes voice_router endpoints under the "/api" URL prefix.
app.include_router(voice_router, prefix="/api")

# USE: Mount admin approval and user management routes into the main application.
# WHY: Exposes /api/admin endpoints for administrator workflows.
# HOW: Includes admin_router endpoints under the "/api" URL prefix.
app.include_router(admin_router, prefix="/api")

# USE: Define HTTP GET route handler on root path "/".
# WHY: Provides an immediate welcome message and links to interactive documentation when visiting API root.
# HOW: FastAPI maps incoming HTTP GET requests for "/" directly to this callable.
@app.get("/")
# USE: Root handler function definition.
# WHY: Returns metadata verifying the API is up and running.
# HOW: Serializes the returned dictionary into an HTTP 200 JSON response.
def root():
    # USE: Return JSON payload with service status, documentation link, and version.
    # WHY: Provides friendly discovery metadata for developers and health monitors.
    # HOW: FastAPI automatically converts this Python dictionary to application/json.
    return {
        # USE: Human-readable status confirmation message.
        # WHY: Informs user that the backend server is active.
        # HOW: Encoded as a JSON string property.
        "message": "MemoryBot API is running 🤖",
        # USE: Relative URL path pointing to interactive OpenAPI documentation.
        # WHY: Directs developers to the Swagger UI explorer.
        # HOW: Encoded as a JSON string property.
        "docs_url": "/docs",
        # USE: Current application release version number.
        # WHY: Allows clients to verify API compatibility.
        # HOW: Evaluates settings.VERSION and encodes it as a JSON string.
        "version": settings.VERSION
    }

# USE: Decorator registering custom handler for Starlette/FastAPI HTTPExceptions.
# WHY: Standardizes JSON error response format across all 4xx HTTP client errors.
# HOW: FastAPI intercepts any raised HTTPException matching StarletteHTTPException and calls this function.
@app.exception_handler(StarletteHTTPException)
# USE: Asynchronous HTTP exception handler callback function.
# WHY: Formats error detail and custom headers consistently in client responses.
# HOW: Receives the incoming request and the caught exception instance, returning a structured JSONResponse.
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # USE: Generate and return standard JSONResponse with exception status and detail.
    # WHY: Ensures predictable error structure ({"detail": ...}) across all HTTP errors.
    # HOW: Instantiates JSONResponse with status_code, JSON dict payload, and forwarded HTTP headers.
    return JSONResponse(
        # USE: Pass the specific HTTP status code from the exception (e.g. 401, 403, 404).
        # WHY: Informs the HTTP client of the exact error classification.
        # HOW: Extracted from exc.status_code attribute.
        status_code=exc.status_code,
        # USE: Payload dictionary containing the error detail message.
        # WHY: Explains why the request was rejected to the calling client.
        # HOW: Serialized into JSON body with key "detail".
        content={"detail": exc.detail},
        # USE: Forward optional response headers associated with the exception (such as WWW-Authenticate).
        # WHY: Required by HTTP specifications for auth challenges and custom error headers.
        # HOW: Uses getattr to safely retrieve exc.headers if present, defaulting to None.
        headers=getattr(exc, "headers", None)
    )

# USE: Decorator registering global catch-all exception handler for unhandled Python exceptions.
# WHY: Prevents uncaught 500 crashes from leaking stack traces to clients while logging full tracebacks on server.
# HOW: Catches any exception inheriting from base Exception that was not caught by specific handlers.
@app.exception_handler(Exception)
# USE: Asynchronous global exception handler callback function.
# WHY: Handles unexpected server-side errors gracefully with structured logging.
# HOW: Receives the active Request and caught Exception, logs diagnostics, and returns HTTP 500 JSON.
async def global_exception_handler(request: Request, exc: Exception):
    # USE: Import Python's built-in traceback formatting module inside error handler.
    # WHY: Lazy-imported here to extract complete call stack of the uncaught exception without loading it globally.
    # HOW: traceback module provides format_exc() which inspects sys.exc_info() for the active traceback.
    import traceback
    # USE: Extract the full formatted string representation of the exception stack trace.
    # WHY: Required for thorough debugging and root-cause analysis by developers.
    # HOW: format_exc() formats the current exception, its type, message, and call frames into a single string.
    tb = traceback.format_exc()
    # USE: Construct a detailed diagnostic error log message string.
    # WHY: Aggregates endpoint path, exception description, and stack trace in one readable block.
    # HOW: String formatting combines request.url.path, exc, and tb into a multi-line formatted string.
    error_msg = f"\n[MemoryBot ERROR]\nEndpoint: {request.url.path}\nException: {exc}\nTraceback:\n{tb}"
    # USE: Print the formatted error message directly to terminal stdout with flush.
    # WHY: Guarantees real-time visibility in development console even during severe failures.
    # HOW: Writes error_msg to stdout and immediately flushes output buffer.
    print(error_msg, flush=True)
    # USE: Record the error message into the application logger.
    # WHY: Ensures server error logs are stored in persistent log sinks and monitoring systems.
    # HOW: logger.error emits an ERROR-level record with the formatted error_msg.
    logger.error(error_msg)
    # USE: Return a safe, sanitized generic HTTP 500 JSON response to the external client.
    # WHY: Prevents sensitive server-internal implementation details and stack traces from leaking to potential attackers.
    # HOW: Instantiates JSONResponse with status_code=500 and sanitized {"detail": "Internal server error"} content.
    return JSONResponse(
        # USE: Set HTTP 500 Internal Server Error status code.
        # WHY: Conforms to HTTP standards indicating an unexpected failure occurred on the server.
        # HOW: Transmitted as the HTTP status line in the response header.
        status_code=500,
        # USE: Sanitized error description payload.
        # WHY: Shields internal database, environment, or code details from the end-user.
        # HOW: Serialized into JSON response body.
        content={"detail": "Internal server error"}
    )

# USE: Standard Python entrypoint guard checking if script is executed directly.
# WHY: Allows starting development server via 'python backend/app/main.py' while preventing auto-run when imported in tests.
# HOW: Python sets __name__ to "__main__" only when this file is the initial script passed to the python interpreter.
if __name__ == "__main__":
    # USE: Import Uvicorn ASGI server module inside the entrypoint guard.
    # WHY: Lazy-imported so test suites and external ASGI runners (like Gunicorn/Uvicorn CLI) don't trigger redundant imports.
    # HOW: Uvicorn is a high-performance asyncio-based ASGI web server implementation.
    import uvicorn
    # USE: Start the Uvicorn web server running the FastAPI app with configured host, port, and hot-reload.
    # WHY: Launches the HTTP server to begin listening for incoming web requests during local development.
    # HOW: uvicorn.run binds to socket on host:port, loads app import string, and watches files if reload is enabled.
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
