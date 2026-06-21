from lexer.lexer import Lexer
from parser.declarations import DeclarationParser

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

if __name__ == "__main__":
    main()