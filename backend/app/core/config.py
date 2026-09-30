# USE: Import Python standard operating system interface module.
# WHY: Needed to read system environment variables, inspect processes, and interact with OS runtime settings.
# HOW: os.environ dictionary allows querying and modifying process-level environment variables.
import os

# USE: Import typing annotations for optional values and lists.
# WHY: Provides strict type hinting for configuration properties to ensure static type safety.
# HOW: Optional[T] represents values that can be T or None; List[T] represents typed lists.
from typing import Optional, List

# USE: Import Pathlib's Path class for cross-platform filesystem navigation.
# WHY: Allows computing absolute folder directories and locating .env configuration files reliably across OSes.
# HOW: Path provides path arithmetic (/ operator), existence checking (.exists()), and resolution (.resolve()).
from pathlib import Path

# USE: Import load_dotenv helper from python-dotenv library.
# WHY: Reads key-value pairs from .env configuration files and injects them into os.environ.
# HOW: Parses the specified file format and sets matching variables in the Python process environment.
from dotenv import load_dotenv

# USE: Import Pydantic v2 BaseSettings and SettingsConfigDict classes.
# WHY: Powers robust, strongly-typed configuration management with automatic environment variable parsing and validation.
# HOW: BaseSettings automatically maps environment variables to typed class fields with defaults and validation.
from pydantic_settings import BaseSettings, SettingsConfigDict

# USE: Import Field constructor from Pydantic.
# WHY: Declares metadata, default values, and validation rules for individual configuration fields.
# HOW: Field(default=...) assigns default values while enabling customization of field parsing behavior.
from pydantic import Field

# USE: Compute the absolute filesystem path to the backend directory.
# WHY: Serves as the primary reference anchor for backend-relative file and path computations.
# HOW: Resolves __file__ (config.py), ascends parent (core), parent (app), and parent (backend).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# USE: Compute the absolute filesystem path to the project root repository directory.
# WHY: References the top-level repository root where data folders and root .env files reside.
# HOW: Takes BASE_DIR (backend) and retrieves its parent folder.
PROJECT_ROOT = BASE_DIR.parent

# USE: Define the path to the persistent data directory for storing SQLite databases and file uploads.
# WHY: Centralizes persistent application state in a designated 'data' directory outside source code.
# HOW: Combines PROJECT_ROOT with the "data" subfolder via the Path / operator.
DATA_DIR = PROJECT_ROOT / "data"

# USE: Ensure the data directory exists on disk prior to application initialization.
# WHY: Prevents SQLite connection errors caused by missing parent directories when creating the database file.
# HOW: mkdir creates the folder; parents=True creates ancestor directories if missing; exist_ok=True prevents errors if already present.
DATA_DIR.mkdir(parents=True, exist_ok=True)

# USE: Define candidate filesystem paths where .env configuration files might be located.
# WHY: Supports diverse execution environments (running from root, backend, Docker, or IDE terminals).
# HOW: Populates a list of Path objects representing possible .env locations in descending order of specificity.
candidate_env_files = [
    # USE: Check backend directory root for .env file.
    # WHY: Standard location for backend-specific environment configuration.
    # HOW: BASE_DIR / ".env" constructs path to backend/.env.
    BASE_DIR / ".env",
    # USE: Explicit path to backend/.env relative to project root.
    # WHY: Guarantees resolution when launched from the workspace parent directory.
    # HOW: PROJECT_ROOT / "backend" / ".env" constructs absolute path.
    PROJECT_ROOT / "backend" / ".env",
    # USE: Root level .env file location.
    # WHY: Supports monorepo setups where environment variables are shared at the repository root.
    # HOW: PROJECT_ROOT / ".env" targets the workspace root .env.
    PROJECT_ROOT / ".env",
    # USE: Relative .env file evaluated from the current working directory.
    # WHY: Resolves .env if python was launched in the directory where .env sits.
    # HOW: Path(".env").resolve() computes absolute path based on cwd.
    Path(".env").resolve(),
    # USE: Relative backend/.env evaluated from current working directory.
    # WHY: Resolves backend/.env when running commands from the root directory.
    # HOW: Path("backend/.env").resolve() checks working directory subfolder.
    Path("backend/.env").resolve(),
]

