import sys
import subprocess

# ANSI Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Enable virtual terminal processing on Windows if possible
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11
        stdout_handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(stdout_handle, ctypes.byref(mode)):
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(stdout_handle, mode.value | 0x0004)
    except Exception:
        pass

def print_success(msg: str) -> None:
    """Print success message in green."""
    print(f"{GREEN}{BOLD}[OK] Success:{RESET} {msg}")

def print_error(msg: str) -> None:
    """Print error message in red."""
    print(f"{RED}{BOLD}[ERROR] Error:{RESET} {msg}", file=sys.stderr)

def print_warning(msg: str) -> None:
    """Print warning message in yellow."""
    print(f"{YELLOW}{BOLD}[WARNING] Warning:{RESET} {msg}")

def print_info(msg: str) -> None:
    """Print informational message in cyan/blue."""
    print(f"{CYAN}[INFO] Info:{RESET} {msg}")

def run_command(cmd: list[str] | str, cwd: str | None = None) -> tuple[int, str, str]:
    """
    Execute a subprocess command, capturing stdout and stderr.
    Returns: (exit_code, stdout, stderr)
    """
    shell = isinstance(cmd, str)
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)
