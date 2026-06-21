from lexer.token import TokenType, Token

KEYWORDS = {
  "var": TokenType.VAR,
  "const": TokenType.CONST,
  "ref": TokenType.REF,
  "if": TokenType.IF,
  "then": TokenType.THEN,
  "else": TokenType.ELSE,
  "unless": TokenType.UNLESS,
  "switch": TokenType.SWITCH,
  "when": TokenType.WHEN,
  "for": TokenType.FOR,
  "in": TokenType.IN,
  "break": TokenType.BREAK,
  "continue": TokenType.CONTINUE,
  "return": TokenType.RETURN,
  "struct": TokenType.STRUCT,
  "impl": TokenType.IMPL,
  "constructor": TokenType.CONSTRUCTOR,
  "destructor": TokenType.DESTRUCTOR,
  "this": TokenType.THIS,
  "enum": TokenType.ENUM,
  "module": TokenType.MODULE,
  "import": TokenType.IMPORT,
  "from": TokenType.FROM,
  "as": TokenType.AS,
  "use_cpp": TokenType.USE_CPP,
  "use_c": TokenType.USE_C,
  "and": TokenType.AND,
  "or": TokenType.OR,
  "not": TokenType.NOT,
  "true": TokenType.BOOL,
  "false": TokenType.BOOL,
  "int": TokenType.TYPE_INT,
  "short": TokenType.TYPE_SHORT,
  "long": TokenType.TYPE_LONG,
  "char": TokenType.TYPE_CHAR,
  "bool": TokenType.TYPE_BOOL,
  "void": TokenType.TYPE_VOID,
  "float": TokenType.TYPE_FLOAT,
  "double": TokenType.TYPE_DOUBLE,
  "signed": TokenType.TYPE_SIGNED,
  "unsigned": TokenType.TYPE_UNSIGNED,
  "let": TokenType.LET,
  "while": TokenType.WHILE,
  "def": TokenType.DEF,
  "class": TokenType.CLASS,
  "try": TokenType.TRY,
  "catch": TokenType.CATCH,
  "finally": TokenType.FINALLY,
  "with": TokenType.WITH,
  "pass": TokenType.PASS,
  "assert": TokenType.ASSERT,
  "raise": TokenType.RAISE,
}

