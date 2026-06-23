# PenguScript 🐧

PenguScript is a statically-typed, highly expressive, and ultra-performant programming language designed to transpile directly into modern, clean C++.

It merges the syntax elegance of modern scripting languages like MoonScript and CoffeeScript (indentation-based, no curly braces `{}` or semicolons `;`) with the absolute speed, deterministic memory safety, and low-level control of a systems language.

## 🚀 Key Features & Philosophy

1. **Zero Hidden Costs:** There is no Garbage Collector. Dynamic memory management is handled entirely at compile-time using C++ RAII and smart pointers (`std::unique_ptr` and `std::shared_ptr`).
2. **Unified Syntax (The Dot Operator):** Eliminates the visual noise of C++. You don't have to jump between `::` for namespaces, `->` for smart pointers, and `.` for structures. In PenguScript, the `.` operator unifies them all under the hood.
3. **Safety by Default:** Variables cannot be declared without an initial value. Uninitialized memory bugs are entirely eliminated at the syntax level.
4. **Unity Build Architecture:** Module imports act like JavaScript, collecting only the dependencies actually utilized. The transpiler aggregates these modules into a single, highly optimized `.cc` file (Single Translation Unit), delivering lightning-fast compilation times.
5. **Self-Hosting Objective:** Designed from scratch to eventually compile its own compiler, keeping the codebase pragmatic and free from massive external dependencies.

---

## 💻 Code Showcase

Here is a quick look at how clean PenguScript looks compared to the robust C++ code it automatically generates:

### 1. Variables and Type Inference

```coffee
var x = 10                                # Mutable, infers type (C++ auto)
const y = 20                              # Immutable, infers type (C++ const auto)
ref z: int = x                            # C++ Native Reference (int &z = x)
var msg = "Hello"                         # Safe read-only string literal (const char*)
var dynamic: std.string = "World"         # Explicit dynamic string allocation
```

### 2. Error Handling via C++23 `std::expected`

PenguScript natively rejects runtime exceptions for performance and predictability reasons. It treats errors as values using modern C++23 standards—without exposing any asterisks (`*`) or pointer syntax to the user:

```coffee
use_cpp <iostream>
use_cpp <expected>
use_cpp <string_view>

# Returns an integer on success OR a clean read-only string view on failure
divide = (a: int, b: int): std.expected<int, std.string_view> ->
  if b == 0
    return std.unexpected("Error: Division by zero")
  else
    return a / b

main = (): int ->
  var result = divide(10, 0)

  if not result.has_value!
    std.cout << "Failed: " << result.error! << std.endl
    return 1

  std.cout << "Success: " << result.value! << std.endl
  return 0
```

### 3. Structural Composition (`struct` & `impl`)

Object-Oriented complexity is replaced by a modern data-behavior separation model, matching paradigms found in Go and Rust:

```coffee
struct Point
  x: int
  y: int

impl Point
  constructor(new_x: int, new_y: int) ->
    this.x = new_x
    this.y = new_y

  destructor() ->
    printf("Point freed safely")

  add = (other_x: int, other_y: int): int ->
    return this.x + other_x
```

---

## 🛠 Compiler Architecture & Status

PenguScript utilizes a hand-crafted, high-performance **Recursive Descent Parser** architecture modeled after modern systems compilers like Zig, V, and Go.

The compiler is implemented in Python (for bootstrapping) and is designed to be **self-hosting** in the near future.

### Pipeline Overview

```
Source Code (.pengu)
       ↓
  [ Lexer ] → Tokens
       ↓
  [ Parser ] → AST (with source positions)
       ↓
  [ Semantic Analysis ] → Annotated AST (types, symbol resolution)
       ↓
  [ C++ Code Generator ] → Single .cc file (Unity Build)
       ↓
  [ C++ Compiler (g++/clang) ] → Executable / Library
```

### Current Implementation Status

