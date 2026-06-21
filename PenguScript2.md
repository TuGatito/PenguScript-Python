# PenguScript Specification

Un lenguaje de programación estático, expresivo y de alto rendimiento que se transpila directamente a C++ moderno. Diseñado con la elegancia sintáctica de MoonScript y CoffeeScript, pero con el control, seguridad y velocidad de un lenguaje de sistemas.

---

## Filosofía de Diseño

1. **Cero Costos Ocultos:** No hay recolector de basura (Garbage Collector). La memoria se gestiona en tiempo de compilación mediante el sistema RAII y punteros inteligentes de C++.
2. **Sintaxis Limpia y Uniforme:** Se elimina la fatiga visual de C++ (llaves `{}`, punto y coma `;`, operadores `::` y `->`). El punto `.` unifica todos los accesos.
3. **Seguridad por Defecto:** Las variables no pueden existir sin un valor inicial. El tipado es estático y predecible.
4. **Arquitectura Pragmática (Unity Build):** Las importaciones estilo JavaScript permiten al transpilador recolectar dependencias y generar un único archivo `.cc` final, acelerando la compilación.

---

## 1. Comentarios

Sintaxis limpia basada en caracteres `#` heredada de CoffeeScript.

```coffee
# Esto es un comentario de una sola línea.

###
Esto es un comentario multilínea
o súper comentario. Ideal para documentar.
###

```

---

## 2. Tipos Primitivos e Inferencia

PenguScript utiliza los mismos tipos primitivos nativos de C++, garantizando compatibilidad binaria absoluta.

```c++
int, short int, long long int, char, bool, void, float, double, long double, signed, unsigned, unsigned char

```

### Regla de Cadenas de Texto (`const char*` vs `std::string`)

Para evitar asignaciones dinámicas de memoria en el _heap_ de forma oculta:

- Si no se especifica tipo, se infiere como un literal de C (`const char*`).
- Para usar cadenas dinámicas mutables, se debe declarar explícitamente `std::string`.

```coffee
using_cpp <string>

var texto_rapido = "Hola"               # Tipo inferido: const char*
var texto_mutable: std.string = "Mundo" # Tipo explícito: std.string

```

---

## 3. Variables y Mutabilidad

Todas las variables en PenguScript **deben inicializarse obligatoriamente** en su declaración. No existe la memoria sin inicializar.

```coffee
var x = 10              # Mutable (Infiere tipo en C++ con auto)
const y = 20            # Inmutable (Infiere tipo con const auto)
const b: int = 20       # Inmutable con tipo explícito
ref z: int = x          # Referencia nativa de C++ (int &z = x)

# Errores de sintaxis:
var k: int              # ¡ERROR! Requiere un valor inicial.

```

---

## 4. Control de Flujo: Condicionales

Los bloques condicionales utilizan indentación significativa. Pueden usarse como expresiones de asignación directa.

```coffee
if 1 > 0
  cout << "1 es mayor que 0" << endl
else if 2 > 1
  cout << "2 es mayor que 1" << endl
else
  cout << "Bloque else" << endl

```

### Sintaxis Corta e Inversa (`unless`)

```coffee
# Sintaxis en una sola línea
if tiene_monedas then printf("Tienes monedas") else printf("No tienes monedas")

# Evaluador inverso
unless es_alto and dinero >= 20
  printf("No puedes entrar")

```

```cpp
if (!(es_alto && dinero >= 20)) {
  printf("No puedes entrar");
}
```

### Asignaciones Condicionales (Operador Ternario)

```coffee
var x = if 1 > 0 then 2 else 3  # Transpila a: auto x = (1 > 0) ? 2 : 3;

```

### Modificadores Posteriores

Para sentencias simples y concisas, los bloques condicionales pueden aplicarse al final de la línea:

```coffee
printf("Hola Pengu") if nombre == "Pengu"

```

### Condicionales con Inicialización de Ámbito (C++17)

Se puede declarar una variable dentro del `if` cuyo ciclo de vida esté estrictamente ligado al cuerpo de la condición.

```coffee
if const usuario: bool = base_datos.existe("Pengu")
  cout << "Existe" << endl # 'usuario' solo es accesible aquí

```

