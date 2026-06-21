from __future__ import annotations
from dataclasses import dataclass, field

# ==============================================================================
# 1. Base AST Nodes
# ==============================================================================

@dataclass
class ASTNode:
  """
  Base class for all AST nodes.
  Includes position information for error reporting.
  """
  start_pos: int = 0
  end_pos: int = 0
  indent_level: int = 0
  file: str = ""

  @property
  def length(self) -> int:
    """
    Returns the character length of the AST node.
    """
    return self.end_pos - self.start_pos


@dataclass
class Expression(ASTNode):
  """
  Base class for all expression nodes.
  """
  pass


@dataclass
class Statement(ASTNode):
  """
  Base class for all statement nodes.
  """
  pass


@dataclass
class ExpressionStatement(Statement):
  """
  Represents an expression evaluated as a statement.
  e.g., function calls, assignments.
  """
  expression: Expression = field(default_factory=Expression)


@dataclass
class Block(Statement):
  """
  Represents a block containing multiple statements.
  """
  statements: list[Statement] = field(default_factory=list)


# ==============================================================================
# 2. Literals and Basic Expressions
# ==============================================================================

@dataclass
class IntegerLiteral(Expression):
  """
  Represents an integer literal (e.g., 42, 100).
  """
  value: str = ""


@dataclass
class FloatLiteral(Expression):
  """
  Represents a floating-point literal (e.g., 3.14, 9.11e-31).
  """
  value: str = ""


@dataclass
class StringLiteral(Expression):
  """
  Represents a double-quoted string literal.
  """
  value: str = ""


@dataclass
class CharacterLiteral(Expression):
  """
  Represents a character literal (e.g., 'a').
  """
  value: str = ""


@dataclass
class BooleanLiteral(Expression):
  """
  Represents a boolean literal (true or false).
  """
  value: str = ""


@dataclass
class ArrayLiteral(Expression):
  """
  Represents an array literal (e.g. [1, 2, 3]).
  """
  elements: list[Expression] = field(default_factory=list)


# ==============================================================================
# 3. Identifiers and Types
# ==============================================================================

@dataclass
class Identifier(Expression):
  """
  Represents an identifier (e.g., variable or function name).
  """
  name: str = ""


@dataclass
class TypeNode(Expression):
  """
  Represents a type annotation or type expression.
  e.g., int, std.string, std.vector<int>.
  """
  name: str = ""
  type_arguments: list[TypeNode] = field(default_factory=list)
  is_ref: bool = False
  array_size: int | None = None


# ==============================================================================
# 4. Operator and Access Expressions
# ==============================================================================

@dataclass
class UnaryOperator(Expression):
  """
  Represents a unary operator expression.
  e.g., -x, ++x, x++, not x.
  """
  operator: str = ""
  operand: Expression = field(default_factory=Expression)
  is_prefix: bool = True


@dataclass
class BinaryOperator(Expression):
  """
  Represents a binary operator expression.
  e.g., x + y, a and b.
  """
  operator: str = ""
  left: Expression = field(default_factory=Expression)
  right: Expression = field(default_factory=Expression)


@dataclass
class MemberAccess(Expression):
  """
  Represents a member access expression (dot notation).
  e.g., object.member.
  """
  object: Expression = field(default_factory=Expression)
  member: Identifier = field(default_factory=Identifier)


@dataclass
class IndexExpression(Expression):
  """
  Represents an index/subscript expression (brackets).
  e.g., array[index].
  """
  object: Expression = field(default_factory=Expression)
  index: Expression = field(default_factory=Expression)


@dataclass
class CallExpression(Expression):
  """
  Represents a function or lambda call.
  is_lambda_call handles calls with '!' syntax (e.g. lambda!).
  """
  function: Expression = field(default_factory=Expression)
  arguments: list[Expression] = field(default_factory=list)
  is_lambda_call: bool = False


@dataclass
class GroupingExpression(Expression):
  """
  Represents a grouped expression enclosed in parentheses.
  e.g., (expression).
  """
  expression: Expression = field(default_factory=Expression)


# ==============================================================================
# 5. Flow Control Expressions
# ==============================================================================

@dataclass
class Case(ASTNode):
  """
  Represents a case clause in a switch expression.
  """
  pattern: Expression = field(default_factory=Expression)
  body: Block = field(default_factory=Block)


@dataclass
class IfExpression(Expression):
  """
  Represents an if-then-else conditional expression.
  """
  condition: Expression | Statement = field(default_factory=Expression)
  then_body: Block = field(default_factory=Block)
  else_body: Block | None = None


@dataclass
class SwitchExpression(Expression):
  """
  Represents a switch expression.
  """
  value: Expression = field(default_factory=Expression)
  cases: list[Case] = field(default_factory=list)
  else_body: Block | None = None


@dataclass
class ForComprehension(Expression):
  """
  Represents a list/collection comprehension.
  """
  variable: Identifier = field(default_factory=Identifier)
  iterable: Expression = field(default_factory=Expression)
  body_expr: Expression = field(default_factory=Expression)


# ==============================================================================
# 6. Flow Control Statements
# ==============================================================================

@dataclass
class ForInStatement(Statement):
  """
  Represents a for-in loop over an iterable.
  """
  variable: Identifier = field(default_factory=Identifier)
  iterable: Expression = field(default_factory=Expression)
  body: Block = field(default_factory=Block)


@dataclass
class ForCStatement(Statement):
  """
  Represents a C-style for loop: for init; condition; increment.
  """
  init: Statement | Expression | None = None
  condition: Expression | None = None
  increment: Expression | None = None
  body: Block = field(default_factory=Block)


