import ast
from collections import namedtuple
from embedvm import asm
from embedvm.util import joining
from embedvm import bytecode

deduplicate = lambda iterable: reduce(lambda a, b: a if b in a else a+[b], iterable, [])

def raising_int(n):
    if not isinstance(n, int):
        raise ValueError("Unsupported type for integer")
    return n

class CodeObject(object):
    @classmethod
    def _raise(cls):
        raise Exception("Operation not implemented on %s"%cls.__name__)

    @classmethod
    def call(cls, context, args, keywords, starargs, kwargs):
        cls._raise()

    @classmethod
    def push_value(cls, context):
        cls._raise()

    @classmethod
    def pop_set(cls, context):
        cls._raise()

    @classmethod
    def getattr(cls, context, attribute):
        cls._raise()

    @classmethod
    def getslice(cls, context, slice):
        cls._raise()

    @classmethod
    def global_assign(cls, value):
        cls._raise()

class UnboundSetter(CodeObject):
    def __init__(self, callback):
        self.callback = callback

    def global_assign(self, value):
        self.callback(value)

class ConstantValue(CodeObject):
    def __init__(self, value):
        self.value = value

    def push_value(self, context):
        context.code.append(bytecode.PushConstantV(value=self.value))

class LocalVariable(CodeObject):
    def __init__(self, index):
        self.index = index

    def push_value(self, context):
        context.code.append(bytecode.PushLocal(self.index))

    def pop_set(self, context):
        context.code.append(bytecode.PopLocal(self.index))

class Argument(CodeObject):
    def __init__(self, index):
        self.index = index

    def push_value(self, context):
        context.code.append(bytecode.PushLocal(-1-self.index))

    def pop_set(self, context):
        context.code.append(bytecode.PopLocal(-1-self.index))

