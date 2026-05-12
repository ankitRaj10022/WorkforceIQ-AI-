from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workforceiq.maintenance import verify_database_backup


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a redacted WorkforceIQ JSON backup.")
    parser.add_argument("backup_path", type=Path)
    args = parser.parse_args()

    result = verify_database_backup(args.backup_path)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
