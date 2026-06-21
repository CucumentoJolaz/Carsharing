#!/usr/bin/env python
import os
import sys
import time

import psycopg2


def main() -> None:
    if os.environ.get("DATABASE_ENGINE", "sqlite3") != "postgresql":
        return

    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print(f"Missing required database env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    host = os.environ.get("POSTGRES_HOST", "db")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    deadline = time.time() + int(os.environ.get("DB_WAIT_TIMEOUT", "60"))

    while time.time() < deadline:
        try:
            conn = psycopg2.connect(
                dbname=os.environ["POSTGRES_DB"],
                user=os.environ["POSTGRES_USER"],
                password=os.environ["POSTGRES_PASSWORD"],
                host=host,
                port=port,
            )
            conn.close()
            print("Database is ready.")
            return
        except psycopg2.OperationalError:
            time.sleep(1)

    print("Timed out waiting for database.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