class Function(CodeObject):
    def __init__(self, name, args, body):
        self.name = name
        if args.kwarg or args.vararg:
            raise Exception("star-args not supported in function definitions")
        try:
            self.defaults = [raising_int(d.n) for d in args.defaults]
        except (ValueError, AttributeError):
            raise Exception("Value not supported for default argument")

        try:
            self.args = dict((a.id, Argument(i)) for (i, a) in enumerate(args.args))
        except AttributeError:
            raise Exception("Non-simple arguments not supported")

        self.body = body
        self.code = asm.FreeCodeBlock()

        self.entry_label = bytecode.Label("function start", export=self.name)
        self.code.append(self.entry_label)

    def __repr__(self):
        return "<%s \"%s\", %d instructions>"%(type(self).__name__, self.name, self.code.length)

    def call(self, context, args, keywords, starargs, kwargs):
        return self.PushableFunctioncall(self, args, keywords, starargs, kwargs)
    class PushableFunctioncall(CodeObject, namedtuple("PushableFunctionData", "function args keywords starargs kwargs")):
        def push_value(self, context):
            if self.starargs or self.keywords or self.kwargs:
                raise Exception("Only positional arguments are supported.")
            if len(self.args) + len(self.function.defaults) < len(self.function.args):
                raise Exception("Insufficient number of arguments")
            if len(self.args) > len(self.function.args):
                raise Exception("Too many arguments")
            for i in range(len(self.function.args) - len(self.args)):
                # push defaults while needed
                context.append_push(self.function.defaults[-1-i])
            for a in self.args[::-1]:
                context.append_push(a)
            context.code.append(bytecode.CallV(self.function.entry_label.get_ref()))
            if len(self.function.args) > 0:
                context.code.append(bytecode.PopMany(len(self.function.args)-1)) # how practical, it keeps the top which just happens to be the return value

    def _gather_locals_from_statement(self, statement):
        if hasattr(statement, "targets"): # assignments
            for t in statement.targets:
                if isinstance(t, ast.Name):
                    yield t.id
        if hasattr(statement, "target"): # for loop
            if isinstance(statement.target, ast.Name):
                yield statement.target.id
        if hasattr(statement, "body"): # blocks
            for s in statement.body:
                for l in self._gather_locals_from_statement(s):
                    yield l

    def _resolve(self, e):
        if isinstance(e, ast.Name):
            if e.id in self.args:
                return self.args[e.id]
            elif e.id in self.locals:
                return self.locals[e.id]
            elif e.id in self.program.globals:
                return self.program.globals[e.id]
            elif e.id in self.program.funcs:
                return self.program.funcs[e.id]
            else:
                raise Exception("Can not resolve name %s"%e.id)
        elif isinstance(e, ast.Attribute):
            leftside = self._resolve(e.value)
            return leftside.getattr(self, e.attr)
        elif isinstance(e, ast.Call):
            func = self._resolve(e.func)
            return func.call(self, e.args, e.keywords, e.starargs, e.kwargs)
        elif isinstance(e, ast.Subscript):
            value = self._resolve(e.value)
            return value.getslice(self, e.slice)
        else:
            raise Exception("Can not resolve %r to a CodeObject"%e)

    def append_push(self, value):
        if isinstance(value, int):
            self.code.append(bytecode.PushConstantV(value=value))
        elif isinstance(value, ast.AST):
            e = value
            if isinstance(e, ast.Name) or isinstance(e, ast.Attribute) or isinstance(e, ast.Subscript) or isinstance(e, ast.Call):
                self._resolve(e).push_value(self)

            elif isinstance(e, ast.Num):
                self.code.append(bytecode.PushConstantV(raising_int(e.n)))

            elif isinstance(e, ast.UnaryOp):
                self.append_push(e.operand)
                if isinstance(e.op, ast.UAdd):
                    return # a no-op in embedvm bytecode
                op2code = {
                        ast.Not: bytecode.LogicNot,
                        ast.Invert: bytecode.BitwiseNot,
                        ast.USub: bytecode.ArithmeticInvert,
                        }
                self.code.append(op2code[type(e.op)]())
            elif isinstance(e, ast.BinOp):
                self.append_push(e.left)
                self.append_push(e.right)
                op2code = {
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
                        ast.And: bytecode.LogicAnd, # TBD: short circuit logic -- easily possible?
                        ast.Or: bytecode.LogicOr,
                        }
                self.code.append(op2code[type(e.op)]())
            elif isinstance(e, ast.Compare):
                # TBD: short circuit logic
                is_first = True
                for (left, right, op) in zip([e.left]+e.comparators[:-1], e.comparators, e.ops):
                    self.append_push(left)
                    self.append_push(right)
                    if op in (ast.Is, ast.IsNot, ast.In, ast.NotIn):
                        raise Exception("Comparison not implemented")
                    op2code = {
                            ast.Eq: bytecode.CompareEE,
                            ast.NotEq: bytecode.CompareNE,
                            ast.Lt: bytecode.CompareLT,
                            ast.Gt: bytecode.CompareGT,
                            ast.LtE: bytecode.CompareLE,
                            ast.GtE: bytecode.CompareGE,
                            }
                    self.code.append(op2code[type(op)]())
                    if not is_first:
                        self.code.append(bytecode.LogicAnd())
                    is_first = False
            else:
                raise Exception("Can not evaluate AST %r"%e)
        else:
            raise Exception("Can not evaluate object %r"%value)

    def _parse_assign(self, s):
        # in any case, evaluate the right side to stack top, then pop it into the left side
        # right side
        self.append_push(s.value)

        # left side
        for x in range(len(s.targets)-1):
            self.code.append(bytecode.Bury(k=0)) # duplicate top element

        for t in s.targets:
            target_obj = self._resolve(t)
            target_obj.pop_set(self)

    def _parse_range(self, s):
        # TBD: empty ranges behave different than in python? (1, -1, 1)
        if not isinstance(s, ast.Call) or not isinstance(s.func, ast.Name) or s.func.id not in ('range', 'xrange'):
            raise Exception("For loops only supported with range iterators")
        if s.starargs or s.keywords or s.kwargs or len(s.args) not in range(1, 4):
            raise Exception("(x)range only supported with 1-3 positional arguments")
        if len(s.args) == 1:
            start, stop, step = ast.Num(n=0), s.args[0], ast.Num(n=1)
        elif len(s.args) == 2:
            start, stop, step = s.args[0], s.args[1], ast.Num(n=1)
        else:
            start, stop, step = s.args

        return start, stop, step

    def _parse(self, s, break_jump=None, continue_jump=None):
        if isinstance(s, ast.Assign):
            self._parse_assign(s)
        elif isinstance(s, ast.For):
            if not isinstance(s.target, ast.Name):
                raise Exception("Iteration over non-locals is not supported.")
            loopcountlocal = self.locals[s.target.id]
            # loop setup
            start, stop, step = self._parse_range(s.iter)
            if isinstance(step, ast.Num) and isinstance(step.n, int):
                self.append_push(stop)
                self.append_push(start)

                loop_compare = bytecode.Label("comp")
                loop_regular_end = bytecode.Label("regend")
                loop_break_end = bytecode.Label("breakend")
                loop_continue = bytecode.Label("continue")
                self.code.append(loop_compare)

                self.code.append(bytecode.Bury(k=0)) # get a copy of start + i*step
                # get a "copy" of end
                self.code.append(bytecode.Dig(k=1))
                self.code.append(bytecode.Bury(k=2))

                if step.n > 0:
                    self.code.append(bytecode.CompareGE())
                else:
                    self.code.append(bytecode.CompareLE())
                self.code.append(bytecode.JumpVIf(address=loop_regular_end.get_ref()))

                # store current iteration counter
                self.code.append(bytecode.Bury(k=0))
                loopcountlocal.pop_set(self)

                # process body
                for iterated_s in s.body:
                    self._parse(iterated_s, loop_break_end, loop_continue)

                # increment counter, jump to top
                self.code.append(loop_continue)
                self.append_push(step)
                self.code.append(bytecode.Add())
                self.code.append(bytecode.JumpV(address=loop_compare.get_ref()))

                self.code.append(loop_regular_end)

                # process else
                for iterated_s in s.orelse:
                    self._parse(iterated_s, break_jump, continue_jump) # TBD: check standard python semantics

                self.code.append(loop_break_end)

                self.code.append(bytecode.DropValue()) # remove start + i*step
                self.code.append(bytecode.DropValue()) # remove stop
            else:
                raise Exception("Variable step not supported")

        elif isinstance(s, ast.If):
            if_end = bytecode.Label("endif")
            if_else = bytecode.Label("else")
            self.append_push(s.test)
            self.code.append(bytecode.JumpVIfNot(address=if_else.get_ref()))
            for iterated_s in s.body:
                self._parse(iterated_s, break_jump, continue_jump)
            if s.orelse:
                self.code.append(bytecode.JumpV(address=if_end.get_ref()))
                self.code.append(if_else)
                for iterated_s in s.orelse:
                    self._parse(iterated_s, break_jump, continue_jump)
                self.code.append(if_end)
            else:
                self.code.append(if_else)

        elif isinstance(s, ast.Expr):
            if isinstance(s.value, ast.Str):
                # a doc string
                pass
            else:
                self.append_push(s.value)
                self.code.append(bytecode.DropValue())

        elif isinstance(s, ast.Pass):
            pass

        elif isinstance(s, ast.While):
            # body, test, orelse
            while_start = bytecode.Label("whilestart")
            while_else = bytecode.Label("whileelse")
            while_end = bytecode.Label("whileend")

            self.code.append(while_start)

            self.append_push(s.test)
            self.code.append(bytecode.JumpVIfNot(address=while_else.get_ref()))

            for iterated_s in s.body:
                self._parse(iterated_s, while_end, while_start)
            self.code.append(bytecode.JumpV(while_start.get_ref()))
            self.code.append(while_else)
            for iterated_s in s.orelse:
                self._parse(iterated_s, break_jump, continue_jump) # TBD: check standard python semantics
            self.code.append(while_end)

        elif isinstance(s, ast.Return):
            if s.value:
                self.append_push(s.value)
                self.code.append(bytecode.Return())
            else:
                self.code.append(bytecode.Return0())

        elif isinstance(s, ast.Continue):
            if continue_jump is None:
                raise Exception("Continue where there is nothing to continue")

            self.code.append(bytecode.JumpV(continue_jump.get_ref()))

        elif isinstance(s, ast.Break):
            if break_jump is None:
                raise Exception("Break where there is nothing to break")

            self.code.append(bytecode.JumpV(break_jump.get_ref()))

        else:
            raise Exception("Unknown statement %r"%s)

    def parse(self):
        # analyze local variables
        local_names = []
        for statement in self.body:
            local_names.extend(self._gather_locals_from_statement(statement))
        self.locals = dict((name, LocalVariable(i)) for (i, name) in enumerate(deduplicate(local_names)))

        if self.locals:
            self.code.append(bytecode.PushZeros(len(self.locals)-1))

        for statement in self.body:
            self._parse(statement)

        if not isinstance(self.code.code[-1], bytecode.Return):
            self.code.append(bytecode.Return0())

