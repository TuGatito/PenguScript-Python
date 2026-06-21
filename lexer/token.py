from enum import Enum, auto
from dataclasses import dataclass

class TokenType(Enum):
  # Special / Control
  ILLEGAL = auto()
  EOF = auto()
  INDENT = auto()
  DEDENT = auto()
  
  # Literals
  IDENTIFIER = auto()
  INT = auto()       # Integer literal
  FLOAT = auto()     # Float literal
  STRING = auto()    # String literal
  CHAR = auto()      # Character literal
  BOOL = auto()      # Boolean literal

  # Operators
  ASSIGN = auto()         # =
  PLUS = auto()           # +
  MINUS = auto()          # -
  ASTERISK = auto()       # *
  SLASH = auto()          # /
  INCREMENT = auto()      # ++
  DECREMENT = auto()      # --
  
  # Comparison Operators
  EQ = auto()             # ==
  NEQ = auto()            # !=
  LT = auto()             # <
  LTE = auto()            # <=
  GT = auto()             # >
  GTE = auto()            # >=
  
  # Stream / Shift Operators
  LSHIFT = auto()         # <<
  RSHIFT = auto()         # >>

  # Arrows & Symbols
  ARROW = auto()          # ->
  DOUBLE_ARROW = auto()   # =>
  EXCLAMATION = auto()    # !
  DOT = auto()            # .
  COLON = auto()          # :
  COMMA = auto()          # ,
  SEMICOLON = auto()      # ;

  # Delimiters
  LPAREN = auto()         # (
  RPAREN = auto()         # )
  LBRACKET = auto()       # [
  RBRACKET = auto()       # ]
  LBRACE = auto()         # {
  RBRACE = auto()         # }

  # Keywords
  VAR = auto()
  CONST = auto()
  REF = auto()
  
  IF = auto()
  THEN = auto()
  ELSE = auto()
  UNLESS = auto()
  SWITCH = auto()
  WHEN = auto()
  
  FOR = auto()
  IN = auto()
  BREAK = auto()
  CONTINUE = auto()
  RETURN = auto()
  
  STRUCT = auto()
  IMPL = auto()
  CONSTRUCTOR = auto()
  DESTRUCTOR = auto()
  THIS = auto()
  ENUM = auto()
  
  MODULE = auto()
  IMPORT = auto()
  FROM = auto()
  AS = auto()
  
  USE_CPP = auto()
  USE_C = auto()
  
  AND = auto()
  OR = auto()
  NOT = auto()

  # C++ Primitive Type Keywords
  TYPE_INT = auto()
  TYPE_SHORT = auto()
  TYPE_LONG = auto()
  TYPE_CHAR = auto()
  TYPE_BOOL = auto()
  TYPE_VOID = auto()
  TYPE_FLOAT = auto()
  TYPE_DOUBLE = auto()
  TYPE_SIGNED = auto()
  TYPE_UNSIGNED = auto()

  # Other Python/JS-like keywords (kept for compatibility/future use)
  LET = auto()
  WHILE = auto()
  DEF = auto()
  CLASS = auto()
  TRY = auto()
  CATCH = auto()
  FINALLY = auto()
  WITH = auto()
  YIELD = auto()
  ASYNC = auto()
  AWAIT = auto()
  PASS = auto()
  ASSERT = auto()
  RAISE = auto()
  

@dataclass
class Token:
  type: TokenType
  value: str
  line: int          # 1-indexed line number
  column: int        # 1-indexed column number
  indent: int = 0    # Indentation level (e.g. spaces) of the line this token is on
  start_pos: int = 0 # 0-indexed start character position in the source
  end_pos: int = 0   # 0-indexed end character position in the source
  file: str = ""     # Source file name/path

  @property
  def length(self) -> int:
    """Returns the character length of the token value."""
    return len(self.value)

  def get_error_context(self, source: str) -> str:
    """
    Returns a formatted string highlighting this token's position in the source line,
    ideal for displaying compiler error messages.
    """
    lines = source.splitlines()
    if 0 < self.line <= len(lines):
      line_text = lines[self.line - 1]
      # Create a caret line pointing to the column
      marker = " " * (self.column - 1) + "^" * max(1, self.length)
      return f"Line {self.line}, Column {self.column}:\n  {line_text}\n  {marker}"
    return f"Line {self.line}, Column {self.column}"