"""
AST Node definitions — one class per construct.
All nodes are plain dataclasses for speed.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


# ─── Statements ────────────────────────────────────────────────────────────────

@dataclass
class Program:
    body: list

@dataclass
class VarDecl:
    kind: str          # 'let' | 'const' | 'var'
    name: str
    init: Any          # expression node or None

@dataclass
class BlockStmt:
    body: list

@dataclass
class ExprStmt:
    expr: Any

@dataclass
class IfStmt:
    test: Any
    consequent: Any
    alternate: Any     # None | IfStmt | BlockStmt

@dataclass
class ForStmt:
    init: Any          # VarDecl | ExprStmt | None
    test: Any
    update: Any
    body: Any

@dataclass
class ForInStmt:
    kind: str          # 'in' | 'of'
    var: str
    iterable: Any
    body: Any

@dataclass
class WhileStmt:
    test: Any
    body: Any

@dataclass
class DoWhileStmt:
    body: Any
    test: Any

@dataclass
class ReturnStmt:
    value: Any         # expression or None

@dataclass
class BreakStmt:
    pass

@dataclass
class ContinueStmt:
    pass

@dataclass
class FuncDecl:
    name: str
    params: list       # list of param names (strings) or destructure patterns
    body: Any          # BlockStmt
    is_arrow: bool = False

@dataclass
class SwitchStmt:
    discriminant: Any
    cases: list        # list of SwitchCase

@dataclass
class SwitchCase:
    test: Any          # None means 'default'
    consequent: list

@dataclass
class TryStmt:
    block: Any
    handler: Any       # CatchClause or None
    finalizer: Any     # BlockStmt or None

@dataclass
class CatchClause:
    param: str
    body: Any

@dataclass
class ThrowStmt:
    argument: Any

@dataclass
class ClassDecl:
    name: str
    superclass: Any    # expression or None
    methods: list      # list of MethodDef

@dataclass
class MethodDef:
    name: str
    func: Any          # FuncDecl
    is_static: bool = False

# ─── Expressions ───────────────────────────────────────────────────────────────

@dataclass
class Literal:
    value: Any         # str | int | float | bool | None

@dataclass
class Identifier:
    name: str

@dataclass
class ArrayExpr:
    elements: list     # expression nodes (None = hole)

@dataclass
class ObjectExpr:
    props: list        # list of (key_str, value_expr)

@dataclass
class FuncExpr:
    name: Optional[str]
    params: list
    body: Any
    is_arrow: bool = False

@dataclass
class BinaryExpr:
    op: str
    left: Any
    right: Any

@dataclass
class UnaryExpr:
    op: str
    operand: Any
    prefix: bool = True

@dataclass
class LogicalExpr:
    op: str            # '&&' | '||' | '??'
    left: Any
    right: Any

@dataclass
class AssignExpr:
    op: str            # '=' | '+=' | '-=' etc.
    target: Any        # Identifier | MemberExpr
    value: Any

@dataclass
class UpdateExpr:
    op: str            # '++' | '--'
    operand: Any
    prefix: bool

@dataclass
class MemberExpr:
    obj: Any
    prop: Any          # Identifier (computed=False) or expression (computed=True)
    computed: bool     # arr[i] vs obj.prop

@dataclass
class CallExpr:
    callee: Any
    args: list

@dataclass
class NewExpr:
    callee: Any
    args: list

@dataclass
class ConditionalExpr:
    test: Any
    consequent: Any
    alternate: Any

@dataclass
class SpreadExpr:
    argument: Any

@dataclass
class TemplateLiteral:
    raw: str           # raw template string with ${...} parts

@dataclass
class SequenceExpr:
    exprs: list
