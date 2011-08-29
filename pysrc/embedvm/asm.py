import ast
from . import bytecode
from util import flipped, joining, adding

class UnresolvedReference(object):
    def __init__(self, id):
        self.id = id

    def resolve(self, labels):
        for l in labels:
            if l.id == self.id:
                self.__class__ = bytecode.Label.LabelRef
                self.ref = l
                del self.id
                break
        else:
            raise Exception("Unresolved label")

class DataBlock(object):
    def read_ast(self, data):
        self.data = ast.literal_eval(data)

    length = property(lambda self: len(self.data))

    def to_asm(self):
        return repr(self.to_binary(0))

    def to_binary(self, startpos):
        return self.data

class CodeBlock(object):
    pass

class FreeCodeBlock(CodeBlock):
    def __init__(self):
        self.code = [] # bytecode objects

    @joining
    def to_asm(self):
        for c in self.code:
            code = repr(c)
            yield code

    def append(self, command):
        self.code.append(command)

    def fixed_code(self, code_start):
        positions = [] # self.code index -> code position
        def update_positions():
            positions[:] = []
            pos = code_start
            for command in self.code:
                positions.append(pos)
                pos += command.length

            for (ln, command) in enumerate(self.code):
                if isinstance(command, bytecode.VariableAddressCommand) and isinstance(command.address, bytecode.Label.LabelRef):
                    assert command.address.ref in self.code, "label not found: %r"%command.address
                    command.reladdr = positions[self.code.index(command.address.ref)] - positions[ln]

        update_positions()
        for i in range(2): # one time enhances the positions, two times only enhances corner cases
            for command in self.code:
                if isinstance(command, bytecode.VariableLengthCommand):
                    command.prebake()

            update_positions()

        fixed = FixedPositionCodeBlock()
        for (pos, c) in zip(positions, self.code):
            if isinstance(c, bytecode.Label):
                if c.export:
                    fixed.sym[c.export] = (pos, "code")
                continue
            assert pos not in fixed.code
            fixed.code[pos] = c

        return fixed

class FixedPositionCodeBlock(CodeBlock):
    def __init__(self):
        self.code = {} # position -> bytecode
        self.sym = {} # export label -> (position, type)

    @property
    def length(self):
        maxindex = max(self.code)
        return maxindex + self.code[maxindex].length

    @joining
    def to_asm(self):
        for (lineno, c) in sorted(self.code.items()):
            yield "%-30r# %04x"%(c, lineno)

    def unfixed_code(self):
        labels = {} # position -> label object
        generalized = {} # like self.code

        for lineno, command in sorted(self.code.items()):
            g = command.generalize(lineno)
            if isinstance(g, bytecode.VariableAddressCommand):
                g.address = labels.setdefault(g.address, bytecode.Label()).get_ref()
            generalized[lineno] = g

        newcode = FreeCodeBlock()
        for lineno, command in sorted(generalized.items()):
            if lineno in labels:
                newcode.code.append(labels[lineno])
            newcode.code.append(command)

        return newcode

    @adding
    def to_binary(self, startpos):
        lastpos = startpos
        for (pos, c) in sorted(self.code.items()):
            assert lastpos == pos
            yield c.to_bin()
            lastpos += c.length

class ASM(object):
    def __init__(self):
        self.blocks = []

    def read_binary(self, data, entry_points):
        code = {}
        while entry_points:
            pos = entry_points.pop()
            while True:
                if len(data) < pos or data[pos] is None:
                    break # been there, parsed that
                command = bytecode.interpret(data, pos)
                code[pos] = command
                data[pos:pos+command.length] = [None] * command.length
                if isinstance(command, bytecode.RelativeAddressCommand):
                    entry_points.append(pos + command.reladdr)
                pos += command.length
                if isinstance(command, bytecode.UnconditionalJumpCommand) or isinstance(command, bytecode.Return):
                    break # no reason to parse on

        data_indices = [i for (i, x) in enumerate(data) if x is not None]
        while data_indices:
            start = data_indices[0]
            length = 0
            while length < len(data_indices) and data_indices[length] == start + length:
                # there must be an easier way to do this with itertools...
                length += 1
            data_indices[:length] = []
            datablock = DataBlock()
            datablock.data = data[start:start+length]
            self.blocks.append(datablock)

        while code:
            next = min(code)
            cb = FixedPositionCodeBlock()
            while next in code:
                command = code.pop(next)
                cb.code[next] = command
                next += command.length
            self.blocks.append(cb)

    @joining
    def to_asm(self):
        for b in self.blocks:
            yield b.to_asm()

    def read_asm(self, data):
        nodes = ast.parse(data).body
        pos = 0

        def finish_codebuffer():
            if not codebuffer:
                return

            if pos is None:
                codeblock = FreeCodeBlock()
                for (i, c) in codebuffer:
                    codeblock.code.append(c)
            else:
                codeblock = FixedPositionCodeBlock()
                for (i, c) in codebuffer:
                    assert i not in codeblock.code
                    codeblock.code[i] = c

            self.blocks.append(codeblock)

            codebuffer[:] = []
            while unrefs:
                unrefs.pop().resolve(labels)
            labels[:] = []

        codebuffer = [] # (pos, code)
        labels = []
        unrefs = []
        for node in nodes:
            (target, ) = getattr(node, 'targets', [None])
            if target is not None:
                target = target.id
            value = node.value

            if not isinstance(value, ast.Call):
                finish_codebuffer()
                # assume it's data
                assert pos is not None, "Can not have global data segment after free code"
                datablock = DataBlock()
                datablock.read_ast(value)
                self.blocks.append(datablock)
                pos += datablock.length

            else: # it's a call -- this is code.
                assert value.kwargs is None and value.starargs is None

                commandclass = getattr(bytecode, value.func.id)
                assert issubclass(commandclass, bytecode.ByteCodeCommand)

                keywords = dict((k.arg, k.value) for k in value.keywords) if value.keywords else {}

                for (k, v) in keywords.items():
                    if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == 'LabelRef':
                        ref = UnresolvedReference(ast.literal_eval(v.args[0]))
                        unrefs.append(ref)
                        keywords[k] = ref
                    else:
                        keywords[k] = ast.literal_eval(v)

                command = commandclass(**keywords)

                if isinstance(command, bytecode.Label):
                    labels.append(command)

                codebuffer.append((pos, command))

                if pos is None or isinstance(command, bytecode.VariableLengthCommand):
                    pos = None
                else:
                    pos += command.length
        finish_codebuffer()

    @adding
    def to_binary(self, startpos=0):
        pos = startpos
        for b in self.blocks:
            data = b.to_binary(pos)
            pos += len(data)
            yield data

    def unfix_all(self):
        self.blocks = [b.unfixed_code() if isinstance(b, FixedPositionCodeBlock) else b for b in self.blocks]


    def fix_all(self):
        for i in range(len(self.blocks)):
            if isinstance(self.blocks[i], FreeCodeBlock):
                self.blocks[i] = self.blocks[i].fixed_code(sum(bb.length for bb in self.blocks[:i]))
