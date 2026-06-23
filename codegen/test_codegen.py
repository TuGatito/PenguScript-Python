from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

# System import path helper to resolve conflict with standard library 'ast' module
_current_dir = os.path.dirname(os.path.abspath(__file__))
_ast_path = os.path.abspath(os.path.join(_current_dir, "../ast/ast_nodes.py"))
if "ast.ast_nodes" not in sys.modules and os.path.exists(_ast_path):
    _spec = importlib.util.spec_from_file_location("ast.ast_nodes", _ast_path)
    _ast_nodes = importlib.util.module_from_spec(_spec)
    sys.modules["ast.ast_nodes"] = _ast_nodes
    _spec.loader.exec_module(_ast_nodes)

from ast.ast_nodes import *

from cpp_generator import CppGenerator
from cpp_helpers import (
    escape_cpp_char,
    escape_cpp_string,
    to_cpp_call,
    to_cpp_literal,
    to_cpp_type,
    to_cpp_var_decl,
)
from cpp_printer import CppPrinter
from cpp_visitor import CppVisitor

from semantic.symbol_table import Symbol


def test_cpp_printer() -> None:
    printer = CppPrinter()
    printer.write_line("int main() {")
    printer.indent()
    printer.write_line("int x = 42;")
    printer.dedent()
    printer.write_line("}")

    expected = "int main() {\n  int x = 42;\n}"
    assert printer.get_code() == expected, (
        f"Expected:\n{expected}\nGot:\n{printer.get_code()}"
    )
    print("OK: test_cpp_printer passed.")


def test_cpp_helpers_type() -> None:
    # Primitive type
    t1 = TypeNode(name="int")
    assert to_cpp_type(t1) == "int"

    # Dotted type
    t2 = TypeNode(name="std.vector", type_arguments=[TypeNode(name="int")])
    assert to_cpp_type(t2) == "std::vector<int>"

    # Reference
    t3 = TypeNode(name="float", is_ref=True)
    assert to_cpp_type(t3) == "float&"

    # Array type
    t4 = TypeNode(name="int", array_size=5)
    assert to_cpp_type(t4) == "int"

    # Complex nesting: const std.unique_ptr<int[3]>& -> unique_ptr of int ref
    t5 = TypeNode(
        name="std.unique_ptr",
        type_arguments=[TypeNode(name="int", array_size=3)],
        is_ref=True,
    )
    assert to_cpp_type(t5) == "std::unique_ptr<int>&"

    print("OK: test_cpp_helpers_type passed.")


def test_cpp_helpers_literals() -> None:
    # Integer
    assert to_cpp_literal(IntegerLiteral(value="123")) == "123"

    # Float
    assert to_cpp_literal(FloatLiteral(value="3.14f")) == "3.14f"

    # Boolean
    assert to_cpp_literal(BooleanLiteral(value="True")) == "true"
    assert to_cpp_literal(BooleanLiteral(value="False")) == "false"

    # Strings with escape characters
    assert escape_cpp_string('hello\n"world"') == 'hello\\n\\"world\\"'
    assert (
        to_cpp_literal(StringLiteral(value='hello\n"world"')) == '"hello\\n\\"world\\""'
    )

    # Characters with escape
    assert escape_cpp_char("'") == "'\\''"
    assert escape_cpp_char("\n") == "'\\n'"
    assert escape_cpp_char("a") == "'a'"
    assert to_cpp_literal(CharacterLiteral(value="\n")) == "'\\n'"

    print("OK: test_cpp_helpers_literals passed.")


def test_cpp_helpers_structure() -> None:
    # Call
    assert to_cpp_call("foo", ["1", "x"]) == "foo(1, x)"

    # Var decl
    assert to_cpp_var_decl("int", "x") == "int x;"
    assert (
        to_cpp_var_decl("float", "y", "3.14f", is_const=True)
        == "const float y = 3.14f;"
    )

    print("OK: test_cpp_helpers_structure passed.")


