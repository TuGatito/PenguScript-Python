import os
import sys
import subprocess
import shutil

class CompilerNotFoundError(RuntimeError):
    """Raised when a suitable C++ compiler cannot be found."""
    pass

class CompilationError(RuntimeError):
    """Raised when compilation of C++ source files fails."""
    pass

class LinkerError(RuntimeError):
    """Raised when linking of object files fails."""
    pass

def detect_compiler(preferred: str = "auto") -> tuple[str, str]:
    """
    Detects a C++ compiler in PATH.
    preferred can be "g++", "clang++", "msvc", "cl", or "auto".
    Returns: (compiler_type, compiler_path) where compiler_type is 'g++', 'clang++', or 'msvc'.
    """
    search_order = []
    
    # Normalize preferred compiler string
    pref = preferred.lower()
    if pref in ("msvc", "cl"):
        search_order = [("msvc", "cl")]
    elif pref == "g++":
        search_order = [("g++", "g++")]
    elif pref == "clang++":
        search_order = [("clang++", "clang++")]
    elif pref == "auto":
        if sys.platform == "win32":
            search_order = [("msvc", "cl"), ("g++", "g++"), ("clang++", "clang++")]
        else:
            search_order = [("g++", "g++"), ("clang++", "clang++")]
    else:
        raise ValueError(f"Unknown compiler preference: '{preferred}'")

    for c_type, executable in search_order:
        path = shutil.which(executable)
        if path:
            return c_type, path

    # If nothing was found, raise exception with helpful installation hints
    error_msg = f"No compatible C++ compiler was found in PATH (preferred: '{preferred}').\n"
    if sys.platform == "win32":
        error_msg += (
            "Please ensure one of the following is installed and added to PATH:\n"
            "  - MSVC (via Visual Studio Installer with 'Desktop development with C++' workload)\n"
            "  - MinGW-w64 (g++)\n"
            "  - Clang (clang++)"
        )
    else:
        error_msg += (
            "Please install a C++ compiler using your package manager:\n"
            "  - Debian/Ubuntu: sudo apt install g++\n"
            "  - macOS: xcode-select --install\n"
            "  - Fedora/RHEL: sudo dnf install gcc-c++"
        )
    raise CompilerNotFoundError(error_msg)

def compile_cpp(
    source_files: list[str],
    output_obj: str,
    flags: list[str],
    standard: str,
    compiler_type: str,
    compiler_path: str
) -> None:
    """
    Compiles list of C++ source files into a single object file.
    """
    if not source_files:
        raise ValueError("No source files specified for compilation.")

    # Clean standard string (e.g. "c++20" -> "c++20")
    std = standard.lower().strip()
    if std.startswith("std="):
        std = std[4:]

    cmd = [compiler_path]

    if compiler_type == "msvc":
        # MSVC flags: /nologo (suppress banner), /EHsc (enable standard C++ exceptions)
        cmd.extend(["/nologo", "/EHsc"])
        cmd.extend(flags)
        
        # Translate c++20 to MSVC format (e.g. /std:c++20)
        cmd.append(f"/std:{std}")
        cmd.append("/c")
        cmd.append(f"/Fo{output_obj}")
        cmd.extend(source_files)
    else:
        # GCC/Clang flags
        cmd.extend(flags)
        cmd.append(f"-std={std}")
        cmd.append("-c")
        cmd.append("-o")
        cmd.append(output_obj)
        cmd.extend(source_files)

    # Run command and capture output
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        error_output = (result.stdout or "") + "\n" + (result.stderr or "")
        raise CompilationError(
            f"Compilation failed with exit code {result.returncode}.\nCommand: {' '.join(cmd)}\nOutput:\n{error_output.strip()}"
        )

def link_files(
    object_files: list[str],
    output_bin: str,
    ld_flags: list[str],
    compiler_type: str,
    compiler_path: str,
    project_type: str = "executable"
) -> None:
    """
    Links list of object files into an executable or library binary.
    """
    if not object_files:
        raise ValueError("No object files specified for linking.")

    if project_type == "static_lib":
        if compiler_type == "msvc":
            # For MSVC, use lib.exe
            lib_dir = os.path.dirname(compiler_path)
            lib_exe = os.path.join(lib_dir, "lib.exe")
            if not os.path.exists(lib_exe):
                lib_exe = shutil.which("lib") or "lib"
            cmd = [lib_exe, "/nologo", f"/OUT:{output_bin}"] + object_files
        else:
            # For GCC/Clang, use ar
            ar_dir = os.path.dirname(compiler_path)
            ar_exe = os.path.join(ar_dir, "ar")
            if not os.path.exists(ar_exe) and sys.platform == "win32":
                ar_exe = os.path.join(ar_dir, "ar.exe")
            if not os.path.exists(ar_exe):
                ar_exe = shutil.which("ar") or "ar"
            cmd = [ar_exe, "rcs", output_bin] + object_files
    else:
        cmd = [compiler_path]
        if compiler_type == "msvc":
            cmd.extend(["/nologo", "/EHsc"])
            cmd.extend(object_files)
            if project_type == "shared_lib":
                cmd.append("/LD")
            cmd.append(f"/Fe{output_bin}")
            cmd.append("/link")
            cmd.extend(ld_flags)
        else:
            cmd.extend(object_files)
            if project_type == "shared_lib":
                cmd.append("-shared")
            cmd.append("-o")
            cmd.append(output_bin)
            cmd.extend(ld_flags)

    # Run command and capture output
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        error_output = (result.stdout or "") + "\n" + (result.stderr or "")
        raise LinkerError(
            f"Linking/Archiving failed with exit code {result.returncode}.\nCommand: {' '.join(cmd)}\nOutput:\n{error_output.strip()}"
        )
