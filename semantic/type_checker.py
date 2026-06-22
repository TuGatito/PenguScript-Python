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
  ForInfiniteStatement, WhileStatement, TemplateInstantiation, ArrayLiteral,
  IntegerLiteral, FloatLiteral, StringLiteral, CharacterLiteral, BooleanLiteral,
  Expression, LambdaExpression
)
from semantic.symbol_table import SymbolTable, Scope, Symbol
from semantic.errors import Diagnostic

def normalize_type_name(name: str) -> str:
  if name == "string":
    return "std.string"
  return name

def types_equal(t1: TypeNode | None, t2: TypeNode | None) -> bool:
  if t1 is None or t2 is None:
    return False
  return (
    normalize_type_name(t1.name) == normalize_type_name(t2.name) and
    t1.is_ref == t2.is_ref and
    t1.array_size == t2.array_size and
    len(t1.type_arguments) == len(t2.type_arguments) and
    all(types_equal(a1, a2) for a1, a2 in zip(t1.type_arguments, t2.type_arguments))
  )

def is_assignable(target: TypeNode | None, value: TypeNode | None) -> bool:
  if target is None or value is None:
    return False
    
  if target.is_ref or value.is_ref:
    target_raw = TypeNode(name=target.name, type_arguments=target.type_arguments, array_size=target.array_size, is_ref=False)
    value_raw = TypeNode(name=value.name, type_arguments=value.type_arguments, array_size=value.array_size, is_ref=False)
    if is_assignable(target_raw, value_raw):
      return True

  if types_equal(target, value):
    return True
    
  # Implicit conversions: int -> float -> double
  if target.name == "float" and value.name == "int":
    return True
  if target.name == "double" and value.name in ("int", "float"):
    return True
    
  # const char* / string literal -> std.string or std.string_view
  if value.name == "const char*" and normalize_type_name(target.name) in ("std.string", "std.string_view"):
    return True
    
  # std.expected<T, E> is assignable from T or std.unexpected<E>
  if target.name == "std.expected" and len(target.type_arguments) == 2:
    success_t = target.type_arguments[0]
    error_t = target.type_arguments[1]
    # Check assignable from success type T
    if is_assignable(success_t, value):
      return True
    # Check assignable from std.unexpected<E>
    if value.name == "std.unexpected" and len(value.type_arguments) > 0:
      if is_assignable(error_t, value.type_arguments[0]):
        return True

  # smart pointer to raw pointer/reference compatibility
  if value.name in ("std.unique_ptr", "std.shared_ptr") and len(value.type_arguments) > 0:
    if is_assignable(target, value.type_arguments[0]):
      return True

  # Array/array literal to std.vector compatibility
  if target.name == "std.vector" and len(target.type_arguments) > 0 and value.array_size is not None:
    if is_assignable(target.type_arguments[0], TypeNode(name=value.name, type_arguments=value.type_arguments)):
      return True

  return False