def test_cpp_visitor_expressions() -> None:
    visitor = CppVisitor()

    # 1. Identifiers & Primitives
    assert visitor.visit(Identifier(name="foo")) == "foo"

    # 2. Binary Operators (with precedence)
    x = Identifier(name="x")
    y = Identifier(name="y")
    z = Identifier(name="z")
    # x + y * z
    b1 = BinaryOperator(
        operator="+", left=x, right=BinaryOperator(operator="*", left=y, right=z)
    )
    assert visitor.visit(b1) == "x + y * z"
    # (x + y) * z
    b2 = BinaryOperator(
        operator="*", left=BinaryOperator(operator="+", left=x, right=y), right=z
    )
    assert visitor.visit(b2) == "(x + y) * z"

    # 3. Unary Operators
    # not x -> !(x)
    u1 = UnaryOperator(operator="not", operand=x)
    assert visitor.visit(u1) == "!(x)"
    # x++ -> x++
    u2 = UnaryOperator(operator="++", operand=x, is_prefix=False)
    assert visitor.visit(u2) == "x++"

    p_val = Identifier(name="p")
    p_val.symbol = Symbol(name="p", kind="variable", type=TypeNode(name="int"))
    p_ptr = Identifier(name="p_ptr")
    p_ptr.symbol = Symbol(
        name="p_ptr",
        kind="variable",
        type=TypeNode(name="std.unique_ptr", type_arguments=[TypeNode(name="int")]),
    )

    # 4. Member Access
    # p.x -> p.x
    m1 = MemberAccess(object=p_val, member=Identifier(name="x"))
    assert visitor.visit(m1) == "p.x"
    # p_ptr->x -> p_ptr->x
    m2 = MemberAccess(object=p_ptr, member=Identifier(name="x"))
    assert visitor.visit(m2) == "p_ptr->x"
    # this->x -> this->x
    this_node = Identifier(name="this")
    m3 = MemberAccess(object=this_node, member=Identifier(name="x"))
    assert visitor.visit(m3) == "this->x"

    # 5. Call Expression
    # foo(1, x) -> foo(1, x)
    c1 = CallExpression(
        function=Identifier(name="foo"), arguments=[IntegerLiteral(value="1"), x]
    )
    assert visitor.visit(c1) == "foo(1, x)"

    # expected_var.value! -> expected_var.value()
    expected_var = Identifier(name="expected_var")
    c2 = CallExpression(
        function=MemberAccess(object=expected_var, member=Identifier(name="value")),
        arguments=[],
        is_lambda_call=True,
    )
    assert visitor.visit(c2) == "expected_var.value()"

    # logger!("msg") -> logger("msg")
    c3 = CallExpression(
        function=CallExpression(
            function=Identifier(name="logger"), arguments=[], is_lambda_call=True
        ),
        arguments=[StringLiteral(value="msg")],
    )
    assert visitor.visit(c3) == 'logger("msg")'

    # 6. Lambda Expression
    # (msg: string_view): void -> ...
    lam = LambdaExpression(
        params=[
            Parameter(name=Identifier(name="msg"), type=TypeNode(name="string_view"))
        ],
        return_type=TypeNode(name="void"),
        body=Identifier(name="x"),
    )
    assert visitor.visit(lam) == "[&](string_view msg) -> void { return x; }"

    # 7. Array Literal
    arr = ArrayLiteral(elements=[IntegerLiteral(value="1"), IntegerLiteral(value="2")])
    assert visitor.visit(arr) == "{1, 2}"

    # 8. Switch Expression
    sw = SwitchExpression(
        value=x,
        cases=[
            Case(pattern=IntegerLiteral(value="1"), body=IntegerLiteral(value="10"))
        ],
        else_body=IntegerLiteral(value="0"),
    )
    expected_sw = "[&]() {\n  switch (x) {\n    case 1:\n      return 10;\n    default:\n      return 0;\n  }\n}()"
    assert visitor.visit(sw) == expected_sw

    print("OK: test_cpp_visitor_expressions passed.")


