## 🧱 Visión General del Pipeline de Compilación

```
Código Fuente (.pengu)
       ↓
  [Lexer] → Tokens
       ↓
  [Parser] → AST (con posición)
       ↓
  [Análisis Semántico] → Árbol anotado (tipos, símbolos)
       ↓
  [Generación de Código] → Código C++ (.cc/.h)
       ↓
  [Compilador C++] → Ejecutable / Biblioteca
```

Cada fase reporta errores con ubicación precisa, similar a Rust (con `error: ...` y contexto).

---

## 🗂️ Estructura de Archivos Propuesta

```
penguscript/
├── compiler/                         # Módulo principal del compilador
│   ├── __init__.py
│   ├── driver.py                     # Orquestador: lee archivos, invoca fases, maneja errores
│   ├── pipeline.py                   # Define el flujo de compilación (lex, parse, semantic, codegen)
│   ├── errors.py                     # Sistema de reporte de errores (colores, contexto)
│   └── config.py                     # Configuración (flags, directorios, optimizaciones)
│
├── lexer/                            # Ya existe
│   ├── __init__.py
│   ├── token.py
│   └── lexer.py
│
├── parser/                           # Ya existe
│   ├── __init__.py
│   ├── parser.py
│   ├── expressions.py
│   ├── statements.py
│   ├── declarations.py
│   └── utils.py                      # Ayudantes de parser
│
├── ast/                              # Ya existe
│   └── ast_nodes.py                  # Nodos del AST (con posición, indent, file)
│
├── semantic/                         # NUEVO: Análisis semántico
│   ├── __init__.py
│   ├── symbol_table.py               # Tabla de símbolos (scope, variables, funciones, tipos)
│   ├── type_checker.py               # Inferencia/verificación de tipos
│   ├── resolver.py                   # Resolución de nombres (referencias a variables/funciones)
│   └── builtins.py                   # Definiciones de tipos/operadores intrínsecos
│
├── codegen/                          # NUEVO: Generación de código C++
│   ├── __init__.py
│   ├── cpp_generator.py              # Clase principal que recorre el AST y produce strings
│   ├── cpp_helpers.py                # Utilidades para generar sintaxis C++ (incluye, namespaces, etc.)
│   ├── cpp_printer.py                # Impresión formateada de código C++ (indentación, líneas)
│   ├── unity_builder.py              # Construye el archivo único .cc (unity build)
│   └── header_writer.py              # Genera archivos .h para módulos (si se requiere)
│
├── driver/                           # NUEVO: Herramientas de línea de comandos y build
│   ├── __init__.py
│   ├── main.py                       # Punto de entrada (CLI)
│   ├── args.py                       # Parseo de argumentos (argparse)
│   ├── build_system.py               # Similar a cargo: compila dependencias, cache
│   └── watcher.py                    # (opcional) Para modo watch
│
├── tests/                            # Pruebas unitarias y de integración
│   ├── test_lexer.py
│   ├── test_parser.py
│   ├── test_semantic.py
│   └── test_codegen.py
│
├── penguscript                        # Ejecutable principal (binario)
└── README.md
```

---

## 🧩 Componentes Detallados

### 1. `driver/main.py` – CLI y Orchestrador

- Lee argumentos (`compile`, `build`, `run`, `test`, etc.).
- Inicializa el sistema de errores (`errors.py`).
- Llama a `pipeline.py` para cada archivo fuente.
- Gestiona la salida (archivos `.cc`, `.h`).
- Modo `watch` (recompilar al cambiar).

### 2. `compiler/errors.py` – Sistema de Errores (Rust-style)

- `Error` y `Diagnostic` con nivel (error, warning, note, help).
- Almacenan la ubicación (archivo, línea, columna, span).
- Formateo a color (ANSI) con el fragmento de código subrayado.
- Acumulación de errores (no detener en el primero).
- Similar a `cargo` con `error: ...` y `--> filename:line:col`.

### 3. `compiler/pipeline.py` – Flujo de Compilación

- Método `compile_file(file_path)`:
  1. Lexer → lista de tokens.
  2. Parser → AST (con posiciones).
  3. Análisis semántico (`semantic/`) → AST anotado con tipos y referencias.
  4. Generación de código (`codegen/`) → string de C++.
  5. Escribe archivos `.cc` y opcionalmente `.h`.
  6. Invoca al compilador C++ (g++/clang) para obtener ejecutable.

### 4. `semantic/` – Análisis Semántico

- **`symbol_table.py`**:  
  Gestiona scopes (global, funciones, bloques).  
  Almacena símbolos (variables, funciones, tipos, módulos).  
  Permite resolver nombres y verificar que existan.
- **`resolver.py`**:  
  Recorre el AST y asigna a cada nodo `Identifier` una referencia al símbolo correspondiente.  
  Detecta variables no declaradas, funciones no definidas, etc.
- **`type_checker.py`**:  
  Infiere y verifica tipos de expresiones (usando el sistema de tipos de C++ simplificado).  
  Detecta incompatibilidades (ej. asignar `int` a `std.string`).  
  Aprovecha la información de `TypeNode` del AST.