```cpp
if (const bool user = database.user_exist("Pengu"); user) {
  cout << "Exists" << endl;
}
```

_Transpila a:_ `if (const bool usuario = base_datos.existe("Pengu"); usuario) { ... }`

---

## 5. Control de Flujo: Switch

El `switch` en PenguScript no permite el _fallthrough_ accidental; introduce un `break` automático en cada caso. Puede usarse como una expresión evaluable gracias al uso interno de funciones lambda autoejecutables (IIFE) en el transpilador.

```coffee
const dia = 3

switch dia
  when 0
    printf("Domingo")
  when 1
    printf("Lunes")
  else
    printf("Día no válido")

```

### Expresión Switch

```coffee
const estado = 1
const mensaje: std.string = switch estado
  when 1
    "Activo"
  else
    "Inactivo"

```

```cpp
const auto estado = 1;

const std::string mensaje = [&]() -> std::string {
  switch (estado) {
    case 1:
      return "Activo";
    default:
      return "Inactivo";
  }
}();
```

---

## 6. Bucles (Bucle Universal `for`)

PenguScript simplifica el flujo unificando todas las estructuras de repetición bajo la palabra clave `for`.

### for / in (Iteradores)

```coffee
for item in lista
  std.cout << item << std.endl # Transpila a: for (auto &item : lista)

```

```cpp
for (auto &item : lista) {
  std::cout << item << std::endl;
}
```

### Classic (Estilo C)

```coffee
for x = 0; x < 5; x++
  std.cout << x << endl

```

### Infinito (Equivalente a `while true`)

```coffee
for
  std.cout << "Bucle infinito" << endl

```

### Comprensión de Listas (List Comprehension)

El bucle `for` puede inicializar colecciones inmutables en una sola línea evaluable:

```coffee
use_cpp <vector>
use_cpp <string>

const nombres: std.vector<std.string> = for usuario in usuarios
  usuario.nombre

```

```cpp
#include <vector>
#include <string>

const std::vector<std::string> nombres = [&]() {
  std::vector<std::string> _temp;
  for (const auto& usuario : usuarios) {
    _temp.push_back(usuario.nombre);
  }
  return _temp;
}();
```

---

## 7. Arreglos Nativos

Fieles a la filosofía de "cero magia por detrás", los arreglos nativos de PenguScript mapean 1:1 con los arreglos estáticos de C++. Tienen tamaño fijo y requieren un tipo y valor inicial.

```coffee
using_c <string>

var numeros: int[] = [1, 2, 3, 4, 5]                  # Tamaño inferido por el inicializador
var nombres: std.string[4] = ["A", "B", "C", "D"]     # Tamaño explícito fijo

```

_Transpila a:_

```cpp
int numeros[] = {1, 2, 3, 4, 5};
std::string nombres[4] = {"A", "B", "C", "D"};

```

---

## 8. Estructuras y Comportamiento (`struct` & `impl`)

No existen las clases nativas. Los datos y el comportamiento se separan limpiamente emulando arquitecturas modernas como las de Go y Rust.

```coffee
struct Point
  x: int
  y: int

# Implementación de métodos asociados
impl Point
  # Constructor obligatorio
  constructor(new_x: int, new_y: int) ->
    this.x = new_x
    this.y = new_y

  # Destructor
  destructor() ->
    printf("Objeto liberado")

  # Método común
  add = (otra_x: int, otra_y: int): int ->
    return this.x + otra_x

```

```cpp
struct Point
{
  int x;
  int y;

  Point(int new_x, int new_y)
  {
    this.x = new_x;
    this.y = new_y;
  }

  ~Point()
  {
    printf("Objeto liberado");
  }

  int add(int otra_x, int otra_y)
  {
    return this.x + otra_x;
  }
};
```

---

## 9. Enums Modernos

Todos los `enum` de PenguScript compilan a un `enum class` de C++ para evitar la contaminación del espacio de nombres global.

```coffee
enum Color
  Red
  Green
  Blue

```

```cpp
enum class Color
{
  Red,
  Green,
  Blue
};
```

_Uso:_ `var mi_color = Color.Red` (Transpila a `Color::Red`).

---

## 10. Gestión de Memoria: Punteros Inteligentes Invisibles

