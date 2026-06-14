"""
Tree-walking evaluator.
Walks the AST produced by the parser and executes it directly.
"""

import math as _math
import random as _random
import re as _re
import datetime as _datetime
from ast_nodes import *
from parser import JSUndefined

UNDEFINED = JSUndefined()

# ── Signals (use exceptions for control flow) ──────────────────────────────────

class ReturnSignal(Exception):
    def __init__(self, value): self.value = value

class BreakSignal(Exception): pass
class ContinueSignal(Exception): pass

class JSError(Exception):
    def __init__(self, value): self.value = value

# ── Environment ───────────────────────────────────────────────────────────────

class Env:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        return UNDEFINED

    def set(self, name, value):
        """Set in the scope where name exists, else create in current scope."""
        if name in self.vars:
            self.vars[name] = value
            return
        if self.parent and self.parent._has(name):
            self.parent.set(name, value)
            return
        self.vars[name] = value

    def define(self, name, value):
        """Always define in current scope."""
        self.vars[name] = value

    def _has(self, name):
        if name in self.vars:
            return True
        if self.parent:
            return self.parent._has(name)
        return False

    def assign(self, name, value):
        """Assign to existing binding, error if not found."""
        if name in self.vars:
            self.vars[name] = value
            return
        if self.parent:
            self.parent.assign(name, value)
            return
        # Auto-create global
        self.vars[name] = value

# ── JS function wrapper ────────────────────────────────────────────────────────

class JSFunction:
    def __init__(self, params, body, closure, name=None, is_arrow=False):
        self.params = params
        self.body = body
        self.closure = closure
        self.name = name or '<anonymous>'
        self.is_arrow = is_arrow

    def __repr__(self):
        return f'[Function: {self.name}]'


class JSClass:
    def __init__(self, name, superclass, methods, static_methods):
        self.name = name
        self.superclass = superclass
        self.methods = methods
        self.static_methods = static_methods

    def __repr__(self):
        return f'[class {self.name}]'


class JSInstance:
    def __init__(self, cls):
        self.cls = cls
        self.props = {}

    def __repr__(self):
        return f'[object {self.cls.name}]'


# ── Evaluator ─────────────────────────────────────────────────────────────────