# USE: Initialize an empty list to track unique, verified .env file paths that exist on disk.
# WHY: Avoids redundant reloading of identical configuration files while collecting all valid sources.
# HOW: Accumulates stringified resolved paths during discovery iteration.
env_files_to_load = []

# USE: Iterate over each candidate .env file path in candidate_env_files.
# WHY: Evaluates each potential location sequentially to discover active configuration files.
# HOW: Standard Python for-in loop iterating through the candidate_env_files list.
for p in candidate_env_files:
    # USE: Verify that the candidate path exists on disk and is a regular file.
    # WHY: Prevents file-not-found errors or attempting to load directories as env files.
    # HOW: p.exists() verifies presence on disk; p.is_file() confirms it is not a directory or socket.
    if p.exists() and p.is_file():
        # USE: Resolve the path to its canonical absolute filesystem location.
        # WHY: Normalizes symlinks and relative segments to ensure reliable deduplication.
        # HOW: p.resolve() computes the canonical absolute Path.
        p_resolved = p.resolve()
        # USE: Convert the canonical Path object to a string.
        # WHY: Enables membership testing against the env_files_to_load string list.
        # HOW: str(p_resolved) returns the full OS path string.
        p_str = str(p_resolved)
        # USE: Guard check to determine if this file path has already been processed.
        # WHY: Eliminates duplicate load_dotenv executions for the same underlying file.
        # HOW: Checks if p_str is not already present in env_files_to_load.
        if p_str not in env_files_to_load:
            # USE: Append the unique environment file path string to the collection list.
            # WHY: Preserves the list of active configuration file sources for Pydantic Settings.
            # HOW: Invokes list.append(p_str).
            env_files_to_load.append(p_str)
            # USE: Load and apply variables from the discovered .env file into the process environment.
            # WHY: Makes API keys and settings immediately accessible to os.environ and Pydantic.
            # HOW: load_dotenv parses variables from dotenv_path and overrides existing process variables with override=True.
            load_dotenv(dotenv_path=p_resolved, override=True)

# USE: Guard check verifying whether any valid .env files were discovered.
# WHY: Fallback mechanism ensuring at least one default env file path is provided to Pydantic Settings.
# HOW: Evaluates whether env_files_to_load list is empty.
if not env_files_to_load:
    # USE: Assign default backend/.env path to the loading list.
    # WHY: Provides Pydantic with a target path even if the file has not yet been created.
    # HOW: Wraps resolved backend .env path string in a single-element list.
    env_files_to_load = [str((BASE_DIR / ".env").resolve())]

