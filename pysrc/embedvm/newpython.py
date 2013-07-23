import ast
from embedvm import asm
from embedvm import bytecode

class CompilerError(Exception):
    """An error that can be presented to the programmer of the code being
    compiled; location should be a tuple of (module, statement), but can be
    anything."""
    def __init__(self, message, location):
        self.message = message
        try:
            self.location = "line %d in module %s"%(location[1].lineno, location[0].codefile)
        except (ValueError, IndexError, KeyError, AttributeError, TypeError):
            self.location = repr(location)

    def __str__(self):
        return "%s (in %s)"%(self.message, self.location)

class PythonExpression(object):
    """A PythonExpression represents an object or a local variable -- something
    that can be assigned to, or be used in a sum, or invoked. In parsing an AST
    expression, a PythonExpression that is an argument of it will be asked to
    generate a VM bytecode to evaluate the operation into a CodeBlock."""

    def get_type(self):
        """Used in all type checking. Types that need more complex comparison
        mechanisms may return something more complex than their own class
        here."""
        return type(self)

    def append_pushintvalue(self, codeblock):
        raise CompilerError("Can not evaluate to an integer", self)

    def binop(self, op, right):
        return NotImplemented

    def rbinop(self, op, left):
        return NotImplemented

    def unop(self, op):
        return NotImplemented

class Integer(PythonExpression):
    binopmap = {
            ast.Add: bytecode.Add,
            ast.Sub: bytecode.Sub,
            ast.Mult: bytecode.Mul,
            ast.Div: bytecode.Div,
            ast.Mod: bytecode.Mod,
            ast.LShift: bytecode.ShiftLeft,
            ast.RShift: bytecode.ShiftRight,
            ast.BitAnd: bytecode.BitwiseAnd,
            ast.BitOr: bytecode.BitwiseOr,
            ast.BitXor: bytecode.BitwiseXor,
            #ast.And: bytecode.LogicAnd, # TBD: short circuit logic -- easily possible?
            #ast.Or: bytecode.LogicOr,
            }
    unopmap = {
            ast.Not: bytecode.LogicNot,
            ast.Invert: bytecode.BitwiseNot,
            ast.USub: bytecode.ArithmeticInvert,
            }
    def binop(self, op, right):
        if right.append_pushintvalue == PythonExpression.append_pushintvalue: # ie it would fail
            return NotImplemented

        code = []
        self.append_pushintvalue(code)
        right.append_pushintvalue(code)
        code.append(self.binopmap[type(op)]())

        return ExpressionInteger(code)

    def unop(self, op):
        code = []
        self.append_pushintvalue(code)
        code.append(self.unopmap[type(op)]())

        return ExpressionInteger(code)

class LocalPythonExpression(object):
    def __init__(self, function):
        self.register_offset = function.local_registers_used
        function.local_registers_used += self.registers_needed

class LocalInteger(Integer, LocalPythonExpression):
    registers_needed = 1

    def append_assigncode(self, pyexpr, codeblock):
        pyexpr.append_pushintvalue(codeblock)
        codeblock.append(bytecode.PopLocal(-self.register_offset))

    def append_pushintvalue(self, codeblock):
        codeblock.append(bytecode.PushLocal(-self.register_offset))

Integer.type_for_local_variable = LocalInteger

class ExpressionInteger(Integer, PythonExpression):
    """An arithmetic result that is integer typed; it only supports the
    append_pushintvalue method, whose result is the only state this carries
    around."""

    def __init__(self, code):
        self.code = code

    def append_pushintvalue(self, codeblock):
        for line in self.code:
            codeblock.append(line)

class StaticInteger(Integer, PythonExpression):
    def __init__(self, value):
        self.value = value

    def append_pushintvalue(self, codeblock):
        codeblock.append(bytecode.PushConstantV(self.value))

