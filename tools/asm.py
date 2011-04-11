import ast
import bytecode

joining = lambda f: lambda self: "\n".join(f(self))
adding = lambda f: lambda self: sum(f(self), [])
flipped = lambda d: dict((v, k) for (k, v) in d.items())

class ASM(object):
    def __init__(self):
        self.data = []
        self.code = [] # (lineno, command)
        self.jumplabels = {} # address -> label
        self.code_points_called = set()
        self.code_points_jumped_to = set()
        self.unconditional_jumps = [] # (from, to)
        self.conditional_jumps = [] # (from, to)
        self.calls = [] # (from, to)
        self.datalabels = {} # address -> label
        self.accessed_as_s8 = set()
        self.accessed_as_u8 = set()
        self.accessed_as_16 = set()
        self.accessed_as_s8_array = set()
        self.accessed_as_u8_array = set()
        self.accessed_as_16_array = set()

    def read_binary(self, data, code_offset):
        if self.data or self.code:
            raise ValueError("Can't feed an already fed Bin2Asm")
        self.data = data[:code_offset]

        pos = code_offset
        while pos < len(data):
            command = bytecode.interpret(data, pos)
            self.code.append((pos, command))
            if isinstance(command, bytecode.AddressCommand):
                absaddr = pos + command.reladdr
                command.address = self.jumplabels.setdefault(absaddr, ("label_%d" if isinstance(command, bytecode.JumpCommand) else "function_%x")%absaddr)
                del command.reladdr
            elif isinstance(command, bytecode.GlobalAccess):
                if command.address is not None:
                    command.address = self.datalabels.setdefault(command.address, "data_%x"%command.address)
            pos += 1 + command.nargs

        self._analyze_flow()
        self._analyze_globals()

    @joining
    def write_asm(self):
        if self.datalabels:
            if 0 not in self.datalabels:
                yield repr(self.data[:min(self.datalabels)])
            for (start, end) in zip(sorted(self.datalabels)[:-1], sorted(self.datalabels)[1:]):
                yield "%s = %r"%(self.datalabels[start], self.data[start:end])
            yield "%s = %r"%(self.datalabels[max(self.datalabels)], self.data[max(self.datalabels):])
        else:
            yield repr(self.data)

        debug = True
        for pos, c in self.code:
            prefix = "%s = "%self.jumplabels[pos] if pos in self.jumplabels else ""
            code = repr(c)
            if debug:
                linenumber = "    # %04x (%s)"%(pos, " ".join("%02x"%x for x in c.to_bin()) if not hasattr(c, 'address') else " address=%s"%c.address)
            else:
                linenumber = ""
            yield prefix + code + linenumber

    def read_asm(self, data):
        if self.data or self.code:
            raise ValueError("Can't feed an already fed Bin2Asm")

        lines = [ast.parse(l) for l in data.split('\n')]
        pos = 0

        for l in lines:
            if not l.body:
                continue # empty line
            (node, ) = l.body
            (target, ) = getattr(node, 'targets', [None])
            if target is not None:
                target = target.id
            value = node.value

            if isinstance(value, ast.Call):
                assert value.kwargs is None and value.starargs is None

                commandclass = getattr(bytecode, value.func.id)
                assert issubclass(commandclass, bytecode.ByteCodeCommand)

                keywords = dict((k.arg, k.value) for k in value.keywords) if value.keywords else {}

                later_replace_address = None
                for (k, v) in keywords.items():
                    if issubclass(commandclass, bytecode.GlobalAccess) and k == "address" and isinstance(v, ast.Name):
                        keywords["address"] = flipped(self.datalabels)[v.id]
                    elif issubclass(commandclass, bytecode.AddressCommand) and k == "address" and isinstance(v, ast.Name):
                        keywords["reladdr"] = 42 # can't tell yet, will replace command later, faking any address for the moment
                        later_replace_address = keywords.pop("address").id
                    else:
                        keywords[k] = ast.literal_eval(v)

                command = commandclass(**keywords)
                if later_replace_address:
                    def build_replacement(pos=pos, commandclass=commandclass, keywords=keywords, labels=self.jumplabels, address=later_replace_address):
                        keywords["reladdr"] = flipped(labels)[address] - pos
                        return commandclass(**keywords)
                    command._replace_me = build_replacement

                self.code.append((pos, command))
                if target is not None:
                    self.jumplabels[pos] = target

                pos += 1 + command.nargs

            else: # not a call but data
                assert pos == len(self.data), "Can't have data after first command"
                self.datalabels[pos] = target
                value = ast.literal_eval(value)
                self.data.extend(value)
                pos += len(value)

        # print "finished at", pos

        for (i, (pos, c)) in enumerate(self.code):
            if hasattr(c, '_replace_me'):
                self.code[i] = (pos, c._replace_me())

        self._analyze_flow()

    @adding
    def write_binary(self):
        yield self.data
        for l, c in self.code:
            yield c.to_bin()

    def _analyze_flow(self):
        labeljumps = flipped(self.jumplabels)
        for (l, c) in self.code:
            if isinstance(c, bytecode.JumpCommand):
                self.code_points_jumped_to.add(labeljumps[c.address])
                if isinstance(c, bytecode.JumpIfCommand) or isinstance(c, bytecode.JumpIfNotCommand):
                    self.conditional_jumps.append([l, labeljumps[c.address]])
                else:
                    self.unconditional_jumps.append([l, labeljumps[c.address]])
            elif isinstance(c, bytecode.CallCommand):
                self.code_points_called.add(labeljumps[c.address])
                self.calls.append([l, labeljumps[c.address]])

    def _analyze_globals(self):
        type2set = {
                bytecode.GlobalU8: (self.accessed_as_u8, self.accessed_as_u8_array),
                bytecode.GlobalS8: (self.accessed_as_s8, self.accessed_as_s8_array),
                bytecode.Global16: (self.accessed_as_16, self.accessed_as_16_array),
                }
        for (l, c) in self.code:
            if isinstance(c, bytecode.GlobalAccess) and c.address is not None:
                for (t, (s, sa)) in type2set.items():
                    if isinstance(c, t):
                        if c.m in (3, 4):
                            sa.add(c.address)
                        else:
                            s.add(c.address)
