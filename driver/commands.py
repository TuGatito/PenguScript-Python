import sys
import os
import subprocess
import shutil
from driver.utils import print_success, print_error, print_warning, print_info
from driver.config import load_config, save_config, ConfigError
from driver.project import create_project_structure
from driver.builder import build_project

def load_local_config() -> dict | None:
    """Helper to load config from current directory."""
    config_path = os.path.join(os.getcwd(), "penguscript.json")
    if not os.path.exists(config_path):
        print_error("Configuration file 'penguscript.json' not found in current directory. Run 'penguscript init' to initialize a new project.")
        return None
    try:
        return load_config(config_path)
    except ConfigError as e:
        print_error(str(e))
        return None

def cmd_init(args) -> int:
    """Initializes a new PenguScript project."""
    name_input = getattr(args, "name", None)
    type_input = getattr(args, "type", None)

    project_name = None
    target_in_sub = False

    # 1. Prompt for project name if not provided
    if not name_input:
        if sys.stdin.isatty():
            try:
                entered = input("Project Name: ").strip()
                if entered:
                    project_name = entered
                    target_in_sub = True
            except (KeyboardInterrupt, EOFError):
                print()  # Newline
                return 1
        
        if not project_name:
            # Fallback to current directory name
            project_name = os.path.basename(os.path.normpath(os.getcwd()))
            if not project_name:
                project_name = "untitled_project"
    else:
        project_name = name_input
        target_in_sub = True

    # 2. Prompt for project type if not provided
    if not type_input:
        if sys.stdin.isatty():
            print("Select project type:")
            print("  1) executable")
            print("  2) static_lib")
            print("  3) shared_lib")
            print("  4) cpp_only")
            try:
                choice = input("Choice (1-4) [1]: ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                return 1
                
            if choice == "2":
                project_type = "static_lib"
            elif choice == "3":
                project_type = "shared_lib"
            elif choice == "4":
                project_type = "cpp_only"
            else:
                project_type = "executable"
        else:
            project_type = "executable"
    else:
        project_type = type_input

    # 3. Resolve target directory
    if target_in_sub:
        target_dir = os.path.join(os.getcwd(), project_name)
    else:
        target_dir = os.getcwd()

    print_info(f"Initializing project '{project_name}' ({project_type}) in {target_dir}...")

    # Check force and existing config
    config_path = os.path.join(target_dir, "penguscript.json")
    force = getattr(args, "force", False)
    if os.path.exists(config_path) and not force:
        print_error("Configuration file 'penguscript.json' already exists. Use --force to overwrite.")
        return 1

    try:
        config_data = create_project_structure(target_dir, project_type, project_name, force=force)
        save_config(config_path, config_data)
    except Exception as e:
        print_error(f"Failed to initialize project: {e}")
        return 1

    print_success(f"Project '{project_name}' successfully initialized!")
    return 0

def cmd_build(args) -> int:
    """Build command."""
    config_path = os.path.join(os.getcwd(), "penguscript.json")
    if not os.path.exists(config_path):
        print_error("Configuration file 'penguscript.json' not found in current directory. Run 'penguscript init' to initialize a new project.")
        return 1
    try:
        profile = getattr(args, "profile", None)
        build_project(config_path, profile_override=profile)
        return 0
    except Exception as e:
        print_error(f"Build failed: {e}")
        return 1

def cmd_run(args) -> int:
    """Run command."""
    config = load_local_config()
    if config is None:
        return 1
        
    if config["type"] != "executable":
        print_error("Run command is only supported for executable projects.")
        return 1

    config_path = os.path.join(os.getcwd(), "penguscript.json")
    try:
        profile = getattr(args, "profile", None)
        build_project(config_path, profile_override=profile)
    except Exception as e:
        print_error(f"Build failed, run aborted: {e}")
        return 1

    name = config["name"]
    is_windows = (sys.platform == "win32")
    binary_name = name + ".exe" if is_windows else name
    binary_path = os.path.join(os.getcwd(), binary_name)

    if not os.path.exists(binary_path):
        print_error(f"Executable binary not found at: {binary_path}")
        return 1

    print_info(f"Running '{binary_name}'...")
    try:
        result = subprocess.run([binary_path], shell=False)
        return result.returncode
    except Exception as e:
        print_error(f"Failed to run binary: {e}")
        return 1

def cmd_clean(args) -> int:
    """Clean command."""
    config = load_local_config()
    if config is None:
        return 1

    print_info("Cleaning build artifacts...")
    
    # 1. Remove build directory
    build_dir = os.path.join(os.getcwd(), "build")
    if os.path.exists(build_dir):
        try:
            shutil.rmtree(build_dir)
            print_info("Removed 'build/' directory.")
        except Exception as e:
            print_warning(f"Failed to remove build directory: {e}")

    # 2. Remove binaries
    name = config["name"]
    possible_binaries = [
        name,
        name + ".exe",
        f"lib{name}.a",
        name + ".lib",
        f"lib{name}.so",
        name + ".dll",
        f"lib{name}.dylib",
        name + ".exp",
        name + ".pdb"
    ]
    
    for filename in possible_binaries:
        path = os.path.join(os.getcwd(), filename)
        if os.path.exists(path):
            try:
                os.remove(path)
                print_info(f"Removed binary asset '{filename}'.")
            except Exception as e:
                print_warning(f"Failed to remove '{filename}': {e}")

    print_success("Clean completed.")
    return 0

def cmd_test(args) -> int:
    """Placeholder test command."""
    config = load_local_config()
    if config is None:
        return 1
    print_info(f"Running tests for project '{config['name']}'...")
    print_warning("Test execution is placeholder in Phase 0/1.")
    return 0