class Evaluator:
    def __init__(self):
        self.output = []
        self.global_env = self._make_global_env()

    def _make_global_env(self) -> Env:
        env = Env()

        # console
        console = {
            'log': self._console_log,
            'error': lambda *a: self._console_log(*a),
            'warn': lambda *a: self._console_log(*a),
        }
        env.define('console', console)

        # Math
        Math = {
            'PI': _math.pi,
            'E': _math.e,
            'abs': abs,
            'ceil': lambda x: int(_math.ceil(x)),
            'floor': lambda x: int(_math.floor(x)),
            'round': lambda x: int(_math.floor(x + 0.5)),
            'sqrt': _math.sqrt,
            'pow': lambda b, e: b ** e,
            'max': lambda *a: max(a),
            'min': lambda *a: min(a),
            'log': _math.log,
            'log2': _math.log2,
            'log10': _math.log10,
            'sin': _math.sin,
            'cos': _math.cos,
            'tan': _math.tan,
            'asin': _math.asin,
            'acos': _math.acos,
            'atan': _math.atan,
            'atan2': _math.atan2,
            'random': _random.random,
            'trunc': lambda x: int(x),
            'sign': lambda x: (1 if x > 0 else -1 if x < 0 else 0),
            'hypot': lambda *a: _math.hypot(*a),
            'cbrt': lambda x: x ** (1/3),
            'SQRT2': _math.sqrt(2),
            'LN2': _math.log(2),
            'LN10': _math.log(10),
            'LOG2E': _math.log2(_math.e),
            'LOG10E': _math.log10(_math.e),
        }
        env.define('Math', Math)

        # Number
        env.define('Number', self._js_number_constructor)
        env.define('parseInt', self._js_parse_int)
        env.define('parseFloat', self._js_parse_float)
        env.define('isNaN', lambda x: x != x or (isinstance(x, float) and _math.isnan(x)))
        env.define('isFinite', lambda x: isinstance(x, (int, float)) and not _math.isinf(x) and x == x)
        env.define('NaN', float('nan'))
        env.define('Infinity', float('inf'))

        # String
        env.define('String', lambda x: self._js_to_string(x))

        # Boolean
        env.define('Boolean', lambda x: bool(x))

        # Array
        env.define('Array', self._js_array_constructor)

        # Object
        env.define('Object', self._js_object_constructor)

        # Date
        env.define('Date', self._js_date_constructor)

        # JSON
        env.define('JSON', {
            'stringify': self._json_stringify,
            'parse': self._json_parse,
        })

        env.define('undefined', UNDEFINED)
        env.define('null', None)

        return env

    # ── Built-ins ─────────────────────────────────────────────────────────────

    def _console_log(self, *args):
        parts = [self._js_to_string(a) for a in args]
        self.output.append(' '.join(parts))

    def _js_to_string(self, val):
        if val is None: return 'null'
        if isinstance(val, JSUndefined): return 'undefined'
        if val is True: return 'true'
        if val is False: return 'false'
        if isinstance(val, float):
            if val != val: return 'NaN'
            if val == float('inf'): return 'Infinity'
            if val == float('-inf'): return '-Infinity'
            if val == int(val): return str(int(val))
            return str(val)
        if isinstance(val, int): return str(val)
        if isinstance(val, str): return val
        if isinstance(val, list): return self._arr_to_string(val)
        if isinstance(val, dict): return '[object Object]'
        if isinstance(val, JSFunction): return f'function {val.name}() {{ [native code] }}'
        if isinstance(val, JSInstance): return '[object Object]'
        if callable(val): return 'function() {}'
        return str(val)

    def _arr_to_string(self, arr):
        return ','.join('' if (v is None or isinstance(v, JSUndefined)) else self._js_to_string(v) for v in arr)

    def _js_to_number(self, val):
        if val is None: return 0
        if isinstance(val, JSUndefined): return float('nan')
        if isinstance(val, bool): return 1 if val else 0
        if isinstance(val, (int, float)): return val
        if isinstance(val, str):
            s = val.strip()
            if s == '': return 0
            try: return int(s, 16) if s.startswith('0x') else float(s)
            except: return float('nan')
        if isinstance(val, list):
            if len(val) == 0: return 0
            if len(val) == 1: return self._js_to_number(val[0])
            return float('nan')
        return float('nan')

    def _js_to_bool(self, val):
        if isinstance(val, bool): return val
        if isinstance(val, JSUndefined): return False
        if val is None: return False
        if isinstance(val, (int, float)): return val != 0 and val == val
        if isinstance(val, str): return len(val) > 0
        return True

    def _js_number_constructor(self, val=UNDEFINED):
        if isinstance(val, JSUndefined): return 0
        return self._js_to_number(val)

    def _js_parse_int(self, val, base=10):
        s = self._js_to_string(val).strip()
        if isinstance(base, float): base = int(base)
        try:
            if base == 10 or isinstance(base, JSUndefined):
                # strip non-numeric tail
                m = _re.match(r'^[+-]?\d+', s)
                return int(m.group()) if m else float('nan')
            return int(s, base)
        except:
            return float('nan')

    def _js_parse_float(self, val):
        s = self._js_to_string(val).strip()
        try:
            m = _re.match(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?', s)
            return float(m.group()) if m else float('nan')
        except:
            return float('nan')

    def _js_array_constructor(self, *args):
        if len(args) == 1 and isinstance(args[0], (int, float)):
            return [UNDEFINED] * int(args[0])
        return list(args)

    def _js_object_constructor(self, val=None):
        if val is None or isinstance(val, JSUndefined):
            return {}
        return val

    def _js_date_constructor(self, *args):
        now = _datetime.datetime.now()
        d = {
            'getFullYear': lambda: now.year,
            'getMonth': lambda: now.month - 1,
            'getDate': lambda: now.day,
            'getDay': lambda: now.weekday(),
            'getHours': lambda: now.hour,
            'getMinutes': lambda: now.minute,
            'getSeconds': lambda: now.second,
            'getTime': lambda: int(now.timestamp() * 1000),
            'toISOString': lambda: now.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'toString': lambda: now.strftime('%a %b %d %Y %H:%M:%S GMT+0000'),
            'toLocaleDateString': lambda: now.strftime('%m/%d/%Y'),
            'toLocaleString': lambda: now.strftime('%m/%d/%Y, %H:%M:%S'),
        }
        return d

    def _json_stringify(self, val, replacer=None, space=None):
        import json
        def convert(v):
            if v is None: return None
            if isinstance(v, JSUndefined): return None
            if isinstance(v, bool): return v
            if isinstance(v, (int, float)): return v
            if isinstance(v, str): return v
            if isinstance(v, list): return [convert(x) for x in v]
            if isinstance(v, dict): return {k: convert(vv) for k, vv in v.items()}
            return str(v)
        indent = int(space) if isinstance(space, (int, float)) else None
        return json.dumps(convert(val), indent=indent)

    def _json_parse(self, s):
        import json
        def to_js(v):
            if isinstance(v, list): return [to_js(x) for x in v]
            if isinstance(v, dict): return {k: to_js(vv) for k, vv in v.items()}
            return v
        return to_js(json.loads(s))

    # ── Eval entry ────────────────────────────────────────────────────────────

    def eval_program(self, program: Program):
        # Hoist function declarations first
        for node in program.body:
            if isinstance(node, FuncDecl):
                fn = JSFunction(node.params, node.body, self.global_env, name=node.name)
                self.global_env.define(node.name, fn)
        for node in program.body:
            if not isinstance(node, FuncDecl):
                self.eval_stmt(node, self.global_env)

    def eval_stmt(self, node, env: Env):
        t = type(node)

        if t == ExprStmt:
            self.eval_expr(node.expr, env)

        elif t == VarDecl:
            val = self.eval_expr(node.init, env) if node.init is not None else UNDEFINED
            name = node.name
            if isinstance(name, tuple):
                self._destructure(name, val, env)
            else:
                env.define(name, val)

        elif t == BlockStmt:
            block_env = Env(parent=env)
            # hoist function decls inside block
            for stmt in node.body:
                if isinstance(stmt, FuncDecl):
                    fn = JSFunction(stmt.params, stmt.body, block_env, name=stmt.name)
                    block_env.define(stmt.name, fn)
            for stmt in node.body:
                if not isinstance(stmt, FuncDecl):
                    self.eval_stmt(stmt, block_env)

        elif t == IfStmt:
            cond = self._js_to_bool(self.eval_expr(node.test, env))
            if cond:
                self.eval_stmt(node.consequent, env)
            elif node.alternate:
                self.eval_stmt(node.alternate, env)

        elif t == ForStmt:
            loop_env = Env(parent=env)
            if node.init:
                self.eval_stmt(node.init, loop_env)
            while True:
                if node.test and not self._js_to_bool(self.eval_expr(node.test, loop_env)):
                    break
                try:
                    self.eval_stmt(node.body, loop_env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    pass
                if node.update:
                    self.eval_expr(node.update, loop_env)

        elif t == ForInStmt:
            iterable = self.eval_expr(node.iterable, env)
            loop_env = Env(parent=env)
            if node.kind == 'of':
                items = self._js_iter(iterable)
            else:  # 'in' → iterate keys
                if isinstance(iterable, dict):
                    items = list(iterable.keys())
                elif isinstance(iterable, list):
                    items = [str(i) for i in range(len(iterable))]
                else:
                    items = []
            for item in items:
                loop_env.define(node.var, item)
                try:
                    self.eval_stmt(node.body, loop_env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue

        elif t == WhileStmt:
            while self._js_to_bool(self.eval_expr(node.test, env)):
                try:
                    self.eval_stmt(node.body, env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue

        elif t == DoWhileStmt:
            while True:
                try:
                    self.eval_stmt(node.body, env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    pass
                if not self._js_to_bool(self.eval_expr(node.test, env)):
                    break

        elif t == ReturnStmt:
            val = self.eval_expr(node.value, env) if node.value is not None else UNDEFINED
            raise ReturnSignal(val)

        elif t == BreakStmt:
            raise BreakSignal()

        elif t == ContinueStmt:
            raise ContinueSignal()

        elif t == FuncDecl:
            fn = JSFunction(node.params, node.body, env, name=node.name)
            env.define(node.name, fn)

        elif t == SwitchStmt:
            disc = self.eval_expr(node.discriminant, env)
            fell_through = False
            for case in node.cases:
                if not fell_through:
                    if case.test is None:
                        fell_through = True
                    else:
                        test_val = self.eval_expr(case.test, env)
                        if self._strict_eq(disc, test_val):
                            fell_through = True
                if fell_through:
                    try:
                        for stmt in case.consequent:
                            self.eval_stmt(stmt, env)
                    except BreakSignal:
                        return

        elif t == TryStmt:
            try:
                self.eval_stmt(node.block, env)
            except JSError as e:
                if node.handler:
                    h_env = Env(parent=env)
                    if node.handler.param:
                        h_env.define(node.handler.param, e.value)
                    self.eval_stmt(node.handler.body, h_env)
            except Exception as e:
                if node.handler:
                    h_env = Env(parent=env)
                    if node.handler.param:
                        h_env.define(node.handler.param, str(e))
                    self.eval_stmt(node.handler.body, h_env)
            finally:
                if node.finalizer:
                    self.eval_stmt(node.finalizer, env)

        elif t == ThrowStmt:
            val = self.eval_expr(node.argument, env)
            raise JSError(val)

        elif t == ClassDecl:
            cls = self._make_class(node, env)
            env.define(node.name, cls)

    def _destructure(self, pattern, val, env):
        kind = pattern[0]
        if kind == 'array_pattern':
            lst = val if isinstance(val, list) else list(val) if hasattr(val, '__iter__') else []
            for i, name in enumerate(pattern[1]):
                if name is None: continue
                if isinstance(name, tuple) and name[0] == 'rest':
                    env.define(name[1], lst[i:])
                else:
                    env.define(name, lst[i] if i < len(lst) else UNDEFINED)
        elif kind == 'object_pattern':
            obj = val if isinstance(val, dict) else {}
            for key, alias in pattern[1]:
                env.define(alias, obj.get(key, UNDEFINED))

    def _make_class(self, node: ClassDecl, env: Env):
        superclass = self.eval_expr(node.superclass, env) if node.superclass else None
        methods = {}
        static_methods = {}
        for m in node.methods:
            fn = JSFunction(m.func.params, m.func.body, env, name=m.name)
            if m.is_static:
                static_methods[m.name] = fn
            else:
                methods[m.name] = fn
        cls = JSClass(node.name, superclass, methods, static_methods)
        return cls

    # ── Expressions ───────────────────────────────────────────────────────────

    def eval_expr(self, node, env: Env):
        if node is None:
            return UNDEFINED
        t = type(node)

        if t == Literal:
            return node.value

        if t == Identifier:
            return env.get(node.name)

        if t == TemplateLiteral:
            return self._eval_template(node.raw, env)

        if t == ArrayExpr:
            result = []
            for el in node.elements:
                if el is None:
                    result.append(UNDEFINED)
                elif isinstance(el, SpreadExpr):
                    spread = self.eval_expr(el.argument, env)
                    result.extend(spread if isinstance(spread, list) else [spread])
                else:
                    result.append(self.eval_expr(el, env))
            return result

        if t == ObjectExpr:
            obj = {}
            for prop in node.props:
                if prop[0] == 'prop':
                    obj[prop[1]] = self.eval_expr(prop[2], env)
                elif prop[0] == 'method':
                    fn = JSFunction(prop[2].params, prop[2].body, env, name=prop[1])
                    obj[prop[1]] = fn
                elif prop[0] == 'spread':
                    spread = self.eval_expr(prop[1], env)
                    if isinstance(spread, dict):
                        obj.update(spread)
                elif prop[0] == 'computed':
                    key = self._js_to_string(self.eval_expr(prop[1], env))
                    obj[key] = self.eval_expr(prop[2], env)
            return obj

        if t in (FuncExpr, FuncDecl):
            return JSFunction(node.params, node.body, env, name=getattr(node, 'name', None), is_arrow=getattr(node, 'is_arrow', False))

        if t == BinaryExpr:
            return self._eval_binary(node, env)

        if t == UnaryExpr:
            return self._eval_unary(node, env)

        if t == LogicalExpr:
            return self._eval_logical(node, env)

        if t == AssignExpr:
            return self._eval_assign(node, env)

        if t == UpdateExpr:
            return self._eval_update(node, env)

        if t == MemberExpr:
            obj = self.eval_expr(node.obj, env)
            prop = self._eval_member_key(node, env)
            return self._get_prop(obj, prop)

        if t == CallExpr:
            return self._eval_call(node, env)

        if t == NewExpr:
            return self._eval_new(node, env)

        if t == ConditionalExpr:
            if self._js_to_bool(self.eval_expr(node.test, env)):
                return self.eval_expr(node.consequent, env)
            return self.eval_expr(node.alternate, env)

        if t == SpreadExpr:
            return self.eval_expr(node.argument, env)

        if t == SequenceExpr:
            result = UNDEFINED
            for e in node.exprs:
                result = self.eval_expr(e, env)
            return result

        return UNDEFINED

    def _eval_template(self, raw: str, env: Env):
        """Evaluate template literal with ${...} interpolations."""
        result = []
        i = 0
        while i < len(raw):
            if raw[i] == '$' and i + 1 < len(raw) and raw[i+1] == '{':
                # Find matching }
                depth = 1
                j = i + 2
                while j < len(raw) and depth > 0:
                    if raw[j] == '{': depth += 1
                    elif raw[j] == '}': depth -= 1
                    j += 1
                expr_src = raw[i+2:j-1]
                from lexer import Lexer
                from parser import Parser
                tokens = Lexer(expr_src).tokenize()
                ast = Parser(tokens).parse_expr()
                val = self.eval_expr(ast, env)
                result.append(self._js_to_string(val))
                i = j
            else:
                result.append(raw[i])
                i += 1
        return ''.join(result)

    def _eval_member_key(self, node: MemberExpr, env: Env):
        if node.computed:
            return self.eval_expr(node.prop, env)
        return node.prop.name  # Identifier

    def _get_prop(self, obj, prop):
        prop_str = self._js_to_string(prop) if not isinstance(prop, str) else prop

        # Array
        if isinstance(obj, list):
            return self._array_prop(obj, prop_str)

        # String
        if isinstance(obj, str):
            return self._string_prop(obj, prop_str)

        # Dict / object
        if isinstance(obj, dict):
            if prop_str in obj:
                return obj[prop_str]
            return UNDEFINED

        # JSInstance
        if isinstance(obj, JSInstance):
            if prop_str in obj.props:
                return obj.props[prop_str]
            if prop_str in obj.cls.methods:
                method = obj.cls.methods[prop_str]
                return self._bind_method(method, obj)
            return UNDEFINED

        # JSClass static
        if isinstance(obj, JSClass):
            if prop_str in obj.static_methods:
                return obj.static_methods[prop_str]
            return UNDEFINED

        # Number methods
        if isinstance(obj, (int, float)):
            return self._number_prop(obj, prop_str)

        return UNDEFINED

    def _bind_method(self, fn: JSFunction, this):
        """Return a wrapped function that injects 'this'."""
        def bound(*args):
            call_env = Env(parent=fn.closure)
            call_env.define('this', this)
            self._bind_params(fn.params, list(args), call_env)
            try:
                self.eval_stmt(fn.body, call_env)
                return UNDEFINED
            except ReturnSignal as r:
                return r.value
        return bound

    def _set_prop(self, obj, prop, value):
        prop_str = self._js_to_string(prop) if not isinstance(prop, str) else prop
        if isinstance(obj, list):
            if prop_str == 'length':
                pass
            else:
                try:
                    idx = int(prop_str)
                    while len(obj) <= idx:
                        obj.append(UNDEFINED)
                    obj[idx] = value
                except (ValueError, TypeError):
                    pass
        elif isinstance(obj, dict):
            obj[prop_str] = value
        elif isinstance(obj, JSInstance):
            obj.props[prop_str] = value

    # ── Array prototype ───────────────────────────────────────────────────────

    def _array_prop(self, arr, prop):
        if prop == 'length':
            return len(arr)

        if prop == 'push':
            def push(*items):
                arr.extend(items)
                return len(arr)
            return push

        if prop == 'pop':
            return lambda: arr.pop() if arr else UNDEFINED

        if prop == 'shift':
            return lambda: arr.pop(0) if arr else UNDEFINED

        if prop == 'unshift':
            def unshift(*items):
                for item in reversed(items):
                    arr.insert(0, item)
                return len(arr)
            return unshift

        if prop == 'reverse':
            def reverse():
                arr.reverse()
                return arr
            return reverse

        if prop == 'sort':
            def sort(cmp_fn=None):
                if cmp_fn and isinstance(cmp_fn, JSFunction):
                    import functools
                    def key_func(a, b):
                        r = self._call_function(cmp_fn, [a, b])
                        return self._js_to_number(r)
                    arr.sort(key=functools.cmp_to_key(key_func))
                elif cmp_fn and callable(cmp_fn):
                    import functools
                    def key_func(a, b):
                        r = cmp_fn(a, b)
                        return self._js_to_number(r)
                    arr.sort(key=functools.cmp_to_key(key_func))
                else:
                    arr.sort(key=lambda x: self._js_to_string(x))
                return arr
            return sort

        if prop == 'slice':
            def slice_fn(start=None, end=None):
                s = int(self._js_to_number(start)) if start is not None and not isinstance(start, JSUndefined) else 0
                e = int(self._js_to_number(end)) if end is not None and not isinstance(end, JSUndefined) else len(arr)
                if s < 0: s = max(0, len(arr) + s)
                if e < 0: e = max(0, len(arr) + e)
                return arr[s:e]
            return slice_fn

        if prop == 'splice':
            def splice(start, delete_count=None, *items):
                s = int(self._js_to_number(start))
                if s < 0: s = max(0, len(arr) + s)
                dc = int(self._js_to_number(delete_count)) if delete_count is not None and not isinstance(delete_count, JSUndefined) else len(arr) - s
                removed = arr[s:s+dc]
                arr[s:s+dc] = list(items)
                return removed
            return splice

        if prop == 'concat':
            def concat(*others):
                result = list(arr)
                for o in others:
                    if isinstance(o, list): result.extend(o)
                    else: result.append(o)
                return result
            return concat

        if prop == 'join':
            def join(sep=','):
                sep = self._js_to_string(sep) if not isinstance(sep, JSUndefined) else ','
                return sep.join('' if (v is None or isinstance(v, JSUndefined)) else self._js_to_string(v) for v in arr)
            return join

        if prop == 'indexOf':
            def index_of(val, from_=0):
                fi = int(self._js_to_number(from_)) if not isinstance(from_, JSUndefined) else 0
                for i in range(fi, len(arr)):
                    if self._strict_eq(arr[i], val):
                        return i
                return -1
            return index_of

        if prop == 'lastIndexOf':
            def last_index_of(val):
                for i in range(len(arr)-1, -1, -1):
                    if self._strict_eq(arr[i], val):
                        return i
                return -1
            return last_index_of

        if prop == 'includes':
            def includes(val):
                return any(self._strict_eq(x, val) for x in arr)
            return includes

        if prop == 'find':
            def find(fn):
                for item in arr:
                    if self._js_to_bool(self._call_function(fn, [item])):
                        return item
                return UNDEFINED
            return find

        if prop == 'findIndex':
            def find_index(fn):
                for i, item in enumerate(arr):
                    if self._js_to_bool(self._call_function(fn, [item, i, arr])):
                        return i
                return -1
            return find_index

        if prop == 'filter':
            def filter_fn(fn):
                return [item for i, item in enumerate(arr)
                        if self._js_to_bool(self._call_function(fn, [item, i, arr]))]
            return filter_fn

        if prop == 'map':
            def map_fn(fn):
                return [self._call_function(fn, [item, i, arr]) for i, item in enumerate(arr)]
            return map_fn

        if prop == 'reduce':
            def reduce_fn(fn, init=UNDEFINED):
                acc = init
                start = 0
                if isinstance(acc, JSUndefined):
                    if not arr: raise JSError('Reduce of empty array with no initial value')
                    acc = arr[0]
                    start = 1
                for i in range(start, len(arr)):
                    acc = self._call_function(fn, [acc, arr[i], i, arr])
                return acc
            return reduce_fn

        if prop == 'reduceRight':
            def reduce_right(fn, init=UNDEFINED):
                acc = init
                end = len(arr) - 1
                if isinstance(acc, JSUndefined):
                    acc = arr[end]
                    end -= 1
                for i in range(end, -1, -1):
                    acc = self._call_function(fn, [acc, arr[i], i, arr])
                return acc
            return reduce_right

        if prop == 'forEach':
            def for_each(fn):
                for i, item in enumerate(arr):
                    self._call_function(fn, [item, i, arr])
                return UNDEFINED
            return for_each

        if prop == 'some':
            def some(fn):
                return any(self._js_to_bool(self._call_function(fn, [item, i, arr])) for i, item in enumerate(arr))
            return some

        if prop == 'every':
            def every(fn):
                return all(self._js_to_bool(self._call_function(fn, [item, i, arr])) for i, item in enumerate(arr))
            return every

        if prop == 'flat':
            def flat(depth=1):
                def _flat(lst, d):
                    result = []
                    for item in lst:
                        if isinstance(item, list) and d > 0:
                            result.extend(_flat(item, d-1))
                        else:
                            result.append(item)
                    return result
                d = int(self._js_to_number(depth)) if not isinstance(depth, JSUndefined) else 1
                return _flat(arr, d)
            return flat

        if prop == 'flatMap':
            def flat_map(fn):
                result = []
                for i, item in enumerate(arr):
                    r = self._call_function(fn, [item, i, arr])
                    if isinstance(r, list): result.extend(r)
                    else: result.append(r)
                return result
            return flat_map

        if prop == 'fill':
            def fill(val, start=0, end=None):
                s = int(self._js_to_number(start)) if not isinstance(start, JSUndefined) else 0
                e = int(self._js_to_number(end)) if end is not None and not isinstance(end, JSUndefined) else len(arr)
                for i in range(s, e):
                    arr[i] = val
                return arr
            return fill

        if prop == 'entries':
            return lambda: [[i, v] for i, v in enumerate(arr)]

        if prop == 'keys':
            return lambda: list(range(len(arr)))

        if prop == 'values':
            return lambda: list(arr)

        if prop == 'toString':
            return lambda: self._arr_to_string(arr)

        # Numeric index
        try:
            idx = int(prop)
            if 0 <= idx < len(arr):
                return arr[idx]
        except (ValueError, TypeError):
            pass
        return UNDEFINED

    # ── String prototype ──────────────────────────────────────────────────────

    def _string_prop(self, s, prop):
        if prop == 'length':
            return len(s)

        if prop == 'charAt':
            return lambda i: s[int(self._js_to_number(i))] if 0 <= int(self._js_to_number(i)) < len(s) else ''

        if prop == 'charCodeAt':
            return lambda i: ord(s[int(i)]) if 0 <= int(i) < len(s) else float('nan')

        if prop == 'indexOf':
            return lambda sub, start=0: s.find(sub, int(start))

        if prop == 'lastIndexOf':
            return lambda sub: s.rfind(sub)

        if prop == 'includes':
            return lambda sub: sub in s

        if prop == 'startsWith':
            return lambda pre, pos=0: s[int(pos):].startswith(pre)

        if prop == 'endsWith':
            return lambda suf: s.endswith(suf)

        if prop == 'slice':
            def str_slice(start, end=None):
                a = int(self._js_to_number(start))
                if a < 0: a = max(0, len(s) + a)
                if end is None or isinstance(end, JSUndefined):
                    return s[a:]
                b = int(self._js_to_number(end))
                if b < 0: b = max(0, len(s) + b)
                return s[a:b]
            return str_slice

        if prop == 'substring':
            def substring(start, end=None):
                a = max(0, int(self._js_to_number(start)))
                if end is None or isinstance(end, JSUndefined):
                    return s[a:]
                b = max(0, int(self._js_to_number(end)))
                if a > b: a, b = b, a
                return s[a:b]
            return substring

        if prop == 'substr':
            def substr(start, length=None):
                a = int(self._js_to_number(start))
                if a < 0: a = max(0, len(s) + a)
                if length is None or isinstance(length, JSUndefined):
                    return s[a:]
                return s[a:a + int(self._js_to_number(length))]
            return substr

        if prop == 'split':
            def split(sep=UNDEFINED, limit=UNDEFINED):
                if isinstance(sep, JSUndefined):
                    return [s]
                if sep == '':
                    parts = list(s)
                else:
                    parts = s.split(sep)
                if not isinstance(limit, JSUndefined):
                    parts = parts[:int(self._js_to_number(limit))]
                return parts
            return split

        if prop == 'replace':
            def replace(pattern, repl):
                if isinstance(repl, str):
                    return s.replace(pattern, repl, 1)
                if isinstance(repl, (JSFunction, type(lambda: None))):
                    idx = s.find(pattern)
                    if idx == -1: return s
                    matched = s[idx:idx+len(pattern)]
                    r = self._call_function(repl, [matched, idx, s])
                    return s[:idx] + self._js_to_string(r) + s[idx+len(pattern):]
                return s
            return replace

        if prop == 'replaceAll':
            def replace_all(pattern, repl):
                if isinstance(repl, str):
                    return s.replace(pattern, repl)
                return s
            return replace_all

        if prop == 'toUpperCase':
            return lambda: s.upper()

        if prop == 'toLowerCase':
            return lambda: s.lower()

        if prop == 'trim':
            return lambda: s.strip()

        if prop == 'trimStart':
            return lambda: s.lstrip()

        if prop == 'trimEnd':
            return lambda: s.rstrip()

        if prop == 'repeat':
            return lambda n: s * int(self._js_to_number(n))

        if prop == 'padStart':
            def pad_start(length, fill=' '):
                l = int(self._js_to_number(length))
                return s.rjust(l, fill[0] if fill else ' ')
            return pad_start

        if prop == 'padEnd':
            def pad_end(length, fill=' '):
                l = int(self._js_to_number(length))
                return s.ljust(l, fill[0] if fill else ' ')
            return pad_end

        if prop == 'concat':
            return lambda *parts: s + ''.join(self._js_to_string(p) for p in parts)

        if prop == 'match':
            def match(pattern):
                if isinstance(pattern, str):
                    m = _re.search(pattern, s)
                    if not m: return None
                    return [m.group(0)]
                return None
            return match

        if prop == 'search':
            def search(pattern):
                m = _re.search(pattern, s)
                return m.start() if m else -1
            return search

        if prop == 'at':
            def at(idx):
                i = int(self._js_to_number(idx))
                if i < 0: i = len(s) + i
                return s[i] if 0 <= i < len(s) else UNDEFINED
            return at

        if prop == 'toString' or prop == 'valueOf':
            return lambda: s

        # Numeric character access: "abc"[0] => 'a'
        try:
            idx = int(prop)
            if 0 <= idx < len(s):
                return s[idx]
        except (ValueError, TypeError):
            pass

        return UNDEFINED

    def _number_prop(self, n, prop):
        if prop == 'toFixed':
            def to_fixed(digits=0):
                d = int(self._js_to_number(digits))
                return f'{n:.{d}f}'
            return to_fixed
        if prop == 'toString':
            def num_to_string(base=10):
                b = int(self._js_to_number(base)) if not isinstance(base, JSUndefined) else 10
                if b == 16: return hex(int(n))[2:]
                if b == 2: return bin(int(n))[2:]
                return self._js_to_string(n)
            return num_to_string
        if prop == 'toLocaleString':
            return lambda: f'{n:,}'
        return UNDEFINED

    # ── Call / New ────────────────────────────────────────────────────────────

    def _eval_call(self, node: CallExpr, env: Env):
        # Special case: member call (method dispatch with 'this')
        if isinstance(node.callee, MemberExpr):
            obj = self.eval_expr(node.callee.obj, env)
            prop = self._eval_member_key(node.callee, env)
            method = self._get_prop(obj, prop)
            args = self._eval_args(node.args, env)

            # If it's a JSFunction, inject 'this'
            if isinstance(method, JSFunction):
                return self._call_function(method, args, this=obj)
            if callable(method):
                return method(*args)
            return UNDEFINED

        callee = self.eval_expr(node.callee, env)
        args = self._eval_args(node.args, env)
        return self._call_function(callee, args)

    def _eval_args(self, arg_nodes, env):
        args = []
        for a in arg_nodes:
            if isinstance(a, SpreadExpr):
                val = self.eval_expr(a.argument, env)
                if isinstance(val, list): args.extend(val)
                else: args.append(val)
            else:
                args.append(self.eval_expr(a, env))
        return args

    def _call_function(self, fn, args, this=None):
        if isinstance(fn, JSFunction):
            call_env = Env(parent=fn.closure)
            if this is not None:
                call_env.define('this', this)
            self._bind_params(fn.params, args, call_env)
            # hoist inner func decls
            if isinstance(fn.body, BlockStmt):
                for stmt in fn.body.body:
                    if isinstance(stmt, FuncDecl):
                        inner_fn = JSFunction(stmt.params, stmt.body, call_env, name=stmt.name)
                        call_env.define(stmt.name, inner_fn)
            try:
                self.eval_stmt(fn.body, call_env)
                return UNDEFINED
            except ReturnSignal as r:
                return r.value
        # JSClass used as constructor (new ClassName())
        if isinstance(fn, JSClass):
            instance = JSInstance(fn)
            instance.props = {}
            # inherit from superclass
            if fn.superclass and isinstance(fn.superclass, JSClass):
                if 'constructor' in fn.superclass.methods:
                    self._call_function(fn.superclass.methods['constructor'], args, this=instance)
            if 'constructor' in fn.methods:
                self._call_function(fn.methods['constructor'], args, this=instance)
            return instance
        if callable(fn):
            return fn(*args)
        raise JSError(f'{self._js_to_string(fn)} is not a function')

    def _bind_params(self, params, args, env):
        for i, param in enumerate(params):
            if isinstance(param, tuple):
                if param[0] == 'rest':
                    env.define(param[1], args[i:])
                elif param[0] == 'default':
                    val = args[i] if i < len(args) and not isinstance(args[i], JSUndefined) else self.eval_expr(param[2], env)
                    env.define(param[1], val)
                else:
                    env.define(param[0], args[i] if i < len(args) else UNDEFINED)
            else:
                env.define(param, args[i] if i < len(args) else UNDEFINED)

    def _eval_new(self, node: NewExpr, env: Env):
        callee = self.eval_expr(node.callee, env)
        args = self._eval_args(node.args, env)

        if isinstance(callee, JSClass):
            instance = JSInstance(callee)
            instance.props = {}
            # Call parent constructor if extends
            if callee.superclass and isinstance(callee.superclass, JSClass):
                if 'constructor' in callee.superclass.methods:
                    self._call_function(callee.superclass.methods['constructor'], args, this=instance)
            if 'constructor' in callee.methods:
                self._call_function(callee.methods['constructor'], args, this=instance)
            return instance
        if callable(callee):
            return callee(*args)
        return {}

    # ── Operators ─────────────────────────────────────────────────────────────

    def _eval_binary(self, node: BinaryExpr, env: Env):
        op = node.op
        # Short-circuit not needed here (handled by logical)
        left = self.eval_expr(node.left, env)
        right = self.eval_expr(node.right, env)

        if op == '+':
            # String coercion if either side is string
            if isinstance(left, str) or isinstance(right, str):
                return self._js_to_string(left) + self._js_to_string(right)
            lv = self._js_to_number(left)
            rv = self._js_to_number(right)
            result = lv + rv
            return int(result) if isinstance(lv, int) and isinstance(rv, int) else result

        if op == '-': return self._numeric_op(left, right, lambda a,b: a-b)
        if op == '*': return self._numeric_op(left, right, lambda a,b: a*b)
        if op == '/':
            r = self._js_to_number(right)
            if r == 0: return float('inf') if self._js_to_number(left) > 0 else float('-inf') if self._js_to_number(left) < 0 else float('nan')
            return self._js_to_number(left) / r
        if op == '%':
            r = self._js_to_number(right)
            if r == 0: return float('nan')
            l = self._js_to_number(left)
            result = _math.fmod(l, r)
            return int(result) if result == int(result) else result
        if op == '**': return self._js_to_number(left) ** self._js_to_number(right)

        if op == '===': return self._strict_eq(left, right)
        if op == '==': return self._loose_eq(left, right)
        if op == '!==': return not self._strict_eq(left, right)
        if op == '!=': return not self._loose_eq(left, right)
        if op == '<': return self._compare(left, right) < 0
        if op == '>': return self._compare(left, right) > 0
        if op == '<=': return self._compare(left, right) <= 0
        if op == '>=': return self._compare(left, right) >= 0

        if op == '&': return int(self._js_to_number(left)) & int(self._js_to_number(right))
        if op == '|': return int(self._js_to_number(left)) | int(self._js_to_number(right))
        if op == '^': return int(self._js_to_number(left)) ^ int(self._js_to_number(right))
        if op == '<<': return int(self._js_to_number(left)) << int(self._js_to_number(right))
        if op == '>>': return int(self._js_to_number(left)) >> int(self._js_to_number(right))
        if op == '>>>': return int(self._js_to_number(left)) >> int(self._js_to_number(right))

        if op == 'instanceof':
            if isinstance(right, JSClass):
                return isinstance(left, JSInstance) and left.cls == right
            return False

        if op == 'in':
            if isinstance(right, dict): return self._js_to_string(left) in right
            if isinstance(right, list):
                try: return int(self._js_to_number(left)) < len(right)
                except: return False
            return False

        return UNDEFINED

    def _numeric_op(self, left, right, fn):
        lv = self._js_to_number(left)
        rv = self._js_to_number(right)
        result = fn(lv, rv)
        if isinstance(result, float) and result == int(result):
            return int(result)
        return result

    def _strict_eq(self, a, b):
        """JS === semantics."""
        if type(a) == type(b):
            if isinstance(a, float) and a != a: return False  # NaN
            return a == b
        # bool / number coercion is NOT applied in ===
        # but Python int/float need care
        if isinstance(a, bool) or isinstance(b, bool):
            return type(a) == type(b) and a == b
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a == b
        if isinstance(a, JSUndefined) and isinstance(b, JSUndefined):
            return True
        if a is None and b is None:
            return True
        return False

    def _loose_eq(self, a, b):
        """JS == semantics with type coercion."""
        # Same type → same as ===
        if self._strict_eq(a, b): return True
        # null == undefined
        if (a is None or isinstance(a, JSUndefined)) and (b is None or isinstance(b, JSUndefined)):
            return True
        # null/undefined only == each other, never anything else
        if a is None or isinstance(a, JSUndefined): return False
        if b is None or isinstance(b, JSUndefined): return False
        # bool → number first
        if isinstance(a, bool): return self._loose_eq(1 if a else 0, b)
        if isinstance(b, bool): return self._loose_eq(a, 1 if b else 0)
        # number == string → convert string to number
        if isinstance(a, (int, float)) and isinstance(b, str):
            return a == self._js_to_number(b)
        if isinstance(b, (int, float)) and isinstance(a, str):
            return self._js_to_number(a) == b
        # object == primitive: not handled deeply here
        return False

    def _compare(self, a, b):
        if isinstance(a, str) and isinstance(b, str):
            return (a > b) - (a < b)
        an, bn = self._js_to_number(a), self._js_to_number(b)
        return (an > bn) - (an < bn)

    def _eval_unary(self, node: UnaryExpr, env: Env):
        op = node.op
        if op == 'typeof':
            # Don't eval if it might throw (variable might not exist)
            if isinstance(node.operand, Identifier):
                val = env.get(node.operand.name)
            else:
                val = self.eval_expr(node.operand, env)
            return self._typeof(val)
        val = self.eval_expr(node.operand, env)
        if op == '!': return not self._js_to_bool(val)
        if op == '-':
            n = self._js_to_number(val)
            return -n
        if op == '+': return self._js_to_number(val)
        if op == '~': return ~int(self._js_to_number(val))
        if op == 'void': return UNDEFINED
        if op == 'delete':
            # Best-effort
            return True
        return UNDEFINED

    def _typeof(self, val):
        if isinstance(val, JSUndefined): return 'undefined'
        if val is None: return 'object'
        if isinstance(val, bool): return 'boolean'
        if isinstance(val, (int, float)): return 'number'
        if isinstance(val, str): return 'string'
        if isinstance(val, (JSFunction,)) or callable(val): return 'function'
        return 'object'

    def _eval_logical(self, node: LogicalExpr, env: Env):
        left = self.eval_expr(node.left, env)
        if node.op == '&&':
            return left if not self._js_to_bool(left) else self.eval_expr(node.right, env)
        if node.op == '||':
            return left if self._js_to_bool(left) else self.eval_expr(node.right, env)
        if node.op == '??':
            return left if (left is not None and not isinstance(left, JSUndefined)) else self.eval_expr(node.right, env)
        return UNDEFINED

    def _eval_assign(self, node: AssignExpr, env: Env):
        op = node.op

        def get_current():
            if isinstance(node.target, Identifier):
                return env.get(node.target.name)
            if isinstance(node.target, MemberExpr):
                obj = self.eval_expr(node.target.obj, env)
                key = self._eval_member_key(node.target, env)
                return self._get_prop(obj, key)
            return UNDEFINED

        def set_value(val):
            if isinstance(node.target, Identifier):
                env.set(node.target.name, val)
            elif isinstance(node.target, MemberExpr):
                obj = self.eval_expr(node.target.obj, env)
                key = self._eval_member_key(node.target, env)
                self._set_prop(obj, key, val)

        rhs = self.eval_expr(node.value, env)

        if op == '=':
            set_value(rhs)
            return rhs

        cur = get_current()
        if op == '+=':
            if isinstance(cur, str) or isinstance(rhs, str):
                result = self._js_to_string(cur) + self._js_to_string(rhs)
            else:
                result = self._js_to_number(cur) + self._js_to_number(rhs)
        elif op == '-=': result = self._js_to_number(cur) - self._js_to_number(rhs)
        elif op == '*=': result = self._js_to_number(cur) * self._js_to_number(rhs)
        elif op == '/=': result = self._js_to_number(cur) / self._js_to_number(rhs)
        elif op == '%=': result = _math.fmod(self._js_to_number(cur), self._js_to_number(rhs))
        elif op == '**=': result = self._js_to_number(cur) ** self._js_to_number(rhs)
        elif op == '&&=': result = cur if not self._js_to_bool(cur) else rhs
        elif op == '||=': result = cur if self._js_to_bool(cur) else rhs
        elif op == '??=': result = cur if (cur is not None and not isinstance(cur, JSUndefined)) else rhs
        else: result = rhs

        set_value(result)
        return result

    def _eval_update(self, node: UpdateExpr, env: Env):
        def get():
            if isinstance(node.operand, Identifier):
                return env.get(node.operand.name)
            if isinstance(node.operand, MemberExpr):
                obj = self.eval_expr(node.operand.obj, env)
                key = self._eval_member_key(node.operand, env)
                return self._get_prop(obj, key)
            return 0

        def put(v):
            if isinstance(node.operand, Identifier):
                env.set(node.operand.name, v)
            elif isinstance(node.operand, MemberExpr):
                obj = self.eval_expr(node.operand.obj, env)
                key = self._eval_member_key(node.operand, env)
                self._set_prop(obj, key, v)

        old = self._js_to_number(get())
        new = old + 1 if node.op == '++' else old - 1
        # Keep int if possible
        new = int(new) if new == int(new) else new
        put(new)
        return old if not node.prefix else new

    def _js_iter(self, val):
        if isinstance(val, list): return val
        if isinstance(val, str): return list(val)
        if isinstance(val, dict): return list(val.values())
        return []