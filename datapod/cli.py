"""Command-line interface for datapod."""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from datapod.vault import PodVault
from datapod.render import render_entry_card, render_table


def parse_metadata_arg(meta_arg: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    """
    Parses user metadata patterns:
    1) "file_name | holder name"  -> holder: holder name
    2) "holder=name,env=prod,key=val"
    3) JSON string: '{"holder": "alice", "env": "prod"}'
    """
    if not meta_arg:
        return "default", {}

    meta_dict: Dict[str, Any] = {}
    holder = "default"

    # Pipe syntax: "file_name | holder_name" or "name | holder"
    if "|" in meta_arg:
        parts = meta_arg.split("|")
        # First part might be a label, second part is holder
        holder = parts[1].strip()
        meta_dict["label"] = parts[0].strip()
        return holder, meta_dict

    # JSON syntax
    if meta_arg.startswith("{") and meta_arg.endswith("}"):
        try:
            parsed = json.loads(meta_arg)
            if isinstance(parsed, dict):
                holder = parsed.pop("holder", "default")
                return holder, parsed
        except Exception:
            pass

    # Key=value comma pairs: holder=alice,env=prod
    if "=" in meta_arg:
        for pair in meta_arg.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k == "holder":
                    holder = v
                else:
                    meta_dict[k] = v
        return holder, meta_dict

    # Simple string: treat as holder name
    return meta_arg.strip(), {}


def normalize_argv(argv: List[str]) -> List[str]:
    """Convert flag-style commands (-add, -pull, etc.) to standard subcommands."""
    aliases = {
        "-add": "add",
        "-pull": "pull",
        "-list": "list",
        "-ls": "list",
        "-info": "info",
        "-cat": "cat",
        "-rm": "rm",
        "-delete": "rm",
        "-meta": "--meta",
        "-metadata": "--meta",
        "--metadata": "--meta",
        "-m": "--meta",
        "-holder": "--holder",
        "-out": "--out",
        "-o": "--out",
        "-init": "init",
    }
    normalized = []
    for arg in argv:
        if arg in aliases:
            normalized.append(aliases[arg])
        else:
            normalized.append(arg)
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datapod",
        description="A metadata-rich content-addressable data vault and pod manager.",
        epilog="Examples:\n"
               "  datapod -add data.csv -meta 'dataset | analytics_team'\n"
               "  datapod -add model.onnx -meta holder=snehil,version=1.0\n"
               "  datapod -pull 7f4a2b\n"
               "  datapod -info 7f4a2b\n"
               "  datapod -list\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Action to execute")

    # init
    init_p = subparsers.add_parser("init", help="Initialize a project-local .datapod vault")

    # add
    add_p = subparsers.add_parser("add", help="Store a file into the vault with metadata")
    add_p.add_argument("file", help="Path to the file to store")
    add_p.add_argument("-meta", "--meta", "--metadata", "-metadata", dest="meta", help="Metadata (e.g. 'label | holder', 'holder=alice,env=prod')")
    add_p.add_argument("-holder", "--holder", dest="holder", help="Holder / owner name explicitly")
    add_p.add_argument("-t", "--tag", dest="tags", action="append", help="Tag to associate with this pod")

    # pull
    pull_p = subparsers.add_parser("pull", help="Extract a file by pod ID")
    pull_p.add_argument("id", help="Pod unique ID (or prefix)")
    pull_p.add_argument("-out", "-o", "--out", dest="out", help="Destination path (default: current directory)")

    # info
    info_p = subparsers.add_parser("info", help="Inspect metadata and details for a pod ID")
    info_p.add_argument("id", help="Pod unique ID")

    # cat
    cat_p = subparsers.add_parser("cat", help="Print file contents directly to stdout")
    cat_p.add_argument("id", help="Pod unique ID")

    # list
    list_p = subparsers.add_parser("list", help="List stored pods in vault")
    list_p.add_argument("-holder", "--holder", dest="holder", help="Filter by holder name")

    # rm
    rm_p = subparsers.add_parser("rm", help="Remove a pod from vault")
    rm_p.add_argument("id", help="Pod unique ID")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    raw_argv = sys.argv[1:] if argv is None else argv
    normalized_argv = normalize_argv(raw_argv)

    parser = build_parser()
    args = parser.parse_args(normalized_argv)

    if not args.subcommand:
        parser.print_help()
        return 1

    vault = PodVault()

    if args.subcommand == "init":
        local_dir = Path.cwd() / ".datapod"
        local_dir.mkdir(exist_ok=True)
        (local_dir / "blobs").mkdir(exist_ok=True)
        (local_dir / "meta").mkdir(exist_ok=True)
        print(f"\033[1;32m✓ Initialized local datapod vault at\033[0m {local_dir}")
        return 0

    elif args.subcommand == "add":
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"\033[1;31mError:\033[0m File '{file_path}' does not exist", file=sys.stderr)
            return 1

        holder, meta_dict = parse_metadata_arg(args.meta)
        if args.holder:
            holder = args.holder

        tags = args.tags or []

        try:
            entry = vault.add(file_path, holder=holder, metadata=meta_dict, tags=tags)
            print(render_entry_card(entry, title="POD STORED SUCCESSFULLY"))
            print(f"\n\033[1;32mAccess with:\033[0m datapod -pull {entry.id}")
            return 0
        except Exception as e:
            print(f"\033[1;31mError:\033[0m {e}", file=sys.stderr)
            return 1

    elif args.subcommand == "pull":
        try:
            entry, dest = vault.pull(args.id, output_path=args.out)
            print(f"\033[1;32m✓ Pulled pod [{entry.id}]\033[0m to: \033[1m{dest}\033[0m ({entry.size_bytes:,} bytes)")
            return 0
        except Exception as e:
            print(f"\033[1;31mError:\033[0m {e}", file=sys.stderr)
            return 1

    elif args.subcommand == "info":
        entry = vault.get(args.id)
        if not entry:
            print(f"\033[1;31mError:\033[0m Pod ID '{args.id}' not found", file=sys.stderr)
            return 1
        print(render_entry_card(entry, title=f"POD [{entry.id}]"))
        return 0

    elif args.subcommand == "cat":
        try:
            entry, data = vault.read_bytes(args.id)
            sys.stdout.buffer.write(data)
            return 0
        except Exception as e:
            print(f"\033[1;31mError:\033[0m {e}", file=sys.stderr)
            return 1

    elif args.subcommand == "list":
        entries = vault.list_all(holder=args.holder)
        print(render_table(entries))
        return 0

    elif args.subcommand == "rm":
        if vault.remove(args.id):
            print(f"\033[1;32m✓ Removed pod\033[0m [{args.id}]")
            return 0
        else:
            print(f"\033[1;31mError:\033[0m Pod ID '{args.id}' not found", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
