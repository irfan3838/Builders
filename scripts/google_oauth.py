"""One-time Google login for the linked account (Gmail + Calendar): gets a refresh token and stores it in .env.

Sign in as the account in GOOGLE_LINKED_EMAIL (irfmed38@gmail.com). The script refuses a token for any other account.

Usage:  uv run python -m scripts.google_oauth [path/to/client.json]   (default .secrets/google_client.json)

Opens Google's consent page in the browser, listens on http://localhost:8765 for the redirect, exchanges the code
(with PKCE) for tokens, and writes GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN into .env.
Secret values are never printed.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

CAL_SCOPE = "https://www.googleapis.com/auth/calendar.events"
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"  # read, label, archive, draft and send (no permanent delete)
SCOPE = " ".join(["openid", "email", CAL_SCOPE, GMAIL_SCOPE])
PORT = 8765
REDIRECT = f"http://localhost:{PORT}/"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def _client(path: Path) -> tuple[str, str]:
    data = json.loads(path.read_text())
    c = data.get("installed") or data.get("web")
    if not c:
        sys.exit(f"{path}: not a Google OAuth client file")
    return c["client_id"], c["client_secret"]


def _wait_for_code(state: str) -> str:
    result: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            if q.get("state") != state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"State mismatch. Close this tab and run the script again.")
                return
            result.update(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "Purser is connected to Gmail and Google Calendar. You can close this tab." if "code" in q else f"Login failed: {q.get('error')}"
            self.wfile.write(f"<p style='font:16px sans-serif'>{msg}</p>".encode())

        def log_message(self, *_):
            pass

    with http.server.HTTPServer(("localhost", PORT), Handler) as srv:
        while not result:
            srv.handle_request()
    if "code" not in result:
        sys.exit(f"Google returned an error: {result.get('error')}")
    return result["code"]


def _set_env(values: dict[str, str], env_path: Path = Path(".env")) -> None:
    text = env_path.read_text() if env_path.exists() else ""
    for key, value in values.items():
        line = f"{key}={value}"
        if re.search(rf"^{key}=.*$", text, flags=re.M):
            text = re.sub(rf"^{key}=.*$", lambda _m, line=line: line, text, flags=re.M)
        else:
            text = text.rstrip("\n") + f"\n{line}\n"
    env_path.write_text(text)


def _env(key: str, env_path: Path = Path(".env")) -> str:
    text = env_path.read_text() if env_path.exists() else ""
    m = re.search(rf"^{key}=(.*)$", text, flags=re.M)
    return m.group(1).strip() if m else ""


def main() -> None:
    client_id, client_secret = _client(Path(sys.argv[1] if len(sys.argv) > 1 else ".secrets/google_client.json"))
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    print("Opening Google sign-in. If the browser does not open, visit this URL:\n" + url + "\n")
    webbrowser.open(url)
    code = _wait_for_code(state)

    body = urllib.parse.urlencode({"code": code, "client_id": client_id, "client_secret": client_secret,
                                   "redirect_uri": REDIRECT, "grant_type": "authorization_code",
                                   "code_verifier": verifier}).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=body), timeout=20) as r:
        tok = json.load(r)
    refresh = tok.get("refresh_token")
    if not refresh:
        sys.exit("Google did not return a refresh token. Remove Purser at myaccount.google.com/permissions and retry.")
    granted = tok.get("scope", "")
    for need, what in ((CAL_SCOPE, "calendar"), (GMAIL_SCOPE, "Gmail")):
        if need not in granted:
            sys.exit(f"The {what} permission was not granted. Run again and tick every checkbox on the consent page.")

    auth = {"Authorization": f"Bearer {tok['access_token']}"}
    with urllib.request.urlopen(urllib.request.Request("https://openidconnect.googleapis.com/v1/userinfo", headers=auth), timeout=20) as r:
        email = (json.load(r).get("email") or "").lower()
    linked = _env("GOOGLE_LINKED_EMAIL").lower()
    if linked and email != linked:
        sys.exit(f"You signed in as {email}, but GOOGLE_LINKED_EMAIL is {linked}. Run again and pick {linked}.")

    # Prove both APIs answer (read-only calls; nothing is sent or created).
    checks = []
    for name, url in (("gmail", "https://gmail.googleapis.com/gmail/v1/users/me/profile"),
                      ("calendar", "https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults=1")):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=auth), timeout=20) as r:
                json.load(r)
            checks.append(f"{name} ok")
        except urllib.error.HTTPError as e:
            checks.append(f"{name} HTTP {e.code} (is the {name.title()} API enabled in the Cloud project?)")

    values = {"GOOGLE_CLIENT_ID": client_id, "GOOGLE_CLIENT_SECRET": client_secret, "GOOGLE_REFRESH_TOKEN": refresh}
    if not linked:
        values["GOOGLE_LINKED_EMAIL"] = email
    _set_env(values)
    print(f"Done for {email} ({', '.join(checks)}). Saved {', '.join(values)} to .env.")


if __name__ == "__main__":
    main()
