# USE: Import the operating system module for cryptographic randomness generation.
# WHY: Needed to generate cryptographically secure random bytes for password salting via os.urandom().
# HOW: Interfaces with the underlying OS CSPRNG (Cryptographically Secure Pseudo-Random Number Generator).
import os

# USE: Import Keyed-Hashing for Message Authentication (HMAC) module.
# WHY: Provides constant-time string/hash comparison to prevent timing attack vulnerabilities during password verification.
# HOW: hmac.compare_digest takes the same amount of CPU cycles regardless of where characters mismatch.
import hmac

# USE: Import Python's built-in secure hash and message digest library.
# WHY: Used to compute PBKDF2-HMAC-SHA256 password hashes without requiring external native C-extensions like bcrypt.
# HOW: hashlib.pbkdf2_hmac stretches password strings through 100,000 iterations of SHA-256 hashing.
import hashlib

# USE: Import PyJWT library for encoding and decoding JSON Web Tokens.
# WHY: Implements stateless, cryptographically signed authentication tokens passed between client and server.
# HOW: Encodes payload dictionaries into base64url-encoded signed tokens using HMAC-SHA256 secrets.
import jwt

# USE: Import date, time delta, and UTC timezone primitives.
# WHY: Required to calculate precise token expiration timestamps (exp) and issued-at timestamps (iat).
# HOW: Uses timezone-aware UTC datetime instances to avoid clock drift and daylight savings issues.
from datetime import datetime, timedelta, timezone

# USE: Import type hints for optional values and dictionaries.
# WHY: Improves static analysis, code clarity, and editor autocompletion for token payloads.
# HOW: Interpreted by IDEs and type checkers to enforce function signature safety.
from typing import Optional, Dict, Any

# USE: Import FastAPI dependency injection primitives and HTTP exception classes.
# WHY: Enables dependency injection of user credentials and standard HTTP 401 Unauthorized responses.
# HOW: Depends injects callable results into route handlers; HTTPException halts request flow with an HTTP status code.
from fastapi import Depends, HTTPException, status

# USE: Import HTTP Bearer authentication scheme handlers from FastAPI Security.
# WHY: Extracts Bearer tokens automatically from incoming HTTP 'Authorization: Bearer <token>' headers.
# HOW: Inspects request headers and yields HTTPAuthorizationCredentials containing the token string.
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# USE: Import SQLAlchemy Session type hint.
# WHY: Annotates the database session parameter passed via dependency injection for user lookups.
# HOW: Represents an active database connection and ORM unit of work.
from sqlalchemy.orm import Session

# USE: Import global application settings instance.
# WHY: Retrieves JWT secret keys, signing algorithms, and token expiration lifetimes configured in the environment.
# HOW: Accesses attributes such as JWT_SECRET_KEY, JWT_ALGORITHM, and ACCESS_TOKEN_EXPIRE_MINUTES.
from app.core.config import settings

# USE: Import database session dependency generator.
# WHY: Provides an active database session for querying the user database during authentication checks.
# HOW: FastAPI executes get_db() to yield a session and closes it cleanly after the request completes.
from app.core.database import get_db

# USE: Instantiate HTTPBearer security scheme with auto_error disabled.
# WHY: Setting auto_error=False prevents FastAPI from prematurely throwing generic 403 errors, allowing custom 401 messages.
# HOW: Returns None instead of throwing if the Authorization header is absent, handing control to get_current_user.
security_bearer = HTTPBearer(auto_error=False)

