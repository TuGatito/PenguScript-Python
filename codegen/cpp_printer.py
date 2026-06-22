class CppPrinter:
  """
  Indentation and formatting helper for generating structured C++ code.
  """
  def __init__(self, indent_string: str = "  ") -> None:
    self.indent_string: str = indent_string
    self.indent_level: int = 0
    self.lines: list[str] = []
    self._current_line: str = ""

  def indent(self) -> None:
    """Increases indentation level."""
    self.indent_level += 1

  def dedent(self) -> None:
    """Decreases indentation level, ensuring it never drops below 0."""
    if self.indent_level > 0:
      self.indent_level -= 1

  def write(self, text: str) -> None:
    """Appends text to the current line buffer without creating a new line."""
    self._current_line += text

  def write_line(self, text: str = "") -> None:
    """Flushes the current line buffer and appends a new formatted line to output."""
    if text:
      self._current_line += text
      
    if self._current_line:
      indent = self.indent_string * self.indent_level
      self.lines.append(indent + self._current_line)
    else:
      self.lines.append("")
    self._current_line = ""

  def get_code(self) -> str:
    """Flushes any remaining buffered text and returns the full generated code as a string."""
    if self._current_line:
      indent = self.indent_string * self.indent_level
      self.lines.append(indent + self._current_line)
      self._current_line = ""
    return "\n".join(self.lines)
