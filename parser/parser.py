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

from typing import Callable, NoReturn
from lexer.token import Token, TokenType
from ast.ast_nodes import ASTNode, Expression, Statement, Program, Block, ExpressionStatement


class ParseError(Exception):
  """
  Custom exception class raised by the parser when a syntax error is encountered.
  Stores the error message and the token where the error occurred.
  """
  def __init__(self, message: str, token: Token):
    super().__init__(message)
    self.message = message
    self.token = token


class Parser:
  """
  Base class for the PenguScript parser.
  Provides core token stream navigation, helper functions for matching and assertion,
  error generation, and the Pratt parsing loop for expression parsing.
  """
  def __init__(self, tokens: list[Token], file_path: str = ""):
    """
    Initializes the Parser with a list of tokens and the file path.
    """
    self.tokens = tokens
    self.pos = 0
    self.file = file_path
    
    # Cache the first token (or EOF if the list is empty)
    if self.tokens:
      self.current_token = self.tokens[0]
    else:
      self.current_token = Token(TokenType.EOF, "", 1, 1, 0, 0, 0, self.file)
      
    # Pratt operator registries to be populated by concrete parser classes
    self.prefix_parsers: dict[TokenType, Callable[[], Expression]] = {}
    self.infix_parsers: dict[TokenType, Callable[[Expression, Token], Expression]] = {}
    self.precedences: dict[TokenType, int] = {}

  def peek(self) -> Token:
    """
    Returns the token at the current position without advancing.
    If position is past the last token, returns the EOF token.
    """
    if self.pos >= len(self.tokens):
      if self.tokens:
        return self.tokens[-1]
      return Token(TokenType.EOF, "", 1, 1, 0, 0, 0, self.file)
    return self.tokens[self.pos]

  def peek_ahead(self, n: int) -> Token:
    """
    Returns the token at n positions ahead of the current position without consuming it.
    If the target position is out of bounds, returns the EOF token.
    """
    index = self.pos + n
    if index >= len(self.tokens):
      if self.tokens:
        return self.tokens[-1]
      return Token(TokenType.EOF, "", 1, 1, 0, 0, 0, self.file)
    return self.tokens[index]

  def consume(self) -> Token:
    """
    Consumes the current token, advances the parser position, and returns
    the token that was just consumed.
    Caches the new current token.
    """
    token = self.peek()
    if token.type != TokenType.EOF:
      self.pos += 1
      self.current_token = self.peek()
    return token

  def expect(self, type: TokenType, error_msg: str) -> Token:
    """
    Asserts that the current token is of the expected type, consumes it, and
    returns it. If not, raises a ParseError with the given message.
    """
    token = self.peek()
    if token.type == type:
      return self.consume()
    self.error(error_msg)

  def match(self, type: TokenType) -> bool:
    """
    Returns True and consumes the current token if it matches the expected type.
    Otherwise, returns False and does not advance.
    """
    if self.peek().type == type:
      self.consume()
      return True
    return False

  def advance_if(self, type: TokenType) -> None:
    """
    Consumes the current token if it matches the expected type.
    Similar to match but does not return a value.
    """
    if self.peek().type == type:
      self.consume()

  def error(self, msg: str) -> NoReturn:
    """
    Raises a ParseError exception including line, column, and file info.
    """
    token = self.peek()
    formatted_msg = (
      f"Syntax Error in '{self.file}' at line {token.line}, column {token.column}: {msg}"
    )
    raise ParseError(formatted_msg, token)

  def parse_expression(self, min_precedence: int = 0) -> Expression:
    """
    Parses an expression using the Pratt parser (top-down operator precedence) algorithm.
    Recursively binds operators with precedence >= min_precedence.
    """
    token = self.peek()
    prefix_fn = self.prefix_parsers.get(token.type)
    if not prefix_fn:
      self.error(f"Expected expression, found unexpected token '{token.value}' (type: {token.type.name})")
      
    left = prefix_fn()
    
    while True:
      next_token = self.peek()
      next_prec = self.precedences.get(next_token.type, 0)
      if next_prec < min_precedence:
        break
        
      infix_fn = self.infix_parsers.get(next_token.type)
      if not infix_fn:
        break
        
      op_token = self.consume()
      left = infix_fn(left, op_token)
      
    return left

  def parse_program(self) -> Program:
    """
    Parses the entire token stream into a Program AST node.
    This is the main entry point of the parser.
    """
    start_pos = self.peek().start_pos
    statements: list[Statement] = []
    
    while self.peek().type != TokenType.EOF:
      token = self.peek()
      # Skip stray INDENT/DEDENT tokens at top-level if any
      if token.type in (TokenType.INDENT, TokenType.DEDENT):
        self.consume()
        continue
      
      # Semicolons can be ignored/consumed at top level
      if token.type == TokenType.SEMICOLON:
        self.consume()
        continue
        
      # Dispatch top-level declarations vs statements explicitly
      if token.type in (TokenType.MODULE, TokenType.IMPORT, TokenType.FROM,
                        TokenType.USE_CPP, TokenType.USE_C, TokenType.ENUM,
                        TokenType.STRUCT, TokenType.IMPL):
        stmt = self.parse_declaration()
      else:
        stmt = self.parse_statement()
        
      if stmt is not None:
        statements.append(stmt)
      
    end_pos = self.peek().end_pos
    return Program(
      statements=statements,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_block(self) -> Block:
    """
    Parses a block of statements delimited by INDENT and DEDENT.
    """
    start_pos = self.peek().start_pos
    self.expect(TokenType.INDENT, "Expected block indentation to start (INDENT)")
    
    statements: list[Statement] = []
    while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
      # Skip stray duplicate indents inside blocks if encountered
      if self.peek().type == TokenType.INDENT:
        self.consume()
        continue
      
      stmt = self.parse_statement()
      if stmt is not None:
        statements.append(stmt)
      
    end_pos = self.peek().end_pos
    self.expect(TokenType.DEDENT, "Expected block indentation to end (DEDENT)")
    
    return Block(
      statements=statements,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_statement(self) -> Statement:
    """
    Parses a single statement. If an INDENT token is seen, parses a block.
    Otherwise defaults to parsing an expression statement.
    """
    if self.peek().type == TokenType.INDENT:
      return self.parse_block()
      
    start_pos = self.peek().start_pos
    expr = self.parse_expression()
    end_pos = self.peek().end_pos
    return ExpressionStatement(
      expression=expr,
      start_pos=start_pos,
      end_pos=end_pos,
      file=self.file
    )

  def parse_declaration(self) -> Statement:
    """
    Parses a single declaration. Base class implementation raises NotImplementedError.
    """
    raise NotImplementedError("parse_declaration must be implemented by subclasses")

  @staticmethod
  def pretty_print(node, indent: int = 0) -> None:
    """
    Helper to print the AST in a beautiful, structured format.
    """
    import dataclasses
    
    indent_str = "  " * indent
    if node is None:
      print(f"{indent_str}None")
      return
      
    if isinstance(node, list):
      if not node:
        print(f"{indent_str}[]")
      else:
        print(f"{indent_str}[")
        for item in node:
          if isinstance(item, (ASTNode, list)):
            Parser.pretty_print(item, indent + 1)
          else:
            print(f"{indent_str}  {repr(item)}")
        print(f"{indent_str}]")
      return
      
    if not isinstance(node, ASTNode):
      print(f"{indent_str}{repr(node)}")
      return
      
    class_name = node.__class__.__name__
    
    if dataclasses.is_dataclass(node):
      flds = dataclasses.fields(node)
      # Filter out metadata fields like start_pos, end_pos, indent_level, file
      display_fields = [f for f in flds if f.name not in ("start_pos", "end_pos", "indent_level", "file")]
      
      # Non-AST / non-list fields to display on the same line
      line_fields = {f.name: getattr(node, f.name) for f in display_fields if not isinstance(getattr(node, f.name), (ASTNode, list))}
      
      if not display_fields:
        print(f"{indent_str}{class_name}()")
      else:
        fields_desc = f" {repr(line_fields)}" if line_fields else ""
        print(f"{indent_str}{class_name}{fields_desc}")
        for f in display_fields:
          val = getattr(node, f.name)
          if isinstance(val, (ASTNode, list)):
            print(f"{indent_str}  {f.name}:")
            Parser.pretty_print(val, indent + 2)
    else:
      print(f"{indent_str}{class_name}(non-dataclass)")


def test_parser() -> None:
  """
  Runs basic verification tests using ExpressionParser.
  """
  print("Running base parser test suite...")
  from parser.declarations import DeclarationParser
  from ast.ast_nodes import GroupingExpression, IntegerLiteral
  
  tokens = [
    Token(TokenType.LPAREN, "(", 1, 1, 0, 0, 1),
    Token(TokenType.INT, "42", 1, 2, 0, 1, 3),
    Token(TokenType.RPAREN, ")", 1, 4, 0, 3, 4),
    Token(TokenType.EOF, "", 1, 5, 0, 4, 4)
  ]
  
  parser = DeclarationParser(tokens, "test_file.pengu")
  ast = parser.parse_program()
  print("AST parsed successfully!")
  
  assert len(ast.statements) == 1
  stmt = ast.statements[0]
  assert isinstance(stmt, ExpressionStatement)
  group = stmt.expression
  assert isinstance(group, GroupingExpression)
  lit = group.expression
  assert isinstance(lit, IntegerLiteral)
  assert lit.value == "42"
  print("OK: Dynamic resolution and ExpressionParser subclass tests passed.")


if __name__ == "__main__":
  test_parser()