- **`builtins.py`**:  
  Define símbolos para tipos primitivos (`int`, `float`, etc.), operadores y funciones estándar (ej. `std.cout`, `std.make_shared`).  
  Esto permite que el análisis semántico conozca los tipos intrínsecos.

### 5. `codegen/` – Generación de C++

- **`cpp_generator.py`**:  
  Clase principal que implementa un **Visitor** para recorrer el AST.  
  Cada nodo (`Expression`, `Statement`, `Declaration`) tiene un método `generate(self, ctx)` que devuelve un string de C++.  
  Usa `cpp_helpers` para construir expresiones, llamadas, etc.
- **`cpp_helpers.py`**:  
  Funciones para generar sintaxis C++:
  - `make_include(header)` → `#include <header>` o `#include "header"`.
  - `make_namespace(name)` → `namespace name {` y `}`.
  - `make_unique_ptr(type)` → `std::make_unique<type>(...)`.
  - `make_lambda(params, body)` → `[&](...) { ... }`.
  - `make_if(cond, then_branch, else_branch)` → `if (cond) { ... } else { ... }`.
- **`cpp_printer.py`**:  
  Formatea el código C++ generado con indentación correcta, manejo de líneas, etc.
- **`unity_builder.py`**:  
  Construye un archivo `.cc` único que incluye todos los módulos y declara los forwards.  
  También genera el `main()` si existe.  
  Maneja las inclusiones de headers y la organización de namespaces.
- **`header_writer.py`**:  
  (Opcional) Genera archivos `.h` para módulos si se desea compilación separada.

### 6. `driver/build_system.py` – Sistema de Build (Cargo‑like)

- Detecta cambios en archivos fuente (por timestamp o hash).
- Compila solo lo necesario (incremental).
- Maneja dependencias entre módulos (imports).
- Permite configurar el compilador C++ y flags.
- Similar a `cargo` con `PenguScript.toml` o `penguscript.json`.

---

## 🚀 Flujo de Generación de C++ para un Archivo de Prueba

Tomemos el `test_compiler.txt` (módulo `physics`). El generador produciría:

```cpp
// main.cc (unity build)

// Incluye todos los headers necesarios (use_cpp, use_c)
#include <iostream>
#include <vector>
#include <string>
#include <expected>
#include <string_view>
#include <memory>

namespace physics {

// Enum class
enum class SpaceType {
  Dimension2D,
  Dimension3D
};

// Structs
struct Vector2 {
  float x;
  float y;
};

struct Particle {
  std::string name;
  Vector2 position;
  Vector2 velocity;
  double mass;
};

// Impl Particle
// Constructor, destructor, métodos...

// Funciones globales
std::expected<double, std::string_view> calculate_energy(Particle& p) { ... }

// main()
int main() {
  // Todo el código
  return 0;
}

} // namespace physics
```

---

## 🔍 Manejo de Errores en la Generación de Código

- **Errores semánticos** se emiten durante el análisis semántico (ej. tipo incorrecto, variable no declarada).
- **Errores de generación** (ej. no se puede generar código para un nodo) son raros; se reportan como errores internos.
- El sistema de errores debe ser **claro y accionable**:
  ```
  error[E0308]: mismatched types
    --> src/main.pengu:10:12
     |
  10 |   var x: int = "hello"
     |              ^^^^^^^^^ expected `int`, found `std.string`
  help: consider using `std.stoi` to convert the string to an integer
  ```

---

## 🔄 Auto‑compilación (Bootstrap)

Para que el compilador pueda compilarse a sí mismo:

1. Escribe el compilador en PenguScript (usando la sintaxis del lenguaje).
2. Compila ese código con una versión previa (por ejemplo, una implementación en Python o una versión estable).
3. El compilador generado será un ejecutable C++ que luego puede compilar su propio código fuente (generando un nuevo ejecutable).
4. Esto requiere que el compilador tenga **módulos estándar** (biblioteca base) y que el generador de C++ sea lo suficientemente robusto para manejar todas las características del lenguaje.

**Plan:**

- Implementar primero el generador en Python, asegurando que pueda compilar programas como `test_compiler.txt`.
- Escribir la biblioteca estándar (tipos, contenedores, algoritmos) en PenguScript.
- Una vez que el compilador pueda compilarse a sí mismo, usarlo para generar su propia versión mejorada.

---

## 🛠️ ¿Cómo Empezar?

Te sugiero este orden de implementación:

1. **Módulo de errores**: sistema básico de reporte.
2. **Análisis semántico (mínimo)**: solo resolución de nombres (sin type checking).
3. **Generador de C++ básico**:
   - Literales, variables, asignaciones.
   - Llamadas a funciones (sin sobrecarga).
   - Estructuras y enums (solo declaraciones).
4. **Soporte para bloques y control de flujo** (if, for, while).
5. **Funciones y lambdas**.
6. **Módulos y uso de C++** (includes, namespaces).
7. **Sistema de build** (similar a cargo) y pruebas con el archivo de prueba.
