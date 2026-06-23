from __future__ import annotations
import sys
import os
import importlib.util

# System import path helper to resolve conflict with standard library 'ast' module
_current_dir = os.path.dirname(os.path.abspath(__file__))
_ast_path = os.path.abspath(os.path.join(_current_dir, "../ast/ast_nodes.py"))
if "ast.ast_nodes" not in sys.modules and os.path.exists(_ast_path):
  _spec = importlib.util.spec_from_file_location("ast.ast_nodes", _ast_path)
  _ast_nodes = importlib.util.module_from_spec(_spec)
  sys.modules["ast.ast_nodes"] = _ast_nodes
  _spec.loader.exec_module(_ast_nodes)

from ast.ast_nodes import (
  ASTNode, TypeNode, IntegerLiteral, FloatLiteral, StringLiteral, CharacterLiteral, BooleanLiteral
)

def escape_cpp_string(s: str) -> str:
  r"""Escapes characters in a Python string to make it safe for a C++ string literal.

  Handles standard escaping sequences (\\", \\\\, \n, \t, \r, \0) and
  escapes other non-printable ASCII characters using \uXXXX format. Non-ASCII
  characters are passed through unless they require special handling.

  Args:
    s: The input string.

  Returns:
    The C++ escaped string literal content (without surrounding quotes).
  """
  escaped = []
  for char in s:
    if char == '"':
      escaped.append('\\"')
    elif char == '\\':
      escaped.append('\\\\')
    elif char == '\n':
      escaped.append('\\n')
    elif char == '\t':
      escaped.append('\\t')
    elif char == '\r':
      escaped.append('\\r')
    elif char == '\0':
      escaped.append('\\0')
    else:
      o = ord(char)
      if 32 <= o <= 126:
        escaped.append(char)
      else:
        escaped.append(f"\\u{o:04x}")
  return "".join(escaped)

def escape_cpp_char(s: str) -> str:
  r"""Escapes a Python string representing a single character to make it safe for a C++ character literal.

  A C++ character literal must be enclosed in single quotes (e.g., 'c'). This function
  handles escaping of special characters within the content, including quotes, backslashes,
  and standard whitespace/control characters, and uses \uXXXX formatting for non-printable
  ASCII characters.

  Args:
    s: The input string containing the character (expected to be length 1 conceptually).

  Returns:
    The C++ escaped character literal, including the surrounding single quotes (e.g., "'\\xXX'").
  """
  if not s:
    return "'\\0'"
  char = s[0]
  if char == "'":
    return "'\\''"
  elif char == '\\':
    return "'\\\\'"
  elif char == '\n':
    return "'\\n'"
  elif char == '\t':
    return "'\\t'"
  elif char == '\r':
    return "'\\r'"
  elif char == '\0':
    return "'\\0'"
  else:
    o = ord(char)
    if 32 <= o <= 126:
      return f"'{char}'"
    else:
      return f"'\\u{o:04x}'"

def to_cpp_type(node: TypeNode | None) -> str:
  """Converts an AST TypeNode into its C++ type string representation.

  Handles basic types, qualified names (e.g., Model::Type), standard library containers,
  std::function, and references.

  Args:
    node: The TypeNode to convert. Can be None for void return types.

  Returns:
    The corresponding C++ type string.
  """
  if node is None:
    return "void"
    
  name = node.name
  # Handle simple type name conversions (e.g., Python 'string' to 'std::string')
  if name == "string":
    name = "std::string"
  elif "." in name:
    # Assuming '.' represents scope resolution that maps to C++ namespaces/scopes
    name = name.replace(".", "::")
    
  if name == "std::function" and node.type_arguments:
    ret_type = to_cpp_type(node.type_arguments[0])
    param_types = ", ".join(to_cpp_type(arg) for arg in node.type_arguments[1:])
    name = f"std::function<{ret_type}({param_types})>"
  elif node.type_arguments:
    # General case for template instantiation (e.g., std::vector<T>)
    args = ", ".join(to_cpp_type(arg) for arg in node.type_arguments)
    name = f"{name}<{args}>"
    
  if node.is_ref:
    # Handle references (&)
    name = f"{name}&"
    
  return name

def to_cpp_literal(node: ASTNode) -> str:
  """Converts an AST literal node into its C++ representation string.

  Detects the type of the literal (int, float, string, bool, etc.) and applies
  the necessary C++ escaping/formatting for accurate translation.

  Args:
    node: The ASTNode representing the literal value.

  Returns:
    The correctly formatted C++ literal string (e.g., "123", "\"hello\"", "'c'", "true").

  Raises:
    ValueError: If the node type is not supported by this function.
  """
  if isinstance(node, IntegerLiteral):
    return str(node.value)
  elif isinstance(node, FloatLiteral):
    # Use str() for float formatting to preserve Python's standard representation
    return str(node.value)
  elif isinstance(node, StringLiteral):
    # Wrap in double quotes and escape internal characters
    return f'"{escape_cpp_string(node.value)}"'
  elif isinstance(node, CharacterLiteral):
    # Returns the full quoted C++ character literal (e.g., "'a'")
    return escape_cpp_char(node.value)
  elif isinstance(node, BooleanLiteral):
    # Convert Python True/False to lowercase C++ keywords
    return node.value.lower()
  else:
    raise ValueError(f"Unknown literal node type: {type(node)}")

def to_cpp_call(func_name: str, args: list[str]) -> str:
  """Converts a function call structure into its C++ string representation.

  Args:
    func_name: The name of the function being called.
    args: A list of strings, where each string is already formatted for its
          C++ argument value (e.g., type names or literals).

  Returns:
    The fully qualified C++ function call signature as a string (e.g., "func(arg1, arg2)").
  """
  return f"{func_name}({', '.join(args)})"

def to_cpp_var_decl(type_name: str, var_name: str, init_val: str | None = None, is_const: bool = False) -> str:
  """Generates a C++ variable declaration statement.

  Args:
    type_name: The fully qualified type name for the variable (e.g., "std::string").
    var_name: The desired name of the variable.
    init_val: An optional string containing the initialization value's C++ representation.
    is_const: If True, prepends 'const ' to make it a const declaration.

  Returns:
    A complete C++ variable declaration statement (e.g., "const std::string var = value;").
  """
  const_str = "const " if is_const else ""
  if init_val is not None:
    return f"{const_str}{type_name} {var_name} = {init_val};"
  else:
    return f"{const_str}{type_name} {var_name};"
