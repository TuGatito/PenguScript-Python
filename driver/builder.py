import os
import sys
import shutil

from lexer.lexer import Lexer
from parser.declarations import DeclarationParser
from semantic.semantic import SemanticAnalyzer
from codegen.cpp_generator import CppGenerator

from driver.config import load_config
from driver.compiler import detect_compiler, compile_cpp, link_files
from driver.utils import print_success, print_error, print_warning, print_info

def build_project(config_path: str, profile_override: str | None = None) -> None:
    """
    Compiles all PenguScript files in the project to C++ and then compiles/links
    them along with C++ files to produce the final executable or library.
    """
    config_path = os.path.abspath(config_path)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    proj_root = os.path.dirname(config_path)
    config = load_config(config_path)
    
    # Resolve compile profile
    profile = profile_override if profile_override else config.get("profile", "debug")

    print_info(f"Building project '{config['name']}' in {proj_root} (profile: {profile})...")

    # 1. Collect all .pengu files
    pengu_files = []
    for src_dir in config["src_dirs"]:
        full_src_dir = os.path.join(proj_root, src_dir)
        if not os.path.exists(full_src_dir):
            continue
        for root, _, files in os.walk(full_src_dir):
            for file in files:
                if file.endswith(".pengu"):
                    pengu_files.append(os.path.join(root, file))

    build_dir = os.path.join(proj_root, "build")
    os.makedirs(build_dir, exist_ok=True)

    # 2. Compile each .pengu file to C++
    print_info("[1/3] Transpiling PenguScript files to C++20...")
    generated_cc_files = []
    for pf in pengu_files:
        rel_path = os.path.relpath(pf, proj_root)
        cc_relative = rel_path.rsplit(".", 1)[0] + ".cc"
        cc_output_path = os.path.join(build_dir, cc_relative)
        os.makedirs(os.path.dirname(cc_output_path), exist_ok=True)

        print_info(f"Compiling '{rel_path}' to C++...")
        
        try:
            with open(pf, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read file '{pf}': {e}")

        # Lexer -> Parser -> Semantic -> Codegen
        lexer = Lexer(content, pf)
        tokens = lexer.tokenize()
        
        parser = DeclarationParser(tokens, pf)
        ast = parser.parse_program()
        
        analyzer = SemanticAnalyzer()
        errors = analyzer.analyze(ast)
        
        has_errors = any(not err.is_warning for err in errors)
        if has_errors:
            print_error(f"Semantic analysis failed for '{rel_path}':")
            print(SemanticAnalyzer.format_diagnostics(errors), file=sys.stderr)
            raise RuntimeError(f"Compilation failed due to semantic errors in '{rel_path}'")

        generator = CppGenerator()
        generator.generate(ast, cc_output_path)
        generated_cc_files.append(cc_output_path)

    # 3. Collect all C++ files (generated + extra)
    cpp_files = [os.path.normpath(os.path.abspath(f)) for f in generated_cc_files]
    for src_dir in config["src_dirs"]:
        full_src_dir = os.path.join(proj_root, src_dir)
        if not os.path.exists(full_src_dir):
            continue
        for root, dirs, files in os.walk(full_src_dir):
            # Prune 'build' directory so we don't look inside it for extra sources
            if "build" in dirs:
                dirs.remove("build")
            for file in files:
                if file.endswith((".cpp", ".cc", ".c", ".cxx")) and not file.endswith(".pengu.cc"):
                    full_path = os.path.normpath(os.path.abspath(os.path.join(root, file)))
                    if full_path not in cpp_files:
                        cpp_files.append(full_path)

    # Collect custom files listed in external_sources
    for ext_src in config.get("external_sources", []):
        full_path = os.path.normpath(os.path.abspath(os.path.join(proj_root, ext_src)))
        if os.path.exists(full_path):
            if full_path not in cpp_files:
                cpp_files.append(full_path)
        else:
            print_warning(f"External source file '{ext_src}' not found at: '{full_path}'")

    if not cpp_files:
        print_warning("No source files found to build.")
        return

    # 4. Detect compiler
    compiler_type, compiler_path = detect_compiler(config["compiler"])
    print_info(f"Using compiler: {compiler_type} ({compiler_path})")

    # 5. Compile C++ files to object files
    print_info("[2/3] Compiling C++ source files to object files...")
    obj_files = []
    for cpp_file in cpp_files:
        rel_path = os.path.relpath(cpp_file, proj_root)
        if rel_path.startswith("build"):
            obj_relative = rel_path.rsplit(".", 1)[0] + (".obj" if compiler_type == "msvc" else ".o")
        else:
            obj_relative = os.path.join("build", rel_path.rsplit(".", 1)[0] + (".obj" if compiler_type == "msvc" else ".o"))
            
        obj_path = os.path.join(proj_root, obj_relative)
        os.makedirs(os.path.dirname(obj_path), exist_ok=True)

        print_info(f"Compiling C++ file '{rel_path}'...")
        
        # Build compilation flags
        c_flags = list(config["c_flags"])
        
        # Add profile-specific compiler flags
        if compiler_type == "msvc":
            if profile == "debug":
                c_flags.extend(["/Od", "/Zi"])
            else:
                c_flags.extend(["/O2", "/DNDEBUG"])
        else:
            if profile == "debug":
                c_flags.extend(["-O0", "-g"])
            else:
                c_flags.extend(["-O2", "-DNDEBUG"])
                
        for inc in config["include_dirs"]:
            full_inc = os.path.join(proj_root, inc)
            if compiler_type == "msvc":
                c_flags.append(f"/I{full_inc}")
            else:
                c_flags.append(f"-I{full_inc}")

        compile_cpp(
            source_files=[cpp_file],
            output_obj=obj_path,
            flags=c_flags,
            standard=config["cpp_standard"],
            compiler_type=compiler_type,
            compiler_path=compiler_path
        )
        obj_files.append(obj_path)

    # 6. Linking/Archiving
    if config["type"] == "cpp_only":
        print_success("C++ source generation and compilation completed successfully (linking skipped for cpp_only).")
        print_info("Generated C++ source files:")
        for gen_cc in generated_cc_files:
            print_info(f"  - {os.path.relpath(gen_cc, proj_root)}")
        return
    
    print_info("[3/3] Linking target objects to binary...")

    # Determine output binary name
    name = config["name"]
    is_windows = (sys.platform == "win32")

    if config["type"] == "executable":
        binary_name = name + ".exe" if is_windows else name
    elif config["type"] == "static_lib":
        binary_name = name + ".lib" if is_windows else f"lib{name}.a"
    elif config["type"] == "shared_lib":
        binary_name = name + ".dll" if is_windows else f"lib{name}.so"
    else:
        raise ValueError(f"Unknown project type: '{config['type']}'")

    binary_path = os.path.join(proj_root, binary_name)
    print_info(f"Linking object files into binary '{binary_name}'...")

    # Build ld_flags with library directories
    ld_flags = list(config["ld_flags"])
    
    # Add profile-specific linker flags
    if profile == "debug":
        if compiler_type == "msvc":
            ld_flags.append("/DEBUG")
        else:
            ld_flags.append("-g")
            
    for lib in config["lib_dirs"]:
        full_lib = os.path.join(proj_root, lib)
        if compiler_type == "msvc":
            ld_flags.append(f"/LIBPATH:{full_lib}")
        else:
            ld_flags.append(f"-L{full_lib}")

    link_files(
        object_files=obj_files,
        output_bin=binary_path,
        ld_flags=ld_flags,
        compiler_type=compiler_type,
        compiler_path=compiler_path,
        project_type=config["type"]
    )

    print_success(f"Project '{name}' built successfully! Binary created at: {binary_path}")
