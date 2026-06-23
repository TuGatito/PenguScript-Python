import sys
from driver.cli import main as cli_main

def main() -> None:
    """
    Main entry point for the PenguScript compiler toolchain CLI.
    Delegates commands to the modular driver.
    """
    sys.exit(cli_main())

if __name__ == "__main__":
    main()