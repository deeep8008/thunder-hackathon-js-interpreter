"""
Recursive-descent parser.
Converts a flat token list into an AST using the nodes in ast_nodes.py.
"""

from lexer import Token, TT
from ast_nodes import *


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # ── Helpers ──────────────────────────────────────────────────────────────

    def peek(self, offset=0) -> Token:
        p = self.pos + offset
        if p < len(self.tokens):
            return self.tokens[p]
        return self.tokens[-1]  # EOF

    def cur(self) -> Token:
        return self.peek()

    def advance(self) -> Token:
        t = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return t

    def check(self, type_=None, value=None) -> bool:
        t = self.cur()
        if type_ is not None and t.type != type_:
            return False
        if value is not None and t.value != value:
            return False
        return True

    def match_type(self, *types) -> bool:
        if self.cur().type in types:
            return True
        return False

    def match_kw(self, *words) -> bool:
        t = self.cur()
        return t.type == TT['KEYWORD'] and t.value in words

    def expect(self, type_, value=None) -> Token:
        t = self.cur()
        if t.type != type_:
            raise ParseError(f"Line {t.line}: expected {type_!r}, got {t.type!r} ({t.value!r})")
        if value is not None and t.value != value:
            raise ParseError(f"Line {t.line}: expected value {value!r}, got {t.value!r}")
        return self.advance()

    def eat_semicolon(self):
        """Consume optional semicolon (ASI)."""
        if self.check(TT['SEMICOLON']):
            self.advance()

    # ── Top-level ─────────────────────────────────────────────────────────────

    def parse(self) -> Program:
        body = []
        while not self.check(TT['EOF']):
            body.append(self.parse_stmt())
        return Program(body=body)

    # ── Statements ────────────────────────────────────────────────────────────

    def parse_stmt(self):
        t = self.cur()

        if t.type == TT['LBRACE']:
            return self.parse_block()

        if t.type == TT['KEYWORD']:
            kw = t.value

            if kw in ('let', 'const', 'var'):
                return self.parse_var_decl()

            if kw == 'function':
                return self.parse_func_decl()

            if kw == 'class':
                return self.parse_class_decl()

            if kw == 'if':
                return self.parse_if()

            if kw == 'for':
                return self.parse_for()

            if kw == 'while':
                return self.parse_while()

            if kw == 'do':
                return self.parse_do_while()

            if kw == 'return':
                self.advance()
                val = None
                if not self.check(TT['SEMICOLON']) and not self.check(TT['RBRACE']) and not self.check(TT['EOF']):
                    val = self.parse_expr()
                self.eat_semicolon()
                return ReturnStmt(value=val)

            if kw == 'break':
                self.advance()
                self.eat_semicolon()
                return BreakStmt()

            if kw == 'continue':
                self.advance()
                self.eat_semicolon()
                return ContinueStmt()

            if kw == 'switch':
                return self.parse_switch()

            if kw == 'throw':
                self.advance()
                arg = self.parse_expr()
                self.eat_semicolon()
                return ThrowStmt(argument=arg)

            if kw == 'try':
                return self.parse_try()

        # expression statement
        expr = self.parse_expr()
        self.eat_semicolon()
        return ExprStmt(expr=expr)

    def parse_block(self) -> BlockStmt:
        self.expect(TT['LBRACE'])
        body = []
        while not self.check(TT['RBRACE']) and not self.check(TT['EOF']):
            body.append(self.parse_stmt())
        self.expect(TT['RBRACE'])
        return BlockStmt(body=body)

    def parse_var_decl(self):
        kind = self.advance().value  # let/const/var
        name_tok = self.cur()

        # Destructuring: let [a, b] = arr  or  let {x, y} = obj
        if name_tok.type == TT['LBRACKET']:
            pattern = self.parse_array_pattern()
            self.expect(TT['OP'], '=')
            init = self.parse_assign_expr()
            self.eat_semicolon()
            return VarDecl(kind=kind, name=pattern, init=init)
        if name_tok.type == TT['LBRACE']:
            pattern = self.parse_object_pattern()
            self.expect(TT['OP'], '=')
            init = self.parse_assign_expr()
            self.eat_semicolon()
            return VarDecl(kind=kind, name=pattern, init=init)

        name = self.expect(TT['IDENT']).value
        init = None
        if self.check(TT['OP'], '='):
            self.advance()
            init = self.parse_assign_expr()
        self.eat_semicolon()
        return VarDecl(kind=kind, name=name, init=init)

    def parse_array_pattern(self):
        """Returns a list of names (strings) for destructuring."""
        self.expect(TT['LBRACKET'])
        names = []
        while not self.check(TT['RBRACKET']) and not self.check(TT['EOF']):
            if self.check(TT['COMMA']):
                names.append(None)  # hole
                self.advance()
                continue
            if self.check(TT['SPREAD']):
                self.advance()
                names.append(('rest', self.expect(TT['IDENT']).value))
            else:
                names.append(self.expect(TT['IDENT']).value)
            if self.check(TT['COMMA']):
                self.advance()
        self.expect(TT['RBRACKET'])
        return ('array_pattern', names)

    def parse_object_pattern(self):
        """Returns list of (key, alias) for destructuring."""
        self.expect(TT['LBRACE'])
        props = []
        while not self.check(TT['RBRACE']) and not self.check(TT['EOF']):
            key = self.expect(TT['IDENT']).value
            alias = key
            if self.check(TT['COLON']):
                self.advance()
                alias = self.expect(TT['IDENT']).value
            props.append((key, alias))
            if self.check(TT['COMMA']):
                self.advance()
        self.expect(TT['RBRACE'])
        return ('object_pattern', props)

    def parse_func_decl(self):
        self.advance()  # 'function'
        name = self.expect(TT['IDENT']).value
        params = self.parse_params()
        body = self.parse_block()
        return FuncDecl(name=name, params=params, body=body)

    def parse_class_decl(self):
        self.advance()  # 'class'
        name = self.expect(TT['IDENT']).value
        superclass = None
        if self.match_kw('extends'):
            self.advance()
            superclass = self.parse_assign_expr()
        self.expect(TT['LBRACE'])
        methods = []
        while not self.check(TT['RBRACE']) and not self.check(TT['EOF']):
            is_static = False
            if self.check(TT['IDENT'], 'static'):
                is_static = True
                self.advance()
            # method name
            if self.cur().type in (TT['IDENT'], TT['KEYWORD'], TT['STRING']):
                mname = self.advance().value
            else:
                break
            params = self.parse_params()
            body = self.parse_block()
            methods.append(MethodDef(
                name=mname,
                func=FuncDecl(name=mname, params=params, body=body),
                is_static=is_static
            ))
        self.expect(TT['RBRACE'])
        return ClassDecl(name=name, superclass=superclass, methods=methods)

    def parse_params(self) -> list:
        self.expect(TT['LPAREN'])
        params = []
        while not self.check(TT['RPAREN']) and not self.check(TT['EOF']):
            if self.check(TT['SPREAD']):
                self.advance()
                params.append(('rest', self.expect(TT['IDENT']).value))
            else:
                p = self.expect(TT['IDENT']).value
                if self.check(TT['OP'], '='):
                    self.advance()
                    default = self.parse_assign_expr()
                    params.append(('default', p, default))
                else:
                    params.append(p)
            if self.check(TT['COMMA']):
                self.advance()
        self.expect(TT['RPAREN'])
        return params

    def parse_if(self) -> IfStmt:
        self.advance()  # 'if'
        self.expect(TT['LPAREN'])
        test = self.parse_expr()
        self.expect(TT['RPAREN'])
        consequent = self.parse_stmt()
        alternate = None
        if self.match_kw('else'):
            self.advance()
            alternate = self.parse_stmt()
        return IfStmt(test=test, consequent=consequent, alternate=alternate)

    def parse_for(self):
        self.advance()  # 'for'
        self.expect(TT['LPAREN'])

        # Detect for...in / for...of
        saved = self.pos
        try:
            kind_kw = None
            if self.match_kw('let', 'const', 'var'):
                kw_tok = self.advance()
                if self.cur().type == TT['IDENT']:
                    var_name = self.advance().value
                    if self.match_kw('in', 'of'):
                        kind_kw = self.advance().value
                        iterable = self.parse_expr()
                        self.expect(TT['RPAREN'])
                        body = self.parse_stmt()
                        return ForInStmt(kind=kind_kw, var=var_name, iterable=iterable, body=body)
            self.pos = saved
        except Exception:
            self.pos = saved

        # Standard for(init; test; update)
        init = None
        if not self.check(TT['SEMICOLON']):
            if self.match_kw('let', 'const', 'var'):
                init = self.parse_var_decl_no_semi()
            else:
                init = ExprStmt(expr=self.parse_expr())
        self.eat_semicolon()
        test = None
        if not self.check(TT['SEMICOLON']):
            test = self.parse_expr()
        self.eat_semicolon()
        update = None
        if not self.check(TT['RPAREN']):
            update = self.parse_expr()
        self.expect(TT['RPAREN'])
        body = self.parse_stmt()
        return ForStmt(init=init, test=test, update=update, body=body)

    def parse_var_decl_no_semi(self):
        """VarDecl without consuming trailing semicolon (used inside for-init)."""
        kind = self.advance().value
        name = self.expect(TT['IDENT']).value
        init = None
        if self.check(TT['OP'], '='):
            self.advance()
            init = self.parse_assign_expr()
        return VarDecl(kind=kind, name=name, init=init)

    def parse_while(self) -> WhileStmt:
        self.advance()  # 'while'
        self.expect(TT['LPAREN'])
        test = self.parse_expr()
        self.expect(TT['RPAREN'])
        body = self.parse_stmt()
        return WhileStmt(test=test, body=body)

    def parse_do_while(self) -> DoWhileStmt:
        self.advance()  # 'do'
        body = self.parse_stmt()
        self.expect(TT['KEYWORD'], 'while')
        self.expect(TT['LPAREN'])
        test = self.parse_expr()
        self.expect(TT['RPAREN'])
        self.eat_semicolon()
        return DoWhileStmt(body=body, test=test)

    def parse_switch(self) -> SwitchStmt:
        self.advance()  # 'switch'
        self.expect(TT['LPAREN'])
        discriminant = self.parse_expr()
        self.expect(TT['RPAREN'])
        self.expect(TT['LBRACE'])
        cases = []
        while not self.check(TT['RBRACE']) and not self.check(TT['EOF']):
            if self.match_kw('case'):
                self.advance()
                test_expr = self.parse_expr()
                self.expect(TT['COLON'])
            elif self.match_kw('default'):
                self.advance()
                self.expect(TT['COLON'])
                test_expr = None
            else:
                break
            consequent = []
            while (not self.match_kw('case', 'default') and
                   not self.check(TT['RBRACE']) and
                   not self.check(TT['EOF'])):
                consequent.append(self.parse_stmt())
            cases.append(SwitchCase(test=test_expr, consequent=consequent))
        self.expect(TT['RBRACE'])
        return SwitchStmt(discriminant=discriminant, cases=cases)

    def parse_try(self) -> TryStmt:
        self.advance()  # 'try'
        block = self.parse_block()
        handler = None
        finalizer = None
        if self.match_kw('catch'):
            self.advance()
            param = None
            if self.check(TT['LPAREN']):
                self.expect(TT['LPAREN'])
                param = self.expect(TT['IDENT']).value
                self.expect(TT['RPAREN'])
            body = self.parse_block()
            handler = CatchClause(param=param, body=body)
        if self.match_kw('finally'):
            self.advance()
            finalizer = self.parse_block()
        return TryStmt(block=block, handler=handler, finalizer=finalizer)

    # ── Expressions ───────────────────────────────────────────────────────────

    def parse_expr(self):
        """Comma-separated expressions → SequenceExpr if multiple."""
        expr = self.parse_assign_expr()
        if self.check(TT['COMMA']):
            exprs = [expr]
            while self.check(TT['COMMA']):
                self.advance()
                exprs.append(self.parse_assign_expr())
            return SequenceExpr(exprs=exprs)
        return expr

    def parse_assign_expr(self):
        left = self.parse_ternary()

        ASSIGN_OPS = {'=', '+=', '-=', '*=', '/=', '%=', '**=', '&&=', '||=', '??=', '<<=', '>>=', '&=', '|=', '^='}
        if self.cur().type == TT['OP'] and self.cur().value in ASSIGN_OPS:
            op = self.advance().value
            right = self.parse_assign_expr()
            return AssignExpr(op=op, target=left, value=right)
        return left

    def parse_ternary(self):
        expr = self.parse_nullish()
        if self.check(TT['QUESTION']):
            self.advance()
            consequent = self.parse_assign_expr()
            self.expect(TT['COLON'])
            alternate = self.parse_assign_expr()
            return ConditionalExpr(test=expr, consequent=consequent, alternate=alternate)
        return expr

    def parse_nullish(self):
        left = self.parse_or()
        while self.check(TT['OP'], '??'):
            op = self.advance().value
            right = self.parse_or()
            left = LogicalExpr(op=op, left=left, right=right)
        return left

    def parse_or(self):
        left = self.parse_and()
        while self.check(TT['OP'], '||'):
            op = self.advance().value
            right = self.parse_and()
            left = LogicalExpr(op=op, left=left, right=right)
        return left

    def parse_and(self):
        left = self.parse_bitwise_or()
        while self.check(TT['OP'], '&&'):
            op = self.advance().value
            right = self.parse_bitwise_or()
            left = LogicalExpr(op=op, left=left, right=right)
        return left

    def parse_bitwise_or(self):
        left = self.parse_bitwise_xor()
        while self.check(TT['OP'], '|'):
            op = self.advance().value
            right = self.parse_bitwise_xor()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_bitwise_xor(self):
        left = self.parse_bitwise_and()
        while self.check(TT['OP'], '^'):
            op = self.advance().value
            right = self.parse_bitwise_and()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_bitwise_and(self):
        left = self.parse_equality()
        while self.check(TT['OP'], '&'):
            op = self.advance().value
            right = self.parse_equality()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_equality(self):
        left = self.parse_relational()
        while self.cur().type == TT['OP'] and self.cur().value in ('==', '!=', '===', '!=='):
            op = self.advance().value
            right = self.parse_relational()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_relational(self):
        left = self.parse_shift()
        while True:
            t = self.cur()
            if t.type == TT['OP'] and t.value in ('<', '>', '<=', '>='):
                op = self.advance().value
                right = self.parse_shift()
                left = BinaryExpr(op=op, left=left, right=right)
            elif t.type == TT['KEYWORD'] and t.value in ('instanceof', 'in'):
                op = self.advance().value
                right = self.parse_shift()
                left = BinaryExpr(op=op, left=left, right=right)
            else:
                break
        return left

    def parse_shift(self):
        left = self.parse_additive()
        while self.cur().type == TT['OP'] and self.cur().value in ('<<', '>>', '>>>'):
            op = self.advance().value
            right = self.parse_additive()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.cur().type == TT['OP'] and self.cur().value in ('+', '-'):
            op = self.advance().value
            right = self.parse_multiplicative()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_multiplicative(self):
        left = self.parse_exponent()
        while self.cur().type == TT['OP'] and self.cur().value in ('*', '/', '%'):
            op = self.advance().value
            right = self.parse_exponent()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_exponent(self):
        left = self.parse_unary()
        if self.check(TT['OP'], '**'):
            op = self.advance().value
            right = self.parse_exponent()  # right-associative
            return BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_unary(self):
        t = self.cur()
        if t.type == TT['OP'] and t.value in ('!', '-', '+', '~'):
            op = self.advance().value
            operand = self.parse_unary()
            return UnaryExpr(op=op, operand=operand)
        if t.type == TT['KEYWORD'] and t.value in ('typeof', 'void', 'delete'):
            op = self.advance().value
            operand = self.parse_unary()
            return UnaryExpr(op=op, operand=operand)
        if t.type == TT['OP'] and t.value in ('++', '--'):
            op = self.advance().value
            operand = self.parse_unary()
            return UpdateExpr(op=op, operand=operand, prefix=True)
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_call_member()
        if self.cur().type == TT['OP'] and self.cur().value in ('++', '--'):
            op = self.advance().value
            return UpdateExpr(op=op, operand=expr, prefix=False)
        return expr

    def parse_call_member(self):
        expr = self.parse_primary()
        while True:
            if self.check(TT['DOT']):
                self.advance()
                prop = self.cur()
                if prop.type in (TT['IDENT'], TT['KEYWORD']):
                    self.advance()
                    expr = MemberExpr(obj=expr, prop=Identifier(name=prop.value), computed=False)
                else:
                    break
            elif self.check(TT['LBRACKET']):
                self.advance()
                prop = self.parse_expr()
                self.expect(TT['RBRACKET'])
                expr = MemberExpr(obj=expr, prop=prop, computed=True)
            elif self.check(TT['LPAREN']):
                args = self.parse_args()
                expr = CallExpr(callee=expr, args=args)
            else:
                break
        return expr

    def parse_args(self) -> list:
        self.expect(TT['LPAREN'])
        args = []
        while not self.check(TT['RPAREN']) and not self.check(TT['EOF']):
            if self.check(TT['SPREAD']):
                self.advance()
                args.append(SpreadExpr(argument=self.parse_assign_expr()))
            else:
                args.append(self.parse_assign_expr())
            if self.check(TT['COMMA']):
                self.advance()
        self.expect(TT['RPAREN'])
        return args

    def parse_primary(self):
        t = self.cur()

        if t.type == TT['NUMBER']:
            self.advance()
            return Literal(value=t.value)

        if t.type == TT['STRING']:
            self.advance()
            return Literal(value=t.value)

        if t.type == TT['BOOL']:
            self.advance()
            return Literal(value=t.value)

        if t.type == TT['NULL']:
            self.advance()
            return Literal(value=None)

        if t.type == TT['UNDEFINED']:
            self.advance()
            return Literal(value=JSUndefined())

        if t.type == TT['TEMPLATE']:
            self.advance()
            return TemplateLiteral(raw=t.value)

        if t.type == TT['IDENT']:
            self.advance()
            # Check for arrow function: ident =>
            if self.check(TT['ARROW']):
                self.advance()
                body = self._parse_arrow_body()
                return FuncExpr(name=None, params=[t.value], body=body, is_arrow=True)
            return Identifier(name=t.value)

        if t.type == TT['KEYWORD']:
            if t.value == 'this':
                self.advance()
                return Identifier(name='this')
            if t.value == 'new':
                self.advance()
                callee = self._parse_new_callee()
                args = []
                if self.check(TT['LPAREN']):
                    args = self.parse_args()
                return NewExpr(callee=callee, args=args)
            if t.value == 'function':
                return self.parse_func_expr()
            if t.value in ('typeof', 'void', 'delete'):
                op = self.advance().value
                operand = self.parse_unary()
                return UnaryExpr(op=op, operand=operand)

        if t.type == TT['LPAREN']:
            self.advance()
            # Could be: (expr) or (params) => body
            # Try to detect arrow function
            if self.check(TT['RPAREN']):
                # () => ...
                self.advance()
                if self.check(TT['ARROW']):
                    self.advance()
                    body = self._parse_arrow_body()
                    return FuncExpr(name=None, params=[], body=body, is_arrow=True)
                return Literal(value=None)  # edge case

            # Tentatively parse expr
            saved = self.pos
            try:
                params = self._try_parse_arrow_params()
                if params is not None and self.check(TT['ARROW']):
                    self.advance()
                    body = self._parse_arrow_body()
                    return FuncExpr(name=None, params=params, body=body, is_arrow=True)
            except Exception:
                pass
            self.pos = saved

            expr = self.parse_expr()
            self.expect(TT['RPAREN'])
            return expr

        if t.type == TT['LBRACKET']:
            return self.parse_array_literal()

        if t.type == TT['LBRACE']:
            return self.parse_object_literal()

        if t.type == TT['SPREAD']:
            self.advance()
            return SpreadExpr(argument=self.parse_assign_expr())

        # Fallthrough: skip token
        self.advance()
        return Literal(value=None)

    def _parse_new_callee(self):
        """Parse the callee of a 'new' expression: just ident + member access, no call parens."""
        if self.cur().type == TT['KEYWORD'] and self.cur().value == 'new':
            # nested new: new new Foo()
            self.advance()
            inner = self._parse_new_callee()
            args = []
            if self.check(TT['LPAREN']):
                args = self.parse_args()
            return NewExpr(callee=inner, args=args)
        # Primary: identifier (or member chain without call)
        expr = self.parse_primary()
        # Allow member access only (no call parens)
        while True:
            if self.check(TT['DOT']):
                self.advance()
                prop = self.cur()
                if prop.type in (TT['IDENT'], TT['KEYWORD']):
                    self.advance()
                    expr = MemberExpr(obj=expr, prop=Identifier(name=prop.value), computed=False)
                else:
                    break
            elif self.check(TT['LBRACKET']):
                self.advance()
                prop = self.parse_expr()
                self.expect(TT['RBRACKET'])
                expr = MemberExpr(obj=expr, prop=prop, computed=True)
            else:
                break
        return expr

    def _try_parse_arrow_params(self):
        """Try to parse (a, b, c) as parameter list. Returns list or None."""
        params = []
        while not self.check(TT['RPAREN']) and not self.check(TT['EOF']):
            if self.check(TT['SPREAD']):
                self.advance()
                params.append(('rest', self.expect(TT['IDENT']).value))
            elif self.cur().type == TT['IDENT']:
                p = self.advance().value
                if self.check(TT['OP'], '='):
                    self.advance()
                    default = self.parse_assign_expr()
                    params.append(('default', p, default))
                else:
                    params.append(p)
            else:
                return None
            if self.check(TT['COMMA']):
                self.advance()
        self.expect(TT['RPAREN'])
        return params

    def _parse_arrow_body(self):
        """Arrow body: block { } or single expression."""
        if self.check(TT['LBRACE']):
            return self.parse_block()
        expr = self.parse_assign_expr()
        return BlockStmt(body=[ReturnStmt(value=expr)])

    def parse_func_expr(self):
        self.advance()  # 'function'
        name = None
        if self.cur().type == TT['IDENT']:
            name = self.advance().value
        params = self.parse_params()
        body = self.parse_block()
        return FuncExpr(name=name, params=params, body=body)

    def parse_array_literal(self) -> ArrayExpr:
        self.expect(TT['LBRACKET'])
        elements = []
        while not self.check(TT['RBRACKET']) and not self.check(TT['EOF']):
            if self.check(TT['COMMA']):
                elements.append(None)  # hole
                self.advance()
                continue
            if self.check(TT['SPREAD']):
                self.advance()
                elements.append(SpreadExpr(argument=self.parse_assign_expr()))
            else:
                elements.append(self.parse_assign_expr())
            if self.check(TT['COMMA']):
                self.advance()
        self.expect(TT['RBRACKET'])
        return ArrayExpr(elements=elements)

    def parse_object_literal(self) -> ObjectExpr:
        self.expect(TT['LBRACE'])
        props = []
        while not self.check(TT['RBRACE']) and not self.check(TT['EOF']):
            t = self.cur()
            # Spread in object: { ...other }
            if t.type == TT['SPREAD']:
                self.advance()
                props.append(('spread', self.parse_assign_expr()))
                if self.check(TT['COMMA']):
                    self.advance()
                continue
            # Computed key: { [expr]: val }
            if t.type == TT['LBRACKET']:
                self.advance()
                key_expr = self.parse_assign_expr()
                self.expect(TT['RBRACKET'])
                self.expect(TT['COLON'])
                val = self.parse_assign_expr()
                props.append(('computed', key_expr, val))
            else:
                # key name
                if t.type in (TT['IDENT'], TT['KEYWORD']):
                    key = self.advance().value
                elif t.type == TT['STRING']:
                    key = self.advance().value
                elif t.type == TT['NUMBER']:
                    key = str(self.advance().value)
                else:
                    self.advance()
                    break

                if self.check(TT['COLON']):
                    self.advance()
                    val = self.parse_assign_expr()
                    props.append(('prop', key, val))
                elif self.check(TT['LPAREN']):
                    # Method shorthand: { foo() { } }
                    params = self.parse_params()
                    body = self.parse_block()
                    props.append(('method', key, FuncExpr(name=key, params=params, body=body)))
                else:
                    # Shorthand: { x } same as { x: x }
                    props.append(('prop', key, Identifier(name=key)))

            if self.check(TT['COMMA']):
                self.advance()
        self.expect(TT['RBRACE'])
        return ObjectExpr(props=props)


class JSUndefined:
    """Sentinel for undefined (distinct from None/null)."""
    def __repr__(self): return 'undefined'
    def __str__(self): return 'undefined'
    def __bool__(self): return False