Se prohíbe el uso de punteros crudos (`*`). La memoria dinámica se gestiona mediante abstracciones seguras de la librería estándar de C++. El punto `.` sustituye automáticamente al operador flecha `->`.

```coffee
use_cpp <memory>

var compartido = std.make_shared<Point>(10, 20)
var unico = std.make_unique<Point>(30, 40)

# Acceso uniforme con punto '.' sin importar que sea un puntero inteligente
compartido.x = 50

```

_Transpila a:_

```cpp
auto compartido = std::make_shared<Point>(10, 20);
auto unico = std::make_unique<Point>(30, 40);

compartido->x = 50;

```

---

## 11. Funciones y Lambdas

El transpilador realiza un análisis de doble pasada, permitiendo invocar funciones antes de su declaración física en el archivo (generando automáticamente los prototipos o _forward declarations_ en C++).

```coffee
main = (): int ->
  std.cout << add(5, 10) << std.endl
  return 0

add = (x: int, y: int): int ->
  return x + y

```

```cpp
int add(int x, int y);

int main()
{
  std::cout << add(5, 10) << std::endl;
  return 0;
}

int add(int x, int y)
{
  return x + y;
}
```

### Funciones Lambda

Definidas mediante el operador flecha doble `=>` y ejecutadas mediante el operador de exclamación `!`.

```coffee
main = (): int ->
  const saludar = () =>
    printf("Hola Mundo")

  saludar! # Ejecución de la lambda sin argumentos
  return 0

```

```cpp
int main()
{
  auto saludar = []() {
    printf("Hola Mundo");
  };

  saludar();
  return 0;
}
```

---

## 12. Módulos y Namespaces de Archivo único

Cada archivo representa un único módulo global exclusivo encapsulado en su propio namespace de C++. Las importaciones se manejan al estilo moderno de JavaScript para inyectar selectivamente sólo el código requerido en el archivo `.cc` consolidado final.

```coffee
# Archivo: src/printer.pengu
module printer

use_cpp <iostream>

say_hi = (): void ->
  std.cout << "¡Hola desde el módulo!" << std::endl

```

```cpp
#include <iostream>

namespace printer {
  void say_hi() {
    std::cout << "¡Hola desde el módulo!" << std::endl;
  }
}
```

### Importación y Uso (Punto Universal)

```coffee
# Archivo: main.pengu
from src.printer import say_hi

main = (): int ->
  printer.say_hi! # Acceso directo mediante el punto '.'
  return 0

```

Transpila en el archivo único final a:

```cpp
namespace printer {
  void say_hi() {
    std::cout << "¡Hola desde el módulo!" << std::endl;
  }
}

int main() {
  printer::say_hi();
  return 0;
}

```

---

## 13. Manejo de Errores Moderno (`std::expected`)

PenguScript rechaza las excepciones tradicionales debido a su alto costo en rendimiento y predictibilidad. Utiliza el estándar de C++23 `std::expected` para tratar los errores como flujos de datos normales que deben ser verificados de forma explícita.

```coffee
use_cpp <expected>
use_cpp <string_view>

# Retorna un entero (éxito) O una cadena (error)
dividir = (a: int, b: int): std.expected<int, std.string_view> ->
  if b == 0
    return std.unexpected("Error: División entre cero")
  else
    return a / b

main = (): int ->
  var resultado = dividir(10, 0)

  if not resultado.has_value!
    cout << "Ocurrió un fallo: " << resultado.error! << endl
    return 1

  cout << "Resultado exitoso: " << resultado.value! << endl
  return 0

```

Transpila en el archivo único final a:

```cpp
#include <iostream>
#include <expected>
#include <string_view>

std::expected<int, std::string_view> dividir(int a, int b)
{
  if (b == 0)
  {
    return std::unexpected("Error: División entre cero");
  }
  else
  {
    return a / b;
  }
}

int main()
{
  auto resultado = dividir(10, 0);

  if (!resultado.has_value())
  {
    std::cout << "Ocurrió un fallo: " << resultado.error() << std::endl;
    return 1;
  }

  std::cout << "Resultado exitoso: " << resultado.value() << std::endl;
  return 0;
}
```