# USE: Function definition for cryptographically hashing plain-text user passwords.
# WHY: Passwords must never be stored in plain text to protect user credentials if the database is compromised.
# HOW: Takes a plain password string, generates a unique random salt, computes PBKDF2 hash, and returns salt$hash.
def hash_password(password: str) -> str:
    # USE: Generate 16 cryptographically random bytes.
    # WHY: Salt guarantees that identical passwords generate completely different hashes, neutralizing rainbow table attacks.
    # HOW: os.urandom(16) pulls 128 bits of entropy directly from the operating system's cryptographic random pool.
    salt = os.urandom(16)
    # USE: Derive cryptographic key using PBKDF2 with SHA-256 and 100,000 iterations.
    # WHY: The high iteration count deliberately slows down brute-force attacks while remaining fast for legitimate logins.
    # HOW: Encodes password as UTF-8 bytes and iteratively hashes it with the salt using sha256.
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    # USE: Return formatted string combining salt and key in hexadecimal encoding separated by $.
    # WHY: Stores both the salt and the hash in a single database column without requiring separate database fields.
    # HOW: salt.hex() and key.hex() produce ASCII hex representations joined by the dollar delimiter.
    return f"{salt.hex()}${key.hex()}"

# USE: Function definition to verify if a plaintext password matches a stored salt$hash string.
# WHY: Authenticates user credentials during the login flow without ever decrypting or storing plaintext.
# HOW: Extracts the salt from the stored hash, hashes the candidate password with that salt, and compares results.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # USE: Begin protected try block to safely handle malformed hash strings.
    # WHY: If a stored password has invalid format or corrupted hex characters, the app must reject without crashing.
    # HOW: Catches split, hex-decode, or length exceptions and safely returns False.
    try:
        # USE: Split stored string by '$' into salt and hash hexadecimal components.
        # WHY: Separates the public salt bytes from the expected cryptographic key bytes.
        # HOW: string.split("$") returns a 2-element tuple of hex strings.
        salt_hex, key_hex = hashed_password.split("$")
        # USE: Convert hexadecimal salt string back into raw byte sequence.
        # WHY: PBKDF2 algorithm requires raw byte input for salting.
        # HOW: bytes.fromhex parses pairs of hexadecimal characters into raw binary bytes.
        salt = bytes.fromhex(salt_hex)
        # USE: Convert hexadecimal expected key string back into raw byte sequence.
        # WHY: Required for constant-time byte comparison against the freshly computed hash.
        # HOW: bytes.fromhex reconstructs the original 32-byte key.
        expected_key = bytes.fromhex(key_hex)
        # USE: Recompute PBKDF2 hash using the candidate plaintext password and original salt.
        # WHY: If the password is correct, hashing with the exact same salt and iteration count yields the identical key.
        # HOW: Runs PBKDF2-HMAC-SHA256 with 100,000 iterations on the candidate password bytes.
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000)
        # USE: Perform constant-time cryptographic comparison between computed key and expected key.
        # WHY: Prevents side-channel timing attacks that deduce characters based on microsecond comparison delays.
        # HOW: hmac.compare_digest compares all bytes in equal time, returning True only if keys match completely.
        return hmac.compare_digest(key, expected_key)
    # USE: Catch any format or conversion exceptions.
    # WHY: Shields the application from crashes due to invalid hash strings.
    # HOW: Handles ValueError, IndexError, etc., and gracefully returns False.
    except Exception:
        # USE: Return boolean False indicating failed password verification.
        # WHY: Safely denies authentication when an error occurs during comparison.
        # HOW: Hands boolean False back to caller.
        return False

