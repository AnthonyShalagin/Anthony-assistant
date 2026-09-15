"""CLI for the brain-dump inbox, called over ssh by Life OS on Anthony's Mac.

    python3 inbox_cli.py list          # JSON array of unfiled dumps
    python3 inbox_cli.py done 3 4 5    # mark dumps filed

Stdlib only (via memory.py), so it runs with the system python3 and doesn't
need Jarvis's virtualenv or .env.
"""

import json
import sys

import memory


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("list", "done"):
        print(__doc__, file=sys.stderr)
        return 1

    memory.init_db()

    if argv[1] == "list":
        print(json.dumps(memory.pending_dumps(), ensure_ascii=False))
        return 0

    try:
        ids = [int(a) for a in argv[2:]]
    except ValueError:
        print("Dump ids must be integers", file=sys.stderr)
        return 1
    print(f"Marked {memory.mark_dumps_done(ids)} dump(s) filed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