# USE: Configuration class defining all typed application settings inheriting from Pydantic BaseSettings.
# WHY: Centralizes, validates, and types all configuration variables across the entire MemoryBot application.
# HOW: Fields declare type annotations and default values; values are automatically populated from environment variables.
class Settings(BaseSettings):
    # USE: Project name displayed in Swagger docs and logging.
    # WHY: Brand identifier and title for OpenAPI specification.
    # HOW: String field initialized with the default project title.
    PROJECT_NAME: str = "MemoryBot — Multi-Turn AI Chatbot with Persistent Memory"
    # USE: Semantic version number of the application.
    # WHY: Informs clients and documentation of the deployed release version.
    # HOW: String field matching current release version (2.0.0).
    VERSION: str = "2.0.0"
    # USE: Boolean flag toggling debugging features and server auto-reloading.
    # WHY: Enables live reload in local development while allowing disabling in production.
    # HOW: Defaults to True; mapped to uvicorn's reload parameter.
    DEBUG: bool = True

    # USE: Network interface host IP address for binding the web server.
    # WHY: Specifies which network adapter listens for incoming connections.
    # HOW: "127.0.0.1" restricts connections to localhost for local development security.
    HOST: str = "127.0.0.1"
    # USE: Network port number on which the server listens.
    # WHY: Standard port assignment for local FastAPI backend services.
    # HOW: Integer port number 8000 passed to Uvicorn.
    PORT: int = 8000

    # USE: Secret cryptographic key used to sign and verify JWT tokens.
    # WHY: Prevents token tampering and forgery; must be kept secret.
    # HOW: Pydantic Field with default development secret; overridden via JWT_SECRET_KEY in .env.
    JWT_SECRET_KEY: str = Field(
        default="memorybot-super-secure-jwt-secret-key-change-in-production-2026"
    )
    # USE: Cryptographic signing algorithm for JWT tokens.
    # WHY: HMAC with SHA-256 (HS256) provides fast, secure symmetric token signing.
    # HOW: Passed as algorithm parameter to PyJWT encode and decode methods.
    JWT_ALGORITHM: str = "HS256"
    # USE: Lifetime duration in minutes for issued JWT authentication tokens.
    # WHY: Governs how long a user session remains valid before requiring re-authentication.
    # HOW: Calculated as 60 minutes * 24 hours * 7 days (7 days total session lifespan).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # USE: Designated administrator email address for account approvals and administrative privileges.
    # WHY: Allows bootstrapping an admin user securely from environment configuration without hardcoded passwords.
    # HOW: Loaded from ADMIN_EMAIL environment variable; matches existing user accounts to grant ADMIN role.
    ADMIN_EMAIL: str = Field(default="")

    # USE: Primary Large Language Model provider identifier.
    # WHY: Determines which AI service (gemini, grok, or openai) generates chat responses by default.
    # HOW: String matching 'gemini', 'grok', or 'openai' used by LLMProvider to route requests.
    LLM_PROVIDER: str = "gemini"
    # USE: API authentication key for Google Gemini AI models.
    # WHY: Authenticates requests made to the Google Generative Language API.
    # HOW: Loaded from GEMINI_API_KEY environment variable.
    GEMINI_API_KEY: str = Field(default="")
    # USE: API authentication key for OpenAI models.
    # WHY: Authenticates requests to the OpenAI API if OpenAI provider is selected.
    # HOW: Loaded from OPENAI_API_KEY environment variable.
    OPENAI_API_KEY: str = Field(default="")
    # USE: Optional generic model override name.
    # WHY: Allows overriding default model selection across any provider from configuration.
    # HOW: Defaults to None; if provided, takes precedence over provider default models.
    MODEL_NAME: Optional[str] = Field(default=None)
    # USE: Specific Gemini model identifier to invoke.
    # WHY: Selects Google's latest multimodal conversational model (gemini-2.5-flash).
    # HOW: String passed to google-generativeai / google-genai client.
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # USE: Specific OpenAI model identifier to invoke.
    # WHY: Selects OpenAI's cost-efficient, high-performance conversational model.
    # HOW: String passed to openai client when openai provider is active.
    OPENAI_MODEL: str = "gpt-4o-mini"

    # USE: API authentication key for xAI / Grok AI services.
    # WHY: Authenticates requests to xAI API for primary generation or automatic quota fallback.
    # HOW: Loaded from XAI_API_KEY environment variable.
    XAI_API_KEY: str = Field(default="")
    # USE: Specific Grok model identifier to invoke.
    # WHY: Selects xAI's high-speed conversational model (grok-4.1-fast).
    # HOW: Passed as model name in xAI API chat completion requests.
    XAI_MODEL: str = Field(default="grok-4.1-fast")
    # USE: Base endpoint URL for xAI / Grok REST API.
    # WHY: Directs HTTP completion requests to the official xAI API gateway.
    # HOW: Configured with standard xAI v1 endpoint https://api.x.ai/v1.
    XAI_BASE_URL: str = Field(default="https://api.x.ai/v1")

    # USE: Web search engine provider identifier for real-time information retrieval.
    # WHY: Specifies which search engine powers live browsing and current event queries.
    # HOW: Defaults to "duckduckgo"; can be configured to other supported search providers.
    WEB_SEARCH_PROVIDER: str = Field(default="duckduckgo")
    # USE: Optional API key for search engine providers requiring authentication.
    # WHY: Authenticates search queries against commercial search APIs (e.g. Tavily, Bing).
    # HOW: Loaded from WEB_SEARCH_API_KEY in environment or .env.
    WEB_SEARCH_API_KEY: str = Field(default="")
    # USE: Maximum number of search result snippets retrieved per query.
    # WHY: Balances context window token usage with search result completeness.
    # HOW: Limits the number of parsed results returned to the context builder (default 5).
    WEB_SEARCH_MAX_RESULTS: int = Field(default=5)
    # USE: Network timeout in seconds for web search HTTP requests.
    # WHY: Prevents slow external search engines from hanging user chat responses.
    # HOW: Enforced as maximum wait duration during search client execution (default 10 seconds).
    WEB_SEARCH_TIMEOUT: int = Field(default=10)

    # USE: Database connection connection string / URI.
    # WHY: Specifies the database engine (SQLite, PostgreSQL) and credentials/file location.
    # HOW: Defaults to SQLite database file located in the data directory.
    DATABASE_URL: str = Field(
        default=f"sqlite:///{DATA_DIR / 'memorybot.db'}"
    )
    # USE: Flag controlling whether a default demo user account is automatically seeded.
    # WHY: Simplifies local testing and live demonstrations without manual account creation.
    # HOW: When True, database initialization checks and creates demo user if not present.
    DEMO_USER_ENABLED: bool = True

    # USE: Property decorator defining a dynamic computed getter for resolved database filesystem path.
    # WHY: Computes the absolute, normalized Path object for SQLite databases regardless of relative notation.
    # HOW: Invoked as an attribute (settings.RESOLVED_DB_PATH) returning a Path instance.
    @property
    def RESOLVED_DB_PATH(self) -> Path:
        # USE: Check whether the database URL targets an SQLite database file.
        # WHY: SQLite paths need local filesystem path resolution; PostgreSQL URLs do not.
        # HOW: Evaluates string prefix "sqlite:///".
        if self.DATABASE_URL.startswith("sqlite:///"):
            # USE: Strip the sqlite:/// protocol prefix to isolate the raw file path segment.
            # WHY: Leaves only the filesystem path string to construct a Path object.
            # HOW: Uses string.replace("sqlite:///", "").
            path_part = self.DATABASE_URL.replace("sqlite:///", "")
            # USE: Convert the stripped path string into a Path object.
            # WHY: Enables path operations and absolute path checks.
            # HOW: Instantiates Path(path_part).
            p = Path(path_part)

            # USE: Check if the extracted path is relative rather than absolute.
            # WHY: Relative paths must be anchored to PROJECT_ROOT to prevent CWD dependency issues.
            # HOW: Evaluates boolean returned by p.is_absolute().
            if not p.is_absolute():
                # USE: Anchor relative path to project root and resolve canonical path.
                # WHY: Guarantees consistent file location regardless of where server process was launched.
                # HOW: Combines PROJECT_ROOT with path_part and calls .resolve().
                return (PROJECT_ROOT / path_part).resolve()

            # USE: Return fully resolved absolute Path for absolute SQLite paths.
            # WHY: Normalizes symlinks and path separators.
            # HOW: Calls .resolve() on existing absolute path.
            return p.resolve()

        # USE: Fallback database path returned for PostgreSQL or external database connections.
        # WHY: Provides a fallback Path object for logging when using external databases.
        # HOW: Returns resolved path to memorybot.db inside DATA_DIR.
        return (DATA_DIR / "memorybot.db").resolve()

    # USE: Property decorator defining computed getter for the fully resolved database connection URL.
    # WHY: Formats connection string correctly with normalized forward slashes for SQLAlchemy compatibility on Windows.
    # HOW: Returns sanitized database connection string with posix-style forward slashes.
    @property
    def RESOLVED_DATABASE_URL(self) -> str:
        # USE: Check if DATABASE_URL is an external database (e.g. PostgreSQL, MySQL).
        # WHY: External database URLs are already complete connection URIs and should not be modified.
        # HOW: Checks if DATABASE_URL does not start with "sqlite:///".
        if not self.DATABASE_URL.startswith("sqlite:///"):
            # USE: Return the raw external database connection string unchanged.
            # WHY: Preserves host, user, password, and port parameters intact.
            # HOW: Returns self.DATABASE_URL directly.
            return self.DATABASE_URL

        # USE: Resolve the canonical local filesystem path for SQLite.
        # WHY: Ensures the SQLite database file exists in a valid directory with absolute pathing.
        # HOW: Calls self.RESOLVED_DB_PATH property.
        db_path = self.RESOLVED_DB_PATH
        # USE: Ensure the parent directory of the database file exists on disk.
        # WHY: Prevents SQLite operational errors when attempting to open a database in a nonexistent folder.
        # HOW: db_path.parent accesses parent folder; mkdir creates it safely.
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # USE: Construct and return normalized SQLite connection URL with POSIX forward slashes.
        # WHY: Windows backslashes in SQLite URLs cause parsing syntax errors in SQLAlchemy.
        # HOW: Formats string using sqlite:/// protocol and db_path.as_posix().
        return f"sqlite:///{db_path.as_posix()}"

    # USE: Maximum number of recent conversational messages included in LLM context.
    # WHY: Enforces a sliding context window to prevent exceeding LLM token limits and reduce latency.
    # HOW: Integer count passed to history retrieval queries to limit recent message slice.
    MAX_CONTEXT_MESSAGES: int = 20
    # USE: Threshold count of messages in a conversation that triggers automatic background summarization.
    # WHY: Condenses older conversation turns into concise summaries before context becomes too large.
    # HOW: When message count exceeds 14, summarizer generates a compressed narrative of older turns.
    SUMMARY_TRIGGER_THRESHOLD: int = 14

    # USE: Lifecycle hook method executed automatically after Pydantic model initialization.
    # WHY: Implements custom fallback parsing and whitespace trimming for critical API keys.
    # HOW: Pydantic v2 automatically calls model_post_init after standard field assignment.
    def model_post_init(self, __context):
        # USE: Check if GEMINI_API_KEY is empty after default environment parsing.
        # WHY: Guarantees fallback retrieval by manually parsing discovered .env files.
        # HOW: Evaluates whether self.GEMINI_API_KEY is falsy/empty.
        if not self.GEMINI_API_KEY:
            # USE: Iterate over each discovered .env file path string.
            # WHY: Checks each environment configuration file directly for the missing key.
            # HOW: Standard for loop traversing env_files_to_load.
            for env_path_str in env_files_to_load:
                # USE: Construct Path object from environment file path string.
                # WHY: Enables filesystem validation methods.
                # HOW: Instantiates Path(env_path_str).
                env_p = Path(env_path_str)
                # USE: Verify file exists and is a regular file.
                # WHY: Prevents trying to parse missing or corrupted files.
                # HOW: Checks env_p.exists() and env_p.is_file().
                if env_p.exists() and env_p.is_file():
                    # USE: Lazy-import dotenv_values dictionary parser from dotenv library.
                    # WHY: Parses .env key-value pairs into a Python dictionary without mutating os.environ.
                    # HOW: Imports dotenv_values inside the fallback loop.
                    from dotenv import dotenv_values
                    # USE: Parse key-value dictionary from the specified .env file.
                    # WHY: Extracts raw configured values directly from disk.
                    # HOW: dotenv_values(env_p) returns a dict of parsed strings.
                    vals = dotenv_values(env_p)
                    # USE: Check if GEMINI_API_KEY is present and non-empty in the parsed dictionary.
                    # WHY: Captures the API key if configured in this file.
                    # HOW: Evaluates vals.get("GEMINI_API_KEY").
                    if vals.get("GEMINI_API_KEY"):
                        # USE: Assign the parsed key to the instance GEMINI_API_KEY attribute.
                        # WHY: Populates the missing configuration setting.
                        # HOW: Directly updates self.GEMINI_API_KEY.
                        self.GEMINI_API_KEY = vals["GEMINI_API_KEY"]
                        # USE: Break out of the fallback loop once a valid key is found.
                        # WHY: Avoids redundant parsing of remaining files.
                        # HOW: Terminates the for loop immediately.
                        break

        # USE: Fallback check against raw os.environ dictionary if GEMINI_API_KEY is still empty.
        # WHY: Captures variables injected dynamically by hosting environments or parent processes.
        # HOW: Inspects os.environ.get("GEMINI_API_KEY").
        if not self.GEMINI_API_KEY and os.environ.get("GEMINI_API_KEY"):
            # USE: Assign API key directly from process environment dictionary.
            # WHY: Ensures system environment variables take effect.
            # HOW: self.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").
            self.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

        # USE: Check if GEMINI_API_KEY contains a value.
        # WHY: Sanitizes key string to eliminate user copy-paste errors (leading spaces, surrounding quotes).
        # HOW: Evaluates truthiness of self.GEMINI_API_KEY.
        if self.GEMINI_API_KEY:
            # USE: Strip surrounding whitespace, single quotes, and double quotes from GEMINI_API_KEY.
            # WHY: Prevents invalid authentication errors caused by accidentally quoted env values like '"AIza..."'.
            # HOW: Chains .strip().strip("'").strip('"') to sanitize the string.
            self.GEMINI_API_KEY = self.GEMINI_API_KEY.strip().strip("'").strip('"')

        # USE: Check if OPENAI_API_KEY is empty after default environment parsing.
        # WHY: Triggers fallback manual parsing for OpenAI credentials.
        # HOW: Evaluates whether self.OPENAI_API_KEY is falsy.
        if not self.OPENAI_API_KEY:
            # USE: Iterate through discovered .env file paths to locate OPENAI_API_KEY.
            # WHY: Checks all candidate configuration files.
            # HOW: Standard for-in loop over env_files_to_load.
            for env_path_str in env_files_to_load:
                # USE: Convert string to Path object.
                # WHY: Enables filesystem validation.
                # HOW: Instantiates Path(env_path_str).
                env_p = Path(env_path_str)
                # USE: Verify that path exists and is a file.
                # WHY: Ensures file can be opened safely.
                # HOW: Checks env_p.exists() and env_p.is_file().
                if env_p.exists() and env_p.is_file():
                    # USE: Lazy-import dotenv_values.
                    # WHY: Reads key-value pairs without side effects.
                    # HOW: Imports dotenv_values from dotenv.
                    from dotenv import dotenv_values
                    # USE: Parse key-value dictionary from the file.
                    # WHY: Retrieves parsed variables.
                    # HOW: Calls dotenv_values(env_p).
                    vals = dotenv_values(env_p)
                    # USE: Check if OPENAI_API_KEY is present in the file.
                    # WHY: Captures configured OpenAI key.
                    # HOW: Evaluates vals.get("OPENAI_API_KEY").
                    if vals.get("OPENAI_API_KEY"):
                        # USE: Assign the parsed key to self.OPENAI_API_KEY.
                        # WHY: Populates the configuration field.
                        # HOW: Updates instance attribute.
                        self.OPENAI_API_KEY = vals["OPENAI_API_KEY"]
                        # USE: Stop checking further files.
                        # WHY: Key has already been resolved.
                        # HOW: Terminates the loop via break.
                        break

        # USE: Fallback check against os.environ for OPENAI_API_KEY.
        # WHY: Captures keys injected into process environment.
        # HOW: Checks os.environ.get("OPENAI_API_KEY").
        if not self.OPENAI_API_KEY and os.environ.get("OPENAI_API_KEY"):
            # USE: Assign value from process environment.
            # WHY: Applies system environment variable.
            # HOW: Updates self.OPENAI_API_KEY.
            self.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
        # USE: Check if OPENAI_API_KEY is populated.
        # WHY: Sanitizes whitespace and quotes.
        # HOW: Evaluates truthiness of self.OPENAI_API_KEY.
        if self.OPENAI_API_KEY:
            # USE: Strip whitespace, single quotes, and double quotes from OPENAI_API_KEY.
            # WHY: Prevents authorization failure due to formatting artifacts.
            # HOW: Invokes .strip().strip("'").strip('"').
            self.OPENAI_API_KEY = self.OPENAI_API_KEY.strip().strip("'").strip('"')

        # USE: Check if WEB_SEARCH_API_KEY is empty.
        # WHY: Triggers fallback manual parsing for web search engine credentials.
        # HOW: Evaluates whether self.WEB_SEARCH_API_KEY is falsy.
        if not self.WEB_SEARCH_API_KEY:
            # USE: Loop over discovered .env paths.
            # WHY: Scans files for search API credentials.
            # HOW: Standard for loop.
            for env_path_str in env_files_to_load:
                # USE: Create Path instance from path string.
                # WHY: Enables existence check.
                # HOW: Instantiates Path(env_path_str).
                env_p = Path(env_path_str)
                # USE: Verify file existence.
                # WHY: Confirms file is accessible.
                # HOW: Checks env_p.exists() and env_p.is_file().
                if env_p.exists() and env_p.is_file():
                    # USE: Lazy-import dotenv_values.
                    # WHY: Non-destructive environment parsing.
                    # HOW: Imports dotenv_values from dotenv.
                    from dotenv import dotenv_values
                    # USE: Parse configuration values.
                    # WHY: Retrieves parsed dictionary.
                    # HOW: Calls dotenv_values(env_p).
                    vals = dotenv_values(env_p)
                    # USE: Check if WEB_SEARCH_API_KEY is defined.
                    # WHY: Captures search key if present.
                    # HOW: Evaluates vals.get("WEB_SEARCH_API_KEY").
                    if vals.get("WEB_SEARCH_API_KEY"):
                        # USE: Assign found key.
                        # WHY: Populates configuration.
                        # HOW: Updates self.WEB_SEARCH_API_KEY.
                        self.WEB_SEARCH_API_KEY = vals["WEB_SEARCH_API_KEY"]
                        # USE: Break from loop.
                        # WHY: Key found.
                        # HOW: Terminates iteration.
                        break
        # USE: Check os.environ fallback for WEB_SEARCH_API_KEY.
        # WHY: Captures container-level search API key.
        # HOW: Checks os.environ.get("WEB_SEARCH_API_KEY").
        if not self.WEB_SEARCH_API_KEY and os.environ.get("WEB_SEARCH_API_KEY"):
            # USE: Assign value from process environment.
            # WHY: Applies environment variable.
            # HOW: Updates self.WEB_SEARCH_API_KEY.
            self.WEB_SEARCH_API_KEY = os.environ.get("WEB_SEARCH_API_KEY", "")
        # USE: Check if WEB_SEARCH_API_KEY is populated.
        # WHY: Sanitizes search API key string.
        # HOW: Evaluates truthiness of self.WEB_SEARCH_API_KEY.
        if self.WEB_SEARCH_API_KEY:
            # USE: Strip whitespace and quotes.
            # WHY: Cleans up formatting artifacts.
            # HOW: Invokes .strip().strip("'").strip('"').
            self.WEB_SEARCH_API_KEY = self.WEB_SEARCH_API_KEY.strip().strip("'").strip('"')

    # USE: Define Pydantic Settings configuration dictionary.
    # WHY: Directs Pydantic to read specified .env files, use UTF-8 encoding, and ignore unknown extra fields.
    # HOW: SettingsConfigDict sets env_file, env_file_encoding, and extra="ignore".
    model_config = SettingsConfigDict(
        # USE: Tuple of environment file paths to load.
        # WHY: Informs Pydantic which .env files to read during model instantiation.
        # HOW: Converts env_files_to_load list to an immutable tuple.
        env_file=tuple(env_files_to_load),
        # USE: Character encoding for parsing .env files.
        # WHY: Ensures proper unicode handling across operating systems.
        # HOW: Configured to standard "utf-8".
        env_file_encoding="utf-8",
        # USE: Handling strategy for unexpected extra fields found in environment.
        # WHY: Prevents Pydantic validation errors when system environment contains unrelated variables.
        # HOW: "ignore" safely discards unmodeled environment keys.
        extra="ignore"
    )

# USE: Instantiate the global settings singleton instance.
# WHY: Allows any module in the application to import 'settings' directly without re-reading .env files repeatedly.
# HOW: Instantiates Settings() which runs Pydantic initialization and model_post_init hooks.
settings = Settings()