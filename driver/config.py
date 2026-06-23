import json
import os

DEFAULT_CONFIG = {
    "name": "project_name",
    "version": "0.1.0",
    "type": "executable",
    "main": "src/main.pengu",
    "src_dirs": ["src"],
    "include_dirs": ["include"],
    "lib_dirs": ["lib"],
    "c_flags": [],
    "ld_flags": [],
    "cpp_standard": "c++23",
    "compiler": "auto",
    "dependencies": [],
    "external_sources": [],
    "profile": "debug"
}

VALID_PROJECT_TYPES = {"executable", "static_lib", "shared_lib", "cpp_only"}
VALID_COMPILERS = {"g++", "clang++", "msvc", "auto"}

class ConfigError(Exception):
    """Exception raised for configuration validation errors."""
    pass

def validate_config(data: dict) -> dict:
    """
    Validates configuration data and returns a completed configuration dict
    with missing optional fields filled with defaults.
    """
    if not isinstance(data, dict):
        raise ConfigError("Configuration must be a JSON object (dictionary).")

    # Name is mandatory
    if "name" not in data or not data["name"]:
        raise ConfigError("Missing or empty mandatory field: 'name'.")
    if not isinstance(data["name"], str):
        raise ConfigError("Field 'name' must be a string.")

    # Create a copy to populate defaults
    validated = DEFAULT_CONFIG.copy()
    validated.update(data)

    # Type validation
    if validated["type"] not in VALID_PROJECT_TYPES:
        raise ConfigError(
            f"Invalid project type '{validated['type']}'. "
            f"Allowed types: {', '.join(sorted(VALID_PROJECT_TYPES))}"
        )

    # Compiler validation
    if validated["compiler"] not in VALID_COMPILERS:
        raise ConfigError(
            f"Invalid compiler '{validated['compiler']}'. "
            f"Allowed compilers: {', '.join(sorted(VALID_COMPILERS))}"
        )

    # Profile validation
    VALID_PROFILES = {"debug", "release"}
    if validated.get("profile") not in VALID_PROFILES:
        raise ConfigError(
            f"Invalid profile '{validated.get('profile')}'. "
            f"Allowed profiles: {', '.join(sorted(VALID_PROFILES))}"
        )

    # Main field validation (only for executable)
    if validated["type"] == "executable":
        if "main" not in validated or not validated["main"]:
            raise ConfigError("Field 'main' is mandatory for executable projects.")
        if not isinstance(validated["main"], str):
            raise ConfigError("Field 'main' must be a string.")
    else:
        validated["main"] = ""

    # String type validations
    for field in ["version", "cpp_standard", "main"]:
        if field in validated and not isinstance(validated[field], str):
            raise ConfigError(f"Field '{field}' must be a string.")

    # List of strings validations
    list_fields = ["src_dirs", "include_dirs", "lib_dirs", "c_flags", "ld_flags", "external_sources"]
    for field in list_fields:
        val = validated.get(field)
        if not isinstance(val, list):
            raise ConfigError(f"Field '{field}' must be a JSON list.")
        if not all(isinstance(item, str) for item in val):
            raise ConfigError(f"All elements in field '{field}' must be strings.")

    # Dependencies validation
    if not isinstance(validated["dependencies"], list):
        raise ConfigError("Field 'dependencies' must be a JSON list.")

    return validated

def load_config(path: str) -> dict:
    """Loads and validates the configuration from the specified JSON file path."""
    if not os.path.exists(path):
        raise ConfigError(f"Configuration file not found: '{path}'")
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Failed to parse configuration file as JSON: {e}")
    except Exception as e:
        raise ConfigError(f"Failed to read configuration file: {e}")

    return validate_config(data)

def save_config(path: str, data: dict) -> None:
    """Validates and saves the configuration to the specified JSON file path."""
    validated = validate_config(data)
    try:
        # Create parent directories if they don't exist
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
            
        with open(path, "w", encoding="utf-8") as f:
            json.dump(validated, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise ConfigError(f"Failed to save configuration file: {e}")
