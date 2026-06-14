"""
Lexer: Tokenizes raw JavaScript source code into a flat list of tokens.
"""

import re

# --- Token Types ---
TT = {
    # Literals
    'NUMBER': 'NUMBER', 'STRING': 'STRING', 'BOOL': 'BOOL',
    'NULL': 'NULL', 'UNDEFINED': 'UNDEFINED',
    # Identifiers & Keywords
    'IDENT': 'IDENT', 'KEYWORD': 'KEYWORD',
    # Operators
    'OP': 'OP',
    # Punctuation
    'LPAREN': '(', 'RPAREN': ')', 'LBRACE': '{', 'RBRACE': '}',
    'LBRACKET': '[', 'RBRACKET': ']',
    'SEMICOLON': ';', 'COMMA': ',', 'DOT': '.', 'COLON': ':', 'QUESTION': '?',
    # Special
    'ARROW': '=>', 'SPREAD': '...', 'NEWLINE': 'NEWLINE', 'EOF': 'EOF',
    'TEMPLATE': 'TEMPLATE',
}

KEYWORDS = {
    'let', 'const', 'var', 'function', 'return', 'if', 'else',
    'for', 'while', 'do', 'break', 'continue', 'new', 'delete',
    'typeof', 'instanceof', 'in', 'of', 'switch', 'case', 'default',
    'throw', 'try', 'catch', 'finally', 'class', 'extends', 'super',
    'import', 'export', 'true', 'false', 'null', 'undefined', 'void',
    'this',
}

class Token:
    __slots__ = ('type', 'value', 'line')
    def __init__(self, type_, value, line=0):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f'Token({self.type}, {self.value!r})'


