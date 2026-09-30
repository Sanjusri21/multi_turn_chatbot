// USE: Define the backend API root base URL.
// WHY: Allows configurable API targeting across local development (proxying to /api) and production deployments.
// HOW: Reads Vite environment variable VITE_API_BASE_URL if defined, falling back to relative '/api'.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// USE: Export primary asynchronous HTTP request wrapper function.
// WHY: Centralizes authentication token injection, headers formatting, error interception, and JSON parsing.
// HOW: Accepts an endpoint string and Fetch options object, returning parsed response data or throwing an Error.
export async function request(endpoint, options = {}) {
  // USE: Construct the complete request target URL string.
  // WHY: Combines the base API path with the specific resource endpoint.
  // HOW: Template literal concatenates BASE_URL and endpoint (e.g. '/api' + '/chat').
  const url = `${BASE_URL}${endpoint}`;
  // USE: Retrieve the stored JWT bearer token from browser LocalStorage.
  // WHY: Authenticated endpoints require this token in the HTTP Authorization header.
  // HOW: localStorage.getItem('token') returns the saved JWT string or null if not logged in.
  const token = localStorage.getItem('token');

  // USE: Initialize the headers dictionary merging caller-supplied headers.
  // WHY: Preserves caller headers while allowing this wrapper to inject default authorization and content-type headers.
  // HOW: Uses object spread syntax (...options.headers) to clone existing headers into a new object.
  const headers = {
    ...options.headers,
  };

  // USE: Guard check to determine if a stored authentication token exists.
  // WHY: If the user is logged in, all outgoing API calls should carry their credentials.
  // HOW: Evaluates whether the 'token' variable is truthy (non-null and non-empty).
  if (token) {
    // USE: Inject the Authorization HTTP header formatted as a Bearer token.
    // WHY: Adheres to the OAuth 2.0 / RFC 6750 Bearer Token specification expected by FastAPI security.
    // HOW: Assigns 'Bearer <token>' string to the Authorization property of the headers object.
    headers['Authorization'] = `Bearer ${token}`;
  }

  // USE: Check if request has a payload body and ensure it is not FormData (e.g. file uploads).
  // WHY: JSON payloads require Content-Type: application/json; FormData must omit it so the browser sets multipart boundary.
  // HOW: Checks options.body truthiness and uses instanceof operator to exclude FormData instances.
  if (options.body && !(options.body instanceof FormData)) {
    // USE: Set Content-Type header to application/json.
    // WHY: Informs backend body parser to deserialize incoming request stream as JSON.
    // HOW: Sets headers['Content-Type'] = 'application/json'.
    headers['Content-Type'] = 'application/json';
  }

  // USE: Begin protected try block for network request dispatch and response handling.
  // WHY: Traps network failures, HTTP error responses, and JSON deserialization errors in a single catch block.
  // HOW: Wraps asynchronous fetch call and response status evaluations.
  try {
    // USE: Execute asynchronous HTTP fetch request against the constructed URL.
    // WHY: Performs the actual network transfer over HTTP/HTTPS to the backend server.
    // HOW: Invokes native window.fetch with target url and combined options including injected headers.
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // USE: Inspect response status code to check for HTTP 401 Unauthorized errors.
    // WHY: Detects expired or revoked session tokens so the frontend can reset authentication state.
    // HOW: Compares response.status integer against 401.
    if (response.status === 401) {
      // USE: Guard check to ensure 401 did not originate from the login or signup forms themselves.
      // WHY: Wrong passwords on /auth/login should display an error message, not trigger an unexpected global logout event.
      // HOW: String method startsWith checks whether endpoint matches '/auth/login' or '/auth/signup'.
      if (!endpoint.startsWith('/auth/login') && !endpoint.startsWith('/auth/signup')) {
        // USE: Clear the invalid JWT token from browser local storage.
        // WHY: Prevents subsequent failing authenticated requests with dead credentials.
        // HOW: Calls localStorage.removeItem('token').
        localStorage.removeItem('token');
        // USE: Clear the cached user profile object from browser local storage.
        // WHY: Clears user state so UI re-renders in unauthenticated view.
        // HOW: Calls localStorage.removeItem('user').
        localStorage.removeItem('user');
        // USE: Dispatch custom global DOM event 'auth:logout' on the window object.
        // WHY: Notifies all React/Vue/vanilla listeners and UI components immediately to switch to login view.
        // HOW: window.dispatchEvent broadcasts a new Event instance across the browser tab.
        window.dispatchEvent(new Event('auth:logout'));
      }
    }

    // USE: Verify whether the HTTP response represents a 2xx success status code.
    // WHY: Fetch does not automatically reject promises on 4xx/5xx HTTP errors; manual checking is required.
    // HOW: response.ok is a boolean property true for HTTP status codes in range 200-299.
    if (!response.ok) {
      // USE: Initialize fallback error message string containing the HTTP status code.
      // WHY: Guarantees an informative fallback error description if the server returns non-JSON error bodies.
      // HOW: Formats string with response.status integer.
      let errorMessage = `HTTP error! status: ${response.status}`;
      // USE: Try block to attempt parsing JSON error payload from the response body.
      // WHY: FastAPI returns structured JSON like {"detail": "Error description"} that should be shown to users.
      // HOW: Executes response.json() inside try-catch to safely handle plain HTML/text error pages.
      try {
        // USE: Parse response stream as JSON data.
        // WHY: Extracts backend exception detail.
        // HOW: Awaits response.json() promise.
        const errorData = await response.json();
        // USE: Extract detail message if present in error payload.
        // WHY: Provides the human-readable explanation emitted by the backend exception handler.
        // HOW: Reads errorData.detail, falling back to status string if absent.
        errorMessage = errorData.detail || errorMessage;
      // USE: Catch clause handling non-JSON error responses.
      // WHY: Prevents JSON parse errors from crashing error extraction.
      // HOW: Catches SyntaxError when response is HTML or plain text.
      } catch (e) {
        // USE: Fallback error message to HTTP status text.
        // WHY: Uses browser standard status string (e.g. 'Not Found', 'Internal Server Error').
        // HOW: Reads response.statusText property.
        errorMessage = response.statusText || errorMessage;
      }
      // USE: Throw standard JavaScript Error object containing the extracted error message.
      // WHY: Rejects the promise and propagates the error to calling UI components for toast/alert rendering.
      // HOW: Instantiates and throws new Error(errorMessage).
      throw new Error(errorMessage);
    }

    // USE: Check if response returned HTTP 204 No Content.
    // WHY: DELETE and empty PUT/POST requests return 204 with no body; calling .json() on them would throw an error.
    // HOW: Checks if response.status strictly equals 204.
    if (response.status === 204) {
      // USE: Return null for empty 204 responses.
      // WHY: Signals successful operation completion without expecting a payload.
      // HOW: Exits function returning null.
      return null;
    }

    // USE: Parse and return the successful response body as parsed JavaScript object.
    // WHY: Delivers the deserialized API data payload to the calling component.
    // HOW: Awaits response.json() and returns the resolved object.
    return await response.json();
  // USE: Catch block intercepting errors thrown in the try block or network fetch failure.
  // WHY: Handles logging diagnostics and re-throwing errors to caller.
  // HOW: Receives error instance caught during execution.
  } catch (error) {
    // USE: Guard check filtering out benign 401 logs from initial session check (/auth/me).
    // WHY: Suppresses noisy console error logs on initial app boot when a visitor is simply not logged in yet.
    // HOW: Checks whether endpoint string does not equal '/auth/me'.
    if (endpoint !== '/auth/me') {
      // USE: Log formatted API error message to browser developer console.
      // WHY: Assists developers in inspecting failing URLs and network errors during debugging.
      // HOW: Prints URL and error object via console.error.
      console.error(`API Error on ${url}:`, error);
    }
    // USE: Re-throw the error to the caller function.
    // WHY: Allows the initiating UI component or service to handle errors (e.g. displaying error alerts).
    // HOW: Re-throws the captured error instance.
    throw error;
  }
}