@dataclass
class ForInfiniteStatement(Statement):
  """
  Represents an infinite loop: for { body }.
  """
  body: Block = field(default_factory=Block)


@dataclass
class WhileStatement(Statement):
  """
  Represents a while loop.
  """
  condition: Expression = field(default_factory=Expression)
  body: Block = field(default_factory=Block)


@dataclass
class BreakStatement(Statement):
  """
  Represents a break statement.
  """
  pass


@dataclass
class ContinueStatement(Statement):
  """
  Represents a continue statement.
  """
  pass


@dataclass
class ReturnStatement(Statement):
  """
  Represents a return statement.
  """
  value: Expression | None = None


@dataclass
class PassStatement(Statement):
  """
  Represents a pass statement.
  """
  pass


@dataclass
class AssertStatement(Statement):
  """
  Represents an assert statement.
  """
  condition: Expression = field(default_factory=Expression)
  message: Expression | None = None


@dataclass
class RaiseStatement(Statement):
  """
  Represents a raise/throw statement.
  """
  value: Expression = field(default_factory=Expression)


# ==============================================================================
# 7. Assignment and Variable Declaration
# ==============================================================================

@dataclass
class AssignmentStatement(Statement):
  """
  Represents a variable assignment.
  """
  left: Expression = field(default_factory=Expression)
  right: Expression = field(default_factory=Expression)


@dataclass
class VariableDeclaration(Statement):
  """
  Represents a variable, constant, or reference declaration.
  """
  name: Identifier = field(default_factory=Identifier)
  type: TypeNode | None = None
  value: Expression = field(default_factory=Expression)
  kind: str = "var"  # "var", "const", or "ref"


# ==============================================================================
# 8. Functions and Lambdas
# ==============================================================================

@dataclass
class Parameter(ASTNode):
  """
  Represents a function or lambda parameter.
  """
  name: Identifier = field(default_factory=Identifier)
  type: TypeNode | None = None
  default: Expression | None = None


@dataclass
class FunctionDeclaration(Statement):
  """
  Represents a function declaration.
  """
  name: Identifier = field(default_factory=Identifier)
  params: list[Parameter] = field(default_factory=list)
  return_type: TypeNode | None = None
  body: Block = field(default_factory=Block)


@dataclass
class LambdaExpression(Expression):
  """
  Represents a lambda expression.
  """
  params: list[Parameter] = field(default_factory=list)
  return_type: TypeNode | None = None
  body: Block = field(default_factory=Block)


# ==============================================================================
# 9. Structures, Implementations and Enums
# ==============================================================================

@dataclass
class Field(ASTNode):
  """
  Represents a member field in a struct.
  """
  name: Identifier = field(default_factory=Identifier)
  type: TypeNode = field(default_factory=TypeNode)


@dataclass
class StructDeclaration(Statement):
  """
  Represents a struct declaration.
  """
  name: Identifier = field(default_factory=Identifier)
  fields: list[Field] = field(default_factory=list)


@dataclass
class ConstructorDeclaration(ASTNode):
  """
  Represents a constructor declaration within an impl block.
  """
  params: list[Parameter] = field(default_factory=list)
  body: Block = field(default_factory=Block)


@dataclass
class DestructorDeclaration(ASTNode):
  """
  Represents a destructor declaration within an impl block.
  """
  body: Block = field(default_factory=Block)


@dataclass
class MethodDeclaration(ASTNode):
  """
  Represents a method declaration within an impl block.
  """
  name: Identifier = field(default_factory=Identifier)
  params: list[Parameter] = field(default_factory=list)
  return_type: TypeNode | None = None
  body: Block = field(default_factory=Block)


@dataclass
class ImplDeclaration(Statement):
  """
  Represents an implementation block for a struct.
  """
  struct_name: Identifier = field(default_factory=Identifier)
  constructors: list[ConstructorDeclaration] = field(default_factory=list)
  destructor: DestructorDeclaration | None = None
  methods: list[MethodDeclaration] = field(default_factory=list)


@dataclass
class EnumDeclaration(Statement):
  """
  Represents an enum declaration.
  """
  name: Identifier = field(default_factory=Identifier)
  variants: list[Identifier] = field(default_factory=list)


# ==============================================================================
# 10. Modules, Imports and C++ Integration
# ==============================================================================

@dataclass
class ModuleDeclaration(Statement):
  """
  Represents a module declaration statement.
  """
  name: Identifier = field(default_factory=Identifier)


@dataclass
class ImportDeclaration(Statement):
  """
  Represents an import declaration.
  """
  source: str = ""
  names: list[Identifier] = field(default_factory=list)
  alias: Identifier | None = None


@dataclass
class UseCppDeclaration(Statement):
  """
  Represents a C++ header inclusion (use_cpp).
  """
  headers: list[str] = field(default_factory=list)


@dataclass
class UseCDeclaration(Statement):
  """
  Represents a C header inclusion (use_c).
  """
  headers: list[str] = field(default_factory=list)


@dataclass
class TemplateInstantiation(Expression):
  """
  Represents a template/generic instantiation in an expression context.
  e.g., std.make_unique<Particle>
  """
  element: Expression = field(default_factory=Expression)
  type_arguments: list[TypeNode] = field(default_factory=list)


# ==============================================================================
# 11. Root Program Node
# ==============================================================================

@dataclass
class Program(ASTNode):
  """
  Represents the root node of the AST containing all statements.
  """
  statements: list[Statement] = field(default_factory=list)
