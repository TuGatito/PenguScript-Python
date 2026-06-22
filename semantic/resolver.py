from __future__ import annotations
import sys
import os
import importlib.util
from typing import Any

# System import path helper to resolve conflict with standard library 'ast' module
_current_dir = os.path.dirname(os.path.abspath(__file__))
_ast_path = os.path.abspath(os.path.join(_current_dir, "../ast/ast_nodes.py"))
if "ast.ast_nodes" not in sys.modules and os.path.exists(_ast_path):
  _spec = importlib.util.spec_from_file_location("ast.ast_nodes", _ast_path)
  _ast_nodes = importlib.util.module_from_spec(_spec)
  sys.modules["ast.ast_nodes"] = _ast_nodes
  _spec.loader.exec_module(_ast_nodes)

from ast.ast_nodes import (
  ASTNode, Program, ModuleDeclaration, ImportDeclaration, UseCppDeclaration,
  UseCDeclaration, StructDeclaration, Field, ImplDeclaration, ConstructorDeclaration,
  DestructorDeclaration, MethodDeclaration, EnumDeclaration, FunctionDeclaration,
  Parameter, Block, VariableDeclaration, AssignmentStatement, ReturnStatement,
  BreakStatement, ContinueStatement, PassStatement, AssertStatement, RaiseStatement,
  ExpressionStatement, Identifier, TypeNode, UnaryOperator, BinaryOperator,
  MemberAccess, IndexExpression, CallExpression, GroupingExpression, IfExpression,
  SwitchExpression, Case, ForComprehension, ForInStatement, ForCStatement,
  ForInfiniteStatement, WhileStatement, TemplateInstantiation, ArrayLiteral
)
from semantic.symbol_table import SymbolTable, Scope, Symbol
from semantic.errors import Diagnostic
from semantic.builtins import populate_builtins

