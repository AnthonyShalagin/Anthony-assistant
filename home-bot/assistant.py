"""Send typed commands to Google Assistant, as if spoken to a Nest speaker.

Controls anything in Google Home (Kasa plugs, Hue later) with one path. Used because
the KP125M plugs' firmware (TPAP encryption) can't be controlled locally by python-kasa yet.

One-time sign-in (opens a browser on the Mac):
    python assistant.py auth --client-secret credentials/google_assistant_client.json

Then:
    python assistant.py say "turn off the bedroom light"

Google no longer returns text replies for most home commands, so success is checked in
the Google Home app or at myactivity.google.com, not from the reply text.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKEN_FILE = HERE / "credentials" / "google_assistant_token.json"  # gitignored
SCOPES = ["https://www.googleapis.com/auth/assistant-sdk-prototype"]


def auth(client_secret: str) -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.parent.mkdir(exist_ok=True)
    TOKEN_FILE.write_text(json.dumps({
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "token_uri": creds.token_uri,
        "scopes": SCOPES,
    }))
    TOKEN_FILE.chmod(0o600)
    print(f"Signed in. Token saved to {TOKEN_FILE}")


def say(command: str) -> str:
    import google.oauth2.credentials
    from gassist_text import TextAssistant

    if not TOKEN_FILE.exists():
        raise SystemExit("Not signed in yet. Run: python assistant.py auth --client-secret <file>")
    creds = google.oauth2.credentials.Credentials(token=None, **json.loads(TOKEN_FILE.read_text()))
    with TextAssistant(creds, language_code="en-US") as assistant:
        text, _html, _audio = assistant.assist(command)
    return text or "(sent; Google gave no text reply, which is normal for home commands)"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("auth", help="one-time Google sign-in")
    a.add_argument("--client-secret", required=True, help="OAuth Desktop client JSON from Google Cloud")
    s = sub.add_parser("say", help="send a command to Google Assistant")
    s.add_argument("command", nargs="+")
    args = p.parse_args()

    if args.action == "auth":
        auth(args.client_secret)
    else:
        print(say(" ".join(args.command)))


if __name__ == "__main__":
    sys.exit(main())
