## 📚 Plan de la Biblioteca Estándar de PenguScript (stdlib)

### Capa 0: Fundamentos (`core`)

**Dependencias:** Ninguna (solo utiliza `use_cpp` sobre la biblioteca estándar de C++ y los intrínsecos del compilador).

| Módulo   | Archivo      | Contenido (funciones/tipos)                                                                                                             | Justificación                                       |
| :------- | :----------- | :-------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------- |
| **Core** | `core.pengu` | `assert(cond, msg)`, `panic(msg)`, `type_name(T)`, `sizeof(T)`, `id(T)`, `bool` operators (`and`, `or`, `not` ya están en el lenguaje). | Base para manejo de errores e introspección básica. |

---

### Capa 1: Interfaz con el Sistema Operativo (`sys`)

**Dependencias:** `core`

| Módulo      | Archivo             | Contenido (funciones/tipos)                                                                                                                                             | Justificación                                                     |
| :---------- | :------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------- |
| **OS**      | `sys/os.pengu`      | `args(): std.vector<std.string>` (argumentos de línea de comandos), `env(key): std.string?`, `exit(code: int)`, `platform(): std.string` ("windows", "linux", "macos"). | Necesario para cualquier programa que interactúe con el exterior. |
| **Process** | `sys/process.pengu` | `exec(cmd: std.string, args: std.vector<std.string>) -> std.expected<int, std.string>` (ejecuta un proceso y devuelve código de salida o error).                        | Para llamar a otros programas (ej. compilador C++).               |

---

### Capa 2: Sistema de Archivos y Rutas (`fs`)

**Dependencias:** `core`, `sys`

| Módulo          | Archivo               | Contenido (funciones/tipos)                                                                                                                                                                                                             | Justificación                                     |
| :-------------- | :-------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------ |
| **Path**        | `fs/path.pengu`       | `Path` (struct con métodos: `.join()`, `.parent()`, `.stem()`, `.extension()`, `.is_absolute()`, `.exists()`, `.is_file()`, `.is_dir()`).                                                                                               | Manipulación segura y multiplataforma de rutas.   |
| **File System** | `fs/filesystem.pengu` | `read_file(path: Path) -> std.expected<std.string, error>`, `write_file(path: Path, content: std.string)`, `read_dir(path: Path) -> std.vector<Path>`, `mkdir(path: Path)`, `remove(path: Path)`, `copy(src, dst)`, `rename(src, dst)`. | Operaciones esenciales de archivos y directorios. |

---

### Capa 3: Entrada/Salida y Streams (`io`)

**Dependencias:** `core`, `fs`, `sys`

| Módulo       | Archivo            | Contenido (funciones/tipos)                                                                                                               | Justificación                                                     |
| :----------- | :----------------- | :---------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------- |
| **File I/O** | `io/file.pengu`    | `File` (struct con métodos: `.open(path, mode)`, `.read_line()`, `.read_all()`, `.write(data)`, `.close()`). Abstracción sobre `fstream`. | Para lectura/escritura eficiente de archivos grandes.             |
| **Console**  | `io/console.pengu` | `print(...)`, `println(...)`, `input() -> std.string`, `error(msg)`, `print_err(...)`.                                                    | Interacción con el usuario. (Sobreescribe los globales `printf`). |

---

### Capa 4: Estructuras de Datos Avanzadas (`collections`)

**Dependencias:** `core`