def test_cpp_visitor_statements() -> None:
    visitor = CppVisitor()

    # 1. VariableDeclaration
    v1 = VariableDeclaration(
        name=Identifier(name="x"),
        type=TypeNode(name="int"),
        kind="var",
        value=IntegerLiteral(value="42"),
    )
    assert visitor.visit(v1) == "int x = 42;"

    v2 = VariableDeclaration(
        name=Identifier(name="y"),
        type=None,
        kind="const",
        value=FloatLiteral(value="3.14f"),
    )
    assert visitor.visit(v2) == "const auto y = 3.14f;"

    v3 = VariableDeclaration(
        name=Identifier(name="z"),
        type=TypeNode(name="Particle"),
        kind="ref",
        value=Identifier(name="p"),
    )
    assert visitor.visit(v3) == "Particle& z = p;"

    v4 = VariableDeclaration(
        name=Identifier(name="x"),
        type=TypeNode(name="int", array_size=4),
        kind="var",
        value=ArrayLiteral(elements=[IntegerLiteral(value="1"), IntegerLiteral(value="2")]),
    )
    assert visitor.visit(v4) == "int x[4] = {1, 2};"

    # 2. Block & Return & Assignment
    stmt1 = VariableDeclaration(
        name=Identifier(name="x"),
        type=None,
        kind="var",
        value=IntegerLiteral(value="1"),
    )
    stmt2 = AssignmentStatement(
        left=Identifier(name="x"), right=IntegerLiteral(value="2")
    )
    stmt3 = ReturnStatement(value=Identifier(name="x"))
    block = Block(statements=[stmt1, stmt2, stmt3])
    expected_block = "{\n  auto x = 1;\n  x = 2;\n  return x;\n}"
    assert visitor.visit(block) == expected_block

    # 3. IfExpression (statement context)
    if_stmt = IfExpression(
        condition=BinaryOperator(
            operator=">", left=Identifier(name="x"), right=IntegerLiteral(value="0")
        ),
        then_body=Block(statements=[ReturnStatement(value=IntegerLiteral(value="1"))]),
        else_body=Block(statements=[ReturnStatement(value=IntegerLiteral(value="0"))]),
    )
    expected_if = "if (x > 0) {\n  return 1;\n} else {\n  return 0;\n}"
    assert visitor.visit(if_stmt) == expected_if

    # 4. If-Init (variable declaration condition)
    if_init_stmt = IfExpression(
        condition=VariableDeclaration(
            name=Identifier(name="res"),
            type=None,
            kind="const",
            value=Identifier(name="calc"),
        ),
        then_body=Block(statements=[ReturnStatement(value=Identifier(name="res"))]),
        else_body=None,
    )
    expected_if_init = "if (const auto res = calc) {\n  return res;\n}"
    assert visitor.visit(if_init_stmt) == expected_if_init

    # 5. ForInStatement (mutation detection)
    # Unmutated -> const auto&
    for_in_const = ForInStatement(
        variable=Identifier(name="item"),
        iterable=Identifier(name="items"),
        body=Block(
            statements=[
                ExpressionStatement(
                    expression=CallExpression(
                        function=Identifier(name="print"),
                        arguments=[Identifier(name="item")],
                    )
                )
            ]
        ),
    )
    expected_for_in_const = "for (const auto& item : items) {\n  print(item);\n}"
    assert visitor.visit(for_in_const) == expected_for_in_const

    # Mutated -> auto&
    for_in_mut = ForInStatement(
        variable=Identifier(name="item"),
        iterable=Identifier(name="items"),
        body=Block(
            statements=[
                AssignmentStatement(
                    left=Identifier(name="item"), right=IntegerLiteral(value="10")
                )
            ]
        ),
    )
    expected_for_in_mut = "for (auto& item : items) {\n  item = 10;\n}"
    assert visitor.visit(for_in_mut) == expected_for_in_mut

    # 6. ForCStatement
    for_c = ForCStatement(
        init=VariableDeclaration(
            name=Identifier(name="i"),
            type=TypeNode(name="int"),
            kind="var",
            value=IntegerLiteral(value="0"),
        ),
        condition=BinaryOperator(
            operator="<", left=Identifier(name="i"), right=IntegerLiteral(value="10")
        ),
        increment=UnaryOperator(
            operator="++", operand=Identifier(name="i"), is_prefix=False
        ),
        body=Block(statements=[PassStatement()]),
    )
    expected_for_c = "for (int i = 0; i < 10; i++) {\n  ;\n}"
    assert visitor.visit(for_c) == expected_for_c

    # 7. ForInfinite & While & Assert & Raise
    assert (
        visitor.visit(ForInfiniteStatement(body=Block(statements=[BreakStatement()])))
        == "for (;;) {\n  break;\n}"
    )
    assert (
        visitor.visit(
            WhileStatement(
                condition=BooleanLiteral(value="True"),
                body=Block(statements=[ContinueStatement()]),
            )
        )
        == "while (true) {\n  continue;\n}"
    )
    assert (
        visitor.visit(
            AssertStatement(
                condition=Identifier(name="cond"), message=StringLiteral(value="fail")
            )
        )
        == 'assert((cond) && "fail");'
    )
    assert visitor.visit(RaiseStatement(value=Identifier(name="err"))) == "throw err;"

    print("OK: test_cpp_visitor_statements passed.")


