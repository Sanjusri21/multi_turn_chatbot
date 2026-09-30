# USE: Import Python's built-in logging framework for structured application diagnostics.
# WHY: Standardizes event logging, log level categorization (INFO, WARNING, ERROR), and formatting across the entire app.
# HOW: Exposes getLogger, Formatter, Handler, and logging level constants (INFO, DEBUG, ERROR) to manage log streams.
import logging

# USE: Import the system module to access standard output stream (sys.stdout).
# WHY: Directs log messages to stdout so container logs (Docker, cloud runtimes) and developer consoles capture logs cleanly.
# HOW: sys.stdout provides an unbuffered or line-buffered character stream connected to terminal output.
import sys

# USE: Function definition to initialize and configure the application logger.
# WHY: Centralizes logging setup in a single reusable function with configurable log severity levels.
# HOW: Accepts a string log level (defaulting to "INFO") and returns a configured logging.Logger instance.
def setup_logging(level: str = "INFO") -> logging.Logger:
    # USE: Define the structured string format pattern for individual log line entries.
    # WHY: Ensures every log entry consistently displays exact timestamp, severity level, logger name, and message body.
    # HOW: Format interpolation tags like %(asctime)s, %(levelname)s, %(name)s, and %(message)s are replaced by logging records.
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    # USE: Define the date and time format string for the timestamp tag.
    # WHY: Provides an unambiguous standard ISO-like date and time format without confusing milliseconds.
    # HOW: Parsed by strftime to format timestamps as YYYY-MM-DD HH:MM:SS.
    date_format = "%Y-%m-%d %H:%M:%S"

    # USE: Convert string level representation into an integer logging level constant.
    # WHY: Safely maps user inputs or config strings like 'INFO' or 'DEBUG' to internal constants (20, 10) with a safe default.
    # HOW: getattr inspects the logging module for the uppercase attribute name, returning logging.INFO (20) if not found.
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # USE: Retrieve or instantiate the named logger singleton for the application namespace.
    # WHY: Scopes all MemoryBot log events under the distinct "memorybot" hierarchy to avoid collisions with third-party libraries.
    # HOW: logging.getLogger("memorybot") fetches the existing Logger with this name or creates a new one if it does not exist.
    logger = logging.getLogger("memorybot")
    # USE: Check whether the logger already possesses output stream handlers attached.
    # WHY: Prevents adding duplicate StreamHandlers if setup_logging is called more than once, which would cause duplicate log lines.
    # HOW: Evaluates the length/truthiness of the logger.handlers list.
    if not logger.handlers:
        # USE: Set the minimum severity threshold for messages captured by this logger.
        # WHY: Filters out messages below this threshold (e.g. ignores DEBUG messages when set to INFO).
        # HOW: Compares the numeric level of incoming log calls and drops records lower than numeric_level.
        logger.setLevel(numeric_level)
        # USE: Instantiate a stream handler directed to standard output (sys.stdout).
        # WHY: Writes log records to stdout rather than stderr so logs are captured as standard stream logs by process managers.
        # HOW: Wraps sys.stdout in a StreamHandler that processes logging.LogRecord instances.
        handler = logging.StreamHandler(sys.stdout)
        # USE: Attach the custom formatter to the stream handler.
        # WHY: Applies the structured timestamp, level, and message formatting string to each emitted line.
        # HOW: logging.Formatter compiles log_format and date_format to transform LogRecord objects into formatted strings.
        handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))
        # USE: Register the configured stream handler onto the logger instance.
        # WHY: Activates message dispatch to sys.stdout whenever a log method (info, error, warning) is called.
        # HOW: Appends the handler to the internal logger.handlers list.
        logger.addHandler(handler)

    # USE: Return the configured Logger object back to the caller.
    # WHY: Provides immediate access to the ready-to-use logger instance.
    # HOW: Hands back the reference to the singleton logger.
    return logger

# USE: Instantiate the primary module-level logger instance on import.
# WHY: Allows any module in the backend to cleanly write 'from app.core.logging_config import logger' and log immediately.
# HOW: Invokes setup_logging() with default INFO level and assigns the returned Logger instance to the global variable.
logger = setup_logging()
