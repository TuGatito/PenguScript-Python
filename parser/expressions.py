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

from typing import Callable
from lexer.token import Token, TokenType
from ast.ast_nodes import (
  Expression, IntegerLiteral, FloatLiteral, StringLiteral,
  CharacterLiteral, BooleanLiteral, Identifier, GroupingExpression,
  UnaryOperator, BinaryOperator, MemberAccess, IndexExpression,
  ExpressionStatement, CallExpression, LambdaExpression, Parameter, TypeNode, Block,
  ArrayLiteral, TemplateInstantiation, ForComprehension
)
from parser.parser import Parser


class ExpressionParser(Parser):
  """
  Subclass of Parser that implements parsing of expressions.
  Populates prefix/infix registries and implements grammar rules for all expression nodes.
  """
  def __init__(self, tokens: list[Token], file_path: str = ""):
    """
    Initializes the ExpressionParser, defining precedence levels and registering prefix/infix/postfix operators.
    """
    super().__init__(tokens, file_path)
    
    # Precedence definition (integers)
    # Higher values bind tighter.
    PREC_NONE = 0
    PREC_ASSIGN = 1      # =
    PREC_OR = 2          # or
    PREC_AND = 3         # and
    PREC_EQUALITY = 4    # == !=
    PREC_COMPARISON = 5  # < <= > >=
    PREC_SHIFT = 6       # << >>
    PREC_TERM = 7        # + -
    PREC_FACTOR = 8      # * /
    PREC_UNARY = 9       # prefix: not - + ++ --
    PREC_CALL = 10       # suffix/infix: . [ ( !

    # --------------------------------------------------------------------------
    # 1. Register Precedences for Infix/Postfix Tokens
    # --------------------------------------------------------------------------
    self.precedences[TokenType.ASSIGN] = PREC_ASSIGN
    
    self.precedences[TokenType.OR] = PREC_OR
    self.precedences[TokenType.AND] = PREC_AND
    
    self.precedences[TokenType.EQ] = PREC_EQUALITY
    self.precedences[TokenType.NEQ] = PREC_EQUALITY
    
    self.precedences[TokenType.LT] = PREC_COMPARISON
    self.precedences[TokenType.LTE] = PREC_COMPARISON
    self.precedences[TokenType.GT] = PREC_COMPARISON
    self.precedences[TokenType.GTE] = PREC_COMPARISON
    
    self.precedences[TokenType.LSHIFT] = PREC_SHIFT
    self.precedences[TokenType.RSHIFT] = PREC_SHIFT
    
    self.precedences[TokenType.PLUS] = PREC_TERM
    self.precedences[TokenType.MINUS] = PREC_TERM
    
    self.precedences[TokenType.ASTERISK] = PREC_FACTOR
    self.precedences[TokenType.SLASH] = PREC_FACTOR
    
    # Suffix/Infix high-precedence operators:
    self.precedences[TokenType.INCREMENT] = PREC_UNARY  # postfix ++
    self.precedences[TokenType.DECREMENT] = PREC_UNARY  # postfix --
    self.precedences[TokenType.DOT] = PREC_CALL         # .member
    self.precedences[TokenType.LBRACKET] = PREC_CALL    # [index]
    self.precedences[TokenType.LPAREN] = PREC_CALL      # function(args)
    self.precedences[TokenType.EXCLAMATION] = PREC_CALL  # lambda!

    # --------------------------------------------------------------------------
    # 2. Register Prefix Parsers (nud)
    # --------------------------------------------------------------------------
    # Primaries & Grouping:
    self.prefix_parsers[TokenType.INT] = self.parse_integer
    self.prefix_parsers[TokenType.FLOAT] = self.parse_float
    self.prefix_parsers[TokenType.STRING] = self.parse_string
    self.prefix_parsers[TokenType.CHAR] = self.parse_character
    self.prefix_parsers[TokenType.BOOL] = self.parse_boolean
    self.prefix_parsers[TokenType.IDENTIFIER] = self.parse_identifier
    self.prefix_parsers[TokenType.LPAREN] = self.parse_grouped_expression
    self.prefix_parsers[TokenType.FOR] = self.parse_for_comprehension
    self.prefix_parsers[TokenType.LBRACKET] = self.parse_array_literal
    self.prefix_parsers[TokenType.THIS] = self.parse_this
    if hasattr(self, "parse_if_statement"):
      self.prefix_parsers[TokenType.IF] = self.parse_if_statement
      self.prefix_parsers[TokenType.UNLESS] = self.parse_if_statement
    if hasattr(self, "parse_switch_statement"):
      self.prefix_parsers[TokenType.SWITCH] = self.parse_switch_statement
    
    # Unary prefix operators:
    self.prefix_parsers[TokenType.NOT] = self.parse_prefix_operator
    self.prefix_parsers[TokenType.MINUS] = self.parse_prefix_operator
    self.prefix_parsers[TokenType.PLUS] = self.parse_prefix_operator
    self.prefix_parsers[TokenType.INCREMENT] = self.parse_prefix_operator
    self.prefix_parsers[TokenType.DECREMENT] = self.parse_prefix_operator
    self.prefix_parsers[TokenType.REF] = self.parse_prefix_operator

    # --------------------------------------------------------------------------
    # 3. Register Infix/Postfix Parsers (led)
    # --------------------------------------------------------------------------
    # Binary operators:
    self.infix_parsers[TokenType.ASSIGN] = self.parse_binary_operator
    self.infix_parsers[TokenType.OR] = self.parse_binary_operator
    self.infix_parsers[TokenType.AND] = self.parse_binary_operator
    self.infix_parsers[TokenType.EQ] = self.parse_binary_operator
    self.infix_parsers[TokenType.NEQ] = self.parse_binary_operator
    self.infix_parsers[TokenType.LT] = self.parse_binary_operator
    self.infix_parsers[TokenType.LTE] = self.parse_binary_operator
    self.infix_parsers[TokenType.GT] = self.parse_binary_operator
    self.infix_parsers[TokenType.GTE] = self.parse_binary_operator
    self.infix_parsers[TokenType.LSHIFT] = self.parse_binary_operator
    self.infix_parsers[TokenType.RSHIFT] = self.parse_binary_operator
    self.infix_parsers[TokenType.PLUS] = self.parse_binary_operator
    self.infix_parsers[TokenType.MINUS] = self.parse_binary_operator
    self.infix_parsers[TokenType.ASTERISK] = self.parse_binary_operator
    self.infix_parsers[TokenType.SLASH] = self.parse_binary_operator
    
    # Postfix / high-precedence operators:
    self.infix_parsers[TokenType.INCREMENT] = self.parse_postfix_operator
    self.infix_parsers[TokenType.DECREMENT] = self.parse_postfix_operator
    self.infix_parsers[TokenType.DOT] = self.parse_member_access
    self.infix_parsers[TokenType.LBRACKET] = self.parse_index_expression
    self.infix_parsers[TokenType.LPAREN] = self.parse_call_expression
    self.infix_parsers[TokenType.EXCLAMATION] = self.parse_lambda_call

  # ==============================================================================
  # Primary Expressions (Fase 1)
  # ==============================================================================

  def parse_integer(self) -> IntegerLiteral:
    """
    Parses an integer literal.
    """
    token = self.expect(TokenType.INT, "Expected integer literal")
    return IntegerLiteral(
      value=token.value,
      start_pos=token.start_pos,
      end_pos=token.end_pos,
      file=self.file
    )

  def parse_float(self) -> FloatLiteral:
    """
    Parses a floating-point literal.
    """
    token = self.expect(TokenType.FLOAT, "Expected float literal")
    return FloatLiteral(
      value=token.value,
      start_pos=token.start_pos,
      end_pos=token.end_pos,
      file=self.file
    )

  def parse_string(self) -> StringLiteral:
    """
    Parses a string literal.
    """
    token = self.expect(TokenType.STRING, "Expected string literal")
    return StringLiteral(
      value=token.value,
      start_pos=token.start_pos,
      end_pos=token.end_pos,
      file=self.file
    )

  def parse_character(self) -> CharacterLiteral:
    """
    Parses a character literal.
    """
    token = self.expect(TokenType.CHAR, "Expected character literal")
    return CharacterLiteral(
      value=token.value,
      start_pos=token.start_pos,
      end_pos=token.end_pos,
      file=self.file
    )

  def parse_boolean(self) -> BooleanLiteral:
    """
    Parses a boolean literal.
    """
    token = self.expect(TokenType.BOOL, "Expected boolean literal")
    return BooleanLiteral(
      value=token.value,
      start_pos=token.start_pos,
      end_pos=token.end_pos,
      file=self.file
    )

  def parse_identifier(self) -> Identifier:
    """
    Parses an identifier.
    """
    token = self.expect(TokenType.IDENTIFIER, "Expected identifier")
    return Identifier(
      name=token.value,
      start_pos=token.start_pos,
      end_pos=token.end_pos,
      file=self.file
    )

  def parse_grouped_expression(self) -> Expression:
    """
    Parses a grouped expression enclosed in parentheses, or routes to
    lambda parsing if lookahead detects a parameter list.
    """
    if self.is_lambda_next():
      return self.parse_lambda()
      
    lparen = self.expect(TokenType.LPAREN, "Expected opening parenthesis '('")
    expr = self.parse_expression()
    rparen = self.expect(TokenType.RPAREN, "Expected closing parenthesis ')'")
    return GroupingExpression(
      expression=expr,
      start_pos=lparen.start_pos,
      end_pos=rparen.end_pos,
      file=self.file
    )

  def parse_primary_expression(self) -> Expression:
    """
    Parses a primary expression by dispatching to the appropriate parser method
    based on the current token type.
    """
    token = self.peek()
    if token.type == TokenType.INT:
      return self.parse_integer()
    elif token.type == TokenType.FLOAT:
      return self.parse_float()
    elif token.type == TokenType.STRING:
      return self.parse_string()
    elif token.type == TokenType.CHAR:
      return self.parse_character()
    elif token.type == TokenType.BOOL:
      return self.parse_boolean()
    elif token.type == TokenType.IDENTIFIER:
      return self.parse_identifier()
    elif token.type == TokenType.LPAREN:
      return self.parse_grouped_expression()
    else:
      self.error(f"Expected primary expression, found unexpected token '{token.value}' (type: {token.type.name})")

  # ==============================================================================
  # Expresiones de Operadores (Fase 2)
  # ==============================================================================

  def parse_prefix_operator(self) -> UnaryOperator:
    """
    Parses a prefix unary operator expression.
    e.g., -x, not x, ++x, --x.
    """
    op_token = self.consume()
    # Unary operators bind tightly (precedence 9)
    operand = self.parse_expression(min_precedence=9)
    return UnaryOperator(
      operator=op_token.value,
      operand=operand,
      is_prefix=True,
      start_pos=op_token.start_pos,
      end_pos=operand.end_pos,
      file=self.file
    )

  def parse_binary_operator(self, left: Expression, op_token: Token) -> BinaryOperator:
    """
    Parses a binary operator expression.
    Handles left/right associativity correctly.
    """
    op_prec = self.precedences.get(op_token.type, 0)
    
    # Right-associative operators (like assignment '=') do not increment min_precedence for RHS.
    # Left-associative operators increment by 1 to force tighter binding to the left.
    is_right_assoc = (op_token.type == TokenType.ASSIGN)
    next_min_prec = op_prec if is_right_assoc else op_prec + 1
    
    right = self.parse_expression(min_precedence=next_min_prec)
    return BinaryOperator(
      operator=op_token.value,
      left=left,
      right=right,
      start_pos=left.start_pos,
      end_pos=right.end_pos,
      file=self.file
    )

  def parse_postfix_operator(self, left: Expression, op_token: Token) -> UnaryOperator:
    """
    Parses a postfix unary operator expression.
    e.g., x++, x--.
    """
    return UnaryOperator(
      operator=op_token.value,
      operand=left,
      is_prefix=False,
      start_pos=left.start_pos,
      end_pos=op_token.end_pos,
      file=self.file
    )

  def parse_member_access(self, left: Expression, op_token: Token) -> MemberAccess:
    """
    Parses a member access expression (dot notation).
    e.g., object.member.
    """
    member = self.parse_identifier()
    return MemberAccess(
      object=left,
      member=member,
      start_pos=left.start_pos,
      end_pos=member.end_pos,
      file=self.file
    )

  def parse_index_expression(self, left: Expression, op_token: Token) -> IndexExpression:
    """
    Parses an index/subscript expression (bracket notation).
    e.g., array[index].
    """
    index_expr = self.parse_expression()
    rbracket = self.expect(TokenType.RBRACKET, "Expected closing bracket ']' after index expression")
    return IndexExpression(
      object=left,
      index=index_expr,
      start_pos=left.start_pos,
      end_pos=rbracket.end_pos,
      file=self.file
    )

  # ==============================================================================
  # Calls and Lambdas (Phase 6 / Phase 3)
  # ==============================================================================

  def is_lambda_next(self) -> bool:
    """
    Looks ahead to determine if the upcoming token sequence represents a lambda expression.
    Scans to find the matching closing parenthesis and checks if it is followed by '=>' or ':'.
    """
    if self.peek().type != TokenType.LPAREN:
      return False
      
    depth = 0
    i = 0
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
          return next_tok.type in (TokenType.DOUBLE_ARROW, TokenType.COLON)
      i += 1
    return False

  def parse_type_node(self) -> TypeNode:
    """
    Parses a type node structure, resolving nested template types and primitive types.
    e.g., int, void, std.string, std.expected<int, std.string_view>.
    """
    start_pos = self.peek().start_pos
    
    is_ref = self.match(TokenType.REF)
    
    # A type name can start with an IDENTIFIER or a primitive type keyword (starts with TYPE_)
    token = self.peek()
    if token.type == TokenType.IDENTIFIER or token.type.name.startswith("TYPE_"):
      self.consume()
      name_parts = [token.value]
    else:
      self.error("Expected type name (identifier or primitive type)")
      
    while self.match(TokenType.DOT):
      name_parts.append(self.expect(TokenType.IDENTIFIER, "Expected sub-identifier in type name").value)
    type_name = ".".join(name_parts)
    
    # Parse optional template parameters delimited by < and >
    type_args: list[TypeNode] = []
    if self.match(TokenType.LT):  # '<'
      type_args.append(self.parse_type_node())
      while self.match(TokenType.COMMA):
        type_args.append(self.parse_type_node())
      self.expect(TokenType.GT, "Expected closing angle bracket '>' for template parameters")
      
    # Parse optional array bracket suffix like [2]
    array_size = None
    if self.match(TokenType.LBRACKET):
      size_val = self.expect(TokenType.INT, "Expected integer for array size").value
      self.expect(TokenType.RBRACKET, "Expected closing bracket ']' for array type")
      array_size = int(size_val)

    end_pos = self.peek().start_pos
    return TypeNode(
      name=type_name,
      type_arguments=type_args,
      is_ref=is_ref,
      array_size=array_size,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_parameter_list(self) -> list[Parameter]:
    """
    Parses a parenthesized parameter list.
    e.g., (name: Type = default, name2: Type2).
    """
    self.expect(TokenType.LPAREN, "Expected opening parenthesis '(' for parameter list")
    params: list[Parameter] = []
    
    if self.peek().type != TokenType.RPAREN:
      params.append(self.parse_parameter())
      while self.match(TokenType.COMMA):
        params.append(self.parse_parameter())
        
    self.expect(TokenType.RPAREN, "Expected closing parenthesis ')' for parameter list")
    return params

  def parse_parameter(self) -> Parameter:
    """
    Parses a single parameter declaration.
    """
    start_pos = self.peek().start_pos
    name = self.parse_identifier()
    
    type_node = None
    if self.match(TokenType.COLON):
      type_node = self.parse_type_node()
      
    default = None
    if self.match(TokenType.ASSIGN):  # '='
      default = self.parse_expression()
      
    end_pos = self.peek().end_pos
    return Parameter(
      name=name,
      type=type_node,
      default=default,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_lambda(self) -> LambdaExpression:
    """
    Parses a lambda expression.
    e.g., (x, y): int => x + y  or  () => { body }
    """
    start_pos = self.peek().start_pos
    params = self.parse_parameter_list()
    
    return_type = None
    if self.match(TokenType.COLON):
      return_type = self.parse_type_node()
      
    self.expect(TokenType.DOUBLE_ARROW, "Expected double arrow '=>' for lambda expression body")
    
    body_start_pos = self.peek().start_pos
    # Check if lambda has a multi-line block body or an inline single expression body
    if self.peek().type == TokenType.INDENT:
      body = self.parse_block()
    else:
      expr = self.parse_expression()
      body_end_pos = self.peek().end_pos
      
      # Wrap inline expression in an ExpressionStatement and Block node
      expr_stmt = ExpressionStatement(
        expression=expr,
        start_pos=body_start_pos,
        end_pos=body_end_pos,
        file=self.file
      )
      body = Block(
        statements=[expr_stmt],
        start_pos=body_start_pos,
        end_pos=body_end_pos,
        file=self.file
      )
      
    end_pos = self.peek().end_pos
    return LambdaExpression(
      params=params,
      return_type=return_type,
      body=body,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_lambda_expression(self) -> LambdaExpression:
    """
    Parses a lambda expression. Alias for parse_lambda.
    """
    return self.parse_lambda()

  def parse_call_expression(self, left: Expression, op_token: Token) -> CallExpression:
    """
    Parses a parenthesized function call expression.
    e.g., function(a, b).
    """
    arguments: list[Expression] = []
    if self.peek().type != TokenType.RPAREN:
      arguments.append(self.parse_expression())
      while self.match(TokenType.COMMA):
        arguments.append(self.parse_expression())
        
    rparen = self.expect(TokenType.RPAREN, "Expected closing parenthesis ')' after function arguments list")
    return CallExpression(
      function=left,
      arguments=arguments,
      is_lambda_call=False,
      start_pos=left.start_pos,
      end_pos=rparen.end_pos,
      file=self.file
    )

  def parse_lambda_call(self, left: Expression, op_token: Token) -> CallExpression:
    """
    Parses a lambda call expression using suffix exclamation mark.
    e.g., lambda!.
    """
    return CallExpression(
      function=left,
      arguments=[],
      is_lambda_call=True,
      start_pos=left.start_pos,
      end_pos=op_token.end_pos,
      file=self.file
    )

  def parse_expression(self, min_precedence: int = 0) -> Expression:
    # First check prefix token
    token = self.peek()
    prefix_fn = self.prefix_parsers.get(token.type)
    if not prefix_fn:
      self.error(f"Expected expression, found unexpected token '{token.value}' (type: {token.type.name})")
      
    left = prefix_fn()
    
    while True:
      next_token = self.peek()
      if next_token.type == TokenType.LT and self.is_template_args_next():
        self.consume() # consume LT
        type_args = []
        type_args.append(self.parse_type_node())
        while self.match(TokenType.COMMA):
          type_args.append(self.parse_type_node())
        self.expect(TokenType.GT, "Expected closing angle bracket '>' for template arguments")
        
        left = TemplateInstantiation(
          element=left,
          type_arguments=type_args,
          start_pos=left.start_pos,
          end_pos=self.peek().start_pos,
          file=self.file
        )
        
        # Pratt infix loop inside template/generic call boundary
        while True:
          nt = self.peek()
          np = self.precedences.get(nt.type, 0)
          if np < min_precedence:
            break
          infix_fn = self.infix_parsers.get(nt.type)
          if not infix_fn:
            break
          op_tok = self.consume()
          left = infix_fn(left, op_tok)
        continue
        
      # Check for compound assignments like +=, -=, *=, /=
      if next_token.type in (TokenType.PLUS, TokenType.MINUS, TokenType.ASTERISK, TokenType.SLASH) and self.peek_ahead(1).type == TokenType.ASSIGN:
        op_prec = 1 # PREC_ASSIGN
        if op_prec < min_precedence:
          break
          
        op_tok1 = self.consume()
        op_tok2 = self.consume()
        op_str = op_tok1.value + op_tok2.value
        
        right = self.parse_expression(min_precedence=1) # right associative
        left = BinaryOperator(
          operator=op_str,
          left=left,
          right=right,
          start_pos=left.start_pos,
          end_pos=right.end_pos,
          file=self.file
        )
        continue

      next_prec = self.precedences.get(next_token.type, 0)
      if next_prec < min_precedence:
        break
        
      infix_fn = self.infix_parsers.get(next_token.type)
      if not infix_fn:
        break
        
      op_token = self.consume()
      left = infix_fn(left, op_token)
      
    return left

  def is_template_args_next(self) -> bool:
    if self.peek().type != TokenType.LT:
      return False
    # Scan ahead to find matching GT
    depth = 0
    i = 0
    while True:
      tok = self.peek_ahead(i)
      if tok.type in (TokenType.EOF, TokenType.SEMICOLON, TokenType.INDENT, TokenType.DEDENT):
        return False
      if tok.type == TokenType.LT:
        depth += 1
      elif tok.type == TokenType.GT:
        depth -= 1
        if depth == 0:
          next_tok = self.peek_ahead(i + 1)
          return next_tok.type in (TokenType.LPAREN, TokenType.EXCLAMATION)
      i += 1

  def parse_for_comprehension(self) -> ForComprehension:
    start_pos = self.peek().start_pos
    self.expect(TokenType.FOR, "Expected 'for' in list comprehension")
    variable = self.parse_identifier()
    self.expect(TokenType.IN, "Expected 'in' in comprehension")
    iterable = self.parse_expression()
    
    if self.match(TokenType.INDENT):
      body_expr = self.parse_expression()
      self.match(TokenType.SEMICOLON)
      self.match(TokenType.COMMA)
      self.expect(TokenType.DEDENT, "Expected DEDENT after comprehension body expression")
    else:
      body_expr = self.parse_expression()
      
    return ForComprehension(
      variable=variable,
      iterable=iterable,
      body_expr=body_expr,
      start_pos=start_pos,
      end_pos=body_expr.end_pos,
      file=self.file
    )

  def parse_array_literal(self) -> ArrayLiteral:
    start_pos = self.peek().start_pos
    self.expect(TokenType.LBRACKET, "Expected '['")
    elements = []
    if self.peek().type != TokenType.RBRACKET:
      elements.append(self.parse_expression())
      while self.match(TokenType.COMMA):
        if self.peek().type == TokenType.RBRACKET:
          break
        elements.append(self.parse_expression())
    rbracket = self.expect(TokenType.RBRACKET, "Expected ']'")
    return ArrayLiteral(
      elements=elements,
      start_pos=start_pos,
      end_pos=rbracket.end_pos,
      file=self.file
    )

  def parse_this(self) -> Identifier:
    tok = self.expect(TokenType.THIS, "Expected 'this'")
    return Identifier(
      name="this",
      start_pos=tok.start_pos,
      end_pos=tok.end_pos,
      file=self.file
    )


def test_parser() -> None:
  """
  Runs basic verification tests for the ExpressionParser class.
  Covers Phase 1, Phase 2, and Phase 3 expression parsing rules.
  """
  print("Running parser unit tests on ExpressionParser...")
  
  # Test case 1: Grouped expression (42)
  tokens1 = [
    Token(TokenType.LPAREN, "(", 1, 1, 0, 0, 1),
    Token(TokenType.INT, "42", 1, 2, 0, 1, 3),
    Token(TokenType.RPAREN, ")", 1, 4, 0, 3, 4),
    Token(TokenType.EOF, "", 1, 5, 0, 4, 4)
  ]
  parser1 = ExpressionParser(tokens1, "test1.pengu")
  ast1 = parser1.parse_program()
  assert len(ast1.statements) == 1
  stmt1 = ast1.statements[0]
  assert isinstance(stmt1, ExpressionStatement)
  group1 = stmt1.expression
  assert isinstance(group1, GroupingExpression)
  assert group1.expression.value == "42"
  print("OK: Test 1 (Grouped expression) passed.")

  # Test case 2: Binary operator precedence: x + y * z
  tokens2 = [
    Token(TokenType.IDENTIFIER, "x", 1, 1, 0, 0, 1),
    Token(TokenType.PLUS, "+", 1, 3, 0, 2, 3),
    Token(TokenType.IDENTIFIER, "y", 1, 5, 0, 4, 5),
    Token(TokenType.ASTERISK, "*", 1, 7, 0, 6, 7),
    Token(TokenType.IDENTIFIER, "z", 1, 9, 0, 8, 9),
    Token(TokenType.EOF, "", 1, 10, 0, 9, 9)
  ]
  parser2 = ExpressionParser(tokens2, "test2.pengu")
  ast2 = parser2.parse_program()
  assert len(ast2.statements) == 1
  expr2 = ast2.statements[0].expression
  assert isinstance(expr2, BinaryOperator)
  assert expr2.operator == "+"
  assert isinstance(expr2.left, Identifier) and expr2.left.name == "x"
  assert isinstance(expr2.right, BinaryOperator)
  assert expr2.right.operator == "*"
  print("OK: Test 2 (Binary operator precedence x + y * z) passed.")

  # Test case 3: Unary prefix and suffix operators: -a++
  tokens3 = [
    Token(TokenType.MINUS, "-", 1, 1, 0, 0, 1),
    Token(TokenType.IDENTIFIER, "a", 1, 2, 0, 1, 2),
    Token(TokenType.INCREMENT, "++", 1, 3, 0, 2, 4),
    Token(TokenType.EOF, "", 1, 5, 0, 4, 4)
  ]
  parser3 = ExpressionParser(tokens3, "test3.pengu")
  ast3 = parser3.parse_program()
  expr3 = ast3.statements[0].expression
  assert isinstance(expr3, UnaryOperator)
  assert expr3.operator == "-"
  assert expr3.is_prefix is True
  assert isinstance(expr3.operand, UnaryOperator)
  assert expr3.operand.operator == "++"
  assert expr3.operand.is_prefix is False
  print("OK: Test 3 (Unary prefix/suffix precedence -a++) passed.")

  # Test case 4: Member access and Indexing: obj.field[0]
  tokens4 = [
    Token(TokenType.IDENTIFIER, "obj", 1, 1, 0, 0, 3),
    Token(TokenType.DOT, ".", 1, 4, 0, 3, 4),
    Token(TokenType.IDENTIFIER, "field", 1, 5, 0, 4, 9),
    Token(TokenType.LBRACKET, "[", 1, 10, 0, 9, 10),
    Token(TokenType.INT, "0", 1, 11, 0, 10, 11),
    Token(TokenType.RBRACKET, "]", 1, 12, 0, 11, 12),
    Token(TokenType.EOF, "", 1, 13, 0, 12, 12)
  ]
  parser4 = ExpressionParser(tokens4, "test4.pengu")
  ast4 = parser4.parse_program()
  expr4 = ast4.statements[0].expression
  assert isinstance(expr4, IndexExpression)
  assert isinstance(expr4.object, MemberAccess)
  print("OK: Test 4 (Member access and indexing obj.field[0]) passed.")

  # Test case 5: Function calls and Lambda suffix: add(x, 1) and logger!
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
  parser5 = ExpressionParser(tokens5, "test5.pengu")
  ast5 = parser5.parse_program()
  expr5 = ast5.statements[0].expression
  assert isinstance(expr5, CallExpression)
  assert expr5.is_lambda_call is True
  assert isinstance(expr5.function, CallExpression)
  assert expr5.function.is_lambda_call is False
  assert isinstance(expr5.function.function, Identifier) and expr5.function.function.name == "add"
  assert len(expr5.function.arguments) == 2
  print("OK: Test 5 (Function call and lambda suffix exclamation) passed.")

  # Test case 6: Lambda expression: (msg: std.string_view): void => print(msg)
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
  parser6 = ExpressionParser(tokens6, "test6.pengu")
  ast6 = parser6.parse_program()
  expr6 = ast6.statements[0].expression
  assert isinstance(expr6, LambdaExpression)
  assert len(expr6.params) == 1
  assert expr6.params[0].name.name == "msg"
  assert isinstance(expr6.params[0].type, TypeNode) and expr6.params[0].type.name == "std.string_view"
  assert isinstance(expr6.return_type, TypeNode) and expr6.return_type.name == "void"
  assert isinstance(expr6.body, Block)
  assert len(expr6.body.statements) == 1
  assert isinstance(expr6.body.statements[0], ExpressionStatement)
  inner_call = expr6.body.statements[0].expression
  assert isinstance(inner_call, CallExpression)
  assert inner_call.function.name == "print"
  print("OK: Test 6 (Lambda expression with type annotations and inline body) passed.")

  print("All unit tests passed successfully!")


if __name__ == "__main__":
  test_parser()
