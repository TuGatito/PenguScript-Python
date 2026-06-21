# System import path helper to resolve conflict with standard library 'ast' module
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

from typing import override
from lexer.token import Token, TokenType
from ast.ast_nodes import (
  Expression, Statement, Block, ExpressionStatement,
  VariableDeclaration, AssignmentStatement, ReturnStatement,
  BreakStatement, ContinueStatement, PassStatement, Identifier, TypeNode,
  MemberAccess, IndexExpression, BinaryOperator,
  IfExpression, SwitchExpression, Case, ForInStatement, ForCStatement,
  ForInfiniteStatement, WhileStatement, UnaryOperator, IntegerLiteral,
  AssertStatement, RaiseStatement, StringLiteral
)
from parser.expressions import ExpressionParser


class StatementParser(ExpressionParser):
  """
  Subclass of ExpressionParser that implements parsing of statements.
  Concrete implementation rules for Phase 4 (Basic Statements) and Phase 5 (Control Flow).
  """
  
  @override
  def parse_block(self) -> Block:
    """
    Parses a block of statements delimited by INDENT and DEDENT.
    Uses base class implementation.
    """
    return super().parse_block()

  @override
  def parse_statement(self) -> Statement | None:
    stmt = self.parse_statement_inner()
    if stmt is not None and self.peek().type in (TokenType.IF, TokenType.UNLESS):
      if self.pos > 0 and self.peek().line == self.tokens[self.pos - 1].line:
        is_unless = self.peek().type == TokenType.UNLESS
        self.consume()  # Consume IF or UNLESS
      
        cond_pos = self.peek().start_pos
        condition = self.parse_expression()
        if is_unless:
          condition = UnaryOperator(
            operator="not",
            operand=condition,
            is_prefix=True,
            start_pos=cond_pos,
            end_pos=condition.end_pos,
            file=self.file
          )
          
        then_body = Block(
          statements=[stmt],
          start_pos=stmt.start_pos,
          end_pos=stmt.end_pos,
          file=self.file
        )
        
        if_expr = IfExpression(
          condition=condition,
          then_body=then_body,
          else_body=None,
          start_pos=stmt.start_pos,
          end_pos=condition.end_pos,
          file=self.file
        )
        
        stmt = ExpressionStatement(
          expression=if_expr,
          start_pos=stmt.start_pos,
          end_pos=condition.end_pos,
          file=self.file
        )
    return stmt

  def parse_statement_inner(self) -> Statement | None:
    """
    Parses a single statement. Dispatches based on the current token type.
    """
    token_type = self.peek().type
    
    if token_type == TokenType.INDENT:
      return self.parse_block()
      
    elif token_type in (TokenType.VAR, TokenType.CONST, TokenType.REF):
      return self.parse_variable_declaration()
      
    elif token_type == TokenType.RETURN:
      return self.parse_return_statement()
      
    elif token_type == TokenType.BREAK:
      return self.parse_break_statement()
      
    elif token_type == TokenType.CONTINUE:
      return self.parse_continue_statement()
      
    elif token_type == TokenType.PASS:
      return self.parse_pass_statement()
      
    elif token_type == TokenType.ASSERT:
      return self.parse_assert_statement()
      
    elif token_type == TokenType.RAISE:
      return self.parse_raise_statement()
      
    elif token_type in (TokenType.IF, TokenType.UNLESS):
      return self.parse_if_statement()
      
    elif token_type == TokenType.SWITCH:
      return self.parse_switch_statement()
      
    elif token_type == TokenType.FOR:
      return self.parse_for_statement()
      
    elif token_type == TokenType.WHILE:
      return self.parse_while_statement()
      
    elif token_type in (TokenType.STRUCT, TokenType.IMPL, TokenType.ENUM, 
                         TokenType.MODULE, TokenType.IMPORT, TokenType.FROM, TokenType.USE_CPP, TokenType.USE_C):
      # Delegated to declarations.py (DeclarationParser subclass)
      return self.parse_declaration()
      
    elif token_type == TokenType.IDENTIFIER:
      # Check if the next token is an assignment '=' or a colon ':' (which could be a type annotation or ':=')
      next_tok = self.peek_ahead(1)
      if next_tok.type in (TokenType.ASSIGN, TokenType.COLON):
        return self.parse_assignment_or_declaration()
      else:
        return self.parse_expression_statement()
        
    elif token_type == TokenType.SEMICOLON:
      self.consume()  # Consume the semicolon
      return None
      
    elif token_type in (TokenType.DEDENT, TokenType.EOF):
      # End of block/file
      return None
      
    else:
      # Fallback to expression statement
      return self.parse_expression_statement()

  def parse_expression_statement(self) -> Statement:
    """
    Parses an expression statement.
    If the expression is an assignment binary operator (=), converts it to an AssignmentStatement.
    """
    start_pos = self.peek().start_pos
    expr = self.parse_expression()
    end_pos = self.peek().end_pos
    
    if isinstance(expr, BinaryOperator) and expr.operator == "=":
      if not isinstance(expr.left, (Identifier, MemberAccess, IndexExpression)):
        self.error("Invalid left-hand side of assignment; expected identifier, member access, or index expression")
      return AssignmentStatement(
        left=expr.left,
        right=expr.right,
        start_pos=expr.start_pos,
        end_pos=expr.end_pos,
        file=self.file
      )
      
    return ExpressionStatement(
      expression=expr,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_variable_declaration(self) -> VariableDeclaration:
    """
    Parses an explicit variable declaration: (var | const | ref) name [: Type] = expression
    """
    start_pos = self.peek().start_pos
    kind_tok = self.consume()
    kind = kind_tok.value  # "var", "const", or "ref"
    
    name = self.parse_identifier()
    
    type_node = None
    if self.match(TokenType.COLON):
      type_node = self.parse_type_node()
      
    self.expect(TokenType.ASSIGN, "Expected '=' after variable name/type in declaration")
    value = self.parse_expression()
    
    return VariableDeclaration(
      name=name,
      type=type_node,
      value=value,
      kind=kind,
      start_pos=start_pos,
      end_pos=value.end_pos,
      file=self.file
    )

  def parse_assignment_or_declaration(self) -> Statement:
    """
    Parses implicit short-variable declarations or simple assignments starting with an identifier.
    e.g.:
      x = 5       -> AssignmentStatement
      x := 5      -> VariableDeclaration
      x: int = 5  -> VariableDeclaration
    """
    start_pos = self.peek().start_pos
    name = self.parse_identifier()
    
    # 1. Short-variable declaration with ':='
    if self.peek().type == TokenType.COLON and self.peek_ahead(1).type == TokenType.ASSIGN:
      self.consume()  # Consume COLON
      self.consume()  # Consume ASSIGN
      value = self.parse_expression()
      return VariableDeclaration(
        name=name,
        type=None,
        value=value,
        kind="var",
        start_pos=start_pos,
        end_pos=value.end_pos,
        file=self.file
      )
      
    # 2. Variable declaration with explicit type annotation: 'name: Type = value'
    elif self.match(TokenType.COLON):
      type_node = self.parse_type_node()
      self.expect(TokenType.ASSIGN, "Expected '=' after type annotation in variable declaration")
      value = self.parse_expression()
      return VariableDeclaration(
        name=name,
        type=type_node,
        value=value,
        kind="var",
        start_pos=start_pos,
        end_pos=value.end_pos,
        file=self.file
      )
      
    # 3. Simple assignment: 'name = value'
    else:
      # Rewind to let parse_assignment_statement handle left-hand-side expression parsing fully
      self.pos -= 1
      self.current_token = self.tokens[self.pos]
      return self.parse_assignment_statement()

  def parse_assignment_statement(self) -> AssignmentStatement:
    """
    Parses a variable assignment. Validates that the left-hand side is a writable target.
    """
    left = self.parse_expression(min_precedence=2)  # Precedence higher than assignment (1)
    if not isinstance(left, (Identifier, MemberAccess, IndexExpression)):
      self.error("Invalid left-hand side of assignment; expected identifier, member access, or index expression")
      
    self.expect(TokenType.ASSIGN, "Expected '=' in assignment statement")
    right = self.parse_expression()
    
    return AssignmentStatement(
      left=left,
      right=right,
      start_pos=left.start_pos,
      end_pos=right.end_pos,
      file=self.file
    )

  def parse_return_statement(self) -> ReturnStatement:
    """
    Parses a return statement with an optional value expression.
    """
    start_pos = self.peek().start_pos
    self.expect(TokenType.RETURN, "Expected 'return'")
    
    value = None
    if self.peek().type not in (TokenType.DEDENT, TokenType.EOF, TokenType.SEMICOLON):
      value = self.parse_expression()
      
    return ReturnStatement(
      value=value,
      start_pos=start_pos,
      end_pos=value.end_pos if value else start_pos + 6,
      file=self.file
    )

  def parse_break_statement(self) -> BreakStatement:
    """
    Parses a break statement.
    """
    tok = self.expect(TokenType.BREAK, "Expected 'break'")
    return BreakStatement(
      start_pos=tok.start_pos,
      end_pos=tok.end_pos,
      file=self.file
    )

  def parse_continue_statement(self) -> ContinueStatement:
    """
    Parses a continue statement.
    """
    tok = self.expect(TokenType.CONTINUE, "Expected 'continue'")
    return ContinueStatement(
      start_pos=tok.start_pos,
      end_pos=tok.end_pos,
      file=self.file
    )

  def parse_pass_statement(self) -> PassStatement:
    """
    Parses a pass statement.
    """
    tok = self.expect(TokenType.PASS, "Expected 'pass'")
    return PassStatement(
      start_pos=tok.start_pos,
      end_pos=tok.end_pos,
      file=self.file
    )

  def parse_assert_statement(self) -> AssertStatement:
    """
    Parses an assert statement: assert condition [, message]
    """
    start_pos = self.peek().start_pos
    self.expect(TokenType.ASSERT, "Expected 'assert'")
    condition = self.parse_expression()
    
    message = None
    if self.match(TokenType.COMMA):
      message = self.parse_expression()
      
    end_pos = message.end_pos if message else condition.end_pos
    return AssertStatement(
      condition=condition,
      message=message,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_raise_statement(self) -> RaiseStatement:
    """
    Parses a raise statement: raise expression
    """
    start_pos = self.peek().start_pos
    self.expect(TokenType.RAISE, "Expected 'raise'")
    value = self.parse_expression()
    
    return RaiseStatement(
      value=value,
      start_pos=start_pos,
      end_pos=value.end_pos,
      file=self.file
    )

  # ==============================================================================
  # Placeholders/Stubs for Subclasses / Future Phases
  # ==============================================================================



  def parse_if_statement(self) -> IfExpression:
    """
    Parses an if or unless statement/expression.
    If it is an unless, the condition is negated.
    """
    start_pos = self.peek().start_pos
    is_unless = self.peek().type == TokenType.UNLESS
    self.consume()  # Consume IF or UNLESS
    
    if self.peek().type in (TokenType.VAR, TokenType.CONST, TokenType.REF):
      condition = self.parse_variable_declaration()
    else:
      condition = self.parse_expression()
    if is_unless:
      # Negate the condition by wrapping it in a UnaryOperator not
      condition = UnaryOperator(
        operator="not",
        operand=condition,
        is_prefix=True,
        start_pos=condition.start_pos,
        end_pos=condition.end_pos,
        file=self.file
      )
      
    # Check if there is THEN (single-line syntax)
    if self.match(TokenType.THEN):
      then_expr = self.parse_expression()
      then_stmt = ExpressionStatement(
        expression=then_expr,
        start_pos=then_expr.start_pos,
        end_pos=then_expr.end_pos,
        file=self.file
      )
      then_body = Block(
        statements=[then_stmt],
        start_pos=then_expr.start_pos,
        end_pos=then_expr.end_pos,
        file=self.file
      )
      
      else_body = None
      if self.match(TokenType.ELSE):
        else_expr = self.parse_expression()
        else_stmt = ExpressionStatement(
          expression=else_expr,
          start_pos=else_expr.start_pos,
          end_pos=else_expr.end_pos,
          file=self.file
        )
        else_body = Block(
          statements=[else_stmt],
          start_pos=else_expr.start_pos,
          end_pos=else_expr.end_pos,
          file=self.file
        )
        
      return IfExpression(
        condition=condition,
        then_body=then_body,
        else_body=else_body,
        start_pos=start_pos,
        end_pos=else_body.end_pos if else_body else then_body.end_pos,
        file=self.file
      )
      
    # Block-based if statement (INDENT ... DEDENT)
    else:
      then_body = self.parse_block()
      
      else_body = None
      if self.match(TokenType.ELSE):
        if self.peek().type in (TokenType.IF, TokenType.UNLESS):
          # Chained else if / else unless
          nested_if = self.parse_if_statement()
          stmt = ExpressionStatement(
            expression=nested_if,
            start_pos=nested_if.start_pos,
            end_pos=nested_if.end_pos,
            file=self.file
          )
          else_body = Block(
            statements=[stmt],
            start_pos=nested_if.start_pos,
            end_pos=nested_if.end_pos,
            file=self.file
          )
        else:
          else_body = self.parse_block()
          
      return IfExpression(
        condition=condition,
        then_body=then_body,
        else_body=else_body,
        start_pos=start_pos,
        end_pos=else_body.end_pos if else_body else then_body.end_pos,
        file=self.file
      )

  def parse_switch_statement(self) -> SwitchExpression:
    """
    Parses a switch statement/expression.
    """
    start_pos = self.peek().start_pos
    self.expect(TokenType.SWITCH, "Expected 'switch'")
    
    value = self.parse_expression()
    self.expect(TokenType.INDENT, "Expected INDENT to start switch block")
    
    cases: list[Case] = []
    else_body = None
    
    while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
      token_type = self.peek().type
      
      if token_type == TokenType.WHEN:
        when_tok = self.consume()
        pattern = self.parse_expression()
        body = self.parse_block()
        cases.append(Case(
          pattern=pattern,
          body=body,
          start_pos=when_tok.start_pos,
          end_pos=body.end_pos,
          file=self.file
        ))
        
      elif token_type == TokenType.ELSE:
        self.consume()
        else_body = self.parse_block()
        
      else:
        self.error(f"Expected 'when' or 'else' in switch block, found '{self.peek().value}' (type: {self.peek().type.name})")
        
    self.expect(TokenType.DEDENT, "Expected DEDENT to end switch block")
    
    end_pos = self.peek().start_pos
    return SwitchExpression(
      value=value,
      cases=cases,
      else_body=else_body,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_for_statement(self) -> Statement:
    """
    Parses a loop starting with 'for'.
    Determines the variant by inspecting tokens:
      - If 'for identifier in iterable': ForInStatement
      - If 'for init; condition; increment': ForCStatement
      - If 'for { body }': ForInfiniteStatement
    """
    start_pos = self.peek().start_pos
    self.expect(TokenType.FOR, "Expected 'for'")
    
    # Check if there is a semicolon in the line to determine if it is a C-style loop
    has_semicolon = False
    i = 0
    while True:
      tok = self.peek_ahead(i)
      if tok.type in (TokenType.INDENT, TokenType.DEDENT, TokenType.EOF):
        break
      if tok.type == TokenType.SEMICOLON:
        has_semicolon = True
        break
      i += 1
      
    # 1. C-style for loop: 'for init; condition; increment'
    if has_semicolon:
      # Parse init: could be empty, a var/const/ref declaration, assignment, or expression
      if self.peek().type == TokenType.SEMICOLON:
        init = None
      else:
        token_type = self.peek().type
        if token_type in (TokenType.VAR, TokenType.CONST, TokenType.REF):
          init = self.parse_variable_declaration()
        elif token_type == TokenType.IDENTIFIER and self.peek_ahead(1).type in (TokenType.ASSIGN, TokenType.COLON):
          init = self.parse_assignment_or_declaration()
        else:
          init = self.parse_expression()
          
      self.expect(TokenType.SEMICOLON, "Expected ';' after init in C-style for loop")
      
      # Parse condition: could be empty
      if self.peek().type == TokenType.SEMICOLON:
        condition = None
      else:
        condition = self.parse_expression()
        
      self.expect(TokenType.SEMICOLON, "Expected ';' after condition in C-style for loop")
      
      # Parse increment: could be empty
      if self.peek().type == TokenType.INDENT:
        increment = None
      else:
        increment = self.parse_expression()
        
      body = self.parse_block()
      return ForCStatement(
        init=init,
        condition=condition,
        increment=increment,
        body=body,
        start_pos=start_pos,
        end_pos=body.end_pos,
        file=self.file
      )
      
    # 2. Iterable for loop: 'for x in iterable'
    elif self.peek().type == TokenType.IDENTIFIER and self.peek_ahead(1).type == TokenType.IN:
      var_tok = self.consume()
      variable = Identifier(
        name=var_tok.value,
        start_pos=var_tok.start_pos,
        end_pos=var_tok.end_pos,
        file=self.file
      )
      self.expect(TokenType.IN, "Expected 'in' in loop")
      iterable = self.parse_expression()
      body = self.parse_block()
      return ForInStatement(
        variable=variable,
        iterable=iterable,
        body=body,
        start_pos=start_pos,
        end_pos=body.end_pos,
        file=self.file
      )
      
    # 3. Infinite for loop: 'for'
    else:
      body = self.parse_block()
      return ForInfiniteStatement(
        body=body,
        start_pos=start_pos,
        end_pos=body.end_pos,
        file=self.file
      )

  def parse_while_statement(self) -> WhileStatement:
    """
    Parses a while loop: 'while condition'
    """
    start_pos = self.peek().start_pos
    self.expect(TokenType.WHILE, "Expected 'while'")
    
    condition = self.parse_expression()
    body = self.parse_block()
    
    return WhileStatement(
      condition=condition,
      body=body,
      start_pos=start_pos,
      end_pos=body.end_pos,
      file=self.file
    )

  @override
  def parse_declaration(self) -> Statement:
    """
    Overrides parse_declaration to raise a clear compilation error.
    Declarations require DeclarationParser.
    """
    self.error("Declarations (struct, impl, enum, module, import, use_cpp, use_c) are not allowed in this context; DeclarationParser is required")


def test_parser() -> None:
  """
  Unit tests for StatementParser class.
  """
  print("Running parser unit tests on StatementParser...")

  # Test Case 1: Explicit variable declaration "var x = 42"
  tokens1 = [
    Token(TokenType.VAR, "var", 1, 1, 0, 0, 3),
    Token(TokenType.IDENTIFIER, "x", 1, 5, 0, 4, 5),
    Token(TokenType.ASSIGN, "=", 1, 7, 0, 6, 7),
    Token(TokenType.INT, "42", 1, 9, 0, 8, 10),
    Token(TokenType.EOF, "", 1, 11, 0, 10, 10)
  ]
  parser1 = StatementParser(tokens1, "test1.pengu")
  ast1 = parser1.parse_program()
  assert len(ast1.statements) == 1
  stmt1 = ast1.statements[0]
  assert isinstance(stmt1, VariableDeclaration)
  assert stmt1.kind == "var"
  assert stmt1.name.name == "x"
  assert stmt1.type is None
  assert stmt1.value.value == "42"
  print("OK: Test 1 (Explicit var declaration) passed.")

  # Test Case 2: Explicit const declaration with type "const y: int = 10"
  tokens2 = [
    Token(TokenType.CONST, "const", 1, 1, 0, 0, 5),
    Token(TokenType.IDENTIFIER, "y", 1, 7, 0, 6, 7),
    Token(TokenType.COLON, ":", 1, 8, 0, 7, 8),
    Token(TokenType.TYPE_INT, "int", 1, 10, 0, 9, 12),
    Token(TokenType.ASSIGN, "=", 1, 14, 0, 13, 14),
    Token(TokenType.INT, "10", 1, 16, 0, 15, 17),
    Token(TokenType.EOF, "", 1, 18, 0, 17, 17)
  ]
  parser2 = StatementParser(tokens2, "test2.pengu")
  ast2 = parser2.parse_program()
  assert len(ast2.statements) == 1
  stmt2 = ast2.statements[0]
  assert isinstance(stmt2, VariableDeclaration)
  assert stmt2.kind == "const"
  assert stmt2.name.name == "y"
  assert isinstance(stmt2.type, TypeNode) and stmt2.type.name == "int"
  assert stmt2.value.value == "10"
  print("OK: Test 2 (Explicit const declaration with type) passed.")

  # Test Case 3: Short variable declaration "x := 42"
  tokens3 = [
    Token(TokenType.IDENTIFIER, "x", 1, 1, 0, 0, 1),
    Token(TokenType.COLON, ":", 1, 2, 0, 1, 2),
    Token(TokenType.ASSIGN, "=", 1, 3, 0, 2, 3),
    Token(TokenType.INT, "42", 1, 5, 0, 4, 6),
    Token(TokenType.EOF, "", 1, 7, 0, 6, 6)
  ]
  parser3 = StatementParser(tokens3, "test3.pengu")
  ast3 = parser3.parse_program()
  assert len(ast3.statements) == 1
  stmt3 = ast3.statements[0]
  assert isinstance(stmt3, VariableDeclaration)
  assert stmt3.kind == "var"
  assert stmt3.name.name == "x"
  assert stmt3.type is None
  assert stmt3.value.value == "42"
  print("OK: Test 3 (Short variable declaration :=) passed.")

  # Test Case 4: Variable declaration with implicit short syntax "y: float = 3.14"
  tokens4 = [
    Token(TokenType.IDENTIFIER, "y", 1, 1, 0, 0, 1),
    Token(TokenType.COLON, ":", 1, 2, 0, 1, 2),
    Token(TokenType.TYPE_FLOAT, "float", 1, 4, 0, 3, 8),
    Token(TokenType.ASSIGN, "=", 1, 10, 0, 9, 10),
    Token(TokenType.FLOAT, "3.14", 1, 12, 0, 11, 15),
    Token(TokenType.EOF, "", 1, 16, 0, 15, 15)
  ]
  parser4 = StatementParser(tokens4, "test4.pengu")
  ast4 = parser4.parse_program()
  assert len(ast4.statements) == 1
  stmt4 = ast4.statements[0]
  assert isinstance(stmt4, VariableDeclaration)
  assert stmt4.kind == "var"
  assert stmt4.name.name == "y"
  assert isinstance(stmt4.type, TypeNode) and stmt4.type.name == "float"
  assert stmt4.value.value == "3.14"
  print("OK: Test 4 (Implicit short declaration with type annotation) passed.")

  # Test Case 5: Simple assignment "x = 10"
  tokens5 = [
    Token(TokenType.IDENTIFIER, "x", 1, 1, 0, 0, 1),
    Token(TokenType.ASSIGN, "=", 1, 3, 0, 2, 3),
    Token(TokenType.INT, "10", 1, 5, 0, 4, 6),
    Token(TokenType.EOF, "", 1, 7, 0, 6, 6)
  ]
  parser5 = StatementParser(tokens5, "test5.pengu")
  ast5 = parser5.parse_program()
  assert len(ast5.statements) == 1
  stmt5 = ast5.statements[0]
  assert isinstance(stmt5, AssignmentStatement)
  assert isinstance(stmt5.left, Identifier) and stmt5.left.name == "x"
  assert stmt5.right.value == "10"
  print("OK: Test 5 (Simple assignment) passed.")

  # Test Case 6: Complex assignment LHS "x.y[0] = 20"
  tokens6 = [
    Token(TokenType.IDENTIFIER, "x", 1, 1, 0, 0, 1),
    Token(TokenType.DOT, ".", 1, 2, 0, 1, 2),
    Token(TokenType.IDENTIFIER, "y", 1, 3, 0, 2, 4),
    Token(TokenType.LBRACKET, "[", 1, 4, 0, 3, 4),
    Token(TokenType.INT, "0", 1, 5, 0, 4, 5),
    Token(TokenType.RBRACKET, "]", 1, 6, 0, 5, 6),
    Token(TokenType.ASSIGN, "=", 1, 8, 0, 7, 8),
    Token(TokenType.INT, "20", 1, 10, 0, 9, 12),
    Token(TokenType.EOF, "", 1, 13, 0, 12, 12)
  ]
  parser6 = StatementParser(tokens6, "test6.pengu")
  ast6 = parser6.parse_program()
  assert len(ast6.statements) == 1
  stmt6 = ast6.statements[0]
  assert isinstance(stmt6, AssignmentStatement)
  assert isinstance(stmt6.left, IndexExpression)
  assert isinstance(stmt6.left.object, MemberAccess)
  assert stmt6.right.value == "20"
  print("OK: Test 6 (Complex assignment LHS) passed.")

  # Test Case 7: Return, break, continue, and pass statements
  tokens7 = [
    Token(TokenType.RETURN, "return", 1, 1, 0, 0, 6),
    Token(TokenType.INT, "42", 1, 8, 0, 7, 9),
    Token(TokenType.SEMICOLON, ";", 1, 10, 0, 9, 10), # return stops here
    Token(TokenType.BREAK, "break", 2, 1, 0, 11, 16),
    Token(TokenType.CONTINUE, "continue", 3, 1, 0, 17, 25),
    Token(TokenType.PASS, "pass", 4, 1, 0, 26, 30),
    Token(TokenType.EOF, "", 5, 1, 0, 31, 31)
  ]
  parser7 = StatementParser(tokens7, "test7.pengu")
  ast7 = parser7.parse_program()
  assert len(ast7.statements) == 4
  assert isinstance(ast7.statements[0], ReturnStatement)
  assert ast7.statements[0].value.value == "42"
  assert isinstance(ast7.statements[1], BreakStatement)
  assert isinstance(ast7.statements[2], ContinueStatement)
  assert isinstance(ast7.statements[3], PassStatement)
  print("OK: Test 7 (Return, Break, Continue, Pass) passed.")

  # Test Case 8: Block parsing with indentation
  tokens8 = [
    Token(TokenType.INDENT, "    ", 1, 1, 4, 0, 4),
    Token(TokenType.PASS, "pass", 1, 5, 4, 4, 8),
    Token(TokenType.DEDENT, "", 1, 9, 0, 8, 8),
    Token(TokenType.EOF, "", 1, 10, 0, 8, 8)
  ]
  parser8 = StatementParser(tokens8, "test8.pengu")
  block8 = parser8.parse_block()
  assert isinstance(block8, Block)
  assert len(block8.statements) == 1
  assert isinstance(block8.statements[0], PassStatement)
  print("OK: Test 8 (Block parsing with indentation) passed.")

  # Test Case 9: Single-line if statement: "if x then 1 else 2"
  tokens9 = [
    Token(TokenType.IF, "if", 1, 1, 0, 0, 2),
    Token(TokenType.IDENTIFIER, "x", 1, 4, 0, 3, 4),
    Token(TokenType.THEN, "then", 1, 6, 0, 5, 10),
    Token(TokenType.INT, "1", 1, 11, 0, 10, 12),
    Token(TokenType.ELSE, "else", 1, 14, 0, 13, 18),
    Token(TokenType.INT, "2", 1, 20, 0, 19, 21),
    Token(TokenType.EOF, "", 1, 22, 0, 21, 21)
  ]
  parser9 = StatementParser(tokens9, "test9.pengu")
  ast9 = parser9.parse_program()
  assert len(ast9.statements) == 1
  stmt9 = ast9.statements[0]
  assert isinstance(stmt9, IfExpression)
  assert isinstance(stmt9.condition, Identifier) and stmt9.condition.name == "x"
  assert len(stmt9.then_body.statements) == 1
  assert isinstance(stmt9.then_body.statements[0], ExpressionStatement)
  assert isinstance(stmt9.then_body.statements[0].expression, IntegerLiteral) and stmt9.then_body.statements[0].expression.value == "1"
  assert stmt9.else_body is not None
  assert len(stmt9.else_body.statements) == 1
  assert isinstance(stmt9.else_body.statements[0], ExpressionStatement)
  assert isinstance(stmt9.else_body.statements[0].expression, IntegerLiteral) and stmt9.else_body.statements[0].expression.value == "2"
  print("OK: Test 9 (Single-line if then else) passed.")

  # Test Case 10: Block if statement: "if x \n  pass \n else \n  return"
  tokens10 = [
    Token(TokenType.IF, "if", 1, 1, 0, 0, 2),
    Token(TokenType.IDENTIFIER, "x", 1, 4, 0, 3, 4),
    Token(TokenType.INDENT, "  ", 2, 1, 2, 5, 7),
    Token(TokenType.PASS, "pass", 2, 3, 2, 7, 11),
    Token(TokenType.DEDENT, "", 3, 1, 0, 11, 11),
    Token(TokenType.ELSE, "else", 3, 1, 0, 11, 15),
    Token(TokenType.INDENT, "  ", 4, 1, 2, 16, 18),
    Token(TokenType.RETURN, "return", 4, 3, 2, 18, 24),
    Token(TokenType.DEDENT, "", 5, 1, 0, 24, 24),
    Token(TokenType.EOF, "", 5, 1, 0, 24, 24)
  ]
  parser10 = StatementParser(tokens10, "test10.pengu")
  ast10 = parser10.parse_program()
  assert len(ast10.statements) == 1
  stmt10 = ast10.statements[0]
  assert isinstance(stmt10, IfExpression)
  assert isinstance(stmt10.condition, Identifier) and stmt10.condition.name == "x"
  assert len(stmt10.then_body.statements) == 1
  assert isinstance(stmt10.then_body.statements[0], PassStatement)
  assert stmt10.else_body is not None
  assert len(stmt10.else_body.statements) == 1
  assert isinstance(stmt10.else_body.statements[0], ReturnStatement)
  print("OK: Test 10 (Block-based if else) passed.")

  # Test Case 11: Unless statement: "unless x \n  pass"
  tokens11 = [
    Token(TokenType.UNLESS, "unless", 1, 1, 0, 0, 6),
    Token(TokenType.IDENTIFIER, "x", 1, 8, 0, 7, 8),
    Token(TokenType.INDENT, "  ", 2, 1, 2, 9, 11),
    Token(TokenType.PASS, "pass", 2, 3, 2, 11, 15),
    Token(TokenType.DEDENT, "", 3, 1, 0, 15, 15),
    Token(TokenType.EOF, "", 3, 1, 0, 15, 15)
  ]
  parser11 = StatementParser(tokens11, "test11.pengu")
  ast11 = parser11.parse_program()
  assert len(ast11.statements) == 1
  stmt11 = ast11.statements[0]
  assert isinstance(stmt11, IfExpression)
  assert isinstance(stmt11.condition, UnaryOperator)
  assert stmt11.condition.operator == "not"
  assert isinstance(stmt11.condition.operand, Identifier) and stmt11.condition.operand.name == "x"
  assert len(stmt11.then_body.statements) == 1
  assert isinstance(stmt11.then_body.statements[0], PassStatement)
  print("OK: Test 11 (Unless block) passed.")

  # Test Case 12: Switch statement: "switch x \n  when 1 \n    pass \n  else \n    return"
  tokens12 = [
    Token(TokenType.SWITCH, "switch", 1, 1, 0, 0, 6),
    Token(TokenType.IDENTIFIER, "x", 1, 8, 0, 7, 8),
    Token(TokenType.INDENT, "  ", 2, 1, 2, 9, 11),
    Token(TokenType.WHEN, "when", 2, 3, 2, 11, 15),
    Token(TokenType.INT, "1", 2, 8, 2, 16, 17),
    Token(TokenType.INDENT, "    ", 3, 1, 4, 18, 22),
    Token(TokenType.PASS, "pass", 3, 5, 4, 22, 26),
    Token(TokenType.DEDENT, "", 4, 3, 2, 26, 26),
    Token(TokenType.ELSE, "else", 4, 3, 2, 26, 30),
    Token(TokenType.INDENT, "    ", 5, 1, 4, 31, 35),
    Token(TokenType.RETURN, "return", 5, 5, 4, 35, 41),
    Token(TokenType.DEDENT, "", 6, 1, 0, 41, 41),
    Token(TokenType.DEDENT, "", 6, 1, 0, 41, 41),
    Token(TokenType.EOF, "", 6, 1, 0, 41, 41)
  ]
  parser12 = StatementParser(tokens12, "test12.pengu")
  ast12 = parser12.parse_program()
  assert len(ast12.statements) == 1
  stmt12 = ast12.statements[0]
  assert isinstance(stmt12, SwitchExpression)
  assert isinstance(stmt12.value, Identifier) and stmt12.value.name == "x"
  assert len(stmt12.cases) == 1
  assert isinstance(stmt12.cases[0].pattern, IntegerLiteral) and stmt12.cases[0].pattern.value == "1"
  assert len(stmt12.cases[0].body.statements) == 1
  assert isinstance(stmt12.cases[0].body.statements[0], PassStatement)
  assert stmt12.else_body is not None
  assert len(stmt12.else_body.statements) == 1
  assert isinstance(stmt12.else_body.statements[0], ReturnStatement)
  print("OK: Test 12 (Switch statement) passed.")

  # Test Case 13: C-style for loop: "for var i = 0; i < 10; ++i \n  pass"
  tokens13 = [
    Token(TokenType.FOR, "for", 1, 1, 0, 0, 3),
    Token(TokenType.VAR, "var", 1, 5, 0, 4, 7),
    Token(TokenType.IDENTIFIER, "i", 1, 9, 0, 8, 9),
    Token(TokenType.ASSIGN, "=", 1, 11, 0, 10, 11),
    Token(TokenType.INT, "0", 1, 13, 0, 12, 13),
    Token(TokenType.SEMICOLON, ";", 1, 14, 0, 13, 14),
    Token(TokenType.IDENTIFIER, "i", 1, 16, 0, 15, 16),
    Token(TokenType.LT, "<", 1, 18, 0, 17, 18),
    Token(TokenType.INT, "10", 1, 20, 0, 19, 21),
    Token(TokenType.SEMICOLON, ";", 1, 22, 0, 21, 22),
    Token(TokenType.INCREMENT, "++", 1, 24, 0, 23, 25),
    Token(TokenType.IDENTIFIER, "i", 1, 26, 0, 25, 26),
    Token(TokenType.INDENT, "  ", 2, 1, 2, 27, 29),
    Token(TokenType.PASS, "pass", 2, 3, 2, 29, 33),
    Token(TokenType.DEDENT, "", 3, 1, 0, 33, 33),
    Token(TokenType.EOF, "", 3, 1, 0, 33, 33)
  ]
  parser13 = StatementParser(tokens13, "test13.pengu")
  ast13 = parser13.parse_program()
  assert len(ast13.statements) == 1
  stmt13 = ast13.statements[0]
  assert isinstance(stmt13, ForCStatement)
  assert isinstance(stmt13.init, VariableDeclaration)
  assert stmt13.init.name.name == "i"
  assert isinstance(stmt13.condition, BinaryOperator) and stmt13.condition.operator == "<"
  assert isinstance(stmt13.increment, UnaryOperator) and stmt13.increment.operator == "++"
  assert len(stmt13.body.statements) == 1
  assert isinstance(stmt13.body.statements[0], PassStatement)
  print("OK: Test 13 (C-style for loop) passed.")

  # Test Case 14: Iterable for loop: "for x in col \n  pass"
  tokens14 = [
    Token(TokenType.FOR, "for", 1, 1, 0, 0, 3),
    Token(TokenType.IDENTIFIER, "x", 1, 5, 0, 4, 5),
    Token(TokenType.IN, "in", 1, 7, 0, 6, 8),
    Token(TokenType.IDENTIFIER, "col", 1, 10, 0, 9, 12),
    Token(TokenType.INDENT, "  ", 2, 1, 2, 13, 15),
    Token(TokenType.PASS, "pass", 2, 3, 2, 15, 19),
    Token(TokenType.DEDENT, "", 3, 1, 0, 19, 19),
    Token(TokenType.EOF, "", 3, 1, 0, 19, 19)
  ]
  parser14 = StatementParser(tokens14, "test14.pengu")
  ast14 = parser14.parse_program()
  assert len(ast14.statements) == 1
  stmt14 = ast14.statements[0]
  assert isinstance(stmt14, ForInStatement)
  assert stmt14.variable.name == "x"
  assert isinstance(stmt14.iterable, Identifier) and stmt14.iterable.name == "col"
  assert len(stmt14.body.statements) == 1
  assert isinstance(stmt14.body.statements[0], PassStatement)
  print("OK: Test 14 (Iterable for loop) passed.")

  # Test Case 15: Infinite for loop: "for \n  pass"
  tokens15 = [
    Token(TokenType.FOR, "for", 1, 1, 0, 0, 3),
    Token(TokenType.INDENT, "  ", 2, 1, 2, 4, 6),
    Token(TokenType.PASS, "pass", 2, 3, 2, 6, 10),
    Token(TokenType.DEDENT, "", 3, 1, 0, 10, 10),
    Token(TokenType.EOF, "", 3, 1, 0, 10, 10)
  ]
  parser15 = StatementParser(tokens15, "test15.pengu")
  ast15 = parser15.parse_program()
  assert len(ast15.statements) == 1
  stmt15 = ast15.statements[0]
  assert isinstance(stmt15, ForInfiniteStatement)
  assert len(stmt15.body.statements) == 1
  assert isinstance(stmt15.body.statements[0], PassStatement)
  print("OK: Test 15 (Infinite for loop) passed.")

  # Test Case 16: While loop: "while x \n  pass"
  tokens16 = [
    Token(TokenType.WHILE, "while", 1, 1, 0, 0, 5),
    Token(TokenType.IDENTIFIER, "x", 1, 7, 0, 6, 7),
    Token(TokenType.INDENT, "  ", 2, 1, 2, 8, 10),
    Token(TokenType.PASS, "pass", 2, 3, 2, 10, 14),
    Token(TokenType.DEDENT, "", 3, 1, 0, 14, 14),
    Token(TokenType.EOF, "", 3, 1, 0, 14, 14)
  ]
  parser16 = StatementParser(tokens16, "test16.pengu")
  ast16 = parser16.parse_program()
  assert len(ast16.statements) == 1
  stmt16 = ast16.statements[0]
  assert isinstance(stmt16, WhileStatement)
  assert isinstance(stmt16.condition, Identifier) and stmt16.condition.name == "x"
  assert len(stmt16.body.statements) == 1
  assert isinstance(stmt16.body.statements[0], PassStatement)
  print("OK: Test 16 (While loop) passed.")

  # Test Case 17: Assert statement "assert x > 0"
  tokens17 = [
    Token(TokenType.ASSERT, "assert", 1, 1, 0, 0, 6),
    Token(TokenType.IDENTIFIER, "x", 1, 8, 0, 7, 8),
    Token(TokenType.GT, ">", 1, 10, 0, 9, 11),
    Token(TokenType.INT, "0", 1, 12, 0, 11, 13),
    Token(TokenType.EOF, "", 1, 14, 0, 13, 13)
  ]
  parser17 = StatementParser(tokens17, "test17.pengu")
  ast17 = parser17.parse_program()
  assert len(ast17.statements) == 1
  stmt17 = ast17.statements[0]
  assert isinstance(stmt17, AssertStatement)
  assert isinstance(stmt17.condition, BinaryOperator)
  assert stmt17.condition.operator == ">"
  assert stmt17.message is None
  print("OK: Test 17 (Assert statement) passed.")

  # Test Case 18: Assert statement with message: "assert x, "error""
  tokens18 = [
    Token(TokenType.ASSERT, "assert", 1, 1, 0, 0, 6),
    Token(TokenType.IDENTIFIER, "x", 1, 8, 0, 7, 8),
    Token(TokenType.COMMA, ",", 1, 9, 0, 8, 9),
    Token(TokenType.STRING, "error", 1, 11, 0, 10, 17),
    Token(TokenType.EOF, "", 1, 18, 0, 17, 17)
  ]
  parser18 = StatementParser(tokens18, "test18.pengu")
  ast18 = parser18.parse_program()
  assert len(ast18.statements) == 1
  stmt18 = ast18.statements[0]
  assert isinstance(stmt18, AssertStatement)
  assert isinstance(stmt18.condition, Identifier) and stmt18.condition.name == "x"
  assert isinstance(stmt18.message, StringLiteral) and stmt18.message.value == "error"
  print("OK: Test 18 (Assert with message) passed.")

  # Test Case 19: Raise statement: "raise x"
  tokens19 = [
    Token(TokenType.RAISE, "raise", 1, 1, 0, 0, 5),
    Token(TokenType.IDENTIFIER, "x", 1, 7, 0, 6, 7),
    Token(TokenType.EOF, "", 1, 8, 0, 7, 7)
  ]
  parser19 = StatementParser(tokens19, "test19.pengu")
  ast19 = parser19.parse_program()
  assert len(ast19.statements) == 1
  stmt19 = ast19.statements[0]
  assert isinstance(stmt19, RaiseStatement)
  assert isinstance(stmt19.value, Identifier) and stmt19.value.name == "x"
  print("OK: Test 19 (Raise statement) passed.")

  # Test Case 20: Struct declaration parsed in StatementParser should raise ParseError
  tokens20 = [
    Token(TokenType.STRUCT, "struct", 1, 1, 0, 0, 6),
    Token(TokenType.IDENTIFIER, "Point", 1, 8, 0, 7, 12),
    Token(TokenType.EOF, "", 1, 13, 0, 12, 12)
  ]
  parser20 = StatementParser(tokens20, "test20.pengu")
  from parser.parser import ParseError
  try:
    parser20.parse_program()
    assert False, "Expected ParseError for declaration in StatementParser"
  except ParseError as e:
    assert "DeclarationParser is required" in str(e)
  print("OK: Test 20 (Declaration block error in StatementParser) passed.")

  print("All unit tests passed successfully!")


if __name__ == "__main__":
  test_parser()