class Function(PythonExpression):
    def __init__(self, module, statement):
        self.module = module
        self.statement = statement

        self.local_registers_used = 0

        self._code_block = None
        self._code_block_entry_point = None

    code_block = property(lambda self: (self.__generate_code_block(), self._code_block)[1] if self._code_block is None else self._code_block)
    code_block_entry_point = property(lambda self: (self.__generate_code_block(), self._code_block_entry_point)[1] if self._code_block is None else self._code_block_entry_point)

    def __generate_code_block(self):
        self._code_block = asm.FreeCodeBlock()

        self._code_block_entry_point = bytecode.Label('Entry point of function %s'%self)
        self.code_block.append(self.code_block_entry_point)

        self.return_type = None

        self.__parse_into_code_block()

    @classmethod
    def __gather_locals_from_statement(cls, statement):
        if hasattr(statement, "targets"): # assignments
            for t in statement.targets:
                if isinstance(t, ast.Name):
                    yield t.id
        if hasattr(statement, "target"): # for loop
            if isinstance(statement.target, ast.Name):
                yield statement.target.id
        if hasattr(statement, "body"): # blocks
            for s in statement.body:
                for l in cls.__gather_locals_from_statement(s):
                    yield l

    def __collect_locals(self):
        self.locals = sorted(set(self.__gather_locals_from_statement(self.statement)))

        self.local_objects = [None for l in self.locals] # unusable until first assigned, when the type will be sure

    # error: exception class with module and line number prefilled
    def __parse_expression(self, expr, error):
        if isinstance(expr, ast.Num) and isinstance(expr.n, int):
            return StaticInteger(expr.n)
        elif isinstance(expr, ast.Num):
            raise error("Unsupported number type")
        elif isinstance(expr, ast.Name):
            if expr.id in self.locals:
                pyexpr = self.local_objects[self.locals.index(expr.id)]
                if pyexpr is None:
                    raise error("Use of unassigned local variable %r"%expr.id)
                return pyexpr
            else:
                raise error("Name %r not found"%expr.id)
        elif isinstance(expr, ast.BinOp):
            lhs = self.__parse_expression(expr.left, error)
            rhs = self.__parse_expression(expr.right, error)

            result = lhs.binop(expr.op, rhs)
            if result == NotImplemented:
                result = rhs.rbinop(expr.op, lhs)
            if result == NotImplemented:
                raise error("Unsupported binary operator for %s and %s"%(lhs, rhs))
            return result
        elif isinstance(expr, ast.UnaryOp):
            pyexpr = self.__parse_expression(expr.operand, error)
            result = pyexpr.unop(expr.op)
            if result == NotImplemented:
                error("Unsupported unary operator for %s"%pyexpr)
            return result
        else:
            raise error("Unsupported expression (type %s)"%type(expr).__name__)

    def __parse_assign(self, s):
        error_in_this_line = lambda message: CompilerError(message, (self.module, s))
        # right hand side
        value = self.__parse_expression(s.value, error_in_this_line)

        for t in s.targets:
            if isinstance(t, ast.Name):
                # local variable
                local_id = self.locals.index(t.id)
                if self.local_objects[local_id] is None:
                    try:
                        self.local_objects[local_id] = value.type_for_local_variable(self)
                    except AttributeError:
                        raise CompilerError("Can not infer type for local variable from expression %r"%value, (self.module, s))

                self.local_objects[local_id].append_assigncode(value, self.code_block)
            else:
                raise CompilerError("Assignments to anything but local variables are currently not supported.", (self.module, s))

    def __parse_statement(self, s):
        if isinstance(s, ast.Assign):
            self.__parse_assign(s)
        elif isinstance(s, ast.Expr):
            print "WARNING -- ignoring side effects..."
        else:
            raise CompilerError("Unsupported statement %s"%s, (self.module, s))

    def __parse_into_code_block(self):
        self.__collect_locals()

        for s in self.statement.body:
            self.__parse_statement(s)

        if not isinstance(self.code_block.code[-1], bytecode.Return):
            pass # TRANSITIONAL, should do whatever is the default action for this type to return

    def fill_required_code_blocks(self, code_block_set):
        """Fill the own code block into the code_block_set passed, and all code
        blocks this function depends on, unless it's already filled in"""

        if self.code_block in code_block_set:
            return

        code_block_set.add(self.code_block)

        # FIXME check for references

class PythonModule(object):
    def __init__(self, program, codefile):
        self.program = program
        self.codefile = codefile
        self._ast = None
        self._globals = None

    @property
    def ast(self):
        if self._ast is None:
            try:
                self._ast = ast.parse(open(self.codefile).read())
            except ValueError, e:
                raise CompilerError(e)
        return self._ast

    @property
    def globals(self):
        if self._globals is None:
            self.parse()
        return self._globals

    def _global_assign(self, name, value, traceback):
        if name in self.globals:
            raise CompilerError("Multiple assignments to global name %s"%name, traceback)
        self.globals[name] = value

    def _parse_global_statement(self, statement):
        if isinstance(statement, ast.ImportFrom):
            return # TRANSITIONAL
        if isinstance(statement, ast.FunctionDef):
            f = Function(self, statement)
            self._global_assign(statement.name, f, (self, statement))
            return
        if isinstance(statement, ast.If):
            return # TRANSITIONAL (see get_main_function)

    def parse(self):
        self._globals = {}

        for s in self.ast.body:
            self._parse_global_statement(s)

    def lookup_global(self, name, traceback):
        try:
            return self.globals[name]
        except KeyError:
            raise CompilerError("No global value %s in module %s; called from %s"%(name, self), traceback)

    def get_main_function(self):
        """Return a function that is generated implicitly in the modules `if
        __name__ == "__main__"` block"""
        # TRANSITIONAL will return the function's main function instead
        return self.lookup_global('main', "looking up main symbol")

class PythonProgram(asm.ASM):
    def __init__(self):
        super(PythonProgram, self).__init__()

        self.modules = {}

    def load_module(self, modulename, modulefile):
        self.modules[modulename] = PythonModule(self, modulefile)

    def resolve_main_symbol(self):
        """Generate a __main__run symbol that contains the code executed in the
        __main__ module. As a side effect, does everything else."""

        main_function = self.modules['__main__'].get_main_function()
        main_function.code_block_entry_point.export = "main"

        return main_function

    def read_python(self, main_module):
        self.load_module('__main__', main_module)

        main = self.resolve_main_symbol()

        requiredblocks = set()
        main.fill_required_code_blocks(requiredblocks)

        # merge everything that has code into a single codeblock so it can
        # resolve jumps relatively
        bigblock = asm.FreeCodeBlock()
        for b in requiredblocks:
            bigblock.code.extend(b.code)

        self.blocks.append(bigblock)

    def get_symbols(self):
        # TRANSITIONAL: this style was only preserved to keep the changes to
        # evm-pycomp to a minimum; this should reather deal with
        # PythonExpression objects. (from old python.py)
        sym = {}
        for b in self.blocks:
            if hasattr(b, 'sym'):
                sym.update(b.sym)
        return sym
