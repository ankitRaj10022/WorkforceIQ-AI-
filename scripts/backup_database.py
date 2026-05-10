from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workforceiq import create_app
from workforceiq.maintenance import export_database_backup
from workforceiq.utils.time import utc_now


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a redacted WorkforceIQ JSON backup.")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    app = create_app()
    timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    output = args.output or Path(app.config["BACKUP_DIRECTORY"]) / f"workforceiq-backup-{timestamp}.json"
    with app.app_context():
        result = export_database_backup(output)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
