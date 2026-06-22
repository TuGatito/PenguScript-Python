from lexer.lexer import Lexer
from parser.declarations import DeclarationParser
from semantic.semantic import SemanticAnalyzer

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

if __name__ == "__main__":
    main()