| Módulo           | Archivo                    | Contenido (funciones/tipos)                                                                                                                                                                                                                                                                                                                                                                            | Justificación                                                        |
| :--------------- | :------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------- |
| **Map**          | `collections/map.pengu`    | `Map<K, V>` (wrappers sobre `std::unordered_map` y `std::map`). Métodos: `.insert()`, `.get()`, `.has_key()`, `.remove()`, `.keys()`, `.values()`, `.items()`.                                                                                                                                                                                                                                         | Diccionarios/claves-valor (fundamental para JSON y configuraciones). |
| **Set**          | `collections/set.pengu`    | `Set<T>` (wrapper sobre `std::unordered_set`). Métodos: `.add()`, `.has()`, `.remove()`.                                                                                                                                                                                                                                                                                                               | Conjuntos, útiles para validaciones.                                 |
| **Tuple**        | `collections/tuple.pengu`  | `Tuple<T1, T2, ...>` (o usar structs, pero una macro/generador de tipos sería ideal). Como no tenemos generics definidos por el usuario, usaremos `struct` para tuplas pequeñas (ej. `Pair<T, U>`). O bien, implementar un `Tuple` dinámico en C++ a través de `std::tuple` y exponerlo. **Decisión:** Crear una macro de generación de código o simplemente confiar en `struct` para casos concretos. | Retorno múltiple de valores.                                         |
| **String Utils** | `collections/string.pengu` | `split(s: std.string, delim: char) -> std.vector<std.string>`, `join(vec: std.vector<std.string>, delim: std.string)`, `trim()`, `to_lower()`, `to_upper()`, `contains()`, `starts_with()`, `ends_with()`.                                                                                                                                                                                             | Manipulación avanzada de cadenas (falta en C++ estándar).            |

---

### Capa 5: Tiempo (`time`)

**Dependencias:** `core`, `sys`

| Módulo   | Archivo           | Contenido (funciones/tipos)                                                                                                                           | Justificación                                     |
| :------- | :---------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------ |
| **Time** | `time/time.pengu` | `now() -> Timestamp`, `sleep(ms: int)`, `format(timestamp, layout: std.string) -> std.string`, `Duration` (struct con métodos `.sec()`, `.millis()`). | Necesario para logs, temporizadores y servidores. |

---

### Capa 6: Serialización (`json`, `toml`)

**Dependencias:** `core`, `collections`, `io`, `fs`

| Módulo   | Archivo           | Contenido (funciones/tipos)                                                                                                                                                                                   | Justificación                                        |
| :------- | :---------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :--------------------------------------------------- |
| **JSON** | `json/json.pengu` | `Value` (enum/union que representa null, bool, int, float, string, array, object). `parse(content: std.string) -> Value`, `stringify(value: Value) -> std.string`, `to_file(value, path)`, `from_file(path)`. | Intercambio de datos con APIs y configuración.       |
| **TOML** | `toml/toml.pengu` | `parse(content: std.string) -> Map<string, Value>`, `stringify(config)`.                                                                                                                                      | Formato de configuración humano-amigable (opcional). |

---

### Capa 7: Redes (`net`)

**Dependencias:** `core`, `sys`, `io`, `collections`

| Módulo     | Archivo            | Contenido (funciones/tipos)                                                                                                                                   | Justificación                         |
| :--------- | :----------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------ |
| **Socket** | `net/socket.pengu` | `Socket` (struct con métodos: `.connect(host, port)`, `.bind(port)`, `.listen()`, `.accept()`, `.send(data)`, `.receive(size)`, `.close()`). Soporte TCP/UDP. | Base para clientes y servidores.      |
| **DNS**    | `net/dns.pengu`    | `resolve(hostname: std.string) -> std.vector<std.string>` (resuelve IPv4/IPv6).                                                                               | Necesario para conectarse a dominios. |

---

### Capa 8: HTTP y APIs Web (`http`)

**Dependencias:** `core`, `collections`, `io`, `net`, `json`, `time`

| Módulo          | Archivo                | Contenido (funciones/tipos)                                                                                                      | Justificación                 |
| :-------------- | :--------------------- | :------------------------------------------------------------------------------------------------------------------------------- | :---------------------------- |
| **HTTP Client** | `http/client.pengu`    | `Request` (struct), `get(url, headers) -> Response`, `post(url, body, headers) -> Response`, `Response` (status, body, headers). | Consumir APIs REST.           |
| **HTTP Server** | `http/server.pengu`    | `Server` (struct con `.handle(route, handler)`), `Handler` (función que toma `Request` y devuelve `Response`).                   | Para construir servicios web. |
| **WebSocket**   | `http/websocket.pengu` | Cliente/servidor WebSocket (opcional).                                                                                           | Comunicación en tiempo real.  |