# USE: Function definition to create a digitally signed JWT access token.
# WHY: Issues stateless session tokens for authenticated users to authorize subsequent API requests.
# HOW: Takes data payload dictionary and expiration delta, injects exp/iat timestamps, and signs with JWT secret.
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    # USE: Create a shallow copy of the input dictionary.
    # WHY: Prevents modifying the caller's original dictionary when adding token claims like exp and iat.
    # HOW: dict.copy() creates a new dictionary with the same keys and values.
    to_encode = data.copy()
    # USE: Capture the current UTC timestamp as a timezone-aware datetime object.
    # WHY: Serves as the baseline timestamp for issued-at (iat) and expiration (exp) token calculations.
    # HOW: datetime.now(timezone.utc) gets the current UTC system clock time.
    now = datetime.now(timezone.utc)
    # USE: Check if a custom expiration timedelta was provided.
    # WHY: Allows callers to issue shorter or longer-lived tokens (e.g. remember-me vs standard sessions).
    # HOW: Evaluates whether expires_delta is not None.
    if expires_delta:
        # USE: Compute expiration timestamp by adding the custom timedelta to current time.
        # WHY: Applies the caller's specific token lifetime.
        # HOW: Datetime addition creates a future datetime instance.
        expire = now + expires_delta
    # USE: Fallback when no custom expiration delta is provided.
    # WHY: Enforces the default system-wide token lifetime defined in configuration settings.
    # HOW: Adds ACCESS_TOKEN_EXPIRE_MINUTES from settings to current UTC time.
    else:
        # USE: Calculate default expiration timestamp based on application settings.
        # WHY: Enforces standard session lifetime (e.g. 7 days).
        # HOW: Constructs timedelta with settings.ACCESS_TOKEN_EXPIRE_MINUTES and adds to now.
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # USE: Inject expiration ('exp') and issued-at ('iat') claims into the payload dictionary.
    # WHY: Standard JWT RFC 7519 claims required for validating token freshness and rejecting expired tokens.
    # HOW: dict.update modifies to_encode with the calculated datetime values.
    to_encode.update({"exp": expire, "iat": now})
    # USE: Cryptographically sign and encode the dictionary into a JWT string.
    # WHY: Produces a tamper-proof compact token string that clients can send in HTTP headers.
    # HOW: jwt.encode serializes payload to JSON, encodes to Base64URL, and generates HMAC-SHA256 signature.
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    # USE: Return the generated JWT string.
    # WHY: Returns the bearer token for transmission to the client in login/registration responses.
    # HOW: Hands back the encoded token string.
    return encoded_jwt

# USE: Function definition to decode, verify, and extract claims from a JWT string.
# WHY: Validates token integrity and authenticity on incoming authenticated requests.
# HOW: Decodes token using secret key and algorithm, checking signature validity and expiration automatically.
def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    # USE: Begin protected try block to handle signature or decoding exceptions.
    # WHY: Invalid, forged, or expired tokens must be safely rejected without throwing unhandled server errors.
    # HOW: Catches PyJWTError exceptions thrown during signature verification.
    try:
        # USE: Decode token and verify signature using the application secret key and allowed algorithms.
        # WHY: Guarantees that the token was signed by this server and has not expired or been tampered with.
        # HOW: jwt.decode verifies HMAC signature, checks 'exp' timestamp against current time, and parses JSON payload.
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        # USE: Return the decoded claims payload dictionary.
        # WHY: Provides caller with user id ('sub') and any other encoded session claims.
        # HOW: Returns dictionary containing token claims.
        return payload
    # USE: Catch JWT decoding errors, expiration errors, or unexpected exceptions.
    # WHY: Safely handles expired, malformed, or tampered token strings.
    # HOW: Intercepts PyJWTError (ExpiredSignatureError, InvalidSignatureError, etc.) and general exceptions.
    except (jwt.PyJWTError, Exception):
        # USE: Return None to signal invalid or unusable token.
        # WHY: Allows callers to cleanly trigger HTTP 401 Unauthorized responses.
        # HOW: Hands back None value.
        return None

