import sys
import os
import argparse
import subprocess
from driver.commands import cmd_init, cmd_build, cmd_run, cmd_clean, cmd_test

def print_version() -> None:
    print("PenguScript Toolchain v0.1.0")
    try:
        from driver.compiler import detect_compiler
        c_type, c_path = detect_compiler("auto")
        if c_type == "msvc":
            res = subprocess.run([c_path], capture_output=True, text=True, errors="replace")
            banner = res.stderr or res.stdout
            first_line = banner.splitlines()[0] if banner else "MSVC"
            print(f"Detected C++ Compiler: MSVC ({first_line.strip()})")
        else:
            res = subprocess.run([c_path, "--version"], capture_output=True, text=True, errors="replace")
            first_line = res.stdout.splitlines()[0] if res.stdout else "g++/clang++"
            print(f"Detected C++ Compiler: {c_type} ({first_line.strip()})")
    except Exception:
        print("Detected C++ Compiler: None (Ensure g++, clang++, or cl is in PATH)")

def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="PenguScript CLI - Professional toolchain for PenguScript compilation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-v", "--version",
        action="store_true",
        help="Show version information and exit"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init parser
    parser_init = subparsers.add_parser("init", help="Initialize a new project")
    parser_init.add_argument("name", nargs="?", help="Name of the project/directory")
    parser_init.add_argument(
        "--type",
        choices=["executable", "static_lib", "shared_lib", "cpp_only"],
        default=None,
        help="Type of the project (if omitted, will prompt in interactive mode)"
    )
    parser_init.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing configuration/source files"
    )

    # build parser
    parser_build = subparsers.add_parser("build", help="Compile and build the project")
    parser_build.add_argument(
        "--profile",
        choices=["debug", "release"],
        default=None,
        help="Compilation profile (debug or release)"
    )

    # run parser
    parser_run = subparsers.add_parser("run", help="Build and run the project executable")
    parser_run.add_argument(
        "--profile",
        choices=["debug", "release"],
        default=None,
        help="Compilation profile (debug or release)"
    )

    # clean parser
    parser_clean = subparsers.add_parser("clean", help="Clean up build directories")

    # test parser
    parser_test = subparsers.add_parser("test", help="Run tests for the project")

    args = parser.parse_args(argv)

    if args.version:
        print_version()
        return 0

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "build":
        return cmd_build(args)
    elif args.command == "run":
        return cmd_run(args)
    elif args.command == "clean":
        return cmd_clean(args)
    elif args.command == "test":
        return cmd_test(args)

    return 0

if __name__ == "__main__":
    sys.exit(main())