class Resolver:
  """
  Semantic analyzer that resolves all variable, function, type, and module references.
  Performs shadowing checks, global variables check, and main function validation.
  """
  def __init__(self) -> None:
    self.table: SymbolTable = SymbolTable()
    self.errors: list[Diagnostic] = []
    self.source_cache: dict[str, str] = {}
    self.function_depth: int = 0
    self.has_module: bool = False

    # Seed the global scope with builtins
    populate_builtins(self.table.current_scope)

  def get_pos(self, node: ASTNode) -> tuple[int, int]:
    """
    Computes (line, column) from character offset start_pos.
    """
    if not node.file:
      return (1, 1)
      
    if node.file not in self.source_cache:
      if os.path.exists(node.file):
        with open(node.file, "r", encoding="utf-8") as f:
          self.source_cache[node.file] = f.read()
      else:
        self.source_cache[node.file] = ""
        
    source = self.source_cache[node.file]
    if not source:
      return (1, 1)
      
    line = 1
    col = 1
    for i in range(min(node.start_pos, len(source))):
      if source[i] == "\n":
        line += 1
        col = 1
      else:
        col += 1
    return (line, col)

  def report_error(self, message: str, node: ASTNode, suggestion: str | None = None) -> None:
    line, col = self.get_pos(node)
    source = self.source_cache.get(node.file, "") if node.file else ""
    source_line = None
    span_len = 1
    if source:
      source_lines = source.splitlines()
      if 1 <= line <= len(source_lines):
        source_line = source_lines[line - 1]
        if getattr(node, "end_pos", 0) > getattr(node, "start_pos", 0):
          span_len = node.end_pos - node.start_pos
          span_len = max(1, min(span_len, len(source_line) - col + 1))
          
    self.errors.append(
      Diagnostic(
        is_warning=False,
        message=message,
        file=node.file,
        line=line,
        column=col,
        suggestion=suggestion,
        source_line=source_line,
        span_len=span_len
      )
    )

  def report_warning(self, message: str, node: ASTNode, suggestion: str | None = None) -> None:
    line, col = self.get_pos(node)
    source = self.source_cache.get(node.file, "") if node.file else ""
    source_line = None
    span_len = 1
    if source:
      source_lines = source.splitlines()
      if 1 <= line <= len(source_lines):
        source_line = source_lines[line - 1]
        if getattr(node, "end_pos", 0) > getattr(node, "start_pos", 0):
          span_len = node.end_pos - node.start_pos
          span_len = max(1, min(span_len, len(source_line) - col + 1))
          
    self.errors.append(
      Diagnostic(
        is_warning=True,
        message=message,
        file=node.file,
        line=line,
        column=col,
        suggestion=suggestion,
        source_line=source_line,
        span_len=span_len
      )
    )

  def _to_snake_case(self, name: str) -> str:
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

  def resolve(self, node: ASTNode | None) -> None:
    if node is None:
      return
      
    class_name = type(node).__name__
    method_name = f"resolve_{self._to_snake_case(class_name)}"
    method = getattr(self, method_name, None)
    
    if method:
      method(node)
    else:
      self.generic_resolve(node)

  def generic_resolve(self, node: ASTNode) -> None:
    import dataclasses
    if not dataclasses.is_dataclass(node):
      return
    for f in dataclasses.fields(node):
      val = getattr(node, f.name)
      if isinstance(val, ASTNode):
        self.resolve(val)
      elif isinstance(val, list):
        for item in val:
          if isinstance(item, ASTNode):
            self.resolve(item)

  # --- Visitor Resolution Methods ---

  def resolve_program(self, node: Program) -> None:
    self.has_module = False
    for stmt in node.statements:
      self.resolve(stmt)
      
    if not self.has_module:
      self.report_warning(
        "No module declared in this file. It is recommended to define a module to avoid naming conflicts.",
        node,
        suggestion="add 'module <name>' at the top of the file."
      )

  def resolve_module_declaration(self, node: ModuleDeclaration) -> None:
    self.has_module = True
    name = node.name.name
    existing = self.table.lookup_current_scope(name)
    if existing:
      self.report_error(
        f"Module name '{name}' collides with an existing declaration.",
        node,
        suggestion="rename the module or remove duplicate declarations."
      )
    else:
      module_scope = Scope(parent=self.table.current_scope, kind="module")
      sym = Symbol(name=name, kind="module", nested_scope=module_scope, declaration=node)
      self.table.define(name, sym)
      node.scope = module_scope
      # Push it to stack and make it current for subsequent file declarations
      self.table.scope_stack.append(module_scope)
      self.table.current_scope = module_scope

  def resolve_import_declaration(self, node: ImportDeclaration) -> None:
    # Basic validation of import paths, names, and aliases
    if node.alias:
      name = node.alias.name
      existing = self.table.lookup_current_scope(name)
      if existing:
        self.report_error(f"Import alias '{name}' collides with an existing declaration.", node)
      else:
        # Define imported namespace symbol
        import_scope = Scope(parent=self.table.current_scope, kind="module")
        sym = Symbol(name=name, kind="module", nested_scope=import_scope, declaration=node)
        self.table.define(name, sym)
        
    for item in node.names:
      name = item.name
      if name != "*":
        existing = self.table.lookup_current_scope(name)
        if existing:
          self.report_error(f"Imported symbol '{name}' collides with an existing declaration.", node)
        else:
          # Define standard symbol mapping placeholder
          sym = Symbol(name=name, kind="variable", declaration=node)
          self.table.define(name, sym)

  def resolve_use_cpp_declaration(self, node: UseCppDeclaration) -> None:
    pass

  def resolve_use_c_declaration(self, node: UseCDeclaration) -> None:
    pass

  def resolve_function_declaration(self, node: FunctionDeclaration) -> None:
    name = node.name.name
    existing = self.table.lookup(name)
    if existing and existing.kind != "module":
      self.report_error(
        f"Redeclaration of function/symbol '{name}'. Duplicate function declarations are not allowed.",
        node,
        suggestion="rename the function to be unique."
      )

    if name == "main":
      if len(node.params) > 0:
        self.report_error(
          "The 'main' function must not take any parameters.",
          node,
          suggestion="change to 'main = (): int -> ...'"
        )
      if node.return_type is None or node.return_type.name != "int":
        self.report_error(
          "The 'main' function must return 'int'.",
          node,
          suggestion="change to 'main = (): int -> ...'"
        )

    func_scope = Scope(parent=self.table.current_scope, kind="function")
    node.scope = func_scope
    sym = Symbol(name=name, kind="function", nested_scope=func_scope, declaration=node)
    self.table.define(name, sym)

    if node.return_type:
      self.resolve(node.return_type)

    self.table.scope_stack.append(func_scope)
    self.table.current_scope = func_scope
    self.function_depth += 1

    for param in node.params:
      self.resolve(param)
      
    self.resolve(node.body)

    self.function_depth -= 1
    self.table.exit_scope()

  def resolve_parameter(self, node: Parameter) -> None:
    name = node.name.name
    existing = self.table.lookup_current_scope(name)
    if existing:
      self.report_error(f"Redeclaration of parameter '{name}'.", node)
    else:
      outer = self.table.lookup(name)
      if outer and outer.kind in ("variable", "function"):
        self.report_error(f"Parameter '{name}' shadows an outer declaration of '{name}'. Shadowing is not allowed.", node)
        
    sym = Symbol(name=name, kind="variable", type=node.type, declaration=node)
    self.table.define(name, sym)
    
    if node.type:
      self.resolve(node.type)
    if node.default:
      self.resolve(node.default)

  def resolve_struct_declaration(self, node: StructDeclaration) -> None:
    name = node.name.name
    existing = self.table.lookup(name)
    if existing and existing.kind != "module":
      self.report_error(f"Redeclaration of type '{name}'.", node)
      
    struct_scope = Scope(parent=self.table.current_scope, kind="struct")
    node.scope = struct_scope
    sym = Symbol(name=name, kind="type", nested_scope=struct_scope, declaration=node)
    self.table.define(name, sym)

    self.table.scope_stack.append(struct_scope)
    self.table.current_scope = struct_scope

    for field in node.fields:
      self.resolve(field)

    self.table.exit_scope()

  def resolve_field(self, node: Field) -> None:
    name = node.name.name
    existing = self.table.lookup_current_scope(name)
    if existing:
      self.report_error(f"Duplicate struct field '{name}'.", node)
    else:
      sym = Symbol(name=name, kind="field", type=node.type, declaration=node)
      self.table.define(name, sym)
      
    if node.type:
      self.resolve(node.type)

  def resolve_impl_declaration(self, node: ImplDeclaration) -> None:
    struct_name = node.struct_name.name
    struct_symbol = self.table.lookup(struct_name)
    if not struct_symbol or struct_symbol.kind != "type" or not struct_symbol.nested_scope:
      self.report_error(
        f"Cannot implement methods for undefined struct '{struct_name}'.",
        node,
        suggestion=f"declare 'struct {struct_name}' before impl."
      )
      struct_scope = Scope(parent=self.table.current_scope, kind="struct")
    else:
      struct_scope = struct_symbol.nested_scope

    node.scope = struct_scope
    self.table.scope_stack.append(struct_scope)
    self.table.current_scope = struct_scope

    for ctor in node.constructors:
      self.resolve_constructor_declaration(ctor, struct_name)
      
    if node.destructor:
      self.resolve_destructor_declaration(node.destructor, struct_name)
      
    for method in node.methods:
      self.resolve_method_declaration(method, struct_name)

    self.table.exit_scope()

  def resolve_constructor_declaration(self, node: ConstructorDeclaration, struct_name: str) -> None:
    existing_ctor = self.table.lookup_current_scope("constructor")
    if existing_ctor:
      self.report_error(f"Duplicate constructor declaration in struct '{struct_name}'.", node)
    else:
      ctor_sym = Symbol(name="constructor", kind="function", declaration=node)
      self.table.define("constructor", ctor_sym)

    ctor_scope = Scope(parent=self.table.current_scope, kind="function")
    node.scope = ctor_scope
    self.table.scope_stack.append(ctor_scope)
    self.table.current_scope = ctor_scope
    self.function_depth += 1

    this_sym = Symbol(name="this", kind="variable", type=TypeNode(name=struct_name), declaration=node)
    self.table.define("this", this_sym)

    for param in node.params:
      self.resolve(param)
    self.resolve(node.body)

    self.function_depth -= 1
    self.table.exit_scope()

  def resolve_destructor_declaration(self, node: DestructorDeclaration, struct_name: str) -> None:
    existing_dtor = self.table.lookup_current_scope("destructor")
    if existing_dtor:
      self.report_error(f"Duplicate destructor declaration in struct '{struct_name}'.", node)
    else:
      dtor_sym = Symbol(name="destructor", kind="function", declaration=node)
      self.table.define("destructor", dtor_sym)

    dtor_scope = Scope(parent=self.table.current_scope, kind="function")
    node.scope = dtor_scope
    self.table.scope_stack.append(dtor_scope)
    self.table.current_scope = dtor_scope
    self.function_depth += 1

    this_sym = Symbol(name="this", kind="variable", type=TypeNode(name=struct_name), declaration=node)
    self.table.define("this", this_sym)

    self.resolve(node.body)

    self.function_depth -= 1
    self.table.exit_scope()

  def resolve_method_declaration(self, node: MethodDeclaration, struct_name: str) -> None:
    name = node.name.name
    existing = self.table.lookup_current_scope(name)
    if existing:
      self.report_error(f"Redeclaration of method/field '{name}' in struct context.", node)
      
    method_scope = Scope(parent=self.table.current_scope, kind="function")
    node.scope = method_scope
    sym = Symbol(name=name, kind="function", nested_scope=method_scope, declaration=node)
    self.table.define(name, sym)

    self.table.scope_stack.append(method_scope)
    self.table.current_scope = method_scope
    self.function_depth += 1

    this_sym = Symbol(name="this", kind="variable", type=TypeNode(name=struct_name), declaration=node)
    self.table.define("this", this_sym)

    for param in node.params:
      self.resolve(param)
    if node.return_type:
      self.resolve(node.return_type)
    self.resolve(node.body)

    self.function_depth -= 1
    self.table.exit_scope()

  def resolve_enum_declaration(self, node: EnumDeclaration) -> None:
    name = node.name.name
    existing = self.table.lookup(name)
    if existing and existing.kind != "module":
      self.report_error(f"Redeclaration of type '{name}'.", node)
      
    enum_scope = Scope(parent=self.table.current_scope, kind="struct")
    node.scope = enum_scope
    sym = Symbol(name=name, kind="type", nested_scope=enum_scope, declaration=node)
    self.table.define(name, sym)

    self.table.scope_stack.append(enum_scope)
    self.table.current_scope = enum_scope

    for variant in node.variants:
      variant_name = variant.name
      existing_variant = self.table.lookup_current_scope(variant_name)
      if existing_variant:
        self.report_error(f"Duplicate enum variant '{variant_name}' in enum '{name}'.", variant)
      else:
        variant_sym = Symbol(name=variant_name, kind="enum_variant", type=TypeNode(name=name), declaration=variant)
        self.table.define(variant_name, variant_sym)

    self.table.exit_scope()

  def resolve_block(self, node: Block) -> None:
    block_scope = self.table.enter_scope("block")
    node.scope = block_scope
    for stmt in node.statements:
      self.resolve(stmt)
    self.table.exit_scope()

  def resolve_variable_declaration(self, node: VariableDeclaration) -> None:
    name = node.name.name
    if node.kind in ("var", "ref") and self.function_depth == 0:
      self.report_error(
        f"Variable '{name}' of kind '{node.kind}' cannot be declared in the global scope.",
        node,
        suggestion="declare this variable inside a function, or declare it as const."
      )
      
    existing = self.table.lookup_current_scope(name)
    if existing:
      self.report_error(f"Redeclaration of variable '{name}' in the same scope.", node)
    else:
      if not getattr(node, "_shadowing_checked", False):
        outer = self.table.lookup(name)
        if outer and outer.kind in ("variable", "function"):
          self.report_error(
            f"Variable '{name}' shadows an existing declaration of '{name}' (kind: {outer.kind}). Shadowing is not allowed.",
            node,
            suggestion="rename the variable to prevent shadowing conflicts."
          )

    sym = Symbol(
      name=name, 
      kind="variable", 
      type=node.type, 
      is_mutable=(node.kind != "const"), 
      is_const=(node.kind == "const"), 
      declaration=node
    )
    self.table.define(name, sym)

    if node.type:
      self.resolve(node.type)
    if node.value:
      self.resolve(node.value)

  def resolve_assignment_statement(self, node: AssignmentStatement) -> None:
    self.resolve(node.left)
    self.resolve(node.right)

  def resolve_expression_statement(self, node: ExpressionStatement) -> None:
    self.resolve(node.expression)

  def resolve_identifier(self, node: Identifier) -> None:
    name = node.name
    sym = self.table.lookup(name)
    if not sym:
      self.report_error(
        f"Undeclared identifier '{name}'.",
        node,
        suggestion=f"declare '{name}' before use, or check the spelling."
      )
    else:
      node.symbol = sym

  def _get_full_dotted_path(self, node: Expression) -> str | None:
    if isinstance(node, Identifier):
      return node.name
    elif isinstance(node, MemberAccess):
      obj_path = self._get_full_dotted_path(node.object)
      if obj_path:
        return f"{obj_path}.{node.member.name}"
    return None

  def resolve_member_access(self, node: MemberAccess) -> None:
    self.resolve(node.object)

    path = self._get_full_dotted_path(node)
    if path:
      sym = self.table.lookup(path)
      if sym:
        node.member.symbol = sym
        node.symbol = sym
        return

    obj_sym = getattr(node.object, "symbol", None)
    if not obj_sym and isinstance(node.object, Identifier):
      obj_sym = self.table.lookup(node.object.name)

    if obj_sym:
      struct_sym = None
      if obj_sym.kind == "type":
        struct_sym = obj_sym
      elif hasattr(obj_sym, "type") and obj_sym.type:
        obj_type = obj_sym.type
        if obj_type.name in ("std.unique_ptr", "std.shared_ptr") and len(obj_type.type_arguments) > 0:
          obj_type = obj_type.type_arguments[0]
        struct_sym = self.table.lookup(obj_type.name)

      if struct_sym and struct_sym.kind == "type" and struct_sym.nested_scope:
        member_sym = struct_sym.nested_scope.lookup_local(node.member.name)
        if member_sym:
          node.member.symbol = member_sym
          node.symbol = member_sym

  def resolve_type_node(self, node: TypeNode) -> None:
    if not node.name:
      return
    sym = self.table.lookup(node.name)
    if not sym:
      self.report_error(
        f"Undefined type '{node.name}'.",
        node,
        suggestion="ensure the type is defined or imported."
      )
    else:
      node.symbol = sym
      
    for arg in node.type_arguments:
      self.resolve(arg)

  def resolve_lambda_expression(self, node: LambdaExpression) -> None:
    lambda_scope = Scope(parent=self.table.current_scope, kind="function")
    node.scope = lambda_scope
    self.table.scope_stack.append(lambda_scope)
    self.table.current_scope = lambda_scope
    self.function_depth += 1

    for param in node.params:
      self.resolve(param)
    if node.return_type:
      self.resolve(node.return_type)
    self.resolve(node.body)

    self.function_depth -= 1
    self.table.exit_scope()

  def resolve_for_comprehension(self, node: ForComprehension) -> None:
    self.resolve(node.iterable)
    
    comprehension_scope = self.table.enter_scope("block")
    node.scope = comprehension_scope
    name = node.variable.name
    sym = Symbol(name=name, kind="variable", declaration=node.variable)
    self.table.define(name, sym)
    
    self.resolve(node.body_expr)
    self.table.exit_scope()

  def resolve_for_in_statement(self, node: ForInStatement) -> None:
    self.resolve(node.iterable)
    
    loop_scope = self.table.enter_scope("block")
    node.scope = loop_scope
    name = node.variable.name
    
    outer = self.table.lookup(name)
    if outer and outer.kind in ("variable", "function"):
      self.report_error(
        f"Loop variable '{name}' shadows an existing declaration of '{name}' (kind: {outer.kind}). Shadowing is not allowed.",
        node.variable,
        suggestion="rename the loop variable to prevent shadowing conflicts."
      )

    sym = Symbol(name=name, kind="variable", declaration=node.variable)
    self.table.define(name, sym)
    
    for stmt in node.body.statements:
      self.resolve(stmt)
      
    self.table.exit_scope()

  def resolve_for_c_statement(self, node: ForCStatement) -> None:
    loop_scope = self.table.enter_scope("block")
    node.scope = loop_scope
    
    # If init is an AssignmentStatement with an Identifier LHS, implicitly declare it in loop_scope
    if node.init and isinstance(node.init, AssignmentStatement) and isinstance(node.init.left, Identifier):
      name = node.init.left.name
      sym = Symbol(name=name, kind="variable", declaration=node.init.left)
      self.table.define(name, sym)
    elif node.init and isinstance(node.init, VariableDeclaration):
      name = node.init.name.name
      outer = self.table.lookup(name)
      if outer and outer.kind in ("variable", "function"):
        self.report_error(
          f"Loop variable '{name}' shadows an existing declaration of '{name}' (kind: {outer.kind}). Shadowing is not allowed.",
          node.init,
          suggestion="rename the loop variable to prevent shadowing conflicts."
        )
      node.init._shadowing_checked = True
      
    if node.init:
      self.resolve(node.init)
    if node.condition:
      self.resolve(node.condition)
    if node.increment:
      self.resolve(node.increment)
      
    for stmt in node.body.statements:
      self.resolve(stmt)
      
    self.table.exit_scope()


