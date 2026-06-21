# System import path helper to resolve conflict with standard library 'ast' module
from typing import override
import sys
import os
import importlib.util

_current_dir = os.path.dirname(os.path.abspath(__file__))
_ast_path = os.path.abspath(os.path.join(_current_dir, "../ast/ast_nodes.py"))
if "ast.ast_nodes" not in sys.modules and os.path.exists(_ast_path):
  _spec = importlib.util.spec_from_file_location("ast.ast_nodes", _ast_path)
  _ast_nodes = importlib.util.module_from_spec(_spec)
  sys.modules["ast.ast_nodes"] = _ast_nodes
  _spec.loader.exec_module(_ast_nodes)

from lexer.token import Token, TokenType
from ast.ast_nodes import (
  Expression, Statement, CallExpression, LambdaExpression, Parameter, TypeNode, Block, ExpressionStatement,
  FunctionDeclaration, Identifier, EnumDeclaration, ModuleDeclaration, ImportDeclaration, UseCppDeclaration, UseCDeclaration,
  StructDeclaration, ImplDeclaration, ConstructorDeclaration, DestructorDeclaration, MethodDeclaration, Field, TemplateInstantiation, ForComprehension
)
from parser.statements import StatementParser


class DeclarationParser(StatementParser):
  """
  Subclass of StatementParser that implements parsing of declarations,
  functions, structures, implementations, enums, modules, imports, and integrates Phase 6 lambdas/calls.
  """
  def __init__(self, tokens: list[Token], file_path: str = ""):
    """
    Initializes the DeclarationParser, inheriting from StatementParser.
    """
    super().__init__(tokens, file_path)

  # ==============================================================================
  # Functions (Phase 6)
  # ==============================================================================

  @override
  def parse_assignment_or_declaration(self) -> Statement:
    """
    Overrides the assignment or variable declaration parser to detect function declarations.
    e.g., main = (): int -> body
    """
    if self.is_function_declaration_next():
      return self.parse_function_declaration()
    return super().parse_assignment_or_declaration()

  def is_function_declaration_next(self) -> bool:
    """
    Checks if the upcoming sequence is a function declaration:
    IDENTIFIER = ( ... ) -> ... or IDENTIFIER = ( ... ) : Type -> ...
    """
    if self.peek().type != TokenType.IDENTIFIER:
      return False
    if self.peek_ahead(1).type != TokenType.ASSIGN:
      return False
    if self.peek_ahead(2).type != TokenType.LPAREN:
      return False
      
    # Scan from the LPAREN to find matching RPAREN
    depth = 0
    i = 2  # self.peek_ahead(2) is LPAREN
    while True:
      tok = self.peek_ahead(i)
      if tok.type == TokenType.EOF:
        break
      if tok.type == TokenType.LPAREN:
        depth += 1
      elif tok.type == TokenType.RPAREN:
        depth -= 1
        if depth == 0:
          next_tok = self.peek_ahead(i + 1)
          # A function declaration has '->' or ':' after parameter list
          return next_tok.type in (TokenType.ARROW, TokenType.COLON)
      i += 1
    return False

  def parse_function_declaration(self) -> FunctionDeclaration:
    """
    Parses a function declaration: name = (params) [: ReturnType] -> body
    """
    start_pos = self.peek().start_pos
    name = self.parse_identifier()
    
    self.expect(TokenType.ASSIGN, "Expected '=' in function declaration")
    
    params = self.parse_parameter_list()
    
    return_type = None
    if self.match(TokenType.COLON):
      return_type = self.parse_type_node()
      
    self.expect(TokenType.ARROW, "Expected '->' before function body")
    
    body_start_pos = self.peek().start_pos
    if self.peek().type == TokenType.INDENT:
      body = self.parse_block()
    else:
      expr = self.parse_expression()
      expr_stmt = ExpressionStatement(
        expression=expr,
        start_pos=body_start_pos,
        end_pos=expr.end_pos,
        file=self.file
      )
      body = Block(
        statements=[expr_stmt],
        start_pos=body_start_pos,
        end_pos=expr.end_pos,
        file=self.file
      )
      
    return FunctionDeclaration(
      name=name,
      params=params,
      return_type=return_type,
      body=body,
      start_pos=start_pos,
      end_pos=body.end_pos,
      file=self.file
    )

  @override
  def parse_declaration(self) -> Statement:
    token_type = self.peek().type
    if token_type == TokenType.ENUM:
      return self.parse_enum_declaration()
    elif token_type == TokenType.MODULE:
      return self.parse_module_declaration()
    elif token_type in (TokenType.IMPORT, TokenType.FROM):
      return self.parse_import_declaration()
    elif token_type == TokenType.USE_CPP:
      return self.parse_use_cpp_declaration()
    elif token_type == TokenType.USE_C:
      return self.parse_use_c_declaration()
    elif token_type == TokenType.STRUCT:
      return self.parse_struct_declaration()
    elif token_type == TokenType.IMPL:
      return self.parse_impl_declaration()
    else:
      self.error(f"Unexpected token in declaration: '{self.peek().value}' (type: {token_type.name})")

  def parse_enum_declaration(self) -> EnumDeclaration:
    start_pos = self.peek().start_pos
    self.expect(TokenType.ENUM, "Expected 'enum'")
    name = self.parse_identifier()
    
    self.expect(TokenType.INDENT, "Expected INDENT to start enum block")
    variants = []
    while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
      if self.peek().type == TokenType.INDENT:
        self.consume()
        continue
      if self.peek().type in (TokenType.SEMICOLON, TokenType.COMMA):
        self.consume()
        continue
        
      variant = self.parse_identifier()
      variants.append(variant)
      
      if self.peek().type in (TokenType.SEMICOLON, TokenType.COMMA):
        self.consume()
        
    self.expect(TokenType.DEDENT, "Expected DEDENT to end enum block")
    
    end_pos = self.peek().start_pos
    
    # Optionally consume trailing semicolon
    self.match(TokenType.SEMICOLON)
    
    return EnumDeclaration(
      name=name,
      variants=variants,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_module_declaration(self) -> ModuleDeclaration:
    start_pos = self.peek().start_pos
    self.expect(TokenType.MODULE, "Expected 'module'")
    
    # Module name could be a dotted identifier (e.g. std.io)
    first_id = self.parse_identifier()
    name_str = first_id.name
    end_pos = first_id.end_pos
    
    while self.match(TokenType.DOT):
      next_id = self.expect(TokenType.IDENTIFIER, "Expected identifier after '.' in module path")
      name_str += "." + next_id.value
      end_pos = next_id.end_pos
      
    # Optionally consume trailing semicolon
    self.match(TokenType.SEMICOLON)
    
    return ModuleDeclaration(
      name=Identifier(name=name_str, start_pos=start_pos, end_pos=end_pos, file=self.file),
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_import_declaration(self) -> ImportDeclaration:
    start_pos = self.peek().start_pos
    
    if self.peek().type == TokenType.IMPORT:
      self.consume() # consume IMPORT
      # Syntax: import source [as alias]
      parts = [self.expect(TokenType.IDENTIFIER, "Expected module name in import").value]
      while self.match(TokenType.DOT):
        parts.append(self.expect(TokenType.IDENTIFIER, "Expected identifier after '.' in import path").value)
      source = ".".join(parts)
      
      alias = None
      if self.match(TokenType.AS):
        alias = self.parse_identifier()
        
      end_pos = alias.end_pos if alias else self.peek().start_pos
      
      # Optionally consume trailing semicolon
      self.match(TokenType.SEMICOLON)
      
      return ImportDeclaration(
        source=source,
        names=[],
        alias=alias,
        start_pos=start_pos,
        end_pos=end_pos,
        file=self.file
      )
      
    elif self.peek().type == TokenType.FROM:
      self.consume() # consume FROM
      # Syntax: from source import names
      parts = [self.expect(TokenType.IDENTIFIER, "Expected module name in import").value]
      while self.match(TokenType.DOT):
        parts.append(self.expect(TokenType.IDENTIFIER, "Expected identifier after '.' in import path").value)
      source = ".".join(parts)
      
      self.expect(TokenType.IMPORT, "Expected 'import' after module source in from-import")
      
      names = []
      if self.peek().type == TokenType.ASTERISK:
        asterisk_tok = self.consume()
        names.append(Identifier(
          name="*",
          start_pos=asterisk_tok.start_pos,
          end_pos=asterisk_tok.end_pos,
          file=self.file
        ))
      else:
        names.append(self.parse_identifier())
        while self.match(TokenType.COMMA):
          if self.peek().type == TokenType.IDENTIFIER:
            names.append(self.parse_identifier())
          else:
            break
            
      end_pos = names[-1].end_pos if names else self.peek().start_pos
      
      # Optionally consume trailing semicolon
      self.match(TokenType.SEMICOLON)
      
      return ImportDeclaration(
        source=source,
        names=names,
        alias=None,
        start_pos=start_pos,
        end_pos=end_pos,
        file=self.file
      )
    else:
      self.error("Expected 'import' or 'from' declaration")

  def parse_single_header(self) -> str:
    if self.match(TokenType.LT):
      # Reconstruct until '>'
      header_content = "<"
      while self.peek().type != TokenType.GT and self.peek().type != TokenType.EOF:
        header_content += self.consume().value
      self.expect(TokenType.GT, "Expected '>' to close header name")
      header_content += ">"
      return header_content
    elif self.peek().type == TokenType.STRING:
      tok = self.consume()
      return tok.value
    else:
      self.error("Expected header path in angle brackets (e.g. <iostream>) or double quotes")

  def parse_use_cpp_declaration(self) -> UseCppDeclaration:
    start_pos = self.peek().start_pos
    self.expect(TokenType.USE_CPP, "Expected 'use_cpp'")
    
    headers = [self.parse_single_header()]
    while self.match(TokenType.COMMA):
      headers.append(self.parse_single_header())
      
    end_pos = self.peek().start_pos
    
    # Optionally consume trailing semicolon
    self.match(TokenType.SEMICOLON)
    
    return UseCppDeclaration(
      headers=headers,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_use_c_declaration(self) -> UseCDeclaration:
    start_pos = self.peek().start_pos
    self.expect(TokenType.USE_C, "Expected 'use_c'")
    
    headers = [self.parse_single_header()]
    while self.match(TokenType.COMMA):
      headers.append(self.parse_single_header())
      
    end_pos = self.peek().start_pos
    
    # Optionally consume trailing semicolon
    self.match(TokenType.SEMICOLON)
    
    return UseCDeclaration(
      headers=headers,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_inline_block(self) -> Block:
    start_pos = self.peek().start_pos
    expr = self.parse_expression()
    expr_stmt = ExpressionStatement(
      expression=expr,
      start_pos=start_pos,
      end_pos=expr.end_pos,
      file=self.file
    )
    return Block(
      statements=[expr_stmt],
      start_pos=start_pos,
      end_pos=expr.end_pos,
      file=self.file
    )

  def parse_struct_declaration(self) -> StructDeclaration:
    start_pos = self.peek().start_pos
    self.expect(TokenType.STRUCT, "Expected 'struct'")
    name = self.parse_identifier()
    
    self.expect(TokenType.INDENT, "Expected INDENT to start struct body")
    fields = []
    while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
      if self.peek().type == TokenType.INDENT:
        self.consume()
        continue
      if self.peek().type in (TokenType.SEMICOLON, TokenType.COMMA):
        self.consume()
        continue
        
      field_start = self.peek().start_pos
      field_name = self.parse_identifier()
      self.expect(TokenType.COLON, "Expected ':' after field name in struct")
      field_type = self.parse_type_node()
      
      # Optional trailing semicolon/comma
      self.match(TokenType.SEMICOLON)
      self.match(TokenType.COMMA)
      
      fields.append(Field(
        name=field_name,
        type=field_type,
        start_pos=field_start,
        end_pos=field_type.end_pos,
        file=self.file
      ))
      
    self.expect(TokenType.DEDENT, "Expected DEDENT to end struct body")
    
    return StructDeclaration(
      name=name,
      fields=fields,
      start_pos=start_pos,
      end_pos=self.peek().start_pos,
      file=self.file
    )

  def parse_impl_declaration(self) -> ImplDeclaration:
    start_pos = self.peek().start_pos
    self.expect(TokenType.IMPL, "Expected 'impl'")
    struct_name = self.parse_identifier()
    
    self.expect(TokenType.INDENT, "Expected INDENT to start impl body")
    
    constructors = []
    destructor = None
    methods = []
    
    while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
      token = self.peek()
      if token.type == TokenType.INDENT:
        self.consume()
        continue
      if token.type == TokenType.SEMICOLON:
        self.consume()
        continue
        
      if token.type == TokenType.CONSTRUCTOR:
        c_start = token.start_pos
        self.consume() # consume constructor
        params = self.parse_parameter_list()
        self.expect(TokenType.ARROW, "Expected '->' after constructor signature")
        body = self.parse_block() if self.peek().type == TokenType.INDENT else self.parse_inline_block()
        constructors.append(ConstructorDeclaration(
          params=params,
          body=body,
          start_pos=c_start,
          end_pos=body.end_pos,
          file=self.file
        ))
        
      elif token.type == TokenType.DESTRUCTOR:
        d_start = token.start_pos
        self.consume() # consume destructor
        self.expect(TokenType.LPAREN, "Expected '(' in destructor signature")
        self.expect(TokenType.RPAREN, "Expected ')' in destructor signature")
        self.expect(TokenType.ARROW, "Expected '->' after destructor signature")
        body = self.parse_block() if self.peek().type == TokenType.INDENT else self.parse_inline_block()
        destructor = DestructorDeclaration(
          body=body,
          start_pos=d_start,
          end_pos=body.end_pos,
          file=self.file
        )
        
      elif token.type == TokenType.IDENTIFIER:
        m_start = token.start_pos
        method_name = self.parse_identifier()
        self.expect(TokenType.ASSIGN, "Expected '=' in method declaration")
        params = self.parse_parameter_list()
        return_type = None
        if self.match(TokenType.COLON):
          return_type = self.parse_type_node()
        self.expect(TokenType.ARROW, "Expected '->' after method signature")
        body = self.parse_block() if self.peek().type == TokenType.INDENT else self.parse_inline_block()
        
        methods.append(MethodDeclaration(
          name=method_name,
          params=params,
          return_type=return_type,
          body=body,
          start_pos=m_start,
          end_pos=body.end_pos,
          file=self.file
        ))
      else:
        self.error(f"Unexpected token inside impl: '{token.value}' (type: {token.type.name})")
        
    self.expect(TokenType.DEDENT, "Expected DEDENT to end impl body")
    
    return ImplDeclaration(
      struct_name=struct_name,
      constructors=constructors,
      destructor=destructor,
      methods=methods,
      start_pos=start_pos,
      end_pos=self.peek().start_pos,
      file=self.file
    )


def test_parser() -> None:
  """
  Runs Phase 3 and Phase 6 tests using DeclarationParser.
  """
  print("Running parser unit tests on DeclarationParser...")
  from ast.ast_nodes import GroupingExpression, IntegerLiteral, BinaryOperator, UnaryOperator, MemberAccess, IndexExpression, FunctionDeclaration, ReturnStatement
  
  # Test case 1: Grouped expression (42)
  tokens1 = [
    Token(TokenType.LPAREN, "(", 1, 1, 0, 0, 1),
    Token(TokenType.INT, "42", 1, 2, 0, 1, 3),
    Token(TokenType.RPAREN, ")", 1, 4, 0, 3, 4),
    Token(TokenType.EOF, "", 1, 5, 0, 4, 4)
  ]
  parser1 = DeclarationParser(tokens1, "test1.pengu")
  ast1 = parser1.parse_program()
  assert len(ast1.statements) == 1
  stmt1 = ast1.statements[0]
  assert isinstance(stmt1, ExpressionStatement)
  group1 = stmt1.expression
  assert isinstance(group1, GroupingExpression)
  assert group1.expression.value == "42"
  print("OK: Test 1 (Grouped expression) passed.")

  # Test case 2: Function call and Lambda suffix: add(x, 1) and logger!
  tokens5 = [
    Token(TokenType.IDENTIFIER, "add", 1, 1, 0, 0, 3),
    Token(TokenType.LPAREN, "(", 1, 4, 0, 3, 4),
    Token(TokenType.IDENTIFIER, "x", 1, 5, 0, 4, 5),
    Token(TokenType.COMMA, ",", 1, 6, 0, 5, 6),
    Token(TokenType.INT, "1", 1, 8, 0, 7, 8),
    Token(TokenType.RPAREN, ")", 1, 9, 0, 8, 9),
    Token(TokenType.EXCLAMATION, "!", 1, 10, 0, 9, 10),
    Token(TokenType.EOF, "", 1, 11, 0, 10, 10)
  ]
  parser5 = DeclarationParser(tokens5, "test5.pengu")
  ast5 = parser5.parse_program()
  expr5 = ast5.statements[0].expression
  assert isinstance(expr5, CallExpression)
  assert expr5.is_lambda_call is True
  assert isinstance(expr5.function, CallExpression)
  assert expr5.function.is_lambda_call is False
  print("OK: Test 5 (Function call and lambda suffix exclamation) passed.")

  # Test case 3: Lambda expression: (msg: std.string_view): void => print(msg)
  tokens6 = [
    Token(TokenType.LPAREN, "(", 1, 1, 0, 0, 1),
    Token(TokenType.IDENTIFIER, "msg", 1, 2, 0, 1, 4),
    Token(TokenType.COLON, ":", 1, 5, 0, 4, 5),
    Token(TokenType.IDENTIFIER, "std", 1, 7, 0, 6, 9),
    Token(TokenType.DOT, ".", 1, 10, 0, 9, 10),
    Token(TokenType.IDENTIFIER, "string_view", 1, 11, 0, 10, 21),
    Token(TokenType.RPAREN, ")", 1, 22, 0, 21, 22),
    Token(TokenType.COLON, ":", 1, 23, 0, 22, 23),
    Token(TokenType.TYPE_VOID, "void", 1, 25, 0, 24, 28),
    Token(TokenType.DOUBLE_ARROW, "=>", 1, 30, 0, 29, 31),
    Token(TokenType.IDENTIFIER, "print", 1, 33, 0, 32, 37),
    Token(TokenType.LPAREN, "(", 1, 38, 0, 37, 38),
    Token(TokenType.IDENTIFIER, "msg", 1, 39, 0, 38, 41),
    Token(TokenType.RPAREN, ")", 1, 42, 0, 41, 42),
    Token(TokenType.EOF, "", 1, 43, 0, 42, 42)
  ]
  parser6 = DeclarationParser(tokens6, "test6.pengu")
  ast6 = parser6.parse_program()
  expr6 = ast6.statements[0].expression
  assert isinstance(expr6, LambdaExpression)
  assert len(expr6.params) == 1
  assert expr6.params[0].name.name == "msg"
  assert isinstance(expr6.params[0].type, TypeNode) and expr6.params[0].type.name == "std.string_view"
  assert isinstance(expr6.return_type, TypeNode) and expr6.return_type.name == "void"
  assert isinstance(expr6.body, Block)
  print("OK: Test 6 (Lambda expression with type annotations and inline body) passed.")

  # Test case 4: Function declaration: main = (): int -> 0
  tokens7 = [
    Token(TokenType.IDENTIFIER, "main", 1, 1, 0, 0, 4),
    Token(TokenType.ASSIGN, "=", 1, 6, 0, 5, 6),
    Token(TokenType.LPAREN, "(", 1, 8, 0, 7, 8),
    Token(TokenType.RPAREN, ")", 1, 9, 0, 8, 9),
    Token(TokenType.COLON, ":", 1, 10, 0, 9, 10),
    Token(TokenType.TYPE_INT, "int", 1, 12, 0, 11, 14),
    Token(TokenType.ARROW, "->", 1, 16, 0, 15, 17),
    Token(TokenType.INT, "0", 1, 19, 0, 18, 19),
    Token(TokenType.EOF, "", 1, 20, 0, 19, 19)
  ]
  parser7 = DeclarationParser(tokens7, "test7.pengu")
  ast7 = parser7.parse_program()
  assert len(ast7.statements) == 1
  stmt7 = ast7.statements[0]
  assert isinstance(stmt7, FunctionDeclaration)
  assert stmt7.name.name == "main"
  assert len(stmt7.params) == 0
  assert isinstance(stmt7.return_type, TypeNode) and stmt7.return_type.name == "int"
  assert isinstance(stmt7.body, Block)
  assert len(stmt7.body.statements) == 1
  assert isinstance(stmt7.body.statements[0], ExpressionStatement)
  assert isinstance(stmt7.body.statements[0].expression, IntegerLiteral) and stmt7.body.statements[0].expression.value == "0"
  print("OK: Test 7 (Function declaration main = (): int -> 0) passed.")

  # Test case 8: Enum declaration
  # enum Colors
  #   Red
  #   Green
  #   Blue
  tokens8 = [
    Token(TokenType.ENUM, "enum", 1, 1, 0, 0, 4),
    Token(TokenType.IDENTIFIER, "Colors", 1, 6, 0, 5, 11),
    Token(TokenType.INDENT, "  ", 2, 1, 2, 12, 14),
    Token(TokenType.IDENTIFIER, "Red", 2, 3, 2, 14, 17),
    Token(TokenType.IDENTIFIER, "Green", 3, 3, 2, 18, 23),
    Token(TokenType.IDENTIFIER, "Blue", 4, 3, 2, 24, 28),
    Token(TokenType.DEDENT, "", 5, 1, 0, 28, 28),
    Token(TokenType.EOF, "", 5, 1, 0, 28, 28)
  ]
  parser8 = DeclarationParser(tokens8, "test8.pengu")
  ast8 = parser8.parse_program()
  assert len(ast8.statements) == 1
  stmt8 = ast8.statements[0]
  assert isinstance(stmt8, EnumDeclaration)
  assert stmt8.name.name == "Colors"
  assert len(stmt8.variants) == 3
  assert stmt8.variants[0].name == "Red"
  assert stmt8.variants[1].name == "Green"
  assert stmt8.variants[2].name == "Blue"
  print("OK: Test 8 (Enum declaration) passed.")

  # Test case 9: Module declaration: module std.io;
  tokens9 = [
    Token(TokenType.MODULE, "module", 1, 1, 0, 0, 6),
    Token(TokenType.IDENTIFIER, "std", 1, 8, 0, 7, 10),
    Token(TokenType.DOT, ".", 1, 11, 0, 10, 11),
    Token(TokenType.IDENTIFIER, "io", 1, 12, 0, 11, 13),
    Token(TokenType.SEMICOLON, ";", 1, 14, 0, 13, 14),
    Token(TokenType.EOF, "", 1, 15, 0, 14, 14)
  ]
  parser9 = DeclarationParser(tokens9, "test9.pengu")
  ast9 = parser9.parse_program()
  assert len(ast9.statements) == 1
  stmt9 = ast9.statements[0]
  assert isinstance(stmt9, ModuleDeclaration)
  assert stmt9.name.name == "std.io"
  print("OK: Test 9 (Module declaration std.io) passed.")

  # Test case 10: Import with alias: import math as m
  tokens10 = [
    Token(TokenType.IMPORT, "import", 1, 1, 0, 0, 6),
    Token(TokenType.IDENTIFIER, "math", 1, 8, 0, 7, 11),
    Token(TokenType.AS, "as", 1, 13, 0, 12, 14),
    Token(TokenType.IDENTIFIER, "m", 1, 16, 0, 15, 16),
    Token(TokenType.EOF, "", 1, 17, 0, 17, 17)
  ]
  parser10 = DeclarationParser(tokens10, "test10.pengu")
  ast10 = parser10.parse_program()
  assert len(ast10.statements) == 1
  stmt10 = ast10.statements[0]
  assert isinstance(stmt10, ImportDeclaration)
  assert stmt10.source == "math"
  assert stmt10.alias is not None and stmt10.alias.name == "m"
  assert len(stmt10.names) == 0
  print("OK: Test 10 (Import with alias) passed.")

  # Test case 11: From import list: from std.io import print, input
  tokens11 = [
    Token(TokenType.FROM, "from", 1, 1, 0, 0, 4),
    Token(TokenType.IDENTIFIER, "std", 1, 6, 0, 5, 8),
    Token(TokenType.DOT, ".", 1, 9, 0, 8, 9),
    Token(TokenType.IDENTIFIER, "io", 1, 10, 0, 9, 11),
    Token(TokenType.IMPORT, "import", 1, 13, 0, 12, 18),
    Token(TokenType.IDENTIFIER, "print", 1, 20, 0, 19, 24),
    Token(TokenType.COMMA, ",", 1, 25, 0, 24, 25),
    Token(TokenType.IDENTIFIER, "input", 1, 27, 0, 26, 31),
    Token(TokenType.EOF, "", 1, 32, 0, 31, 31)
  ]
  parser11 = DeclarationParser(tokens11, "test11.pengu")
  ast11 = parser11.parse_program()
  assert len(ast11.statements) == 1
  stmt11 = ast11.statements[0]
  assert isinstance(stmt11, ImportDeclaration)
  assert stmt11.source == "std.io"
  assert stmt11.alias is None
  assert len(stmt11.names) == 2
  assert stmt11.names[0].name == "print"
  assert stmt11.names[1].name == "input"
  print("OK: Test 11 (From import list) passed.")

  # Test case 12: From import asterisk: from sys import *
  tokens12 = [
    Token(TokenType.FROM, "from", 1, 1, 0, 0, 4),
    Token(TokenType.IDENTIFIER, "sys", 1, 6, 0, 5, 8),
    Token(TokenType.IMPORT, "import", 1, 10, 0, 9, 15),
    Token(TokenType.ASTERISK, "*", 1, 17, 0, 16, 17),
    Token(TokenType.EOF, "", 1, 18, 0, 17, 17)
  ]
  parser12 = DeclarationParser(tokens12, "test12.pengu")
  ast12 = parser12.parse_program()
  assert len(ast12.statements) == 1
  stmt12 = ast12.statements[0]
  assert isinstance(stmt12, ImportDeclaration)
  assert stmt12.source == "sys"
  assert len(stmt12.names) == 1
  assert stmt12.names[0].name == "*"
  print("OK: Test 12 (From import asterisk) passed.")

  # Test case 13: use_cpp <iostream>
  tokens13 = [
    Token(TokenType.USE_CPP, "use_cpp", 1, 1, 0, 0, 7),
    Token(TokenType.LT, "<", 1, 9, 0, 8, 9),
    Token(TokenType.IDENTIFIER, "iostream", 1, 10, 0, 9, 17),
    Token(TokenType.GT, ">", 1, 18, 0, 17, 18),
    Token(TokenType.EOF, "", 1, 19, 0, 18, 18)
  ]
  parser13 = DeclarationParser(tokens13, "test13.pengu")
  ast13 = parser13.parse_program()
  assert len(ast13.statements) == 1
  stmt13 = ast13.statements[0]
  assert isinstance(stmt13, UseCppDeclaration)
  assert len(stmt13.headers) == 1
  assert stmt13.headers[0] == "<iostream>"
  print("OK: Test 13 (use_cpp <iostream>) passed.")

  # Test case 14: use_c multiple string headers: use_c "my_header.h", "another.h"
  tokens14 = [
    Token(TokenType.USE_C, "use_c", 1, 1, 0, 0, 5),
    Token(TokenType.STRING, '"my_header.h"', 1, 7, 0, 6, 19),
    Token(TokenType.COMMA, ",", 1, 20, 0, 19, 20),
    Token(TokenType.STRING, '"another.h"', 1, 22, 0, 21, 32),
    Token(TokenType.EOF, "", 1, 33, 0, 32, 32)
  ]
  parser14 = DeclarationParser(tokens14, "test14.pengu")
  ast14 = parser14.parse_program()
  assert len(ast14.statements) == 1
  stmt14 = ast14.statements[0]
  assert isinstance(stmt14, UseCDeclaration)
  assert len(stmt14.headers) == 2
  assert stmt14.headers[0] == '"my_header.h"'
  assert stmt14.headers[1] == '"another.h"'
  print("OK: Test 14 (use_c multiple string headers) passed.")

  print("All unit tests passed successfully!")


if __name__ == "__main__":
  test_parser()
