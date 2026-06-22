from __future__ import annotations
import sys
import os
import importlib.util
from typing import TYPE_CHECKING, Any

# System import path helper to resolve conflict with standard library 'ast' module
_current_dir = os.path.dirname(os.path.abspath(__file__))
_ast_path = os.path.abspath(os.path.join(_current_dir, "../ast/ast_nodes.py"))
if "ast.ast_nodes" not in sys.modules and os.path.exists(_ast_path):
  _spec = importlib.util.spec_from_file_location("ast.ast_nodes", _ast_path)
  _ast_nodes = importlib.util.module_from_spec(_spec)
  sys.modules["ast.ast_nodes"] = _ast_nodes
  _spec.loader.exec_module(_ast_nodes)

from ast.ast_nodes import ASTNode, TypeNode

class Symbol:
  """
  Represents a resolved identifier/name in the source code.
  """
  def __init__(
    self, 
    name: str, 
    kind: str, 
    type: TypeNode | None = None, 
    declaration: ASTNode | None = None,
    is_mutable: bool = True,
    is_const: bool = False,
    nested_scope: Scope | None = None
  ) -> None:
    self.name: str = name
    self.kind: str = kind  # e.g., "variable", "function", "type", "module", "field", "enum_variant", "namespace"
    self.type: TypeNode | None = type
    self.declaration: ASTNode | None = declaration
    self.is_mutable: bool = is_mutable
    self.is_const: bool = is_const
    self.nested_scope: Scope | None = nested_scope
    self.scope: Scope | None = None  # Filled when defined in a scope

  def __repr__(self) -> str:
    return f"Symbol(name='{self.name}', kind='{self.kind}', type={self.type}, is_mutable={self.is_mutable}, is_const={self.is_const})"


class Scope:
  """
  Represents a lexical scope in the symbol table.
  """
  def __init__(self, parent: Scope | None = None, kind: str = "global") -> None:
    self.symbols: dict[str, Symbol] = {}
    self.parent: Scope | None = parent
    self.kind: str = kind  # e.g., "global", "function", "block", "struct", "impl"

  def define(self, name: str, symbol: Symbol) -> None:
    """
    Defines a new symbol in this scope.
    """
    symbol.scope = self
    self.symbols[name] = symbol

  def lookup(self, name: str) -> Symbol | None:
    """
    Looks up a symbol in this scope or recursive parent scopes (simple names).
    """
    if name in self.symbols:
      return self.symbols[name]
    if self.parent:
      return self.parent.lookup(name)
    return None

  def lookup_local(self, name: str) -> Symbol | None:
    """
    Looks up a symbol strictly in this scope (no parent traversal).
    """
    return self.symbols.get(name)

  def lookup_any(self, name: str) -> Symbol | None:
    """
    Looks up a symbol, supporting dotted paths (e.g., 'std.cout').
    """
    if "." in name:
      parts = name.split(".")
      current = self.lookup(parts[0])
      if not current:
        return None
      for part in parts[1:]:
        if current.nested_scope:
          current = current.nested_scope.lookup_local(part)
          if not current:
            return None
        else:
          return None
      return current
    return self.lookup(name)

  def __repr__(self) -> str:
    return f"Scope(kind='{self.kind}', symbols={list(self.symbols.keys())})"


class SymbolTable:
  """
  Manages lexical scopes during semantic analysis.
  """
  def __init__(self) -> None:
    self.current_scope: Scope = Scope(parent=None, kind="global")
    self.scope_stack: list[Scope] = [self.current_scope]

  def enter_scope(self, kind: str) -> Scope:
    """
    Enters a new nested scope.
    """
    new_scope = Scope(parent=self.current_scope, kind=kind)
    self.scope_stack.append(new_scope)
    self.current_scope = new_scope
    return new_scope

  def exit_scope(self) -> Scope:
    """
    Exits the current scope and returns to the parent scope.
    """
    if len(self.scope_stack) <= 1:
      raise ValueError("Cannot exit global scope")
    self.scope_stack.pop()
    self.current_scope = self.scope_stack[-1]
    return self.current_scope

  def define(self, name: str, symbol: Symbol) -> None:
    """
    Defines a symbol in the current scope.
    """
    self.current_scope.define(name, symbol)

  def lookup(self, name: str) -> Symbol | None:
    """
    Looks up a symbol from the current scope.
    """
    return self.current_scope.lookup_any(name)

  def lookup_current_scope(self, name: str) -> Symbol | None:
    """
    Looks up a symbol only in the current active scope.
    """
    return self.current_scope.lookup_local(name)


def test_symbol_table() -> None:
  print("Running SymbolTable unit tests...")
  
  table = SymbolTable()
  assert table.current_scope.kind == "global"
  
  # Define a type symbol in global scope
  type_int = Symbol(name="int", kind="type")
  table.define("int", type_int)
  assert table.lookup("int") == type_int
  
  # Define a variable
  var_x = Symbol(name="x", kind="variable", type=TypeNode(name="int"))
  table.define("x", var_x)
  assert table.lookup("x") == var_x
  
  # Enter function scope
  table.enter_scope("function")
  assert table.current_scope.kind == "function"
  
  # Lookup x from child scope (should resolve to global x)
  assert table.lookup("x") == var_x
  assert table.lookup_current_scope("x") is None
  
  # Define local variable x (shadowing)
  local_x = Symbol(name="x", kind="variable", type=TypeNode(name="int"))
  table.define("x", local_x)
  assert table.lookup("x") == local_x
  assert table.lookup_current_scope("x") == local_x
  
  # Exit scope
  table.exit_scope()
  assert table.current_scope.kind == "global"
  assert table.lookup("x") == var_x
  
  # Test nested namespaces (dotted lookups)
  std_scope = Scope(kind="namespace")
  std_symbol = Symbol(name="std", kind="namespace", nested_scope=std_scope)
  table.define("std", std_symbol)
  
  cout_symbol = Symbol(name="cout", kind="variable")
  std_scope.define("cout", cout_symbol)
  
  assert table.lookup("std.cout") == cout_symbol
  assert table.lookup("std.nonexistent") is None
  
  print("SymbolTable unit tests passed successfully!")

if __name__ == "__main__":
  test_symbol_table()
