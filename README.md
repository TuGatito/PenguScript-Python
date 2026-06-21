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

Current architecture components being migrated to the pipeline:

```
Source Code (.pengu) ──> [ Lexer ] ──> Token Stream ──> [ Parser ] ──> AST ──> [ Transpiler ] ──> Single C++ File (.cc)

```

### Current Status:

- [x] **Lexer (`lexer.py`)**: 100% complete, fully custom machine-state tokenizer. Handles single/multi-line tracking, Windows/Unix line-ending normalizations, and safely manages physical indentation scopes emitting virtual `INDENT`/`DEDENT` tokens.
- [x] **Tokens (`token.py`)**: 100% complete, featuring robust caret-pointing error context generation for Clang/Rust-like diagnostics.
- [x] **AST Tree Nodes (`ast_nodes.py`)**: In progress.
- [x] **Parser (`parser.py`)**: In progress.

---

## 📦 How to Explore (Development Version)

The current host compiler implementation is being written in Python using strict types to perfectly map the architectural structures required for the imminent self-hosting translation phase.

### Running the Tokenizer Test Bench:

1. Clone this repository.
2. Ensure you have Python 3.10+ installed.
3. Run the compiler entry point against a script:

```bash
python main.py compile path/to/your_file.pengu

```

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details. This grants permissions for commercial use, modification, distribution, patent use, and private use under the condition that license and copyright notices are preserved.
