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
  if node is None:
    return "void"
    
  name = node.name
  if name == "string":
    name = "std::string"
  elif "." in name:
    name = name.replace(".", "::")
    
  if name == "std::function" and node.type_arguments:
    ret_type = to_cpp_type(node.type_arguments[0])
    param_types = ", ".join(to_cpp_type(arg) for arg in node.type_arguments[1:])
    name = f"std::function<{ret_type}({param_types})>"
  elif node.type_arguments:
    args = ", ".join(to_cpp_type(arg) for arg in node.type_arguments)
    name = f"{name}<{args}>"
    
  if node.array_size is not None:
    name = f"std::array<{name}, {node.array_size}>"
    
  if node.is_ref:
    name = f"{name}&"
    
  return name

def to_cpp_literal(node: ASTNode) -> str:
  if isinstance(node, IntegerLiteral):
    return node.value
  elif isinstance(node, FloatLiteral):
    return node.value
  elif isinstance(node, StringLiteral):
    return f'"{escape_cpp_string(node.value)}"'
  elif isinstance(node, CharacterLiteral):
    return escape_cpp_char(node.value)
  elif isinstance(node, BooleanLiteral):
    return node.value.lower()
  else:
    raise ValueError(f"Unknown literal node type: {type(node)}")

def to_cpp_call(func_name: str, args: list[str]) -> str:
  return f"{func_name}({', '.join(args)})"

def to_cpp_var_decl(type_name: str, var_name: str, init_val: str | None = None, is_const: bool = False) -> str:
  const_str = "const " if is_const else ""
  if init_val is not None:
    return f"{const_str}{type_name} {var_name} = {init_val};"
  else:
    return f"{const_str}{type_name} {var_name};"