class Lexer:
  def __init__(self, source: str, file_path: str = ""):
    """
    Initializes the Lexer with the source code and optional file path.
    """
    self.source = source
    self.file_path = file_path
    self.pos = 0
    self.line = 1
    self.column = 1
    self.tokens: list[Token] = []
    self.indent_stack = [0]
    self.at_line_start = True

  def peek(self) -> str:
    """
    Returns the character at the current position without advancing the position pointer.
    """
    if self.pos >= len(self.source):
      return ""
    return self.source[self.pos]

  def peek_ahead(self, n: int) -> str:
    """
    Returns the character at n positions ahead of the current position without advancing.
    """
    if self.pos + n >= len(self.source):
      return ""
    return self.source[self.pos + n]

  def advance(self) -> str:
    """
    Advances the position pointer and returns the character at the previous position.
    Updates the line and column counters accordingly.
    Handles Unix (\n), Windows (\r\n), and legacy Mac (\r) line endings.
    """
    if self.pos >= len(self.source):
      return ""
    char = self.source[self.pos]
    self.pos += 1
    
    if char == '\n':
      self.line += 1
      self.column = 1
    elif char == '\r':
      # Standalone \r or part of \r\n
      if self.peek() != '\n':
        self.line += 1
        self.column = 1
      else:
        # Part of \r\n, temporarily increment column.
        # It will be reset to 1 when the subsequent \n is advanced.
        self.column += 1
    else:
      self.column += 1
      
    return char

  def consume_newline(self) -> None:
    """
    Consumes a newline sequence (\n, \r, or \r\n) using advance().
    """
    char = self.peek()
    if char == '\r':
      self.advance()
    if self.peek() == '\n':
      self.advance()

  def tokenize(self) -> list[Token]:
    """
    Scans the entire source code and returns a list of processed Token objects.
    """
    while self.pos < len(self.source):
      if self.at_line_start:
        self.handle_line_start()
        if self.pos >= len(self.source):
          break
        if self.at_line_start:
          continue
      
      self.skip_whitespace_horizontal()
      
      if self.pos >= len(self.source):
        break
        
      char = self.peek()
      if char == '\n' or char == '\r':
        self.consume_newline()
        self.at_line_start = True
        continue
      
      if char == '#':
        self.skip_comment()
        continue

      self.scan_token()
      
    self.handle_eof()
    return self.tokens

  def handle_line_start(self) -> None:
    """
    Measures the leading whitespace (indentation) of a new line.
    Emits INDENT or DEDENT tokens based on changes in the indentation level.
    Skips empty or comment-only lines without altering the indentation stack.
    """
    start_pos = self.pos
    start_line = self.line
    start_col = self.column
    
    # 1. Measure indentation spaces
    indent_spaces = 0
    while self.pos < len(self.source):
      char = self.peek()
      if char == ' ':
        indent_spaces += 1
        self.advance()
      elif char == '\t':
        indent_spaces += 4
        self.advance()
      else:
        break
        
    char = self.peek()
    
    # 2. Check if we have a block comment, a single-line comment, or empty line
    is_block_comment = self.source[self.pos:self.pos+3] == "###"
    
    if is_block_comment:
      comment_start_pos = self.pos
      comment_start_line = self.line
      comment_start_col = self.column
      
      self.advance() # '#'
      self.advance() # '#'
      self.advance() # '#'
      
      closed = False
      while self.pos < len(self.source):
        if self.source[self.pos:self.pos+3] == "###":
          self.advance()
          self.advance()
          self.advance()
          closed = True
          break
        self.advance()
        
      if not closed:
        self.tokens.append(Token(
          type=TokenType.ILLEGAL,
          value="Unclosed block comment",
          line=comment_start_line,
          column=comment_start_col,
          indent=self.indent_stack[-1],
          start_pos=comment_start_pos,
          end_pos=self.pos,
          file=self.file_path
        ))
        
      # Check if the rest of the line contains code
      temp_pos = self.pos
      has_code = False
      while temp_pos < len(self.source):
        c = self.source[temp_pos]
        if c == '\n' or c == '\r':
          break
        if c != ' ' and c != '\t':
          has_code = True
          break
        temp_pos += 1
        
      if has_code:
        self.process_indentation(indent_spaces, start_line, start_col, start_pos)
        self.at_line_start = False
        return
      else:
        self.skip_whitespace_horizontal()
        self.consume_newline()
        self.at_line_start = True
        return
        
    elif char == '#':
      # Single-line comment: always empty/comment-only line
      self.skip_comment()
      self.consume_newline()
      self.at_line_start = True
      return
      
    elif char == '\n' or char == '\r' or char == '':
      # Empty line
      self.consume_newline()
      self.at_line_start = True
      return
      
    # 3. Regular line of code: process indentation
    self.process_indentation(indent_spaces, start_line, start_col, start_pos)
    self.at_line_start = False

  def process_indentation(self, indent_spaces: int, start_line: int, start_col: int, start_pos: int) -> None:
    """
    Processes indentation changes, emitting INDENT/DEDENT tokens,
    and handling mismatch errors by adjusting the stack.
    """
    current_indent = self.indent_stack[-1]
    if indent_spaces > current_indent:
      self.indent_stack.append(indent_spaces)
      self.tokens.append(Token(
        type=TokenType.INDENT,
        value=" " * indent_spaces,
        line=start_line,
        column=1,
        indent=indent_spaces,
        start_pos=start_pos,
        end_pos=self.pos,
        file=self.file_path
      ))
    elif indent_spaces < current_indent:
      while len(self.indent_stack) > 1 and self.indent_stack[-1] > indent_spaces:
        self.indent_stack.pop()
        self.tokens.append(Token(
          type=TokenType.DEDENT,
          value="",
          line=start_line,
          column=1,
          indent=self.indent_stack[-1],
          start_pos=start_pos,
          end_pos=start_pos,
          file=self.file_path
        ))
      
      if self.indent_stack[-1] != indent_spaces:
        self.tokens.append(Token(
          type=TokenType.ILLEGAL,
          value=f"Indentation mismatch: expected {self.indent_stack[-1]} spaces, got {indent_spaces}",
          line=start_line,
          column=start_col,
          indent=indent_spaces,
          start_pos=start_pos,
          end_pos=self.pos,
          file=self.file_path
        ))
        self.indent_stack.append(indent_spaces)

  def skip_whitespace_horizontal(self) -> None:
    """
    Consumes horizontal whitespace characters (spaces and tabs) on the current line.
    """
    while self.pos < len(self.source):
      char = self.peek()
      if char == ' ' or char == '\t':
        self.advance()
      else:
        break

  def skip_comment(self) -> None:
    """
    Consumes single-line (#) or multi-line (###) comments.
    Correctly tracks line and column changes for multi-line comments.
    """
    start_pos = self.pos
    start_line = self.line
    start_col = self.column
    
    is_block_comment = self.source[self.pos:self.pos+3] == "###"
    
    if is_block_comment:
      self.advance() # '#'
      self.advance() # '#'
      self.advance() # '#'
      
      closed = False
      while self.pos < len(self.source):
        if self.source[self.pos:self.pos+3] == "###":
          self.advance()
          self.advance()
          self.advance()
          closed = True
          break
        self.advance()
        
      if not closed:
        self.tokens.append(Token(
          type=TokenType.ILLEGAL,
          value="Unclosed block comment",
          line=start_line,
          column=start_col,
          indent=self.indent_stack[-1],
          start_pos=start_pos,
          end_pos=self.pos,
          file=self.file_path
        ))
    else:
      while self.pos < len(self.source):
        char = self.peek()
        if char == '\n' or char == '\r':
          break
        self.advance()
        
    # Check if the rest of the line contains only whitespace, newline, or EOF
    temp_pos = self.pos
    is_eol = True
    while temp_pos < len(self.source):
      c = self.source[temp_pos]
      if c == '\n' or c == '\r':
        break
      if c != ' ' and c != '\t':
        is_eol = False
        break
      temp_pos += 1
      
    if is_eol:
      self.at_line_start = True
    else:
      self.at_line_start = False

  def scan_token(self) -> None:
    """
    Scans the next syntactic token at the current position and appends it to the tokens list.
    Handles operators, separators, strings, numbers, and identifiers.
    """
    char = self.peek()
    
    # 1. Operators and Symbols
    if char == '=':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      if self.peek() == '=':
        self.advance()
        self.tokens.append(Token(TokenType.EQ, "==", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      elif self.peek() == '>':
        self.advance()
        self.tokens.append(Token(TokenType.DOUBLE_ARROW, "=>", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      else:
        self.tokens.append(Token(TokenType.ASSIGN, "=", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
        
    elif char == '+':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      if self.peek() == '+':
        self.advance()
        self.tokens.append(Token(TokenType.INCREMENT, "++", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      else:
        self.tokens.append(Token(TokenType.PLUS, "+", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
        
    elif char == '-':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      if self.peek() == '>':
        self.advance()
        self.tokens.append(Token(TokenType.ARROW, "->", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      elif self.peek() == '-':
        self.advance()
        self.tokens.append(Token(TokenType.DECREMENT, "--", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      else:
        self.tokens.append(Token(TokenType.MINUS, "-", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
        
    elif char == '*':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.ASTERISK, "*", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == '/':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.SLASH, "/", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == '!':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      if self.peek() == '=':
        self.advance()
        self.tokens.append(Token(TokenType.NEQ, "!=", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      else:
        self.tokens.append(Token(TokenType.EXCLAMATION, "!", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
        
    elif char == '<':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      if self.peek() == '<':
        self.advance()
        self.tokens.append(Token(TokenType.LSHIFT, "<<", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      elif self.peek() == '=':
        self.advance()
        self.tokens.append(Token(TokenType.LTE, "<=", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      else:
        self.tokens.append(Token(TokenType.LT, "<", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
        
    elif char == '>':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      if self.peek() == '>':
        self.advance()
        self.tokens.append(Token(TokenType.RSHIFT, ">>", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      elif self.peek() == '=':
        self.advance()
        self.tokens.append(Token(TokenType.GTE, ">=", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      else:
        self.tokens.append(Token(TokenType.GT, ">", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
        
    elif char == '.':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.DOT, ".", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == ':':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.COLON, ":", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == ',':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.COMMA, ",", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == ';':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.SEMICOLON, ";", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == '(':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.LPAREN, "(", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == ')':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.RPAREN, ")", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == '[':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.LBRACKET, "[", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == ']':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.RBRACKET, "]", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == '{':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.LBRACE, "{", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))
      
    elif char == '}':
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.RBRACE, "}", self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))

    # 2. String Literals
    elif char == '"':
      self.tokens.append(self.read_string())
      
    # 3. Numeric Literals
    elif char.isdigit():
      self.tokens.append(self.read_number())
      
    # 4. Identifiers and Keywords
    elif char.isalpha() or char == '_':
      self.tokens.append(self.read_identifier())
      
    # 5. Illegal character
    else:
      start_pos = self.pos
      start_col = self.column
      self.advance()
      self.tokens.append(Token(TokenType.ILLEGAL, char, self.line, start_col, self.indent_stack[-1], start_pos, self.pos, self.file_path))

  def read_string(self) -> Token:
    """
    Reads and parses a double-quoted string literal, handling escaped characters.
    Supports standard escapes (\\n, \\t, \\r, \\\", \\\\), hex escape (\\xHH),
    unicode escape (\\uHHHH), null escape (\\0), and alert/backspace/formfeed/vertical tab.
    Returns a STRING token or an ILLEGAL token if the string is unclosed.
    """
    start_pos = self.pos
    start_line = self.line
    start_col = self.column
    self.advance() # consume the opening '"'
    
    value_chars = []
    closed = False
    while self.pos < len(self.source):
      char = self.peek()
      if char == '"':
        self.advance() # consume closing '"'
        closed = True
        break
      elif char == '\\':
        self.advance() # consume escape '\'
        if self.pos < len(self.source):
          escaped = self.advance()
          if escaped == 'n':
            value_chars.append('\n')
          elif escaped == 't':
            value_chars.append('\t')
          elif escaped == 'r':
            value_chars.append('\r')
          elif escaped == '\\':
            value_chars.append('\\')
          elif escaped == '"':
            value_chars.append('"')
          elif escaped == '0':
            value_chars.append('\0')
          elif escaped == 'a':
            value_chars.append('\a')
          elif escaped == 'b':
            value_chars.append('\b')
          elif escaped == 'f':
            value_chars.append('\f')
          elif escaped == 'v':
            value_chars.append('\v')
          elif escaped == 'x':
            # Read next 2 hex digits
            hex_chars = ""
            for _ in range(2):
              if self.pos < len(self.source):
                hex_chars += self.advance()
            try:
              value_chars.append(chr(int(hex_chars, 16)))
            except ValueError:
              value_chars.append('\\x' + hex_chars)
          elif escaped == 'u':
            # Read next 4 hex digits
            hex_chars = ""
            for _ in range(4):
              if self.pos < len(self.source):
                hex_chars += self.advance()
            try:
              value_chars.append(chr(int(hex_chars, 16)))
            except ValueError:
              value_chars.append('\\u' + hex_chars)
          else:
            value_chars.append('\\' + escaped)
        else:
          value_chars.append('\\')
      elif char == '\n' or char == '\r':
        break
      else:
        value_chars.append(self.advance())
        
    value = "".join(value_chars)
    if not closed:
      return Token(
        type=TokenType.ILLEGAL,
        value=self.source[start_pos:self.pos],
        line=start_line,
        column=start_col,
        indent=self.indent_stack[-1],
        start_pos=start_pos,
        end_pos=self.pos,
        file=self.file_path
      )
      
    return Token(
      type=TokenType.STRING,
      value=value,
      line=start_line,
      column=start_col,
      indent=self.indent_stack[-1],
      start_pos=start_pos,
      end_pos=self.pos,
      file=self.file_path
    )

  def read_number(self) -> Token:
    """
    Reads and parses a numeric literal, supporting integers, floats, and scientific notation.
    Returns either an INT or FLOAT token.
    """
    start_pos = self.pos
    start_line = self.line
    start_col = self.column
    
    while self.peek().isdigit():
      self.advance()
      
    is_float = False
    
    if self.peek() == '.':
      if self.peek_ahead(1).isdigit():
        is_float = True
        self.advance() # consume '.'
        while self.peek().isdigit():
          self.advance()
          
    if self.peek() in ('e', 'E'):
      next_char = self.peek_ahead(1)
      has_exponent = False
      exponent_offset = 1
      if next_char in ('+', '-'):
        next_char = self.peek_ahead(2)
        exponent_offset = 2
      if next_char.isdigit():
        has_exponent = True
        
      if has_exponent:
        is_float = True
        self.advance() # consume 'e'/'E'
        if self.peek() in ('+', '-'):
          self.advance()
        while self.peek().isdigit():
          self.advance()
          
    value = self.source[start_pos:self.pos]
    token_type = TokenType.FLOAT if is_float else TokenType.INT
    return Token(
      type=token_type,
      value=value,
      line=start_line,
      column=start_col,
      indent=self.indent_stack[-1],
      start_pos=start_pos,
      end_pos=self.pos,
      file=self.file_path
    )

  def read_identifier(self) -> Token:
    """
    Reads an alphanumeric identifier or keyword.
    Returns the matching keyword Token if present in KEYWORDS, otherwise an IDENTIFIER Token.
    """
    start_pos = self.pos
    start_line = self.line
    start_col = self.column
    
    while self.pos < len(self.source):
      char = self.peek()
      if char.isalnum() or char == '_':
        self.advance()
      else:
        break
        
    value = self.source[start_pos:self.pos]
    token_type = KEYWORDS.get(value, TokenType.IDENTIFIER)
    
    return Token(
      type=token_type,
      value=value,
      line=start_line,
      column=start_col,
      indent=self.indent_stack[-1],
      start_pos=start_pos,
      end_pos=self.pos,
      file=self.file_path
    )

  def handle_eof(self) -> None:
    """
    Cleans up the lexer state at the end of the file.
    Emits remaining DEDENT tokens to balance the indentation stack and appends the EOF token.
    """
    start_pos = self.pos
    while len(self.indent_stack) > 1:
      self.indent_stack.pop()
      self.tokens.append(Token(
        type=TokenType.DEDENT,
        value="",
        line=self.line,
        column=self.column,
        indent=self.indent_stack[-1],
        start_pos=start_pos,
        end_pos=start_pos,
        file=self.file_path
      ))
      
    self.tokens.append(Token(
      type=TokenType.EOF,
      value="",
      line=self.line,
      column=self.column,
      indent=0,
      start_pos=start_pos,
      end_pos=start_pos,
      file=self.file_path
    ))

  @staticmethod
  def pretty_print(tokens: list[Token]) -> None:
    """
    Prints a beautifully formatted tree representation of the token stream.
    Visualizes nested indentation levels using tree branches.
    """
    indent_level = 0
    prefixes = []
    use_ascii = False
    
    for i, token in enumerate(tokens):
      if token.type == TokenType.DEDENT:
        if indent_level > 0:
          indent_level -= 1
          if prefixes:
            prefixes.pop()
            
      line_prefix = "".join(prefixes)
      value_part = f": {repr(token.value)}" if token.value else ""
      pos_info = f" [L{token.line}:C{token.column}]"
      
      is_last_in_block = (i == len(tokens) - 1 or 
                          (i < len(tokens) - 1 and tokens[i+1].type == TokenType.DEDENT))
      
      if use_ascii:
        branch = "+-- " if is_last_in_block else "|-- "
      else:
        branch = "└── " if is_last_in_block else "├── "
        
      try:
        print(f"{line_prefix}{branch}{token.type.name}{value_part}{pos_info}")
      except UnicodeEncodeError:
        use_ascii = True
        prefixes = ["|   " for _ in range(indent_level)]
        line_prefix = "".join(prefixes)
        branch = "+-- " if is_last_in_block else "|-- "
        print(f"{line_prefix}{branch}{token.type.name}{value_part}{pos_info}")
      
      if token.type == TokenType.INDENT:
        indent_level += 1
        prefixes.append("|   " if use_ascii else "│   ")

def test_lexer() -> None:
  """
  Runs unit tests to verify the lexer's robustness, correctness, and bug fixes.
  """
  print("Running lexer unit tests...")
  
  # Test 1: Block comment at start of line followed by code on the same line
  src1 = "    ### comment ### var x = 1"
  lexer1 = Lexer(src1)
  tokens1 = lexer1.tokenize()
  token_types1 = [t.type for t in tokens1]
  assert TokenType.INDENT in token_types1, "Test 1 failed: INDENT token missing"
  assert token_types1[0] == TokenType.INDENT, "Test 1 failed: first token must be INDENT"
  assert tokens1[0].indent == 4, f"Test 1 failed: expected indent of 4, got {tokens1[0].indent}"
  print("OK: Test 1 passed: Block comment followed by code detected indentation correctly.")
  
  # Test 2: Blank line / carriage returns and line counts
  src2 = "var x = 1\r\n\r\n  var y = 2"
  lexer2 = Lexer(src2)
  tokens2 = lexer2.tokenize()
  y_tokens = [t for t in tokens2 if t.value == "y"]
  assert len(y_tokens) == 1, "Test 2 failed: token y not found"
  assert y_tokens[0].line == 3, f"Test 2 failed: expected line 3 for y, got {y_tokens[0].line}"
  indents2 = [t for t in tokens2 if t.type == TokenType.INDENT]
  assert len(indents2) == 1 and indents2[0].indent == 2, "Test 2 failed: INDENT with 2 spaces not found"
  print("OK: Test 2 passed: Windows line endings and empty lines processed correctly.")

  # Test 3: Indentation mismatch adjustment
  src3 = "  var x = 1\n    var y = 2\n   var z = 3"
  lexer3 = Lexer(src3)
  tokens3 = lexer3.tokenize()
  illegals = [t for t in tokens3 if t.type == TokenType.ILLEGAL]
  assert len(illegals) == 1, "Test 3 failed: ILLEGAL token for mismatch missing"
  assert "Indentation mismatch" in illegals[0].value, "Test 3 failed: incorrect error message"
  z_tokens = [t for t in tokens3 if t.value == "z"]
  assert len(z_tokens) == 1, "Test 3 failed: token z not found"
  assert z_tokens[0].indent == 3, f"Test 3 failed: expected indent 3 for z, got {z_tokens[0].indent}"
  print("OK: Test 3 passed: Indentation mismatch handled and stack adjusted successfully.")

  # Test 4: Extended escape characters in string literals
  src4 = 'var str = "hello\\nworld\\x0a\\u0020\\0"'
  lexer4 = Lexer(src4)
  tokens4 = lexer4.tokenize()
  str_tokens = [t for t in tokens4 if t.type == TokenType.STRING]
  assert len(str_tokens) == 1, "Test 4 failed: string literal token missing"
  assert str_tokens[0].value == "hello\nworld\n \0", f"Test 4 failed: expected parsed string 'hello\\nworld\\n \\0', got {repr(str_tokens[0].value)}"
  print("OK: Test 4 passed: Extended string escape characters parsed correctly.")
  
  print("All unit tests passed successfully!")

if __name__ == "__main__":
  test_lexer()