def test_cpp_visitor_and_generator() -> None:
    visitor = CppVisitor()
    prog = Program(statements=[])
    # Checks dispatch of Program node works and returns empty string as skeleton
    assert visitor.visit(prog) == ""

    # Generator writes generated code output
    generator = CppGenerator()
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "out.cpp")
        generator.generate(prog, out_file)
        assert os.path.exists(out_file)
        with open(out_file, "r") as f:
            content = f.read()
        assert content == ""

    print("OK: test_cpp_visitor_and_generator passed.")


def test_cpp_visitor_declarations() -> None:
    visitor = CppVisitor()
    visitor.struct_impls = {}

    # 1. Parameter with default
    p1 = Parameter(name=Identifier(name="x"), type=TypeNode(name="int"))
    assert visitor.visit_parameter(p1) == "int x"
    p2 = Parameter(
        name=Identifier(name="y"),
        type=TypeNode(name="float"),
        default=FloatLiteral(value="1.0f"),
    )
    assert visitor.visit_parameter(p2) == "float y = 1.0f"

    # 2. EnumDeclaration
    enum_decl = EnumDeclaration(
        name=Identifier(name="Color"),
        variants=[
            Identifier(name="Red"),
            Identifier(name="Green"),
            Identifier(name="Blue"),
        ],
    )
    expected_enum = "enum class Color {\n  Red,\n  Green,\n  Blue\n};"
    assert visitor.visit(enum_decl) == expected_enum

    # 3. StructDeclaration with ImplDeclaration
    struct_decl = StructDeclaration(
        name=Identifier(name="Particle"),
        fields=[
            Field(name=Identifier(name="x"), type=TypeNode(name="float")),
            Field(name=Identifier(name="y"), type=TypeNode(name="float")),
        ],
    )

    ctor = ConstructorDeclaration(
        params=[
            Parameter(name=Identifier(name="px"), type=TypeNode(name="float")),
            Parameter(name=Identifier(name="py"), type=TypeNode(name="float")),
        ],
        body=Block(
            statements=[
                AssignmentStatement(
                    left=MemberAccess(
                        object=Identifier(name="this"), member=Identifier(name="x")
                    ),
                    right=Identifier(name="px"),
                ),
                AssignmentStatement(
                    left=MemberAccess(
                        object=Identifier(name="this"), member=Identifier(name="y")
                    ),
                    right=Identifier(name="py"),
                ),
            ]
        ),
    )

    dtor = DestructorDeclaration(body=Block(statements=[]))

    method = MethodDeclaration(
        name=Identifier(name="move"),
        params=[Parameter(name=Identifier(name="dx"), type=TypeNode(name="float"))],
        return_type=TypeNode(name="void"),
        body=Block(
            statements=[
                AssignmentStatement(
                    left=MemberAccess(
                        object=Identifier(name="this"), member=Identifier(name="x")
                    ),
                    right=BinaryOperator(
                        operator="+",
                        left=MemberAccess(
                            object=Identifier(name="this"), member=Identifier(name="x")
                        ),
                        right=Identifier(name="dx"),
                    ),
                )
            ]
        ),
    )

    impl_decl = ImplDeclaration(
        struct_name=Identifier(name="Particle"),
        constructors=[ctor],
        destructor=dtor,
        methods=[method],
    )

    visitor.struct_impls["Particle"] = [impl_decl]

    expected_struct = (
        "struct Particle {\n"
        "  float x;\n"
        "  float y;\n"
        "  Particle(float px, float py) {\n"
        "    this->x = px;\n"
        "    this->y = py;\n"
        "  }\n"
        "  ~Particle() {\n"
        "\n"
        "  }\n"
        "  void move(float dx) {\n"
        "    this->x = this->x + dx;\n"
        "  }\n"
        "};"
    )
    assert visitor.visit(struct_decl) == expected_struct

    print("OK: test_cpp_visitor_declarations passed.")