class PythonProgram(asm.ASM):
    def __init__(self):
        super(PythonProgram, self).__init__()

        self.globals = {'True': ConstantValue(1), 'False': ConstantValue(0)}
        self.funcs = {}

    def _resolve(self, e):
        if isinstance(e, ast.Name):
            if e.id in self.globals:
                return self.globals[e.id]
            else:
                return UnboundSetter(lambda value: self.globals.__setitem__(e.id, value))
        elif isinstance(e, ast.Attribute):
            leftside = self._resolve(e.value)
            return leftside.getattr(self, e.attr)
        elif isinstance(e, ast.Call):
            func = self._resolve(e.func)
            return func.call(self, e.args, e.keywords, e.starargs, e.kwargs)
        else:
            raise Exception("Can not resolve %r to a CodeObject"%e)

    def _parse_global_statement(self, statement):
        if isinstance(statement, ast.ImportFrom):
            # module, names [name, asname=None]
            realmodule = __import__(statement.module, fromlist=[n.name for n in statement.names])
            for n in statement.names:
                realobject = getattr(realmodule, n.name)

                # these two lines were introduced for embedvm.runtime.Globals,
                # which has two completely different implementations for
                # behaving as a CodeObject or acting in live code execution. if
                # a more beautiful solution is found there, this hack can be
                # dropped
                if hasattr(realobject, 'import_to_codeobject'):
                    realobject = realobject.import_to_codeobject(realobject)

                if not isinstance(realobject, CodeObject) and not (isinstance(realobject, type) and issubclass(realobject, CodeObject)):
                    raise Exception("Can not import %s from %s: not a embedvm.runtime.Importable"%(n.name, statement.module))
                self.globals[n.asname or n.name] = realobject

        elif isinstance(statement, ast.Assign):
            right = self._resolve(statement.value)

            for t in statement.targets:
                target_obj = self._resolve(t)
                target_obj.global_assign(right)

        elif isinstance(statement, ast.FunctionDef):
            f = Function(statement.name, statement.args, statement.body)
            f.program = self
            self.funcs[statement.name] = f
            self.blocks.append(f.code)

        elif isinstance(statement, ast.If):
            if statement.orelse or not isinstance(statement.test, ast.Compare) or len(statement.test.ops) != 1 or not isinstance(statement.test.ops[0], ast.Eq) or not isinstance(statement.test.left, ast.Name) or statement.test.left.id != '__name__' or len(statement.test.comparators) != 1 or not isinstance(statement.test.comparators[0], ast.Str) or statement.test.comparators[0].s != '__main__':
                raise Exception("The only allowed top-level if is an `if __name__ == \"__main__\".")

        else:
            raise Exception("Unknown top level statement %r"%statement)

    def read_python(self, data):
        t = ast.parse(data)

        for statement in t.body:
            self._parse_global_statement(statement)

        for fn, f in self.funcs.items():
            f.parse()

        # merge function blocks so calls can be solved in a relative (short address) way
        bigblock = asm.FreeCodeBlock()
        for f in self.funcs.values():
            self.blocks.remove(f.code)
            bigblock.code.extend(f.code.code)

        self.blocks.append(bigblock)

    def get_symbols(self):
        sym = {}
        for b in self.blocks:
            if hasattr(b, 'sym'):
                sym.update(b.sym)
        return sym
