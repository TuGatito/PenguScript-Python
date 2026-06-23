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

from ast.ast_nodes import *
from codegen.cpp_helpers import to_cpp_type, to_cpp_literal

class CppVisitor:
  """
  AST Visitor that traverses PenguScript AST and yields C++20 code strings.
  For Phase 0, all visitor methods return skeleton/empty strings.
  """
  def __init__(self) -> None:
    self.includes: set[str] = set()
    self.struct_impls: dict[str, list[ImplDeclaration]] = {}
    self.module_name: str | None = None
    self.current_struct_name: str | None = None

  def visit(self, node: ASTNode | None) -> str:
    if node is None:
      return ""
      
    # Dispatch based on class name
    class_name = type(node).__name__
    method_name = f"visit_{self._to_snake_case(class_name)}"
    method = getattr(self, method_name, None)
    if method:
      return method(node)
    else:
      return f"/* Warning: No visitor implemented for {class_name} */"

  def _to_snake_case(self, name: str) -> str:
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

  PRECEDENCE = {
      "=": 0.5, "+=": 0.5, "-=": 0.5, "*=": 0.5, "/=": 0.5,
      "or": 1, "||": 1,
      "and": 2, "&&": 2,
      "==": 3, "!=": 3,
      "<": 4, "<=": 4, ">": 4, ">=": 4,
      "<<": 4.5, ">>": 4.5,
      "+": 5, "-": 5,
      "*": 6, "/": 6, "%": 6,
  }

  def _get_precedence(self, op: str) -> float:
    return self.PRECEDENCE.get(op, 99.0)

  def _visit_with_precedence(self, node: Expression, parent_op: str, is_right: bool) -> str:
    code = self.visit(node)
    if isinstance(node, BinaryOperator):
      parent_prec = self._get_precedence(parent_op)
      node_prec = self._get_precedence(node.operator)
      if node_prec < parent_prec:
        return f"({code})"
      elif node_prec == parent_prec and is_right:
        return f"({code})"
    return code

  def _is_pointer_type(self, node: ASTNode) -> bool:
    if isinstance(node, CallExpression):
      # Detect std::make_unique or std::make_shared calls
      func = node.function
      if isinstance(func, TemplateInstantiation):
        func = func.element
      func_name = ""
      if isinstance(func, Identifier):
        func_name = func.name
      elif isinstance(func, MemberAccess):
        parts = []
        curr = func
        while isinstance(curr, MemberAccess):
          parts.append(curr.member.name)
          curr = curr.object
        if isinstance(curr, Identifier):
          parts.append(curr.name)
        func_name = ".".join(reversed(parts))
      if "make_unique" in func_name or "make_shared" in func_name:
        return True

    if isinstance(node, Identifier) and node.name == "this":
      return True

    t = None
    if hasattr(node, "type") and isinstance(getattr(node, "type"), TypeNode):
      t = node.type
    else:
      sym = getattr(node, "symbol", None)
      if sym and hasattr(sym, "type") and sym.type:
        t = sym.type

    if t and isinstance(t, TypeNode):
      name = t.name
      if name in ("std.unique_ptr", "std.shared_ptr", "std::unique_ptr", "std::shared_ptr") or name.endswith("*"):
        return True
    return False

  # Literals
  def visit_integer_literal(self, node: IntegerLiteral) -> str:
    return to_cpp_literal(node)
    
  def visit_float_literal(self, node: FloatLiteral) -> str:
    return to_cpp_literal(node)
    
  def visit_string_literal(self, node: StringLiteral) -> str:
    return to_cpp_literal(node)
    
  def visit_character_literal(self, node: CharacterLiteral) -> str:
    return to_cpp_literal(node)
    
  def visit_boolean_literal(self, node: BooleanLiteral) -> str:
    return to_cpp_literal(node)
    
  def visit_array_literal(self, node: ArrayLiteral) -> str:
    elems = [self.visit(elem) for elem in node.elements]
    return f"{{{', '.join(elems)}}}"

  # Identifiers and Types
  def visit_identifier(self, node: Identifier) -> str:
    return node.name
    
  def visit_type_node(self, node: TypeNode) -> str:
    return to_cpp_type(node)

  # Expressions
  def visit_unary_operator(self, node: UnaryOperator) -> str:
    op = node.operator
    if op == "not":
      operand = self.visit(node.operand)
      return f"!({operand})"
    
    operand = self.visit(node.operand)
    if op == "ref":
      if self._is_pointer_type(node.operand):
        return f"*({operand})"
      else:
        return operand
    if node.is_prefix:
      return f"{op}{operand}"
    else:
      return f"{operand}{op}"
    
  def visit_binary_operator(self, node: BinaryOperator) -> str:
    op = node.operator
    if op == "and":
      op = "&&"
    elif op == "or":
      op = "||"
      
    left = self._visit_with_precedence(node.left, node.operator, is_right=False)
    right = self._visit_with_precedence(node.right, node.operator, is_right=True)
    return f"{left} {op} {right}"
    
  def visit_member_access(self, node: MemberAccess) -> str:
    obj = self.visit(node.object)
    member = node.member.name
    
    def is_scope_resolution(obj_node) -> bool:
      if isinstance(obj_node, Identifier):
        if obj_node.name in ("std", "physics"):
          return True
        sym = getattr(obj_node, "symbol", None)
        if sym:
          if getattr(sym, "kind", None) in ("namespace", "module"):
            return True
          if isinstance(getattr(sym, "declaration", None), EnumDeclaration):
            return True
      elif isinstance(obj_node, MemberAccess):
        sym = getattr(obj_node.member, "symbol", None)
        if sym:
          if getattr(sym, "kind", None) in ("namespace", "module"):
            return True
          if isinstance(getattr(sym, "declaration", None), EnumDeclaration):
            return True
        if is_scope_resolution(obj_node.object) and obj_node.member.name in ("expected", "unexpected", "cout", "vector", "array", "cin", "endl", "make_unique", "make_shared"):
          return True
      return False

    if is_scope_resolution(node.object):
      op = "::"
    else:
      is_ptr = self._is_pointer_type(node.object)
      op = "->" if is_ptr else "."
    return f"{obj}{op}{member}"
    
  def visit_index_expression(self, node: IndexExpression) -> str:
    obj = self.visit(node.object)
    idx = self.visit(node.index)
    return f"{obj}[{idx}]"
    
  def visit_call_expression(self, node: CallExpression) -> str:
    func_node = node.function
    if (isinstance(func_node, CallExpression) and 
        func_node.is_lambda_call and 
        not func_node.arguments and 
        not isinstance(func_node.function, MemberAccess)):
      func_node = func_node.function
      
    func = self.visit(func_node)
    
    if node.is_lambda_call:
      if isinstance(node.function, MemberAccess):
        return f"{func}()"
      elif not node.arguments:
        return f"{func}()"
        
    args = [self.visit(arg) for arg in node.arguments]
    return f"{func}({', '.join(args)})"
    
  def visit_grouping_expression(self, node: GroupingExpression) -> str:
    return f"({self.visit(node.expression)})"
    
  def visit_if_expression(self, node: IfExpression) -> str:
    cond = self.visit(node.condition).strip()
    if cond.endswith(";"):
      cond = cond[:-1]
      
    def get_single_expression(body):
      if body is None:
        return None
      if isinstance(body, Expression):
        return body
      if isinstance(body, ExpressionStatement):
        return body.expression
      if isinstance(body, Block) and len(body.statements) == 1:
        stmt = body.statements[0]
        if isinstance(stmt, ExpressionStatement):
          return stmt.expression
        elif isinstance(stmt, Expression):
          return stmt
      return None

    then_expr = get_single_expression(node.then_body)
    else_expr = get_single_expression(node.else_body) if node.else_body else None

    if (node.else_body is not None 
        and then_expr is not None 
        and else_expr is not None 
        and not isinstance(node.condition, Statement)):
      then_val = self.visit(then_expr).strip()
      else_val = self.visit(else_expr).strip()
      if then_val.endswith(";"): then_val = then_val[:-1]
      if else_val.endswith(";"): else_val = else_val[:-1]
      return f"(({cond}) ? ({then_val}) : ({else_val}))"
    else:
      then_val = self.visit(node.then_body)
      else_str = ""
      if node.else_body:
        else_val = self.visit(node.else_body)
        if isinstance(node.else_body, IfExpression):
          else_str = f" else {else_val}"
        else:
          else_val_str = else_val
          if not else_val_str.strip().startswith("{"):
            else_val_str = f"{{\n{else_val_str}\n}}"
          else_str = f" else {else_val_str}"
          
      then_str = then_val
      if not then_str.strip().startswith("{"):
        then_str = f"{{\n{then_str}\n}}"
        
      return f"if ({cond}) {then_str}{else_str}"
    
  def visit_switch_expression(self, node: SwitchExpression) -> str:
    val = self.visit(node.value)
    
    def get_single_expression(body):
      if body is None:
        return None
      if isinstance(body, Expression):
        return body
      if isinstance(body, ExpressionStatement):
        return body.expression
      if isinstance(body, Block) and len(body.statements) == 1:
        stmt = body.statements[0]
        if isinstance(stmt, ExpressionStatement):
          return stmt.expression
        elif isinstance(stmt, Expression):
          return stmt
      return None

    def format_switch_body(body_node) -> str:
      expr = get_single_expression(body_node)
      if expr is not None:
        code = self.visit(expr).strip()
        if code.endswith(";"):
          code = code[:-1]
        return f"return {code};"
      
      code = self.visit(body_node).strip()
      if not code.startswith("{"):
        if not code.startswith("return"):
          if code.endswith(";"):
            code = code[:-1]
          return f"return {code};"
        return code
      else:
        if isinstance(body_node, Block) and len(body_node.statements) == 1:
          stmt = body_node.statements[0]
          if isinstance(stmt, ExpressionStatement):
            expr_code = self.visit(stmt.expression).strip()
            if expr_code.endswith(";"):
              expr_code = expr_code[:-1]
            return f"return {expr_code};"
          elif isinstance(stmt, ReturnStatement):
            return self.visit(stmt).strip()
        return code

    lines = []
    lines.append("[&]() {")
    lines.append(f"  switch ({val}) {{")
    for case in node.cases:
      pattern = self.visit(case.pattern)
      body = format_switch_body(case.body)
      lines.append(f"    case {pattern}:")
      lines.append(f"      {body}")
      
    if node.else_body:
      else_body = format_switch_body(node.else_body)
      lines.append("    default:")
      lines.append(f"      {else_body}")
      
    lines.append("  }")
    lines.append("}()")
    return "\n".join(lines)
    
  def visit_case(self, node: Case) -> str:
    pattern = self.visit(node.pattern)
    body = self.visit(node.body)
    return f"case {pattern}:\n  {body}\n  break;"
    
  def visit_lambda_expression(self, node: LambdaExpression) -> str:
    params = ", ".join(self.visit_parameter(p) for p in node.params)
    ret_type_str = ""
    if node.return_type:
      ret_type_str = f" -> {to_cpp_type(node.return_type)}"
      
    body = self.visit(node.body)
    if isinstance(node.body, Block):
      return f"[&]({params}){ret_type_str} {body}"
    else:
      return f"[&]({params}){ret_type_str} {{ return {body}; }}"
    
  def visit_template_instantiation(self, node: TemplateInstantiation) -> str:
    element = self.visit(node.element)
    args = ", ".join(to_cpp_type(arg) for arg in node.type_arguments)
    return f"{element}<{args}>"

  def _indent_text(self, text: str, indent: str = "  ") -> str:
    if not text:
      return ""
    lines = text.splitlines()
    return "\n".join(indent + line if line.strip() else "" for line in lines)

  def _is_variable_mutated(self, body: ASTNode, var_name: str) -> bool:
    if body is None:
      return False
      
    if isinstance(body, AssignmentStatement):
      if isinstance(body.left, Identifier) and body.left.name == var_name:
        return True
      curr = body.left
      while isinstance(curr, (MemberAccess, IndexExpression)):
        curr = curr.object
      if isinstance(curr, Identifier) and curr.name == var_name:
        return True
        
    elif isinstance(body, UnaryOperator):
      if body.operator in ("++", "--") and isinstance(body.operand, Identifier) and body.operand.name == var_name:
        return True
        
    elif isinstance(body, Block):
      return any(self._is_variable_mutated(stmt, var_name) for stmt in body.statements)
      
    import dataclasses
    if dataclasses.is_dataclass(body):
      for f in dataclasses.fields(body):
        val = getattr(body, f.name)
        if isinstance(val, ASTNode):
          if self._is_variable_mutated(val, var_name):
            return True
        elif isinstance(val, list):
          for item in val:
            if isinstance(item, ASTNode):
              if self._is_variable_mutated(item, var_name):
                return True
    return False

  # Statements
  def visit_expression_statement(self, node: ExpressionStatement) -> str:
    expr = self.visit(node.expression)
    if not expr:
      return ""
    if expr.endswith(";") or expr.endswith("}"):
      return expr
    return f"{expr};"
    
  def visit_block(self, node: Block) -> str:
    stmt_strs = []
    for stmt in node.statements:
      code = self.visit(stmt)
      if code:
        stmt_strs.append(code)
    body_code = "\n".join(stmt_strs)
    indented = self._indent_text(body_code)
    return f"{{\n{indented}\n}}"
    
  def visit_variable_declaration(self, node: VariableDeclaration) -> str:
    is_const = (node.kind == "const")
    is_ref = (node.kind == "ref")
    
    use_auto_override = False
    if node.type and node.value:
      type_name = node.type.name
      if type_name in ("std.expected", "std::expected"):
        use_auto_override = True
        
    if node.type and not use_auto_override:
      type_str = to_cpp_type(node.type)
      if is_ref and not type_str.endswith("&"):
        type_str = f"{type_str}&"
    else:
      if is_ref:
        type_str = "auto&"
      else:
        type_str = "auto"
        
    const_str = "const " if (is_const and not type_str.startswith("const ")) else ""
    
    array_suffix = ""
    if node.type and node.type.array_size is not None:
      array_suffix = f"[{node.type.array_size}]"
    name = f"{node.name.name}{array_suffix}"
    
    if node.value:
      val_str = self.visit(node.value)
      return f"{const_str}{type_str} {name} = {val_str};"
    else:
      return f"{const_str}{type_str} {name};"
    
  def visit_assignment_statement(self, node: AssignmentStatement) -> str:
    left = self.visit(node.left)
    right = self.visit(node.right)
    return f"{left} = {right};"
    
  def visit_return_statement(self, node: ReturnStatement) -> str:
    if node.value:
      val = self.visit(node.value)
      return f"return {val};"
    return "return;"
    
  def visit_break_statement(self, node: BreakStatement) -> str:
    return "break;"
    
  def visit_continue_statement(self, node: ContinueStatement) -> str:
    return "continue;"
    
  def visit_pass_statement(self, node: PassStatement) -> str:
    return ";"
    
  def visit_assert_statement(self, node: AssertStatement) -> str:
    cond = self.visit(node.condition)
    if node.message:
      msg = self.visit(node.message)
      return f"assert(({cond}) && {msg});"
    return f"assert({cond});"
    
  def visit_raise_statement(self, node: RaiseStatement) -> str:
    val = self.visit(node.value)
    return f"throw {val};"
    
  def visit_for_comprehension(self, node: ForComprehension) -> str:
    var_name = node.variable.name
    iterable = self.visit(node.iterable)
    body_expr = self.visit(node.body_expr)
    
    lines = []
    lines.append("[&]() {")
    lines.append(f"  using _elem_type = std::decay_t<decltype(*std::begin({iterable}))>;")
    lines.append(f"  _elem_type {var_name}{{}};")
    lines.append(f"  std::vector<std::decay_t<decltype({body_expr})>> _res;")
    lines.append(f"  for (const auto& _val : {iterable}) {{")
    lines.append(f"    {var_name} = _val;")
    lines.append(f"    _res.push_back({body_expr});")
    lines.append("  }")
    lines.append("  return _res;")
    lines.append("}()")
    return "\n".join(lines)
    
  def visit_for_in_statement(self, node: ForInStatement) -> str:
    var_name = node.variable.name
    iterable = self.visit(node.iterable)
    
    is_mutated = self._is_variable_mutated(node.body, var_name)
    ref_type = "auto&" if is_mutated else "const auto&"
    
    body = self.visit(node.body)
    if not body.strip().startswith("{"):
      body = f"{{\n{self._indent_text(body)}\n}}"
      
    return f"for ({ref_type} {var_name} : {iterable}) {body}"
    
  def visit_for_c_statement(self, node: ForCStatement) -> str:
    init_str = ""
    if node.init:
      if isinstance(node.init, AssignmentStatement) and isinstance(node.init.left, Identifier):
        var_name = node.init.left.name
        val_str = self.visit(node.init.right).strip()
        init_str = f"auto {var_name} = {val_str}"
      else:
        init_str = self.visit(node.init).strip()
        if init_str.endswith(";"):
          init_str = init_str[:-1]
          
    cond_str = self.visit(node.condition).strip() if node.condition else ""
    if cond_str.endswith(";"):
      cond_str = cond_str[:-1]
      
    inc_str = self.visit(node.increment).strip() if node.increment else ""
    if inc_str.endswith(";"):
      inc_str = inc_str[:-1]
      
    body = self.visit(node.body)
    if not body.strip().startswith("{"):
      body = f"{{\n{self._indent_text(body)}\n}}"
      
    return f"for ({init_str}; {cond_str}; {inc_str}) {body}"
    
  def visit_for_infinite_statement(self, node: ForInfiniteStatement) -> str:
    body = self.visit(node.body)
    if not body.strip().startswith("{"):
      body = f"{{\n{self._indent_text(body)}\n}}"
    return f"for (;;) {body}"
    
  def visit_while_statement(self, node: WhileStatement) -> str:
    cond = self.visit(node.condition).strip()
    if cond.endswith(";"):
      cond = cond[:-1]
      
    body = self.visit(node.body)
    if not body.strip().startswith("{"):
      body = f"{{\n{self._indent_text(body)}\n}}"
    return f"while ({cond}) {body}"

  # Declarations
  def visit_program(self, node: Program) -> str:
    self.includes = set()
    self.struct_impls = {}
    self.module_name = None
    self.current_struct_name = None
    
    self.auto_collect_includes(node)
    
    # 1. Pre-scan for ImplDeclarations and ModuleDeclaration
    for stmt in node.statements:
      if isinstance(stmt, ImplDeclaration):
        name = stmt.struct_name.name
        if name not in self.struct_impls:
          self.struct_impls[name] = []
        self.struct_impls[name].append(stmt)
      elif isinstance(stmt, ModuleDeclaration):
        self.module_name = stmt.name.name
        
    # 2. Visit statements to generate the body declarations
    decl_strs = []
    main_decl = ""
    for stmt in node.statements:
      if isinstance(stmt, (UseCppDeclaration, UseCDeclaration, ImplDeclaration, ModuleDeclaration)):
        self.visit(stmt) # Populate self.includes
        continue
      code = self.visit(stmt)
      if code:
        if isinstance(stmt, FunctionDeclaration) and stmt.name.name == "main":
          main_decl = code
        else:
          decl_strs.append(code)
          
    body_code = "\n\n".join(decl_strs)
    
    # 3. Wrap body in module namespace if present
    if self.module_name:
      body_code = f"namespace {self.module_name} {{\n\n{body_code}\n\n}} // namespace {self.module_name}"
      
    # 4. Append global main if present
    if main_decl:
      body_code = f"{body_code}\n\n{main_decl}"
      
    # 5. Generate header includes at the top
    include_strs = [f"#include {header}" for header in sorted(self.includes)]
    if include_strs:
      header_section = "\n".join(include_strs)
      return f"{header_section}\n\n{body_code}"
    return body_code
    
  def visit_module_declaration(self, node: ModuleDeclaration) -> str:
    self.module_name = node.name.name
    return ""
    
  def visit_import_declaration(self, node: ImportDeclaration) -> str:
    return ""
    
  def visit_use_cpp_declaration(self, node: UseCppDeclaration) -> str:
    for h in node.headers:
      self.includes.add(h)
    return ""
    
  def visit_use_c_declaration(self, node: UseCDeclaration) -> str:
    for h in node.headers:
      self.includes.add(h)
    return ""
    
  def visit_parameter(self, node: Parameter) -> str:
    type_str = to_cpp_type(node.type) if node.type else "auto"
    name_str = node.name.name
    if node.default:
      default_str = self.visit(node.default)
      return f"{type_str} {name_str} = {default_str}"
    return f"{type_str} {name_str}"
    
  def visit_struct_declaration(self, node: StructDeclaration) -> str:
    struct_name = node.name.name
    self.current_struct_name = struct_name
    
    # Generate fields
    field_strs = [self.visit(f) for f in node.fields]
    
    # Generate impl methods inline
    impl_strs = []
    impl_nodes = self.struct_impls.get(struct_name, [])
    for impl in impl_nodes:
      for ctor in impl.constructors:
        impl_strs.append(self.visit_constructor_declaration(ctor))
      if impl.destructor:
        impl_strs.append(self.visit_destructor_declaration(impl.destructor))
      for method in impl.methods:
        impl_strs.append(self.visit_method_declaration(method))
        
    body_lines = field_strs + impl_strs
    body_code = "\n".join(body_lines)
    indented = self._indent_text(body_code)
    
    self.current_struct_name = None
    return f"struct {struct_name} {{\n{indented}\n}};"
    
  def visit_field(self, node: Field) -> str:
    type_str = to_cpp_type(node.type)
    name_str = node.name.name
    return f"{type_str} {name_str};"
    
  def visit_impl_declaration(self, node: ImplDeclaration) -> str:
    return ""
    
  def visit_constructor_declaration(self, node: ConstructorDeclaration) -> str:
    struct_name = self.current_struct_name or "Constructor"
    params = ", ".join(self.visit_parameter(p) for p in node.params)
    body = self.visit(node.body)
    return f"{struct_name}({params}) {body}"
    
  def visit_destructor_declaration(self, node: DestructorDeclaration) -> str:
    struct_name = self.current_struct_name or "Destructor"
    body = self.visit(node.body)
    return f"~{struct_name}() {body}"
    
  def visit_method_declaration(self, node: MethodDeclaration) -> str:
    name = node.name.name
    params = ", ".join(self.visit_parameter(p) for p in node.params)
    ret_type = to_cpp_type(node.return_type) if node.return_type else "void"
    body = self.visit(node.body)
    return f"{ret_type} {name}({params}) {body}"
    
  def visit_enum_declaration(self, node: EnumDeclaration) -> str:
    name = node.name.name
    variants = [v.name for v in node.variants]
    body = ",\n".join(variants)
    indented = self._indent_text(body)
    return f"enum class {name} {{\n{indented}\n}};"
    
  def visit_function_declaration(self, node: FunctionDeclaration) -> str:
    name = node.name.name
    params = ", ".join(self.visit_parameter(p) for p in node.params)
    if name == "main":
      ret_type = to_cpp_type(node.return_type) if node.return_type else "int"
    else:
      ret_type = to_cpp_type(node.return_type) if node.return_type else "void"
    body = self.visit(node.body)
    return f"{ret_type} {name}({params}) {body}"

  def auto_collect_includes(self, node: ASTNode | None) -> None:
    if node is None:
      return
      
    if isinstance(node, AssertStatement):
      self.includes.add("<cassert>")
    elif isinstance(node, ForComprehension):
      self.includes.add("<vector>")
    elif isinstance(node, LambdaExpression):
      self.includes.add("<functional>")
    elif isinstance(node, CallExpression):
      func_node = node.function
      if isinstance(func_node, Identifier) and func_node.name in ("printf", "scanf"):
        self.includes.add("<cstdio>")
    elif isinstance(node, TypeNode):
      name = node.name
      if name in ("std.vector", "std::vector"):
        self.includes.add("<vector>")
      elif name in ("std.string", "std::string", "string"):
        self.includes.add("<string>")
      elif name in ("std.unique_ptr", "std::unique_ptr", "std.shared_ptr", "std::shared_ptr", "std.make_unique", "std::make_unique", "std.make_shared", "std::make_shared"):
        self.includes.add("<memory>")
      elif name in ("std.expected", "std::expected", "std.unexpected", "std::unexpected"):
        self.includes.add("<expected>")
      elif name in ("std.string_view", "std::string_view"):
        self.includes.add("<string_view>")
    elif isinstance(node, Identifier):
      name = node.name
      if "make_unique" in name or "make_shared" in name:
        self.includes.add("<memory>")
      elif "cout" in name or "cin" in name or "endl" in name:
        self.includes.add("<iostream>")
        
    # Recurse
    import dataclasses
    if dataclasses.is_dataclass(node):
      for f in dataclasses.fields(node):
        val = getattr(node, f.name)
        if isinstance(val, ASTNode):
          self.auto_collect_includes(val)
        elif isinstance(val, list):
          for item in val:
            if isinstance(item, ASTNode):
              self.auto_collect_includes(item)
