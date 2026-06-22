from __future__ import annotations
import sys
import os

from ast.ast_nodes import ASTNode
from semantic.resolver import Resolver
from semantic.type_checker import TypeChecker
from semantic.errors import Diagnostic

class SemanticAnalyzer:
  """
  Facade class that coordinates the semantic analysis phases:
  - Name resolution and scope setup
  - Type checking and type inference
  Reports aggregated compilation warnings and errors.
  """
  def __init__(self) -> None:
    self.resolver: Resolver = Resolver()
    self.errors: list[Diagnostic] = []

  def analyze(self, ast: ASTNode) -> list[Diagnostic]:
    # Phase 1: Resolve names and scopes
    self.resolver.resolve(ast)
    
    # Phase 2: Verify types and infer expressions
    checker = TypeChecker(self.resolver.table, self.resolver.errors, self.resolver.source_cache)
    checker.check(ast)
    
    self.errors = self.resolver.errors
    return self.errors

  @staticmethod
  def format_diagnostics(errors: list[Diagnostic]) -> str:
    output = []
    warnings = [e for e in errors if e.is_warning]
    errs = [e for e in errors if not e.is_warning]
    
    if warnings:
      output.append("\nWarnings:")
      for w in warnings:
        output.append(str(w).strip())
        
    if errs:
      output.append("\nErrors:")
      for e in errs:
        output.append(str(e).strip())
      output.append(f"\nCompilation failed: {len(errs)} error(s), {len(warnings)} warning(s)")
    else:
      output.append("\nSemantic analysis succeeded! 0 errors, 0 warnings.")
      
    return "\n".join(output)
