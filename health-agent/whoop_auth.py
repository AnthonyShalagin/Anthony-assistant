"""One-time Whoop login. Run on the VPS from health-agent/.

    .venv/bin/python whoop_auth.py url
        Prints the Whoop login link. Open it, log in, approve. Whoop redirects to
        WHOOP_REDIRECT_URI; the page may not load, which is fine. Copy that URL.

    .venv/bin/python whoop_auth.py finish '<the redirected URL>'
        Exchanges the code (single use, expires in minutes) and stores the tokens.

The login now includes the offline scope, so Whoop issues a refresh token and
clients/whoop.py keeps it renewed. This should be the last manual login.
"""

import os
import sys

# Whoop may echo scopes in a different order; don't treat that as an error.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from clients.whoop import complete_auth, get_auth_url  # noqa: E402
from database import init_db  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "url":
        print(get_auth_url())
        return 0
    if len(argv) == 3 and argv[1] == "finish":
        init_db()
        token = complete_auth(argv[2])
        print(f"Saved. Refresh token received: {bool(token.get('refresh_token'))}. "
              f"Scope: {token.get('scope')}")
        return 0
    print(__doc__, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