class TypeChecker:
  """
  Semantic analyzer pass for type verification and inference.
  """
  def __init__(self, table: SymbolTable, errors: list[Diagnostic], source_cache: dict[str, str]) -> None:
    self.table: SymbolTable = table
    self.errors: list[Diagnostic] = errors
    self.source_cache: dict[str, str] = source_cache
    self.expected_return_types: list[TypeNode] = []

  def get_pos(self, node: ASTNode) -> tuple[int, int]:
    if not node.file:
      return (1, 1)
    if node.file not in self.source_cache:
      return (1, 1)
    source = self.source_cache[node.file]
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

  def is_numeric(self, t: TypeNode) -> bool:
    return t.name in ("int", "float", "double", "char")

  def is_string_like(self, t: TypeNode) -> bool:
    name = normalize_type_name(t.name)
    return name in ("std.string", "std.string_view", "const char*")

  def promote_numeric_types(self, t1: TypeNode, t2: TypeNode) -> TypeNode:
    names = [t1.name, t2.name]
    if "double" in names:
      return TypeNode(name="double")
    if "float" in names:
      return TypeNode(name="float")
    return TypeNode(name="int")

  def _to_snake_case(self, name: str) -> str:
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

  def check(self, node: ASTNode | None) -> TypeNode | None:
    if node is None:
      return None
      
    if isinstance(node, Program):
      self.table.scope_stack = [self.table.scope_stack[0]]
      self.table.current_scope = self.table.scope_stack[0]
      
    class_name = type(node).__name__
    method_name = f"check_{self._to_snake_case(class_name)}"
    method = getattr(self, method_name, None)
    
    if method:
      return method(node)
    else:
      self.generic_check(node)
      return TypeNode(name="void")

  def generic_check(self, node: ASTNode) -> None:
    import dataclasses
    if not dataclasses.is_dataclass(node):
      return
    for f in dataclasses.fields(node):
      val = getattr(node, f.name)
      if isinstance(val, ASTNode):
        self.check(val)
      elif isinstance(val, list):
        for item in val:
          if isinstance(item, ASTNode):
            self.check(item)

  # --- Visitor Check Methods ---

  def check_program(self, node: Program) -> None:
    for stmt in node.statements:
      self.check(stmt)

  def check_module_declaration(self, node: ModuleDeclaration) -> None:
    sym = self.table.lookup(node.name.name)
    if sym and sym.nested_scope:
      self.table.scope_stack.append(sym.nested_scope)
      self.table.current_scope = sym.nested_scope

  def check_import_declaration(self, node: ImportDeclaration) -> None:
    pass

  def check_use_cpp_declaration(self, node: UseCppDeclaration) -> None:
    pass

  def check_use_c_declaration(self, node: UseCDeclaration) -> None:
    pass

  def check_function_declaration(self, node: FunctionDeclaration) -> None:
    expected_ret = node.return_type if node.return_type else TypeNode(name="void")
    self.expected_return_types.append(expected_ret)
    
    func_scope = getattr(node, "scope", None)
    if func_scope:
      self.table.scope_stack.append(func_scope)
      self.table.current_scope = func_scope
    else:
      func_sym = self.table.lookup(node.name.name)
      if func_sym and func_sym.nested_scope:
        func_scope = func_sym.nested_scope
        self.table.scope_stack.append(func_scope)
        self.table.current_scope = func_scope
      
    self.check(node.return_type)
    for param in node.params:
      self.check(param)
    self.check(node.body)
    
    if func_scope:
      self.table.exit_scope()
      
    self.expected_return_types.pop()

  def check_lambda_expression(self, node: LambdaExpression) -> TypeNode:
    expected_ret = node.return_type if node.return_type else TypeNode(name="void")
    self.expected_return_types.append(expected_ret)
    
    lambda_scope = getattr(node, "scope", None)
    if lambda_scope:
      self.table.scope_stack.append(lambda_scope)
      self.table.current_scope = lambda_scope
    else:
      lambda_scope = Scope(parent=self.table.current_scope, kind="function")
      self.table.scope_stack.append(lambda_scope)
      self.table.current_scope = lambda_scope
      
    for param in node.params:
      self.check(param)
    if node.return_type:
      self.check(node.return_type)
    self.check(node.body)
    
    self.table.exit_scope()
    self.expected_return_types.pop()
    
    return TypeNode(
      name="std.function",
      type_arguments=[expected_ret] + [p.type if p.type else TypeNode(name="void") for p in node.params]
    )

  def check_parameter(self, node: Parameter) -> None:
    if node.type:
      self.check(node.type)
    if node.default:
      self.check(node.default)

  def check_struct_declaration(self, node: StructDeclaration) -> None:
    struct_scope = getattr(node, "scope", None)
    if struct_scope:
      self.table.scope_stack.append(struct_scope)
      self.table.current_scope = struct_scope
    else:
      sym = self.table.lookup(node.name.name)
      if sym and sym.nested_scope:
        struct_scope = sym.nested_scope
        self.table.scope_stack.append(struct_scope)
        self.table.current_scope = struct_scope
      
    for field in node.fields:
      self.check(field)
      
    if struct_scope:
      self.table.exit_scope()

  def check_field(self, node: Field) -> None:
    if node.type:
      self.check(node.type)

  def check_impl_declaration(self, node: ImplDeclaration) -> None:
    struct_name = node.struct_name.name
    struct_scope = getattr(node, "scope", None)
    if struct_scope:
      self.table.scope_stack.append(struct_scope)
      self.table.current_scope = struct_scope
    else:
      struct_symbol = self.table.lookup(struct_name)
      if struct_symbol and struct_symbol.nested_scope:
        struct_scope = struct_symbol.nested_scope
        self.table.scope_stack.append(struct_scope)
        self.table.current_scope = struct_scope

    for ctor in node.constructors:
      self.check_constructor_declaration(ctor, struct_name)
    if node.destructor:
      self.check_destructor_declaration(node.destructor, struct_name)
    for method in node.methods:
      self.check_method_declaration(method, struct_name)

    if struct_scope:
      self.table.exit_scope()

  def check_constructor_declaration(self, node: ConstructorDeclaration, struct_name: str) -> None:
    ctor_scope = getattr(node, "scope", None)
    if ctor_scope:
      self.table.scope_stack.append(ctor_scope)
      self.table.current_scope = ctor_scope
    else:
      ctor_scope = Scope(parent=self.table.current_scope, kind="function")
      self.table.scope_stack.append(ctor_scope)
      self.table.current_scope = ctor_scope
      this_sym = Symbol(name="this", kind="variable", type=TypeNode(name=struct_name), declaration=node)
      self.table.define("this", this_sym)
      
    self.expected_return_types.append(TypeNode(name="void"))

    for param in node.params:
      self.check(param)
    self.check(node.body)

    self.expected_return_types.pop()
    self.table.exit_scope()

  def check_destructor_declaration(self, node: DestructorDeclaration, struct_name: str) -> None:
    dtor_scope = getattr(node, "scope", None)
    if dtor_scope:
      self.table.scope_stack.append(dtor_scope)
      self.table.current_scope = dtor_scope
    else:
      dtor_scope = Scope(parent=self.table.current_scope, kind="function")
      self.table.scope_stack.append(dtor_scope)
      self.table.current_scope = dtor_scope
      this_sym = Symbol(name="this", kind="variable", type=TypeNode(name=struct_name), declaration=node)
      self.table.define("this", this_sym)
      
    self.expected_return_types.append(TypeNode(name="void"))

    self.check(node.body)

    self.expected_return_types.pop()
    self.table.exit_scope()

  def check_method_declaration(self, node: MethodDeclaration, struct_name: str) -> None:
    method_scope = getattr(node, "scope", None)
    if method_scope:
      self.table.scope_stack.append(method_scope)
      self.table.current_scope = method_scope
    else:
      name = node.name.name
      method_sym = self.table.lookup_current_scope(name)
      if method_sym and method_sym.nested_scope:
        method_scope = method_sym.nested_scope
        self.table.scope_stack.append(method_scope)
        self.table.current_scope = method_scope

    expected_ret = node.return_type if node.return_type else TypeNode(name="void")
    self.expected_return_types.append(expected_ret)

    # In case 'this' is not in scope yet
    if method_scope and not method_scope.lookup_local("this"):
      this_sym = Symbol(name="this", kind="variable", type=TypeNode(name=struct_name), declaration=node)
      self.table.define("this", this_sym)

    for param in node.params:
      self.check(param)
    if node.return_type:
      self.check(node.return_type)
    self.check(node.body)

    self.expected_return_types.pop()
    if method_scope:
      self.table.exit_scope()

  def check_enum_declaration(self, node: EnumDeclaration) -> None:
    pass

  def check_block(self, node: Block) -> TypeNode:
    scope = getattr(node, "scope", None)
    if scope:
      self.table.scope_stack.append(scope)
      self.table.current_scope = scope
    else:
      self.table.enter_scope("block")
      
    last_t = None
    for stmt in node.statements:
      last_t = self.check(stmt)
      
    self.table.exit_scope()
    return last_t if last_t else TypeNode(name="void")

  def check_variable_declaration(self, node: VariableDeclaration) -> None:
    val_type = self.check(node.value)
    
    sym = None
    if node.name:
      sym = self.table.lookup_current_scope(node.name.name)

    if node.type:
      self.check(node.type)
      if val_type:
        if not is_assignable(node.type, val_type):
          self.report_error(
            f"Type mismatch: cannot initialize variable of type '{node.type.name}' with value of type '{val_type.name}'.",
            node
          )
      if sym:
        sym.type = node.type
    else:
      # Type inference
      if val_type:
        if sym:
          sym.type = val_type
        node.type = val_type

  def check_assignment_statement(self, node: AssignmentStatement) -> None:
    sym = None
    if isinstance(node.left, Identifier):
      sym = getattr(node.left, "symbol", None)
      if not sym:
        sym = self.table.lookup(node.left.name)

    right_type = self.check(node.right)
    
    # If the symbol has no type yet (e.g. implicitly declared loop variable), infer it!
    if sym and sym.type is None and right_type:
      sym.type = right_type
      
    left_type = self.check(node.left)
    
    if left_type and right_type:
      if not is_assignable(left_type, right_type):
        self.report_error(
          f"Type mismatch: cannot assign value of type '{right_type.name}' to variable of type '{left_type.name}'.",
          node
        )

  def check_return_statement(self, node: ReturnStatement) -> None:
    val_type = self.check(node.value) if node.value else TypeNode(name="void")
    
    if self.expected_return_types:
      expected = self.expected_return_types[-1]
      if not is_assignable(expected, val_type):
        self.report_error(
          f"Return type mismatch: expected '{expected.name}', got '{val_type.name}'.",
          node
        )
    else:
      self.report_error("Return statement outside function context.", node)

  def check_assert_statement(self, node: AssertStatement) -> None:
    cond_t = self.check(node.condition)
    if cond_t and cond_t.name != "bool":
      self.report_error(f"Assert condition must be boolean, got '{cond_t.name}'.", node)
    if node.message:
      self.check(node.message)

  def check_raise_statement(self, node: RaiseStatement) -> None:
    self.check(node.value)

  def check_expression_statement(self, node: ExpressionStatement) -> TypeNode:
    return self.check(node.expression)

  # --- Expressions check & type resolution ---

  def check_integer_literal(self, node: IntegerLiteral) -> TypeNode:
    return TypeNode(name="int")

  def check_float_literal(self, node: FloatLiteral) -> TypeNode:
    return TypeNode(name="float")

  def check_string_literal(self, node: StringLiteral) -> TypeNode:
    # Base string literals are mapped to const char*
    return TypeNode(name="const char*")

  def check_character_literal(self, node: CharacterLiteral) -> TypeNode:
    return TypeNode(name="char")

  def check_boolean_literal(self, node: BooleanLiteral) -> TypeNode:
    return TypeNode(name="bool")

  def check_array_literal(self, node: ArrayLiteral) -> TypeNode:
    if not node.elements:
      return TypeNode(name="void", array_size=0)
    # Infer base type from first element
    base_type = self.check(node.elements[0])
    if not base_type:
      base_type = TypeNode(name="void")
      
    for elem in node.elements[1:]:
      t = self.check(elem)
      if t and not types_equal(base_type, t):
        self.report_error(
          f"Array literal contains mixed types: '{base_type.name}' and '{t.name}'.",
          node
        )
    return TypeNode(name=base_type.name, array_size=len(node.elements))

  def check_identifier(self, node: Identifier) -> TypeNode:
    sym = getattr(node, "symbol", None)
    if not sym:
      sym = self.table.lookup(node.name)
      
    if not sym:
      self.report_error(f"Undeclared identifier '{node.name}'.", node)
      return TypeNode(name="void")
      
    if sym.type:
      return sym.type
    if sym.kind == "function":
      decl = sym.declaration
      if decl and hasattr(decl, "return_type") and decl.return_type:
        return decl.return_type
      return TypeNode(name="void")
      
    return TypeNode(name="void")

  def _get_full_dotted_path(self, node: Expression) -> str | None:
    if isinstance(node, Identifier):
      return node.name
    elif isinstance(node, MemberAccess):
      obj_path = self._get_full_dotted_path(node.object)
      if obj_path:
        return f"{obj_path}.{node.member.name}"
    return None

  def check_member_access(self, node: MemberAccess) -> TypeNode:
    sym = getattr(node, "symbol", None)
    if sym:
      if sym.type:
        return sym.type
      return TypeNode(name=sym.name)

    obj_type = self.check(node.object)
    if not obj_type:
      return TypeNode(name="void")

    # Smart pointers lookup resolution (unique_ptr / shared_ptr)
    if obj_type.name in ("std.unique_ptr", "std.shared_ptr") and len(obj_type.type_arguments) > 0:
      obj_type = obj_type.type_arguments[0]

    struct_sym = self.table.lookup(obj_type.name)
    if not struct_sym or struct_sym.kind != "type" or not struct_sym.nested_scope:
      # Skip error reporting if standard library expected wrapper is accessed
      if obj_type.name == "std.expected":
        # expected.value() or expected.error() resolved to success_t / error_t, handled by call check or directly
        return TypeNode(name="void")
      self.report_error(
        f"Member access '{node.member.name}' on non-struct type '{obj_type.name}'.",
        node
      )
      return TypeNode(name="void")

    member_sym = struct_sym.nested_scope.lookup_local(node.member.name)
    if not member_sym:
      self.report_error(
        f"Struct '{obj_type.name}' has no member '{node.member.name}'.",
        node
      )
      return TypeNode(name="void")

    if member_sym.type:
      return member_sym.type
    return TypeNode(name="void")

  def check_index_expression(self, node: IndexExpression) -> TypeNode:
    obj_t = self.check(node.object)
    idx_t = self.check(node.index)
    
    if idx_t and idx_t.name != "int":
      self.report_error(f"Index expression must be an integer, got '{idx_t.name}'.", node)
      
    if obj_t:
      if obj_t.array_size is not None:
        return TypeNode(name=obj_t.name)
      elif obj_t.name == "std.vector" and len(obj_t.type_arguments) > 0:
        return obj_t.type_arguments[0]
      else:
        self.report_error(f"Subscript operator [] applied to non-subscriptable type '{obj_t.name}'.", node)
        
    return TypeNode(name="void")

  def check_call_expression(self, node: CallExpression) -> TypeNode:
    # 1. Intercept lambda call of the form logger!("...")
    # which is parsed as CallExpression(CallExpression(logger, is_lambda_call=True, arguments=[]), arguments=[...])
    if (isinstance(node.function, CallExpression) and 
        getattr(node.function, "is_lambda_call", False) and 
        len(node.function.arguments) == 0):
      actual_func = node.function.function
      actual_args = node.arguments
      
      func_type = self.check(actual_func)
      arg_types = [self.check(arg) for arg in actual_args]
      
      if func_type and func_type.name == "std.function" and len(func_type.type_arguments) > 0:
        ret_type = func_type.type_arguments[0]
        param_types = func_type.type_arguments[1:]
        if len(arg_types) != len(param_types):
          self.report_error(
            f"Lambda expects {len(param_types)} arguments, got {len(arg_types)}.",
            node
          )
        else:
          for i, (arg_t, param_t) in enumerate(zip(arg_types, param_types)):
            if param_t and arg_t:
              if not is_assignable(param_t, arg_t):
                self.report_error(
                  f"Argument {i+1} of lambda call has type '{arg_t.name}' which is not assignable to parameter type '{param_t.name}'.",
                  node
                )
        return ret_type
      return func_type if func_type else TypeNode(name="void")

    # 2. Intercept expected method wrappers (expected.value! or expected.error!)
    is_excl_call = False
    func_to_check = None
    if getattr(node, "is_lambda_call", False) and isinstance(node.function, MemberAccess):
      is_excl_call = True
      func_to_check = node.function
    elif isinstance(node.function, CallExpression) and getattr(node.function, "is_lambda_call", False) and isinstance(node.function.function, MemberAccess):
      is_excl_call = True
      func_to_check = node.function.function

    if is_excl_call and func_to_check:
      inner_obj_t = self.check(func_to_check.object)
      method_name = func_to_check.member.name
      if inner_obj_t and inner_obj_t.name == "std.expected" and len(inner_obj_t.type_arguments) == 2:
        if method_name == "value":
          return inner_obj_t.type_arguments[0]
        elif method_name == "error":
          return inner_obj_t.type_arguments[1]

    func_type = self.check(node.function)
    
    # Handle template calls like std.make_unique<Particle>
    target = node.function
    type_args = []
    if isinstance(target, TemplateInstantiation):
      type_args = target.type_arguments
      target = target.element
      
    name = None
    if isinstance(target, Identifier):
      name = target.name
    elif isinstance(target, MemberAccess):
      name = self._get_full_dotted_path(target)

    if name:
      # make_unique, make_shared resolution mapping
      if name in ("std.make_unique", "make_unique") and len(type_args) > 0:
        for arg in node.arguments:
          self.check(arg)
        return TypeNode(name="std.unique_ptr", type_arguments=[type_args[0]])
      elif name in ("std.make_shared", "make_shared") and len(type_args) > 0:
        for arg in node.arguments:
          self.check(arg)
        return TypeNode(name="std.shared_ptr", type_arguments=[type_args[0]])
      elif name in ("std.unexpected", "unexpected") and len(node.arguments) > 0:
        arg_t = self.check(node.arguments[0])
        return TypeNode(name="std.unexpected", type_arguments=[arg_t])

    # Standard lookup and validation
    func_sym = None
    if isinstance(target, Identifier):
      func_sym = self.table.lookup(target.name)
    elif isinstance(target, MemberAccess):
      path = self._get_full_dotted_path(target)
      if path:
        func_sym = self.table.lookup(path)

    arg_types = [self.check(arg) for arg in node.arguments]
    
    if func_sym and func_sym.kind == "function" and func_sym.declaration:
      decl = func_sym.declaration
      params = getattr(decl, "params", [])
      if len(arg_types) != len(params):
        if func_sym.name not in ("printf", "print", "scanf"):
          self.report_error(
            f"Function '{func_sym.name}' expects {len(params)} arguments, got {len(arg_types)}.",
            node
          )
      else:
        for i, (arg_t, param) in enumerate(zip(arg_types, params)):
          if param.type and arg_t:
            if not is_assignable(param.type, arg_t):
              self.report_error(
                f"Argument {i+1} of function '{func_sym.name}' has type '{arg_t.name}' which is not assignable to parameter type '{param.type.name}'.",
                node
              )
      if decl and hasattr(decl, "return_type") and decl.return_type:
        return decl.return_type
        
    elif func_sym and func_sym.type:
      # If the function/variable is a lambda/std.function
      ft = func_sym.type
      if ft and ft.name == "std.function" and len(ft.type_arguments) > 0:
        ret_type = ft.type_arguments[0]
        param_types = ft.type_arguments[1:]
        if len(arg_types) != len(param_types):
          self.report_error(
            f"Lambda expects {len(param_types)} arguments, got {len(arg_types)}.",
            node
          )
        else:
          for i, (arg_t, param_t) in enumerate(zip(arg_types, param_types)):
            if param_t and arg_t:
              if not is_assignable(param_t, arg_t):
                self.report_error(
                  f"Argument {i+1} of lambda call has type '{arg_t.name}' which is not assignable to parameter type '{param_t.name}'.",
                  node
                )
        return ret_type
      return func_sym.type

    if func_type:
      if func_type.name == "std.function" and len(func_type.type_arguments) > 0:
        ret_type = func_type.type_arguments[0]
        param_types = func_type.type_arguments[1:]
        if len(arg_types) != len(param_types):
          self.report_error(
            f"Lambda expects {len(param_types)} arguments, got {len(arg_types)}.",
            node
          )
        else:
          for i, (arg_t, param_t) in enumerate(zip(arg_types, param_types)):
            if param_t and arg_t:
              if not is_assignable(param_t, arg_t):
                self.report_error(
                  f"Argument {i+1} of lambda call has type '{arg_t.name}' which is not assignable to parameter type '{param_t.name}'.",
                  node
                )
        return ret_type
      return func_type
    return TypeNode(name="void")

  def check_unary_operator(self, node: UnaryOperator) -> TypeNode:
    t = self.check(node.operand)
    if not t:
      return TypeNode(name="void")
      
    op = node.operator
    if op == "not":
      if t.name != "bool":
        self.report_error(f"Unary operator 'not' requires boolean operand, got '{t.name}'.", node)
      return TypeNode(name="bool")
    elif op in ("-", "+", "++", "--"):
      if not self.is_numeric(t):
        self.report_error(f"Unary operator '{op}' requires numeric operand, got '{t.name}'.", node)
      return t
    elif op == "ref":
      # Mutability modifier reference type wrapper
      return TypeNode(name=t.name, is_ref=True, type_arguments=t.type_arguments, array_size=t.array_size)
      
    return t

  def check_binary_operator(self, node: BinaryOperator) -> TypeNode:
    left_t = self.check(node.left)
    right_t = self.check(node.right)
    
    if not left_t or not right_t:
      return TypeNode(name="void")
      
    op = node.operator
    if op in ("and", "or"):
      if left_t.name != "bool" or right_t.name != "bool":
        self.report_error(
          f"Logical operator '{op}' requires boolean operands, got '{left_t.name}' and '{right_t.name}'.",
          node
        )
      return TypeNode(name="bool")
      
    elif op in ("<", "<=", ">", ">=", "==", "!="):
      if not (self.is_numeric(left_t) and self.is_numeric(right_t)) and not types_equal(left_t, right_t):
        if self.is_string_like(left_t) and self.is_string_like(right_t):
          return TypeNode(name="bool")
        self.report_error(
          f"Comparison operator '{op}' cannot be applied to types '{left_t.name}' and '{right_t.name}'.",
          node
        )
      return TypeNode(name="bool")
      
    elif op in ("+", "-", "*", "/"):
      if not self.is_numeric(left_t) or not self.is_numeric(right_t):
        self.report_error(
          f"Arithmetic operator '{op}' requires numeric operands, got '{left_t.name}' and '{right_t.name}'.",
          node
        )
        return TypeNode(name="void")
      return self.promote_numeric_types(left_t, right_t)
      
    elif op in ("=", "+=", "-=", "*=", "/=", "<<=", ">>="):
      if not is_assignable(left_t, right_t):
        self.report_error(
          f"Type mismatch: cannot assign value of type '{right_t.name}' to variable of type '{left_t.name}'.",
          node
        )
      return left_t
      
    elif op == "<<":
      # Stream insertion operator
      return left_t

    return TypeNode(name="void")

  def check_grouping_expression(self, node: GroupingExpression) -> TypeNode:
    return self.check(node.expression)

  def check_if_expression(self, node: IfExpression) -> TypeNode:
    if isinstance(node.condition, VariableDeclaration):
      self.check(node.condition)
    else:
      cond_t = self.check(node.condition)
      if cond_t and cond_t.name != "bool" and not is_assignable(TypeNode(name="bool"), cond_t):
        self.report_error(f"If condition must be boolean, got '{cond_t.name}'.", node)
      
    then_t = self.check(node.then_body)
    if not then_t:
      then_t = TypeNode(name="void")
      
    if node.else_body:
      else_t = self.check(node.else_body)
      if not else_t:
        else_t = TypeNode(name="void")
      if types_equal(then_t, else_t):
        return then_t
      elif self.is_numeric(then_t) and self.is_numeric(else_t):
        return self.promote_numeric_types(then_t, else_t)
      # Otherwise, return then_t but check if mismatch
      if not is_assignable(then_t, else_t) and not is_assignable(else_t, then_t):
        self.report_error(
          f"Conditional branches return incompatible types: '{then_t.name}' and '{else_t.name}'.",
          node
        )
      return then_t
      
    return TypeNode(name="void")

  def check_switch_expression(self, node: SwitchExpression) -> TypeNode:
    val_t = self.check(node.value)
    
    # Infer branch types
    branch_types = []
    for case in node.cases:
      pat_t = self.check(case.pattern)
      if val_t and pat_t and not types_equal(val_t, pat_t):
        self.report_error(
          f"Switch case pattern of type '{pat_t.name}' mismatch with target value type '{val_t.name}'.",
          case
        )
      body_t = self.check(case.body)
      if body_t:
        branch_types.append(body_t)
        
    if node.else_body:
      else_t = self.check(node.else_body)
      if else_t:
        branch_types.append(else_t)
        
    if branch_types:
      # Return promoted or base branch type
      base_t = branch_types[0]
      for t in branch_types[1:]:
        if not types_equal(base_t, t):
          if self.is_numeric(base_t) and self.is_numeric(t):
            base_t = self.promote_numeric_types(base_t, t)
          else:
            self.report_error(f"Switch branches return incompatible types: '{base_t.name}' and '{t.name}'.", node)
      return base_t
      
    return TypeNode(name="void")

  def check_for_comprehension(self, node: ForComprehension) -> TypeNode:
    iterable_type = self.check(node.iterable)
    elem_type = TypeNode(name="void")
    if iterable_type:
      if iterable_type.name == "std.vector" and len(iterable_type.type_arguments) > 0:
        elem_type = iterable_type.type_arguments[0]
      elif iterable_type.array_size is not None:
        elem_type = TypeNode(name=iterable_type.name)

    scope = getattr(node, "scope", None)
    if scope:
      self.table.scope_stack.append(scope)
      self.table.current_scope = scope
    else:
      self.table.enter_scope("block")
      name = node.variable.name
      sym = Symbol(name=name, kind="variable", declaration=node.variable)
      self.table.define(name, sym)
    
    sym = self.table.lookup_current_scope(node.variable.name)
    if sym:
      sym.type = elem_type
    
    body_t = self.check(node.body_expr)
    self.table.exit_scope()
    
    # List comprehension returns std.vector<T> where T is body_expr type
    return TypeNode(name="std.vector", type_arguments=[body_t if body_t else TypeNode(name="void")])

  def check_for_in_statement(self, node: ForInStatement) -> None:
    iterable_type = self.check(node.iterable)
    elem_type = TypeNode(name="void")
    if iterable_type:
      if iterable_type.name == "std.vector" and len(iterable_type.type_arguments) > 0:
        elem_type = iterable_type.type_arguments[0]
      elif iterable_type.array_size is not None:
        elem_type = TypeNode(name=iterable_type.name)

    scope = getattr(node, "scope", None)
    if scope:
      self.table.scope_stack.append(scope)
      self.table.current_scope = scope
    else:
      self.table.enter_scope("block")
      name = node.variable.name
      sym = Symbol(name=name, kind="variable", declaration=node.variable)
      self.table.define(name, sym)
      
    sym = self.table.lookup_current_scope(node.variable.name)
    if sym:
      sym.type = elem_type
    
    for stmt in node.body.statements:
      self.check(stmt)
      
    self.table.exit_scope()

  def check_for_c_statement(self, node: ForCStatement) -> None:
    scope = getattr(node, "scope", None)
    if scope:
      self.table.scope_stack.append(scope)
      self.table.current_scope = scope
    else:
      self.table.enter_scope("block")
      if node.init and isinstance(node.init, AssignmentStatement) and isinstance(node.init.left, Identifier):
        name = node.init.left.name
        sym = Symbol(name=name, kind="variable", declaration=node.init.left)
        self.table.define(name, sym)
      
    if node.init:
      self.check(node.init)
    if node.condition:
      self.check(node.condition)
    if node.increment:
      self.check(node.increment)
      
    for stmt in node.body.statements:
      self.check(stmt)
      
    self.table.exit_scope()

  def check_for_infinite_statement(self, node: ForInfiniteStatement) -> None:
    self.check(node.body)

  def check_while_statement(self, node: WhileStatement) -> None:
    cond_t = self.check(node.condition)
    if cond_t and cond_t.name != "bool":
      self.report_error(f"While condition must be boolean, got '{cond_t.name}'.", node)
    self.check(node.body)

  def check_type_node(self, node: TypeNode) -> TypeNode:
    return node

  def check_template_instantiation(self, node: TemplateInstantiation) -> TypeNode:
    # Resolve the inner element type
    elem_t = self.check(node.element)
    return TypeNode(name=elem_t.name if elem_t else "void", type_arguments=node.type_arguments)