# USE: FastAPI dependency function to extract and authenticate the current user from Bearer credentials.
# WHY: Secures protected endpoints by verifying the token and injecting the User ORM object into route handlers.
# HOW: Injected via Depends(get_current_user); extracts token, validates claims, and queries user from DB.
def get_current_user(
    # USE: Dependency parameter extracting HTTP Bearer token credentials from incoming request headers.
    # WHY: Automatically parses the Authorization header containing 'Bearer <token>'.
    # HOW: FastAPI security evaluates security_bearer dependency on the incoming request.
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    # USE: Dependency parameter providing an active SQLAlchemy database session.
    # WHY: Needed to query the database to verify the user exists and retrieve their full profile.
    # HOW: FastAPI calls get_db() generator to provide an open Session instance.
    db: Session = Depends(get_db)
):
    # USE: Guard check verifying that Bearer credentials were provided in the request.
    # WHY: Rejects unauthenticated requests immediately if the Authorization header is missing.
    # HOW: Evaluates whether credentials is None.
    if not credentials:
        # USE: Raise HTTP 401 Unauthorized exception with WWW-Authenticate header.
        # WHY: Informs the HTTP client that credentials are required to access this resource.
        # HOW: Halts route execution and returns 401 status with custom error detail.
        raise HTTPException(
            # USE: Set HTTP 401 Unauthorized status code.
            # WHY: Standard HTTP status for missing or unprovided authentication.
            # HOW: Transmitted in HTTP response header.
            status_code=status.HTTP_401_UNAUTHORIZED,
            # USE: Human-readable error message explaining why the request was rejected.
            # WHY: Instructs the frontend or user to log in.
            # HOW: Included in the JSON error response body.
            detail="Authentication required. Please log in.",
            # USE: Attach WWW-Authenticate challenge header.
            # WHY: Conforms to RFC 7235 specification for HTTP authentication challenges.
            # HOW: Sets WWW-Authenticate: Bearer header on the response.
            headers={"WWW-Authenticate": "Bearer"},
        )

    # USE: Decode the JWT token string extracted from the credentials container.
    # WHY: Verifies cryptographic signature and extracts encoded claims payload.
    # HOW: Calls decode_access_token passing credentials.credentials (the raw token string).
    payload = decode_access_token(credentials.credentials)
    # USE: Check if the token payload is invalid, expired, or missing the subject ('sub') claim.
    # WHY: Rejects tampered, expired, or malformed tokens lacking user identification.
    # HOW: Checks if payload is None or if "sub" key is absent from the dictionary.
    if not payload or "sub" not in payload:
        # USE: Raise HTTP 401 Unauthorized exception for invalid tokens.
        # WHY: Informs client that the supplied token has expired or is invalid and requires re-login.
        # HOW: Halts execution and returns 401 response with WWW-Authenticate header.
        raise HTTPException(
            # USE: Set HTTP 401 Unauthorized status code.
            # WHY: Signals expired or invalid session token.
            # HOW: Sent as HTTP status code.
            status_code=status.HTTP_401_UNAUTHORIZED,
            # USE: Clear error message prompting re-authentication.
            # WHY: Directs client to refresh tokens or prompt the user for credentials.
            # HOW: Serialized into JSON response.
            detail="Invalid or expired token. Please log in again.",
            # USE: Attach Bearer authentication challenge header.
            # WHY: Standards-compliant response for expired Bearer tokens.
            # HOW: Sets HTTP response header.
            headers={"WWW-Authenticate": "Bearer"},
        )

    # USE: Extract the user identifier from the token's subject ('sub') claim.
    # WHY: Identifies the exact user primary key stored when the token was minted.
    # HOW: Reads string or integer value from payload["sub"].
    user_id = payload["sub"]
    # USE: Lazy-import the User ORM model from app.models.user.
    # WHY: Prevents circular import issues between models, database, and security modules during startup.
    # HOW: Imports User class dynamically within the function execution scope.
    from app.models.user import User
    # USE: Query the database for the user record matching the user_id.
    # WHY: Ensures the user account still exists in the database and has not been deleted or deactivated.
    # HOW: Executes SELECT query on the users table with WHERE id = user_id and returns the first record.
    user = db.query(User).filter(User.id == user_id).first()
    # USE: Check if no user was found in the database for the given ID.
    # WHY: Prevents valid tokens belonging to deleted or nonexistent users from gaining access.
    # HOW: Evaluates whether user is None.
    if not user:
        # USE: Raise HTTP 401 Unauthorized exception when user account does not exist.
        # WHY: Denies access and informs the client that the identity is unrecognized.
        # HOW: Halts request processing and returns 401 status.
        raise HTTPException(
            # USE: Set HTTP 401 Unauthorized status code.
            # WHY: Rejects requests with identities that no longer exist.
            # HOW: Sent as HTTP status code.
            status_code=status.HTTP_401_UNAUTHORIZED,
            # USE: Informative error message indicating missing user.
            # WHY: Clarifies reason for authorization refusal.
            # HOW: Serialized into JSON detail body.
            detail="User not found.",
            # USE: Challenge header for Bearer authentication.
            # WHY: Standard compliance for unauthorized access.
            # HOW: Sets WWW-Authenticate header.
            headers={"WWW-Authenticate": "Bearer"},
        )

    # USE: Return the authenticated User ORM model instance.
    # WHY: Injected directly into the calling route handler for authorization checks and user-scoped data queries.
    # HOW: FastAPI delivers the returned User object to any endpoint parameter declaring Depends(get_current_user).
    return user