def test_unity_builder() -> None:
    from codegen.unity_builder import UnityBuilder

    prog = Program(
        statements=[
            UseCppDeclaration(headers=["<iostream>", "<vector>"]),
            ModuleDeclaration(name=Identifier(name="physics")),
            EnumDeclaration(
                name=Identifier(name="SpaceType"), variants=[Identifier(name="Dim2D")]
            ),
            FunctionDeclaration(
                name=Identifier(name="main"),
                params=[],
                return_type=TypeNode(name="int"),
                body=Block(
                    statements=[ReturnStatement(value=IntegerLiteral(value="0"))]
                ),
            ),
        ]
    )

    builder = UnityBuilder()
    code = builder.build(prog)

    expected_code = (
        "#include <iostream>\n"
        "#include <vector>\n"
        "\n"
        "namespace physics {\n"
        "  enum class SpaceType {\n"
        "    Dim2D\n"
        "  };\n"
        "\n"
        "} // namespace physics\n"
        "\n"
        "int main() {\n"
        "  using namespace physics;\n"
        "  return 0;\n"
        "}"
    )
    assert code.strip() == expected_code.strip(), (
        f"Expected:\n{expected_code}\nGot:\n{code}"
    )

    # Test multiple programs merged
    prog1 = Program(
        statements=[
            UseCppDeclaration(headers=["<vector>"]),
            ModuleDeclaration(name=Identifier(name="physics")),
            EnumDeclaration(
                name=Identifier(name="SpaceType"), variants=[Identifier(name="Dim2D")]
            ),
        ]
    )
    prog2 = Program(
        statements=[
            UseCppDeclaration(headers=["<iostream>"]),
            ModuleDeclaration(name=Identifier(name="physics")),
            StructDeclaration(
                name=Identifier(name="Vector2"),
                fields=[Field(name=Identifier(name="x"), type=TypeNode(name="float"))],
            ),
            FunctionDeclaration(
                name=Identifier(name="main"),
                params=[],
                return_type=TypeNode(name="int"),
                body=Block(
                    statements=[ReturnStatement(value=IntegerLiteral(value="0"))]
                ),
            ),
        ]
    )

    merged_code = builder.build([prog1, prog2])
    expected_merged = (
        "#include <iostream>\n"
        "#include <vector>\n"
        "\n"
        "namespace physics {\n"
        "  enum class SpaceType {\n"
        "    Dim2D\n"
        "  };\n"
        "\n"
        "  struct Vector2 {\n"
        "    float x;\n"
        "  };\n"
        "\n"
        "} // namespace physics\n"
        "\n"
        "int main() {\n"
        "  using namespace physics;\n"
        "  return 0;\n"
        "}"
    )
    assert merged_code.strip() == expected_merged.strip(), (
        f"Expected:\n{expected_merged}\nGot:\n{merged_code}"
    )

    print("OK: test_unity_builder passed.")


