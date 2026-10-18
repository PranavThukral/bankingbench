"""Operations CLI: print the accounts stored in a holds database."""
import argparse
from pathlib import Path
from holds.export import export_authorizations
from holds.storage import accounts_overview, initialize, transaction
from holds.summary import render_overview


def overview(path):
    initialize(path)
    with transaction(path) as db:
        return accounts_overview(db)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Show synthetic accounts and authorization counts")
    parser.add_argument("database", type=Path)
    parser.add_argument("--export-csv", type=Path, help="also write every authorization record to a CSV file")
    args = parser.parse_args(argv)
    print(render_overview(overview(args.database)), end="")
    if args.export_csv:
        print(f"exported {export_authorizations(args.database, args.export_csv)} authorization records")


if __name__ == "__main__":
    main()
