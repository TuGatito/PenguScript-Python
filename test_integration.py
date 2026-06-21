import sys
import os

def run_unit_tests() -> None:
    print("--- Running Component Unit Tests ---")
    
    # Run expressions.py tests
    print("\nRunning expressions unit tests...")
    import parser.expressions as expr_module
    expr_module.test_parser()
    
    # Run statements.py tests
    print("\nRunning statements unit tests...")
    import parser.statements as stmt_module
    stmt_module.test_parser()
    
    # Run declarations.py tests
    print("\nRunning declarations unit tests...")
    import parser.declarations as decl_module
    decl_module.test_parser()
    
    # Run parser.py tests
    print("\nRunning parser unit tests...")
    import parser.parser as parser_module
    parser_module.test_parser()
    
    print("\nAll component unit tests passed successfully!")

def run_integration_test() -> None:
    print("\n--- Running Integration Test on test_compiler.txt ---")
    
    from lexer.lexer import Lexer
    from parser.declarations import DeclarationParser
    from ast.ast_nodes import Program, TypeNode, IfExpression
    
    test_file = "test_compiler.txt"
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"Could not find integration test file: {test_file}")
        
    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    print(f"Tokenizing {test_file}...")
    lexer = Lexer(content, test_file)
    tokens = lexer.tokenize()
    
    print(f"Parsing {test_file}...")
    parser = DeclarationParser(tokens, test_file)
    ast = parser.parse_program()
    
    print("Verifying AST structure...")
    assert isinstance(ast, Program), "Expected parsed AST to be a Program node"
    assert len(ast.statements) > 0, "Expected AST to contain statements"
    
    # Verify the AST has ModuleDeclaration physics
    from ast.ast_nodes import ModuleDeclaration
    assert isinstance(ast.statements[0], ModuleDeclaration), "Expected first statement to be module physics"
    assert ast.statements[0].name.name == "physics", f"Expected module name physics, got {ast.statements[0].name.name}"
    
    # Let's perform validation of type is_ref attribute update
    # In test_compiler.txt:
    # calculate_energy = (p: ref Particle): std.expected<double, std.string_view> -> ...
    # We want to verify that `p` parameter type standard check yields `is_ref=True`.
    
    # Let's find calculate_energy function
    calculate_energy_func = None
    for stmt in ast.statements:
        # In declarations.py, global functions are parsed as VariableDeclaration (kind="const") or AssignmentStatement if implicit.
        # Let's find standard identifier name calculate_energy
        from ast.ast_nodes import VariableDeclaration, AssignmentStatement, FunctionDeclaration
        if isinstance(stmt, VariableDeclaration) and stmt.name.name == "calculate_energy":
            calculate_energy_func = stmt.value
            break
        elif isinstance(stmt, AssignmentStatement) and getattr(stmt.left, 'name', None) == "calculate_energy":
            calculate_energy_func = stmt.right
            break
        elif isinstance(stmt, FunctionDeclaration) and stmt.name.name == "calculate_energy":
            calculate_energy_func = stmt
            break
            
    assert calculate_energy_func is not None, "Could not find calculate_energy declaration in AST"
    
    # Verify type is_ref attribute is True for parameter 'p'
    param_p = calculate_energy_func.params[0]
    assert param_p.name.name == "p"
    assert isinstance(param_p.type, TypeNode)
    assert param_p.type.name == "Particle"
    assert param_p.type.is_ref is True, "Expected is_ref to be True for ref Particle type node"
    
    # Let's verify standard TypeNode for void return type does not have is_ref
    # logger = (msg: std.string_view): void => ...
    # Find logger function in main()
    main_func = None
    for stmt in ast.statements:
        if isinstance(stmt, VariableDeclaration) and stmt.name.name == "main":
            main_func = stmt.value
            break
        elif isinstance(stmt, AssignmentStatement) and getattr(stmt.left, 'name', None) == "main":
            main_func = stmt.right
            break
        elif isinstance(stmt, FunctionDeclaration) and stmt.name.name == "main":
            main_func = stmt
            break
            
    assert main_func is not None, "Could not find main function in AST"
    
    # Find logger declaration inside main function body
    logger_decl = None
    for stmt in main_func.body.statements:
        if isinstance(stmt, VariableDeclaration) and stmt.name.name == "logger":
            logger_decl = stmt.value
            break
            
    assert logger_decl is not None, "Could not find logger declaration in main"
    assert isinstance(logger_decl.return_type, TypeNode)
    assert logger_decl.return_type.name == "void"
    assert logger_decl.return_type.is_ref is False, "Expected is_ref to be False for void return type"
    
    # Let's verify that C++17 If-Init works:
    # if const energy_result = calculate_energy(ref p_ptr)
    # The condition should be a VariableDeclaration or Statement.
    print("Statements in main function:")
    for i, stmt in enumerate(main_func.body.statements):
        print(f"  {i}: {type(stmt).__name__}")
        
    if_init_stmt = None
    for stmt in main_func.body.statements:
        if isinstance(stmt, IfExpression):
            if isinstance(stmt.condition, VariableDeclaration) and stmt.condition.name.name == "energy_result":
                if_init_stmt = stmt
                break
                
    assert if_init_stmt is not None, "Could not find C++17 If-Init statement with energy_result condition in main"
    assert isinstance(if_init_stmt.condition, VariableDeclaration), "Expected If-Init condition to be a VariableDeclaration statement"
    
    # Verify array type representation: var raw_matrix: int[2] -> name: 'int', array_size: 2
    raw_matrix_decl = None
    for stmt in main_func.body.statements:
        if isinstance(stmt, VariableDeclaration) and stmt.name.name == "raw_matrix":
            raw_matrix_decl = stmt
            break
    assert raw_matrix_decl is not None, "Could not find raw_matrix declaration in main"
    assert isinstance(raw_matrix_decl.type, TypeNode)
    assert raw_matrix_decl.type.name == "int"
    assert raw_matrix_decl.type.array_size == 2, f"Expected array_size=2, got {raw_matrix_decl.type.array_size}"
    
    print("Integration test passed successfully!")

def main() -> None:
    try:
        run_unit_tests()
        run_integration_test()
        print("\n==================================================")
        print("SUCCESS: All unit and integration tests passed!")
        print("==================================================")
    except Exception as e:
        print(f"\nFAILURE: Test suite execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
