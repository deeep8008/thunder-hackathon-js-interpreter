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
# Windows
python interpreter.py script.js
python interpreter.py "console.log('Hello, World!');"

# macOS/Linux
python3 interpreter.py script.js
python3 interpreter.py "console.log('Hello, World!');"

# Pipe from stdin (any OS)
echo "console.log(2 + 2);" | python interpreter.py
```

> **Note:** On Windows, `python3` may not resolve due to the Microsoft Store app execution alias. Use `python` instead.

---

## Test Cases

All 5 official test cases pass:

```bash
# TC1 — Odd/Even
python interpreter.py tc1.js   # → 7 is Odd

# TC2 — Triangle Pattern  
python interpreter.py tc2.js   # → * ** *** **** *****

# TC3 — Armstrong Number
python interpreter.py tc3.js   # → true / false

# TC4 — Array Reverse
python interpreter.py tc4.js   # → Original: 1,2,3,4,5 / Reversed: 5,4,3,2,1

# TC5 — String Palindrome
python interpreter.py tc5.js   # → racecar is a Palindrome
```

---

## Getting the Code (For Beginners)

If you've never used Git before, here's how to get this project running on your computer:

### Step 1: Install Python
Download and install Python from [python.org/downloads](https://python.org/downloads). During installation, make sure to check **"Add Python to PATH"**.

### Step 2: Download this repository
You don't need Git for this — just:
1. Click the green **`<> Code`** button at the top of this page
2. Click **Download ZIP**
3. Extract the ZIP file to a folder on your computer

### Step 3: Open a terminal in that folder
- **Windows**: Open the extracted folder, click the address bar, type `cmd`, and press Enter
- **macOS**: Right-click the folder → "New Terminal at Folder" (or open Terminal and `cd` into it)

### Step 4: Run the interpreter
```bash
# Windows
python interpreter.py tc1.js

# macOS/Linux
python3 interpreter.py tc1.js
```

You should see the output printed directly in the terminal.

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

## Design Notes

This interpreter uses a classic **Lexer → Parser → AST → Evaluator** pipeline instead of regex-based transpilation. Each piece of JS source is tokenized, parsed into a structured AST, then walked and evaluated directly — so nested expressions, closures, chained method calls, and destructuring all work correctly because the structure is understood, not pattern-matched.

---

*Built for Thunder Hackathon 2.0 | Author: Deepak (jinx)*