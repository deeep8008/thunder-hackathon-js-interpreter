#!/usr/bin/env python3
"""
THUNDER HACKATHON 2.0 — JavaScript Interpreter
Author: Deepak (jinxdeep.dev)
Language: Python 3.10+

Architecture:
  Source → Lexer → Token list → Parser → AST → Evaluator → stdout

Usage:
  python3 interpreter.py <file.js>
  python3 interpreter.py "let x = 1 + 2; console.log(x);"
  echo "console.log('hi')" | python3 interpreter.py
"""

import sys
import os

# Add directory to path so modules find each other
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer, LexerError
from parser import Parser, ParseError, JSUndefined
from evaluator import Evaluator, JSError


def run(source: str) -> int:
    """Lex → parse → evaluate. Returns exit code."""
    try:
        tokens = Lexer(source).tokenize()
    except LexerError as e:
        print(f"SyntaxError: {e}", file=sys.stderr)
        return 1

    try:
        ast = Parser(tokens).parse()
    except ParseError as e:
        print(f"ParseError: {e}", file=sys.stderr)
        return 1

    ev = Evaluator()
    try:
        ev.eval_program(ast)
    except JSError as e:
        val = e.value
        msg = ev._js_to_string(val) if hasattr(ev, '_js_to_string') else str(val)
        print(f"Uncaught: {msg}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"RuntimeError: {e}", file=sys.stderr)
        return 1

    # Print all collected output
    if ev.output:
        print('\n'.join(ev.output))
    return 0


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if os.path.isfile(arg):
            with open(arg, 'r', encoding='utf-8') as f:
                source = f.read()
        else:
            # Treat argument as inline JS code
            source = arg
    else:
        source = sys.stdin.read()

    if not source.strip():
        print("Error: no input provided", file=sys.stderr)
        sys.exit(1)

    sys.exit(run(source))


if __name__ == '__main__':
    main()