def test_codegen_fixes_and_enhancements() -> None:
    visitor = CppVisitor()

    # 1. Ternary Operator Conversion
    x_id = Identifier(name="x")
    if_ternary = IfExpression(
        condition=BinaryOperator(
            operator=">", left=x_id, right=IntegerLiteral(value="0")
        ),
        then_body=Block(
            statements=[ExpressionStatement(expression=IntegerLiteral(value="1"))]
        ),
        else_body=Block(
            statements=[ExpressionStatement(expression=IntegerLiteral(value="0"))]
        ),
    )
    assert visitor.visit(if_ternary) == "((x > 0) ? (1) : (0))"

    # 2. Switch IIFE Return Statements (with Block wrapping a single expression/statement)
    sw = SwitchExpression(
        value=x_id,
        cases=[
            Case(
                pattern=IntegerLiteral(value="1"),
                body=Block(
                    statements=[
                        ExpressionStatement(expression=IntegerLiteral(value="10"))
                    ]
                ),
            )
        ],
        else_body=Block(
            statements=[ExpressionStatement(expression=IntegerLiteral(value="0"))]
        ),
    )
    expected_sw = "[&]() {\n  switch (x) {\n    case 1:\n      return 10;\n    default:\n      return 0;\n  }\n}()"
    assert visitor.visit(sw) == expected_sw

    # 3. ref Operator for Pointer/Smart Pointer vs Value
    p_ptr = Identifier(name="p_ptr")
    p_ptr.symbol = Symbol(
        name="p_ptr",
        kind="variable",
        type=TypeNode(name="std.unique_ptr", type_arguments=[TypeNode(name="int")]),
    )
    ref_ptr = UnaryOperator(operator="ref", operand=p_ptr)
    assert visitor.visit(ref_ptr) == "*(p_ptr)"

    p_val = Identifier(name="p_val")
    p_val.symbol = Symbol(name="p_val", kind="variable", type=TypeNode(name="int"))
    ref_val = UnaryOperator(operator="ref", operand=p_val)
    assert visitor.visit(ref_val) == "p_val"

    # 4. Scope Resolution :: on Namespace/Module/Enum Access
    # Namespace std.cout
    std_node = Identifier(name="std")
    m1 = MemberAccess(object=std_node, member=Identifier(name="cout"))
    assert visitor.visit(m1) == "std::cout"

    # Enum SpaceType.Dimension2D where SpaceType is resolved as an Enum
    space_type = Identifier(name="SpaceType")
    space_type.symbol = Symbol(name="SpaceType", kind="type")
    space_type.symbol.declaration = EnumDeclaration(
        name=Identifier(name="SpaceType"), variants=[]
    )
    m2 = MemberAccess(object=space_type, member=Identifier(name="Dimension2D"))
    assert visitor.visit(m2) == "SpaceType::Dimension2D"

    # Nested namespaces std.expected
    std_expected = MemberAccess(object=std_node, member=Identifier(name="expected"))
    assert visitor.visit(std_expected) == "std::expected"

    # 5. C-style for loop with assignment init
    for_c = ForCStatement(
        init=AssignmentStatement(
            left=Identifier(name="i"), right=IntegerLiteral(value="0")
        ),
        condition=BinaryOperator(
            operator="<", left=Identifier(name="i"), right=IntegerLiteral(value="10")
        ),
        increment=UnaryOperator(
            operator="++", operand=Identifier(name="i"), is_prefix=False
        ),
        body=Block(statements=[PassStatement()]),
    )
    expected_for_c = "for (auto i = 0; i < 10; i++) {\n  ;\n}"
    assert visitor.visit(for_c) == expected_for_c

    # 6. Lambda std::function Type Formatting
    t_func = TypeNode(
        name="std.function",
        type_arguments=[
            TypeNode(name="int"),
            TypeNode(name="float"),
            TypeNode(name="string"),
        ],
    )
    assert to_cpp_type(t_func) == "std::function<int(float, std::string)>"

    # 7. Auto-inclusion of <functional> and <cstdio>
    prog = Program(
        statements=[
            FunctionDeclaration(
                name=Identifier(name="main"),
                params=[],
                return_type=TypeNode(name="int"),
                body=Block(
                    statements=[
                        ExpressionStatement(
                            expression=CallExpression(
                                function=Identifier(name="printf"),
                                arguments=[StringLiteral(value="hello")],
                            )
                        ),
                        ExpressionStatement(
                            expression=LambdaExpression(
                                params=[],
                                return_type=TypeNode(name="void"),
                                body=Block(statements=[]),
                            )
                        ),
                    ]
                ),
            )
        ]
    )
    visitor.auto_collect_includes(prog)
    assert "<functional>" in visitor.includes
    assert "<cstdio>" in visitor.includes

    # 8. std.expected Type Qualifier Override
    expected_type = TypeNode(
        name="std.expected",
        type_arguments=[TypeNode(name="int"), TypeNode(name="string")],
    )
    var_decl = VariableDeclaration(
        name=Identifier(name="res"),
        type=expected_type,
        kind="const",
        value=CallExpression(function=Identifier(name="compute"), arguments=[]),
    )
    assert visitor.visit(var_decl) == "const auto res = compute();"

    var_decl_mutable = VariableDeclaration(
        name=Identifier(name="res"),
        type=expected_type,
        kind="var",
        value=CallExpression(function=Identifier(name="compute"), arguments=[]),
    )
    assert visitor.visit(var_decl_mutable) == "auto res = compute();"

    print("OK: test_codegen_fixes_and_enhancements passed.")


def run_all_tests() -> None:
    print("--- Running Codegen Phase 1-4 Unit Tests ---")
    test_cpp_printer()
    test_cpp_helpers_type()
    test_cpp_helpers_literals()
    test_cpp_helpers_structure()
    test_cpp_visitor_expressions()
    test_cpp_visitor_statements()
    test_cpp_visitor_and_generator()
    test_cpp_visitor_declarations()
    test_unity_builder()
    test_codegen_fixes_and_enhancements()
    print("All Codegen tests passed successfully!")


if __name__ == "__main__":
    run_all_tests()
