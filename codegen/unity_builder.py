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
  Program, ASTNode, UseCppDeclaration, UseCDeclaration,
  ImplDeclaration, ModuleDeclaration, EnumDeclaration,
  StructDeclaration, FunctionDeclaration
)
from codegen.cpp_visitor import CppVisitor
from codegen.cpp_printer import CppPrinter

class UnityBuilder:
  """
  Builds a unified C++20 source file from one or more Program ASTs.
  Orders:
    1. Includes (#include)
    2. Module namespaces with contents (Enums, Structs, Functions)
    3. Global main function (at global scope, at the end)
  """
  def __init__(self) -> None:
    pass

  def build(self, programs: list[Program] | Program) -> str:
    if isinstance(programs, Program):
      programs = [programs]

    # Quick check if all programs are empty
    if not any(prog.statements for prog in programs):
      return ""

    visitor = CppVisitor()
    visitor.struct_impls = {}
    visitor.includes = set()

    # Step 1: Pre-scan for all ImplDeclarations and UseCpp/UseC declarations
    for prog in programs:
      visitor.auto_collect_includes(prog)
      for stmt in prog.statements:
        if isinstance(stmt, ImplDeclaration):
          name = stmt.struct_name.name
          if name not in visitor.struct_impls:
            visitor.struct_impls[name] = []
          visitor.struct_impls[name].append(stmt)
        elif isinstance(stmt, (UseCppDeclaration, UseCDeclaration)):
          visitor.visit(stmt)

    # Step 2: Group other declarations by module namespace
    modules: dict[str | None, dict[str, list[ASTNode]]] = {}
    def get_module_bucket(name: str | None) -> dict[str, list[ASTNode]]:
      if name not in modules:
        modules[name] = {
          'enums': [],
          'structs': [],
          'functions': []
        }
      return modules[name]

    main_decl_node = None
    main_module = None

    for prog in programs:
      current_module = None
      for stmt in prog.statements:
        if isinstance(stmt, ModuleDeclaration):
          current_module = stmt.name.name
          continue
        elif isinstance(stmt, (UseCppDeclaration, UseCDeclaration, ImplDeclaration)):
          # Pre-scanned
          continue
        elif isinstance(stmt, FunctionDeclaration) and stmt.name.name == "main":
          main_decl_node = stmt
          main_module = current_module
          continue
        elif hasattr(stmt, "name") and getattr(stmt.name, "name", None) == "main":
          # Just in case it's parsed as VariableDeclaration/AssignmentStatement
          main_decl_node = stmt
          main_module = current_module
          continue

        bucket = get_module_bucket(current_module)
        if isinstance(stmt, EnumDeclaration):
          bucket['enums'].append(stmt)
        elif isinstance(stmt, StructDeclaration):
          bucket['structs'].append(stmt)
        else:
          # Functions and other global statements
          bucket['functions'].append(stmt)

    # Step 3: Print Consolidated Code
    printer = CppPrinter()

    # Includes
    if visitor.includes:
      for header in sorted(visitor.includes):
        printer.write_line(f"#include {header}")
      printer.write_line()

    # Generate each module namespace
    # Sort modules: None (global) last, or sorted by name
    sorted_mod_names = sorted([k for k in modules.keys() if k is not None])
    if None in modules:
      sorted_mod_names.append(None)

    for mod_name in sorted_mod_names:
      contents = modules[mod_name]
      if not contents['enums'] and not contents['structs'] and not contents['functions']:
        continue

      if mod_name is not None:
        printer.write_line(f"namespace {mod_name} {{")
        printer.indent()

      # Enums first
      for enum_node in contents['enums']:
        code = visitor.visit(enum_node)
        if code:
          # Break lines in code if it has multiple lines to avoid double-indenting
          for line in code.splitlines():
            printer.write_line(line)
          printer.write_line()

      # Structs next
      for struct_node in contents['structs']:
        code = visitor.visit(struct_node)
        if code:
          for line in code.splitlines():
            printer.write_line(line)
          printer.write_line()

      # Functions last
      for func_node in contents['functions']:
        code = visitor.visit(func_node)
        if code:
          for line in code.splitlines():
            printer.write_line(line)
          printer.write_line()

      if mod_name is not None:
        printer.dedent()
        printer.write_line(f"}} // namespace {mod_name}")
        printer.write_line()

    # Main function at the global scope at the very end
    if main_decl_node:
      code = visitor.visit(main_decl_node)
      if code and main_module:
        lines = code.splitlines()
        if lines and "{" in lines[0]:
          lines.insert(1, f"  using namespace {main_module};")
          code = "\n".join(lines)
      if code:
        for line in code.splitlines():
          printer.write_line(line)
        printer.write_line()

    # Strip excessive trailing newlines, return exactly one trailing newline
    result = printer.get_code().strip()
    if result:
      return result + "\n"
    return ""
