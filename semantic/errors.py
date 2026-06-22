from __future__ import annotations
from typing import Any

def get_error_code(message: str, is_warning: bool) -> str | None:
  if is_warning:
    return None
  msg_lower = message.lower()
  if "redecl" in msg_lower or "shadow" in msg_lower or "duplicate" in msg_lower or "collides" in msg_lower:
    return "E0001"
  if "undeclared" in msg_lower or "undefined" in msg_lower:
    return "E0002"
  if "type mismatch" in msg_lower or "cannot assign" in msg_lower or "cannot initialize" in msg_lower or "return type mismatch" in msg_lower or "must be boolean" in msg_lower or "must be an integer" in msg_lower or "applied to non-subscriptable" in msg_lower or "requires numeric" in msg_lower or "requires boolean" in msg_lower or "incompatible types" in msg_lower or "cannot be applied" in msg_lower:
    return "E0003"
  if "global scope" in msg_lower:
    return "E0004"
  if "main function" in msg_lower or "the 'main' function" in msg_lower:
    return "E0005"
  if "expects" in msg_lower and "argument" in msg_lower:
    return "E0006"
  if "member access" in msg_lower or "has no member" in msg_lower:
    return "E0007"
  if "return statement outside" in msg_lower:
    return "E0008"
  return "E0000"


class Diagnostic:
  """
  Represents a semantic diagnostic (error or warning) with rich formatting.
  Matches the Cargo/Rust-style output.
  """
  def __init__(
    self,
    is_warning: bool,
    message: str,
    file: str,
    line: int,
    column: int,
    suggestion: str | None = None,
    code: str | None = None,
    source_line: str | None = None,
    span_len: int = 1
  ) -> None:
    self.is_warning: bool = is_warning
    self.message: str = message
    self.file: str = file
    self.line: int = line
    self.column: int = column
    self.suggestion: str | None = suggestion
    self.source_line: str | None = source_line
    self.span_len: int = span_len
    
    if not code:
      self.code: str | None = get_error_code(message, is_warning)
    else:
      self.code = code

  def __str__(self) -> str:
    level = "warning" if self.is_warning else "error"
    code_part = f"[{self.code}]" if self.code else ""
    header = f"{level}{code_part}: {self.message}"
    location = f"  --> {self.file}:{self.line}:{self.column}"
    
    if self.source_line is not None:
      line_num_str = f"{self.line}"
      padding = " " * len(line_num_str)
      
      pointer = "^" * self.span_len
      leading_spaces = ""
      for char in self.source_line[:self.column - 1]:
        if char == "\t":
          leading_spaces += "\t"
        else:
          leading_spaces += " "
          
      source_part = (
        f"\n{padding} |\n"
        f"{line_num_str} | {self.source_line}\n"
        f"{padding} | {leading_spaces}{pointer}"
      )
      if self.suggestion:
        source_part += f" help: {self.suggestion}"
    else:
      suggestion_part = f"\n  help: {self.suggestion}" if self.suggestion else ""
      source_part = suggestion_part
      
    return f"{header}\n{location}{source_part}\n"

  def __repr__(self) -> str:
    return f"Diagnostic(warning={self.is_warning}, message='{self.message}', {self.file}:{self.line}:{self.column})"


class SemanticError(Exception):
  """
  Exception raised for immediate halt on a semantic error.
  """
  def __init__(self, diagnostic: Diagnostic) -> None:
    super().__init__(str(diagnostic))
    self.diagnostic: Diagnostic = diagnostic


class SemanticWarning(Exception):
  """
  Exception raised or mapped for a semantic warning.
  """
  def __init__(self, diagnostic: Diagnostic) -> None:
    super().__init__(str(diagnostic))
    self.diagnostic: Diagnostic = diagnostic
