¡Perfecto! Con el AST definido y el lexer funcionando, el siguiente paso es construir el **parser**. Te daré una **hoja de ruta ordenada** para implementarlo con la ayuda de Gemini, comenzando por una **clase base robusta** que simplifique el desarrollo, y luego una secuencia de fases para ir completando las reglas gramaticales.

---

## 🧱 Estructura de Archivos Recomendada

Organiza el código en varios módulos para mantenerlo limpio:

```
penguscript/
├── lexer/
│   ├── __init__.py
│   ├── token.py          (ya lo tienes)
│   └── lexer.py          (ya lo tienes)
├── parser/
│   ├── __init__.py
│   ├── parser.py         ← Clase base Parser y lógica principal
│   ├── expressions.py    ← Parseo de expresiones (operadores, literales, llamadas)
│   ├── statements.py     ← Parseo de sentencias (asignaciones, bucles, condicionales)
│   ├── declarations.py   ← Parseo de declaraciones (funciones, structs, enums, módulos)
│   └── utils.py          ← Funciones auxiliares (si las hay)
├── ast/
│   └── ast_nodes.py      (ya lo tienes)
└── main.py               (punto de entrada para pruebas)
```

---

## 🧬 Clase Base `Parser`

Te sugiero una clase base que gestione el flujo de tokens, la posición actual, y provea métodos de utilidad para consumir y verificar tokens. También incluirá el manejo de errores.

**Atributos esenciales:**

- `self.tokens: list[Token]` – lista de tokens del lexer.
- `self.pos: int` – índice actual.
- `self.current_token: Token` – token actual (cacheado para acceso rápido).
- `self.file: str` – nombre del archivo (para errores).

**Métodos fundamentales:**

- `peek()` → Token (siguiente sin consumir).
- `peek_ahead(n)` → Token a n posiciones.
- `consume()` → avanza y devuelve el token anterior.
- `expect(type: TokenType, error_msg: str)` → consume y verifica que sea del tipo esperado; si no, lanza error.
- `match(type: TokenType)` → devuelve `True` si el actual es de ese tipo, y lo consume; si no, no avanza.
- `advance_if(type)` → igual que `match` pero sin devolver booleano (útil para opcionales).
- `error(msg: str)` → lanza una excepción con mensaje y ubicación actual.

**Además, para manejar la precedencia de operadores:**

- `parse_expression(min_precedence=0)` → método que implementa el algoritmo Pratt (top-down operator precedence) para manejar todos los operadores binarios y unarios.

**Consejo:** Mantén la clase base lo más genérica posible y delega el parseo de cada categoría a métodos específicos (`parse_statement`, `parse_expression`, `parse_declaration`), que serán implementados en los módulos correspondientes.

---

## 🗺️ Orden de Implementación (Fases)

Sigue este orden para que Gemini pueda construir el parser de forma incremental y testeable.

### ✅ Fase 0 – Infraestructura

- Crear `parser.py` con la clase base `Parser`.
- Implementar los métodos básicos: `peek`, `consume`, `expect`, `match`, `error`.
- Añadir el método `parse_program()` que será el punto de entrada y que devolverá un nodo `Program`.
- Configurar el manejo de la indentación (los tokens `INDENT`/`DEDENT` ya están en el flujo; el parser deberá usarlos para delimitar bloques).

### ✅ Fase 1 – Expresiones Primarias

Implementar el parseo de:

- Literales: `parse_integer`, `parse_float`, `parse_string`, `parse_boolean`, `parse_character`.
- Identificadores: `parse_identifier`.
- Agrupación: `parse_grouped_expression` (paréntesis).
- `parse_primary_expression` que detecta el tipo de token y llama al correspondiente.

### ✅ Fase 2 – Operadores (Precedencia)

- Implementar `parse_expression(min_precedence)` con la tabla de precedencias para:
  - Unarios: `not`, `-`, `+`, `++`, `--` (prefijo y sufijo).
  - Binarios: `*`, `/`, `+`, `-`, `<<`, `>>`, `<`, `<=`, `>`, `>=`, `==`, `!=`, `and`, `or`.
  - Asignación: `=`, aunque normalmente es una sentencia, también puede aparecer en inicializaciones.