class LexerError(Exception):
    pass


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.tokens: list[Token] = []

    def error(self, msg):
        raise LexerError(f"Line {self.line}: {msg}")

    def peek(self, offset=0):
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else ''

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
        return ch

    def match(self, expected):
        if self.pos < len(self.source) and self.source[self.pos] == expected:
            self.pos += 1
            return True
        return False

    def skip_whitespace_and_comments(self):
        while self.pos < len(self.source):
            ch = self.peek()
            if ch in ' \t\r\n':
                self.advance()
            elif ch == '/' and self.peek(1) == '/':
                while self.pos < len(self.source) and self.peek() != '\n':
                    self.advance()
            elif ch == '/' and self.peek(1) == '*':
                self.pos += 2
                while self.pos < len(self.source):
                    if self.peek() == '*' and self.peek(1) == '/':
                        self.pos += 2
                        break
                    self.advance()
            else:
                break

    def read_string(self, quote):
        self.pos += 1  # skip opening quote
        buf = []
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == '\\':
                self.pos += 1
                esc = self.source[self.pos] if self.pos < len(self.source) else ''
                ESC = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\',
                       "'": "'", '"': '"', '`': '`', '0': '\0'}
                buf.append(ESC.get(esc, esc))
                self.pos += 1
            elif ch == quote:
                self.pos += 1
                break
            else:
                if ch == '\n':
                    self.line += 1
                buf.append(ch)
                self.pos += 1
        return ''.join(buf)

    def read_template_literal(self):
        """Read a template literal (backtick string), return raw content."""
        self.pos += 1  # skip opening `
        buf = []
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == '`':
                self.pos += 1
                break
            elif ch == '\\':
                self.pos += 1
                esc = self.source[self.pos] if self.pos < len(self.source) else ''
                ESC = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '`': '`'}
                buf.append(ESC.get(esc, esc))
                self.pos += 1
            else:
                if ch == '\n':
                    self.line += 1
                buf.append(ch)
                self.pos += 1
        return ''.join(buf)

    def read_number(self):
        start = self.pos
        # Hex
        if self.peek() == '0' and self.peek(1) in 'xX':
            self.pos += 2
            while self.pos < len(self.source) and self.source[self.pos] in '0123456789abcdefABCDEF':
                self.pos += 1
            return int(self.source[start:self.pos], 16)
        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == '.'):
            self.pos += 1
        # exponent
        if self.pos < len(self.source) and self.source[self.pos] in 'eE':
            self.pos += 1
            if self.pos < len(self.source) and self.source[self.pos] in '+-':
                self.pos += 1
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                self.pos += 1
        raw = self.source[start:self.pos]
        return float(raw) if '.' in raw or 'e' in raw or 'E' in raw else int(raw)

    def tokenize(self) -> list[Token]:
        src = self.source
        length = len(src)

        while self.pos < length:
            self.skip_whitespace_and_comments()
            if self.pos >= length:
                break

            line = self.line
            ch = src[self.pos]

            # Numbers
            if ch.isdigit() or (ch == '.' and self.peek(1).isdigit()):
                val = self.read_number()
                self.tokens.append(Token(TT['NUMBER'], val, line))
                continue

            # Strings
            if ch in ('"', "'"):
                val = self.read_string(ch)
                self.tokens.append(Token(TT['STRING'], val, line))
                continue

            # Template literals
            if ch == '`':
                val = self.read_template_literal()
                self.tokens.append(Token(TT['TEMPLATE'], val, line))
                continue

            # Identifiers / Keywords
            if ch.isalpha() or ch == '_' or ch == '$':
                start = self.pos
                while self.pos < length and (src[self.pos].isalnum() or src[self.pos] in '_$'):
                    self.pos += 1
                word = src[start:self.pos]
                if word in ('true', 'false'):
                    self.tokens.append(Token(TT['BOOL'], word == 'true', line))
                elif word == 'null':
                    self.tokens.append(Token(TT['NULL'], None, line))
                elif word == 'undefined':
                    self.tokens.append(Token(TT['UNDEFINED'], None, line))
                elif word in KEYWORDS:
                    self.tokens.append(Token(TT['KEYWORD'], word, line))
                else:
                    self.tokens.append(Token(TT['IDENT'], word, line))
                continue

            # Spread / Rest ...
            if ch == '.' and self.peek(1) == '.' and self.peek(2) == '.':
                self.pos += 3
                self.tokens.append(Token(TT['SPREAD'], '...', line))
                continue

            # Dot
            if ch == '.':
                self.pos += 1
                self.tokens.append(Token(TT['DOT'], '.', line))
                continue

            # Arrow =>
            if ch == '=' and self.peek(1) == '>':
                self.pos += 2
                self.tokens.append(Token(TT['ARROW'], '=>', line))
                continue

            # Two/three-char operators
            two = src[self.pos:self.pos+2]
            three = src[self.pos:self.pos+3]

            if three in ('===', '!==', '**=', '>>>', '<<=', '>>='):
                self.pos += 3
                self.tokens.append(Token(TT['OP'], three, line))
                continue

            if two in ('==', '!=', '<=', '>=', '&&', '||', '??',
                       '++', '--', '+=', '-=', '*=', '/=', '%=',
                       '**', '<<', '>>', '&=', '|=', '^='):
                self.pos += 2
                self.tokens.append(Token(TT['OP'], two, line))
                continue

            # Single-char operators and punctuation
            SINGLE_OP = set('+-*/%<>=!&|^~')
            PUNCT = {
                '(': TT['LPAREN'], ')': TT['RPAREN'],
                '{': TT['LBRACE'], '}': TT['RBRACE'],
                '[': TT['LBRACKET'], ']': TT['RBRACKET'],
                ';': TT['SEMICOLON'], ',': TT['COMMA'],
                ':': TT['COLON'], '?': TT['QUESTION'],
            }

            if ch in PUNCT:
                self.pos += 1
                self.tokens.append(Token(PUNCT[ch], ch, line))
                continue

            if ch in SINGLE_OP:
                self.pos += 1
                self.tokens.append(Token(TT['OP'], ch, line))
                continue

            # Unknown — skip silently
            self.pos += 1

        self.tokens.append(Token(TT['EOF'], None, self.line))
        return self.tokens