---

### Capa 9: Concurrencia (`async` o `threading`)

**Dependencias:** `core`, `sys`, `collections`

| Módulo        | Archivo                  | Contenido (funciones/tipos)                                                                           | Justificación                               |
| :------------ | :----------------------- | :---------------------------------------------------------------------------------------------------- | :------------------------------------------ |
| **Threading** | `threading/thread.pengu` | `Thread` (struct con `.spawn(fn)`, `.join()`, `.detach()`) sobre `std::thread`. `Mutex`, `LockGuard`. | Para paralelismo y servidores concurrentes. |
| **Async**     | `async/future.pengu`     | `async(fn) -> Future<T>`, `await(future)` (simulado con promesas de C++).                             | Para operaciones no bloqueantes (I/O).      |

---

### Capa 10: Utilidades de Desarrollo y Pruebas (`testing`)

**Dependencias:** `core`, `collections`, `io`, `time`

| Módulo          | Archivo              | Contenido (funciones/tipos)                                                                               | Justificación                                           |
| :-------------- | :------------------- | :-------------------------------------------------------------------------------------------------------- | :------------------------------------------------------ |
| **Test Runner** | `testing/test.pengu` | `test(name: std.string, fn: () -> void)`, `expect(actual, expected)`, `expect_throws(fn)`, `run_tests()`. | Marco de pruebas unitarias (como `unittest` de Python). |

---

## 🗺️ Orden de Implementación (Fases)

Para llegar a un lenguaje "independiente" (capaz de compilarse a sí mismo y escribir aplicaciones reales), recomiendo esta prioridad:

### Fase 1 – Core y Sys (Mínimo para compilar)

- `core.pengu` (assert, panic)
- `sys/os.pengu` (args, env, exit, platform)

**Objetivo:** Tener lo necesario para manejar argumentos y errores en el propio compilador.

### Fase 2 – Filesystem y IO

- `fs/path.pengu`
- `fs/filesystem.pengu`
- `io/file.pengu`
- `io/console.pengu`

**Objetivo:** Poder leer archivos de código fuente, escribir el `.cc` generado y mostrar mensajes.

### Fase 3 – Colecciones y Strings

- `collections/string.pengu`
- `collections/map.pengu`
- `collections/set.pengu`

**Objetivo:** Procesar configuraciones y manejar datos estructurados.

### Fase 4 – Serialización (JSON/TOML)

- `json/json.pengu`

**Objetivo:** Leer `penguscript.json` o archivos de configuración sin depender de Python.

### Fase 5 – Testing (para validar la stdlib)

- `testing/test.pengu`

**Objetivo:** Escribir pruebas unitarias para la propia stdlib en PenguScript.

### Fase 6 – Networking y HTTP (¡Lo divertido!)

- `net/socket.pengu`
- `http/client.pengu`
- `http/server.pengu`

**Objetivo:** Poder consumir APIs y servir aplicaciones web.

### Fase 7 – Concurrencia (Opcional pero valiosa)

- `threading/thread.pengu`

**Objetivo:** Servidores eficientes y procesamiento en paralelo.

---

## 📦 Ejemplo de Uso en PenguScript

```coffee
use_cpp <iostream>

# Importaciones de la stdlib
from stdlib.sys.os import args, platform
from stdlib.fs.filesystem import read_file, write_file
from stdlib.json.json import parse, stringify
from stdlib.http.client import get

main = (): int ->
  # Leer un archivo de configuración
  config_content = read_file("config.json")!
  config = parse(config_content)

  # Si hay una URL en la config, llamarla
  if config.has_key("api_url")
    url = config.get("api_url")!
    response = get(url)!
    json_response = parse(response.body)
    println("API Response: " + stringify(json_response))

  return 0
```
