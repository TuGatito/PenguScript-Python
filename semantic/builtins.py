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

from ast.ast_nodes import TypeNode
from semantic.symbol_table import Symbol, Scope

def populate_builtins(global_scope: Scope) -> None:
  """
  Populates the given global scope with intrinsic primitives, basic library functions,
  and the std namespace symbols.
  """
  # 1. Primitives (types)
  primitive_types = ["int", "float", "double", "bool", "void", "char"]
  for type_name in primitive_types:
    global_scope.define(type_name, Symbol(name=type_name, kind="type"))
    
  # 'string' type alias (represented as mapping to std.string or type symbol directly)
  global_scope.define("string", Symbol(name="string", kind="type", type=TypeNode(name="std.string")))

  # 2. Builtin standard library base level functions
  global_scope.define("printf", Symbol(name="printf", kind="function"))
  global_scope.define("print", Symbol(name="print", kind="function"))
  global_scope.define("scanf", Symbol(name="scanf", kind="function"))

  # 3. std namespace setup
  std_scope = Scope(parent=global_scope, kind="namespace")
  std_symbol = Symbol(name="std", kind="namespace", nested_scope=std_scope)
  global_scope.define("std", std_symbol)

  # Nested std types
  std_types = ["string", "vector", "expected", "string_view"]
  for type_name in std_types:
    std_scope.define(type_name, Symbol(name=type_name, kind="type"))

  # Nested std variables/streams
  std_scope.define("cout", Symbol(name="cout", kind="variable"))
  std_scope.define("endl", Symbol(name="endl", kind="variable"))

  # Nested std functions
  std_scope.define("make_shared", Symbol(name="make_shared", kind="function"))
  std_scope.define("make_unique", Symbol(name="make_unique", kind="function"))
  std_scope.define("unexpected", Symbol(name="unexpected", kind="function"))


def test_builtins() -> None:
  print("Running builtins unit tests...")
  
  global_scope = Scope(parent=None, kind="global")
  populate_builtins(global_scope)
  
  # Check primitives
  assert global_scope.lookup("int") is not None
  assert global_scope.lookup("int").kind == "type"
  assert global_scope.lookup("string") is not None
  assert global_scope.lookup("string").kind == "type"
  
  # Check basic library function
  assert global_scope.lookup("printf") is not None
  assert global_scope.lookup("printf").kind == "function"
  
  # Check std namespace resolution via dotted names
  assert global_scope.lookup_any("std") is not None
  assert global_scope.lookup_any("std").kind == "namespace"
  
  assert global_scope.lookup_any("std.cout") is not None
  assert global_scope.lookup_any("std.cout").kind == "variable"
  
  assert global_scope.lookup_any("std.make_unique") is not None
  assert global_scope.lookup_any("std.make_unique").kind == "function"
  
  assert global_scope.lookup_any("std.nonexistent") is None
  
  print("builtins unit tests passed successfully!")

if __name__ == "__main__":
  test_builtins()
