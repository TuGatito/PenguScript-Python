from lexer.lexer import Lexer
from parser.declarations import DeclarationParser
from semantic.semantic import SemanticAnalyzer
from codegen.cpp_generator import CppGenerator

def main() -> None:
    try:
        with open("test_compiler.pengu", "r", encoding="utf-8") as f:
            content = f.read()
            filename = "test_compiler.pengu"
    except FileNotFoundError:
        with open("test_compiler.txt", "r", encoding="utf-8") as f:
            content = f.read()
            filename = "test_compiler.txt"
            
    print("--- Running Lexer ---")
    lexer = Lexer(content, filename)
    tokens = lexer.tokenize()
    Lexer.pretty_print(tokens)
    
    print("\n--- Running Parser ---")
    parser = DeclarationParser(tokens, filename)
    ast = parser.parse_program()
    DeclarationParser.pretty_print(ast)
    
    print("\n--- Running Semantic Analysis ---")
    analyzer = SemanticAnalyzer()
    errors = analyzer.analyze(ast)
    print(SemanticAnalyzer.format_diagnostics(errors))
    
    has_errors = any(not err.is_warning for err in errors)
    if has_errors:
        print("\nCode generation skipped due to semantic errors.")
        return
        
    print("\n--- Running Code Generation ---")
    generator = CppGenerator()
    output_filename = filename.rsplit(".", 1)[0] + ".cc"
    generator.generate(ast, output_filename)
    print(f"C++ code generated successfully: {output_filename}")

if __name__ == "__main__":
    main()