- Soporte para `MemberAccess` (punto) y `IndexExpression` (corchetes) con la precedencia adecuada (mayor que todos).

### ✅ Fase 3 – Llamadas a Funciones y Lambdas

- `parse_call_expression` (reconocer `!` para lambdas).
- `parse_lambda` (flecha doble `=>`).

### ✅ Fase 4 – Sentencias Básicas

- `parse_block` (usa INDENT/DEDENT para delimitar).
- `parse_expression_statement` (cualquier expresión al inicio de línea).
- `parse_assignment` (identificador o miembro a la izquierda, `=` a la derecha).
- `parse_variable_declaration` (var/const/ref con o sin tipo).
- `parse_return`, `parse_break`, `parse_continue`, `parse_pass`.

### ✅ Fase 5 – Estructuras de Control

- `parse_if` (incluyendo `unless` y `then` en línea).
- `parse_switch` (con casos `when` y `else`).
- `parse_for` (tres variantes: `for x in y`, `for init; cond; inc`, `for` infinito).
- `parse_while`.

### ✅ Fase 6 – Funciones y Declaraciones de Ámbito Superior

- `parse_function_declaration` (nombre, parámetros, tipo de retorno, cuerpo).
- `parse_parameter_list` (con tipos y opcional valor por defecto).

### ✅ Fase 7 – Estructuras (`struct` e `impl`)

- `parse_struct` (nombre y campos).
- `parse_impl` (constructores, destructor, métodos).

### ✅ Fase 8 – Enums, Módulos e Importaciones

- `parse_enum`.
- `parse_module`.
- `parse_import`.
- `parse_use_cpp` / `parse_use_c`.

### ✅ Fase 9 – Programa Completo

- `parse_program` itera sobre todas las declaraciones top‑level y las agrupa en un `Program`.
- Manejar correctamente las declaraciones que pueden aparecer en cualquier orden (funciones, structs, enums, etc.) y el orden de las sentencias dentro de bloques.

---

## 🔧 Manejo de la Indentación en el Parser

El lexer ya emite `INDENT` y `DEDENT` tokens. En el parser, estos tokens se usan para controlar la entrada/salida de bloques.

- Al empezar un bloque (por ejemplo, después de `if`, `for`, `struct`), el parser debe consumir un `INDENT` y luego parsear el contenido del bloque hasta encontrar un `DEDENT` que cierre.
- Los `DEDENT` se emiten automáticamente por el lexer cuando la indentación disminuye. El parser debe consumirlos en el orden correcto.
- La función `parse_block` típicamente:
  1. Consume el `INDENT`.
  2. Mientras el token actual no sea `DEDENT` (ni `EOF`), parsea una sentencia.
  3. Al encontrar `DEDENT`, lo consume y retorna el bloque.
- En caso de `EOF` sin el `DEDENT` correspondiente, el lexer ya emite los `DEDENT` necesarios, así que no hay problema.

---

## 🧪 Pruebas Incrementales

Ve probando cada fase con el archivo `test_compiler.txt` (o partes de él). Puedes ir añadiendo casos de prueba unitarios pequeños para cada construcción.

- **Fase 0:** Verifica que `parse_program` retorne un `Program` vacío para un archivo sin código.
- **Fase 1:** Prueba solo literales e identificadores.
- **Fase 2:** Prueba expresiones matemáticas simples.
- **Fase 3:** Prueba llamadas a funciones.
- ... y así sucesivamente.

---

## 💡 Consejos para Gemini

Cuando le pidas a Gemini que genere código, dale siempre el contexto de la fase actual, los nodos AST involucrados y las reglas de precedencia concretas. Por ejemplo:

> "Implementa `parse_expression` con los operadores binarios de la tabla: `* /` (precedencia 10), `+ -` (9), `< <= > >=` (8), `== !=` (7), `and` (6), `or` (5). Además, soporta los unarios `not`, `-` y `++/--`."

Esto le permitirá generar código preciso y coherente con el resto del diseño.

---

Con esta hoja de ruta, tendrás un parser completo, bien estructurado y fácil de extender. ¡Manos a la obra!