| Component                             | Status  | Description                                                                                                                                                                                    |
| ------------------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Lexer** (`lexer/`)                  | ✅ 100% | Full machine-state tokenizer, handles indentation (INDENT/DEDENT), comments (`#` and `###`), Unicode line endings, and precise position tracking.                                              |
| **Tokens** (`token.py`)               | ✅ 100% | Rich token representation with location info, caret‑pointing error context, and file metadata.                                                                                                 |
| **AST Nodes** (`ast/ast_nodes.py`)    | ✅ 100% | Complete node hierarchy covering all language constructs (literals, operators, control flow, functions, structs, enums, modules, imports, and C++ integration).                                |
| **Parser** (`parser/`)                | ✅ 100% | Pratt‑style expression parser with precedence; fully implemented for all statements, declarations, lambdas, structs, enums, modules, and imports. Supports single‑line and block‑based syntax. |
| **Semantic Analysis** (`semantic/`)   | ✅ 100% | Complete semantic analysis pipeline with symbol table, name resolution, type checking, and shadowing detection. Supports if‑init, comprehensive type inference, and Rust‑style diagnostics.    |
| **C++ Code Generator** (`codegen/`)   | ✅ 100% | Generates clean, well‑formatted C++ code with proper RAII, namespaces, and Unity Build output.                                                                                                 |
| **Build System / Driver** (`driver/`) | ✅ 100% | Cargo‑like CLI with incremental builds, error reporting, and self‑hosting bootstrap.                                                                                                           |

### Error Reporting

The compiler features **Rust/Cargo‑style diagnostics** with coloured output, precise span highlighting, and contextual hints. Errors are collected and reported in a non‑blocking manner, allowing multiple issues to be surfaced in a single run.

Example:

```
error[E0308]: mismatched types
  --> src/main.pengu:10:12
   |
10 |   var x: int = "hello"
   |              ^^^^^^^^^ expected `int`, found `std.string`
   |
help: consider using `std.stoi` to convert the string to an integer
```

---

## 📦 How to Explore (Development Version)

The host compiler is written in Python 3.10+ with strict typing, making the codebase easy to extend and debug while we transition to self‑hosting.

### Quick Start

1. Clone the repository.
2. Install Python 3.10 or newer.
3. Run the compiler against a source file:

```bash
python main.py compile path/to/your_file.pengu
```

### Build Pipeline

- `compile` – generates a single `.cc` file and optionally compiles it with g++/clang.
- `build` – performs a full build with dependency resolution.
- `run` – compiles and executes the generated binary.
- `test` – runs the test suite (unit and integration).
- `watch` – watches for changes and recompiles automatically.

### Configuration

PenguScript uses a simple `PenguScript.toml` (or `penguscript.json`) for project settings, similar to `Cargo.toml`. Example:

```toml
[project]
name = "my_app"
version = "0.1.0"
edition = "2024"

[dependencies]
# future support for external PenguScript modules
```

---

## 🔄 Self‑Hosting Roadmap

We are actively working toward compiling the compiler itself in PenguScript. The plan is:

1. **Write the compiler in PenguScript** – using the language’s own features.
2. **Bootstrap** – compile this source with the existing Python implementation.
3. **Generate a C++ executable** from the PenguScript compiler.
4. **Use that executable** to recompile itself, achieving a fully self‑hosted toolchain.

This approach ensures that the language stays pragmatic, minimal, and free from external library bloat.

---

## 🧪 Test Suite

A comprehensive test suite is included to verify the correctness of each compiler phase:

- `test_lexer.py` – tokenizer correctness.
- `test_parser.py` – AST generation and syntax validation.
- `test_semantic.py` – symbol resolution and type checking.
- `test_codegen.py` – C++ output against expected patterns.

Run all tests with:

```bash
python -m unittest discover tests
```

---

## 📄 License

This project is licensed under the Apache License 2.0 – see the LICENSE file for details. This grants permissions for commercial use, modification, distribution, patent use, and private use under the condition that license and copyright notices are preserved.