def test_type_checker() -> None:
  print("Running TypeChecker unit tests...")

  # Test Case 1: Simple assignment validation (valid)
  # var x: float = 10 (int implicitly assignable to float)
  table = SymbolTable()
  table.define("float", Symbol(name="float", kind="type"))
  table.define("int", Symbol(name="int", kind="type"))
  
  var_decl = VariableDeclaration(
    name=Identifier(name="x"),
    type=TypeNode(name="float"),
    kind="var",
    value=IntegerLiteral(value="10")
  )
  
  # Setup dummy symbol mapping that Resolver would have created
  x_sym = Symbol(name="x", kind="variable", type=TypeNode(name="float"), declaration=var_decl)
  table.define("x", x_sym)
  
  errors = []
  checker = TypeChecker(table, errors, {})
  checker.check(var_decl)
  assert len(errors) == 0, f"Expected no type errors, got: {errors}"
  print("OK: Test 1 (Implicit promotion int -> float) passed.")

  # Test Case 2: Assignment validation (invalid mismatch)
  # var y: int = 3.14 (float cannot be assigned to int implicitly)
  var_decl2 = VariableDeclaration(
    name=Identifier(name="y"),
    type=TypeNode(name="int"),
    kind="var",
    value=FloatLiteral(value="3.14")
  )
  y_sym = Symbol(name="y", kind="variable", type=TypeNode(name="int"), declaration=var_decl2)
  table.define("y", y_sym)
  
  errors2 = []
  checker2 = TypeChecker(table, errors2, {})
  checker2.check(var_decl2)
  assert len(errors2) == 1, "Expected type mismatch error"
  assert "cannot initialize variable of type" in errors2[0].message
  print("OK: Test 2 (Type mismatch error float -> int) passed.")

  # Test Case 3: Return type check (invalid)
  # main returning float instead of int
  func_decl = FunctionDeclaration(
    name=Identifier(name="main"),
    params=[],
    return_type=TypeNode(name="int"),
    body=Block(
      statements=[
        ReturnStatement(value=FloatLiteral(value="3.14"))
      ]
    )
  )
  main_sym = Symbol(name="main", kind="function", nested_scope=Scope(parent=table.current_scope, kind="function"), declaration=func_decl)
  table.define("main", main_sym)
  
  errors3 = []
  checker3 = TypeChecker(table, errors3, {})
  checker3.check(func_decl)
  assert len(errors3) == 1, "Expected return mismatch error"
  assert "Return type mismatch" in errors3[0].message
  print("OK: Test 3 (Return mismatch error float -> int) passed.")

  # Test Case 4: If expression with variable declaration condition
  # if const x = 10
  #   pass
  var_decl_cond = VariableDeclaration(
    name=Identifier(name="x"),
    type=TypeNode(name="int"),
    kind="const",
    value=IntegerLiteral(value="10")
  )
  if_expr = IfExpression(
    condition=var_decl_cond,
    then_body=Block(statements=[PassStatement()]),
    else_body=None
  )
  x_sym = Symbol(name="x", kind="variable", type=TypeNode(name="int"), declaration=var_decl_cond)
  table.define("x", x_sym)
  
  errors4 = []
  checker4 = TypeChecker(table, errors4, {})
  checker4.check(if_expr)
  assert len(errors4) == 0, f"Expected no type errors in if-init, got: {errors4}"
  print("OK: Test 4 (If-init variable declaration condition) passed.")

  print("TypeChecker unit tests passed successfully!")

if __name__ == "__main__":
  test_type_checker()
