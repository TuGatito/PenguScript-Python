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

from ast.ast_nodes import ASTNode, Program
from codegen.cpp_visitor import CppVisitor
from codegen.unity_builder import UnityBuilder

class CppGenerator:
  """
  Coordinator class for C++20 code generation.
  Walks the AST using CppVisitor and saves the generated code to the output file.
  """
  def __init__(self) -> None:
    self.visitor: CppVisitor = CppVisitor()
    self.builder: UnityBuilder = UnityBuilder()

  def generate(self, ast: ASTNode | list[Program], output_path: str) -> None:
    """
    Generates C++ code from AST and writes it to output_path.
    """
    if isinstance(ast, (Program, list)):
      code = self.builder.build(ast)
    else:
      code = self.visitor.visit(ast)
    
    # Ensure target directory exists
    dir_name = os.path.dirname(os.path.abspath(output_path))
    if dir_name:
      os.makedirs(dir_name, exist_ok=True)
      
    with open(output_path, "w", encoding="utf-8") as f:
      f.write(code)
