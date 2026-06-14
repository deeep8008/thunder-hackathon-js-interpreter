# Thunder Hackathon 2.0 — JavaScript Interpreter

A **from-scratch JavaScript interpreter written in Python 3**, built for Thunder Hackathon 2.0.

No Node.js. No subprocess calls. No transpilation hacks. Pure tree-walking interpreter.

---

## Architecture

```
Source Code
    │
    ▼
┌─────────┐
│  Lexer  │  → Token stream
└─────────┘
    │
    ▼
┌──────────┐
│  Parser  │  → Abstract Syntax Tree (AST)
└──────────┘
    │
    ▼
┌───────────┐
│ Evaluator │  → Output to stdout
└───────────┘
```

**Three clean modules, zero dependencies beyond Python stdlib.**

| Module | Role |
|---|---|
| `lexer.py` | Tokenizes JS source into a flat token list |
| `parser.py` | Recursive-descent parser → AST nodes |
| `evaluator.py` | Tree-walking evaluator with full environment chain |
| `ast_nodes.py` | Dataclass definitions for every AST node type |
| `interpreter.py` | Entry point — wires everything together |

---

## How to Run

**Requirements:** Python 3.10+

```bash
# Run a JS file
python3 interpreter.py script.js

# Run inline JS
python3 interpreter.py "console.log('Hello, World!');"

# Pipe from stdin
echo "console.log(2 + 2);" | python3 interpreter.py
```

---

## Test Cases

All 5 official test cases pass:

```bash
# TC1 — Odd/Even
python3 interpreter.py tc1.js   # → 7 is Odd

# TC2 — Triangle Pattern  
python3 interpreter.py tc2.js   # → * ** *** **** *****

# TC3 — Armstrong Number
python3 interpreter.py tc3.js   # → true / false

# TC4 — Array Reverse
python3 interpreter.py tc4.js   # → Original: 1,2,3,4,5 / Reversed: 5,4,3,2,1

# TC5 — String Palindrome
python3 interpreter.py tc5.js   # → racecar is a Palindrome
```

---

## Supported JavaScript Features

### Variables & Types
- `let`, `const`, `var` declarations
- Primitives: `number`, `string`, `boolean`, `null`, `undefined`
- Reference types: `object`, `array`, `function`
- Type coercion and conversion (`Number()`, `String()`, `Boolean()`, `parseInt()`, `parseFloat()`)

### Operators
- Arithmetic: `+`, `-`, `*`, `/`, `%`, `**`
- Comparison: `==`, `!=`, `===`, `!==`, `<`, `>`, `<=`, `>=`
- Logical: `&&`, `||`, `!`, `??` (nullish coalescing)
- Bitwise: `&`, `|`, `^`, `~`, `<<`, `>>`
- Assignment: `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `**=`, `&&=`, `||=`, `??=`
- Update: `++`, `--` (prefix and postfix)
- Ternary: `condition ? a : b`
- `typeof`, `instanceof`, `in`, `void`, `delete`

### Control Flow
- `if` / `else if` / `else`
- `for (init; test; update)`
- `for...of` / `for...in`
- `while` / `do...while`
- `switch` / `case` / `default` / `break`
- `break` / `continue`
- `try` / `catch` / `finally` / `throw`

### Functions
- Function declarations (hoisted)
- Function expressions
- Arrow functions (`=>`) — single param, multi-param, block body, expression body
- Default parameters
- Rest parameters (`...args`)
- Closures
- Callback functions
- Recursion

### Arrays
All built-in methods: `push`, `pop`, `shift`, `unshift`, `slice`, `splice`, `concat`, `join`, `indexOf`, `lastIndexOf`, `includes`, `reverse`, `sort`, `find`, `findIndex`, `filter`, `map`, `reduce`, `reduceRight`, `forEach`, `some`, `every`, `flat`, `flatMap`, `fill`, `entries`, `keys`, `values`

### Strings
All built-in methods: `length`, `charAt`, `charCodeAt`, `indexOf`, `lastIndexOf`, `includes`, `startsWith`, `endsWith`, `slice`, `substring`, `substr`, `split`, `replace`, `replaceAll`, `toUpperCase`, `toLowerCase`, `trim`, `trimStart`, `trimEnd`, `repeat`, `padStart`, `padEnd`, `concat`, `match`, `at`

### Objects
- Object literals with shorthand properties and method shorthand
- Computed property keys `{ [expr]: val }`
- Spread in objects `{ ...other }`
- Property get/set

### Spread & Destructuring
- Spread in arrays: `[...arr]`
- Spread in function calls: `fn(...args)`
- Array destructuring: `const [a, b, ...rest] = arr`
- Object destructuring: `const { x, y } = obj`

### Math Object
`Math.abs`, `ceil`, `floor`, `round`, `sqrt`, `pow`, `max`, `min`, `log`, `log2`, `log10`, `sin`, `cos`, `tan`, `random`, `trunc`, `sign`, `PI`, `E`, and more

### Template Literals
Backtick strings with `${expression}` interpolation (nested expressions supported)

### Classes
- `class` declarations
- `constructor`
- Instance methods
- `extends` (inheritance)
- `static` methods
- `new` keyword

### Other
- `JSON.stringify` / `JSON.parse`
- `Date` object (basic)
- Sequence expressions
- `typeof` safe on undeclared variables

---

## Why This Approach Wins

| Approach | Fragility |
|---|---|
| Regex transpile (JS→Python text→exec) | Breaks on chained calls, closures, complex expressions |
| Call Node.js via subprocess | Violates hackathon rules (own interpreter required) |
| **AST tree-walking interpreter** ✓ | Handles any valid JS by design |

The Lexer → Parser → Evaluator pipeline is how real language runtimes work. Each layer has a single responsibility, making the code readable, testable, and extensible.

---

*Built for Thunder Hackathon 2.0 | Author: Deepak (jinxdeep.dev)*