def test_resolver() -> None:
  print("Running Resolver unit tests...")

  # Test Case 1: Simple valid program (no errors)
  # module main
  # main = (): int ->
  #   var x = 42
  #   return x
  prog1 = Program(
    statements=[
      ModuleDeclaration(name=Identifier(name="main")),
      FunctionDeclaration(
        name=Identifier(name="main"),
        params=[],
        return_type=TypeNode(name="int"),
        body=Block(
          statements=[
            VariableDeclaration(name=Identifier(name="x"), kind="var", value=Identifier(name="int")), # value doesn't matter for resolve
            ReturnStatement(value=Identifier(name="x"))
          ]
        )
      )
    ]
  )
  resolver1 = Resolver()
  resolver1.resolve(prog1)
  assert len(resolver1.errors) == 0, f"Expected no errors, got: {resolver1.errors}"
  print("OK: Test 1 (Simple valid program) passed.")

  # Test Case 2: Global variable var/ref check
  # var g = 10
  prog2 = Program(
    statements=[
      VariableDeclaration(name=Identifier(name="g"), kind="var", value=Identifier(name="int"))
    ]
  )
  resolver2 = Resolver()
  resolver2.resolve(prog2)
  # Expects error (global variable) and warning (no module declared)
  assert any(not e.is_warning and "cannot be declared in the global scope" in e.message for e in resolver2.errors)
  print("OK: Test 2 (Global variable error) passed.")

  # Test Case 3: Shadowing check
  # x = 10
  # if x
  #   var x = 20
  prog3 = Program(
    statements=[
      FunctionDeclaration(
        name=Identifier(name="test"),
        params=[],
        body=Block(
          statements=[
            VariableDeclaration(name=Identifier(name="x"), kind="var", value=Identifier(name="int")),
            Block(
              statements=[
                VariableDeclaration(name=Identifier(name="x"), kind="var", value=Identifier(name="int"))
              ]
            )
          ]
        )
      )
    ]
  )
  resolver3 = Resolver()
  resolver3.resolve(prog3)
  assert any("shadows" in e.message for e in resolver3.errors)
  print("OK: Test 3 (Shadowing error) passed.")

  # Test Case 4: Main validation check
  # main = (x: int): void -> pass
  prog4 = Program(
    statements=[
      FunctionDeclaration(
        name=Identifier(name="main"),
        params=[Parameter(name=Identifier(name="x"), type=TypeNode(name="int"))],
        return_type=TypeNode(name="void"),
        body=Block(statements=[PassStatement()])
      )
    ]
  )
  resolver4 = Resolver()
  resolver4.resolve(prog4)
  assert any("must not take any parameters" in e.message for e in resolver4.errors)
  assert any("must return 'int'" in e.message for e in resolver4.errors)
  print("OK: Test 4 (Main signature validation) passed.")

  # Test Case 5: Duplicate fields & duplicate variants check
  prog5 = Program(
    statements=[
      StructDeclaration(
        name=Identifier(name="Point"),
        fields=[
          Field(name=Identifier(name="x"), type=TypeNode(name="int")),
          Field(name=Identifier(name="x"), type=TypeNode(name="int"))
        ]
      ),
      EnumDeclaration(
        name=Identifier(name="Color"),
        variants=[
          Identifier(name="Red"),
          Identifier(name="Red")
        ]
      )
    ]
  )
  resolver5 = Resolver()
  resolver5.resolve(prog5)
  assert any("Duplicate struct field" in e.message for e in resolver5.errors), "Expected duplicate struct field error"
  assert any("Duplicate enum variant" in e.message for e in resolver5.errors), "Expected duplicate enum variant error"
  print("OK: Test 5 (Duplicate fields & variants) passed.")

  # Test Case 6: Duplicate constructors & duplicate destructors & undefined struct impl
  prog6 = Program(
    statements=[
      StructDeclaration(
        name=Identifier(name="Point"),
        fields=[
          Field(name=Identifier(name="x"), type=TypeNode(name="int"))
        ]
      ),
      ImplDeclaration(
        struct_name=Identifier(name="Point"),
        constructors=[
          ConstructorDeclaration(params=[], body=Block(statements=[PassStatement()])),
          ConstructorDeclaration(params=[], body=Block(statements=[PassStatement()]))
        ],
        destructor=DestructorDeclaration(body=Block(statements=[PassStatement()])),
        methods=[]
      ),
      ImplDeclaration(
        struct_name=Identifier(name="Point"),
        constructors=[],
        destructor=DestructorDeclaration(body=Block(statements=[PassStatement()])),
        methods=[]
      ),
      ImplDeclaration(
        struct_name=Identifier(name="UndefinedStruct"),
        constructors=[],
        destructor=None,
        methods=[]
      )
    ]
  )
  resolver6 = Resolver()
  resolver6.resolve(prog6)
  assert any("Duplicate constructor declaration" in e.message for e in resolver6.errors), "Expected duplicate constructor error"
  assert any("Duplicate destructor declaration" in e.message for e in resolver6.errors), "Expected duplicate destructor error"
  assert any("Cannot implement methods for undefined struct" in e.message for e in resolver6.errors), "Expected undefined struct impl error"
  print("OK: Test 6 (Constructor/destructor/impl validation) passed.")

  # Test Case 7: ForInStatement shadowing check
  prog7 = Program(
    statements=[
      FunctionDeclaration(
        name=Identifier(name="test"),
        params=[],
        body=Block(
          statements=[
            VariableDeclaration(name=Identifier(name="x"), kind="var", value=Identifier(name="int")),
            ForInStatement(
              variable=Identifier(name="x"),
              iterable=ArrayLiteral(elements=[]),
              body=Block(statements=[PassStatement()])
            )
          ]
        )
      )
    ]
  )
  resolver7 = Resolver()
  resolver7.resolve(prog7)
  assert any("Loop variable 'x' shadows" in e.message for e in resolver7.errors), "Expected loop variable shadowing error"
  print("OK: Test 7 (For-in loop variable shadowing) passed.")

  # Test Case 8: ForCStatement shadowing check
  prog8 = Program(
    statements=[
      FunctionDeclaration(
        name=Identifier(name="test"),
        params=[],
        body=Block(
          statements=[
            VariableDeclaration(name=Identifier(name="x"), kind="var", value=Identifier(name="int")),
            ForCStatement(
              init=VariableDeclaration(name=Identifier(name="x"), kind="var", value=Identifier(name="int")),
              condition=None,
              increment=None,
              body=Block(statements=[PassStatement()])
            )
          ]
        )
      )
    ]
  )
  resolver8 = Resolver()
  resolver8.resolve(prog8)
  assert any("Loop variable 'x' shadows" in e.message for e in resolver8.errors), "Expected loop variable shadowing error in C-style for"
  print("OK: Test 8 (For-C loop variable shadowing) passed.")

  # Test Case 9: Function declaration colliding with outer type
  prog9 = Program(
    statements=[
      StructDeclaration(
        name=Identifier(name="Point"),
        fields=[]
      ),
      FunctionDeclaration(
        name=Identifier(name="Point"),
        params=[],
        return_type=TypeNode(name="int"),
        body=Block(statements=[PassStatement()])
      )
    ]
  )
  resolver9 = Resolver()
  resolver9.resolve(prog9)
  assert any("Redeclaration of function/symbol 'Point'" in e.message for e in resolver9.errors), "Expected redeclaration collision error"
  print("OK: Test 9 (Redeclaration collision with outer symbol) passed.")

  print("Resolver unit tests passed successfully!")

if __name__ == "__main__":
  test_resolver()