# USE: FastAPI dependency function to ensure the current authenticated user has an APPROVED account.
# WHY: Protects Zara endpoints (chat, conversations, memories, files, voice) from unapproved or suspended users.
# HOW: Injected via Depends(get_current_approved_user); checks account_status and role, raising 403 Forbidden if not approved.
def get_current_approved_user(
    current_user: Any = Depends(get_current_user)
) -> Any:
    # USE: Allow administrators access regardless of separate status checks.
    # WHY: Admins must always retain management access to the system.
    # HOW: Checks if user.role is 'ADMIN' and returns immediately.
    if getattr(current_user, "role", "USER") == "ADMIN":
        return current_user

    # USE: Retrieve the account status string from the authenticated user model.
    # WHY: Governs access control based on user approval lifecycle.
    # HOW: Reads current_user.account_status, defaulting to 'PENDING'.
    status_val = getattr(current_user, "account_status", "PENDING")

    # USE: Check if account status is APPROVED.
    # WHY: Only approved users may interact with Zara conversational services.
    # HOW: Returns the current_user if status strictly equals 'APPROVED'.
    if status_val == "APPROVED":
        return current_user

    # USE: Specific error message for accounts still waiting for administrator review.
    # WHY: Informs user that their account is pending approval without misleading them.
    # HOW: Raises 403 Forbidden with exact required detail string.
    if status_val == "PENDING":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval."
        )

    # USE: Specific error message for rejected accounts.
    # WHY: Informs user that their registration request was declined.
    # HOW: Raises 403 Forbidden.
    if status_val == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account request was rejected. Please contact the administrator."
        )

    # USE: Specific error message for suspended accounts.
    # WHY: Informs user that their access privileges have been revoked by an administrator.
    # HOW: Raises 403 Forbidden.
    if status_val == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact the administrator."
        )

    # USE: Generic fallback rejection for unrecognized non-approved account statuses.
    # WHY: Defense-in-depth against unexpected database state.
    # HOW: Raises HTTP 403 Forbidden.
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. Your account is not approved."
    )

# USE: FastAPI dependency function ensuring the authenticated user holds the ADMIN role.
# WHY: Secures administrative endpoints (approving, rejecting, listing pending users) exclusively for administrators.
# HOW: Injected via Depends(get_current_admin_user); checks current_user.role == 'ADMIN', raising 403 Forbidden if not.
def get_current_admin_user(
    current_user: Any = Depends(get_current_user)
) -> Any:
    # USE: Verify that the user's role is strictly ADMIN.
    # WHY: Prevents standard users or pending accounts from accessing administrative functions.
    # HOW: Compares current_user.role string against 'ADMIN'.
    if getattr(current_user, "role", "USER") != "ADMIN":
        # USE: Raise HTTP 403 Forbidden for non-admin accounts.
        # WHY: Blocks unauthorized access to admin capabilities.
        # HOW: Halts request processing and returns 403 with error detail.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required."
        )

    # USE: Return the verified administrator user instance.
    # WHY: Provides the admin model to route handlers for audit logging (e.g. approved_by).
    # HOW: Delivers current_user to endpoint parameter.
    return current_user

