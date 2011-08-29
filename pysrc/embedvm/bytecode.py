import copy

from util import signext, assert_signexted

class UnknownCommand(Exception):
    """A byte sequence was attempted to parse that has no byte code command associated"""

class ByteCodeCommand(object):
    # defaul values
    nargs = 0
    length = property(lambda self: self.nargs + 1)
    commandmask = 0xff

    @classmethod
    def from_bin(cls, data, offset):
        assert cls.check_match(data[offset])
        instance = ByteCodeCommand()
        instance.__class__ = cls
        instance.set_from_data(data, offset)

        instance._check()
        return instance

    @classmethod
    def check_match(cls, command):
        if not hasattr(cls, 'command'):
            # happens for command groups like BinaryOperator
            return False
        return (command & cls.commandmask) == cls.command

    def __repr__(self):
        # generic initialize-by-__dict__
        return '%s(%s)'%(type(self).__name__, ', '.join('%s=%r'%(k, v) for (k, v) in vars(self).items()))

    ############ defaults for trivial cases ############

    def to_bin(self):
        assert self.commandmask == 0xff
        assert self.nargs == 0
        return [self.command]

    def _check(self):
        pass

    def set_from_data(self, data, offset):
        assert self.commandmask == 0xff
        assert self.nargs == 0
        pass

    def generalize(self, own_position):
        """Return a copy of self, possibly modified to a more general
        command that has the same semantics but not necessarily a
        defined length"""
        return copy.copy(self)

class VariableLengthCommand(ByteCodeCommand):
    """Command that has different length versions depending on the exact
    payload"""
    def _get_real_command(self):
        """Return a proper ByteCodeCommand, use current .nargs for determining
        the length requirements."""
        raise NotImplementedError

    nargs = None

    def to_bin(self):
        real = self._get_real_command() # if the worst case was wrong, this will raise an error e.g. from assert_signexted
        ret = real.to_bin()
        if len(ret) != self.length:
            raise Exception("_get_real_command didn't respect nargs")
        return ret

class SFACommand(ByteCodeCommand):
    def __init__(self, sfa):
        self.sfa = sfa

    def set_from_data(self, data, offset):
        self.sfa = signext(data[offset], 0x3f)

    def _check(self):
        assert_signexted(self.sfa, 0x3f)

    def to_bin(self):
        self._check()
        return [self.command | (self.sfa & 0x3f)]

class PushLocal(SFACommand):
    command = 0x00
    commandmask = 0xc0

class PopLocal(SFACommand):
    command = 0x40
    commandmask = 0xc0

class UnaryOperator(ByteCodeCommand):
    pass

class BitwiseNot(UnaryOperator): command = 0x8c
class ArithmeticInvert(UnaryOperator): command = 0x8d
class LogicNot(UnaryOperator): command = 0x8e

class BinaryOperator(ByteCodeCommand):
    pass

class Add(BinaryOperator): command = 0x80
class Sub(BinaryOperator): command = 0x81
class Mul(BinaryOperator): command = 0x82
class Div(BinaryOperator): command = 0x83
class Mod(BinaryOperator): command = 0x84
class ShiftLeft(BinaryOperator): command = 0x85
class ShiftRight(BinaryOperator): command = 0x86
class BitwiseAnd(BinaryOperator): command = 0x87
class BitwiseOr(BinaryOperator): command = 0x88
class BitwiseXor(BinaryOperator): command = 0x89
class LogicAnd(BinaryOperator): command = 0x8a
class LogicOr(BinaryOperator): command = 0x8b

class PushConstant(ByteCodeCommand):
    def generalize(self, own_position):
        return PushConstantV(value=self.value)

class PushConstantV(VariableLengthCommand):
    def __init__(self, value):
        self.value = value
    nargs = 2 # maximum

    def _get_real_command(self):
        if self.nargs == 2:
            return Push16(value=self.value)
        elif self.nargs == 1:
            if self.value < 128:
                return PushS8(value=self.value)
            else:
                return PushU8(value=self.value)
        else:
            return PushImmediate(value=self.value)

    def prebake(self):
        if -4 <= self.value < 4:
            self.nargs = 0
        elif -128 <= self.value < 256: # will either be signed or unsigned
            self.nargs = 1
        elif -0x8000 <= self.value < 0x10000: # will accept both negative signed limit and positive unsigned, as machine size integers work as both for the VM, and using positive or negative sign helps showing what is meant
            self.nargs = 2
        else:
            raise ValueError("Integer overflow")

class PushImmediate(PushConstant):
    command = 0x90
    commandmask = 0xf8

    def __init__(self, value):
        self.value = value

    def set_from_data(self, data, offset):
        self.value = signext(data[offset], 0x07)

    def _check(self):
        assert_signexted(self.value, 0x07)

    def to_bin(self):
        self._check()
        return [self.command | (self.value & 0x07)]

class PushData(PushConstant):
    pass

class PushU8(PushData):
    command = 0x98
    nargs = 1
    def __init__(self, value=None):
        self.value = value

    def set_from_data(self, data, offset):
        self.value = data[offset+1]

    def _check(self):
        assert self.value in xrange(256)

    def to_bin(self):
        self._check()
        return [self.command, self.value]

class PushS8(PushData):
    command = 0x99
    nargs = 1
    def __init__(self, value):
        self.value = value

    def set_from_data(self, data, offset):
        self.value = signext(data[offset+1], 0xff)

    def _check(self):
        assert_signexted(self.value, 0xff)

    def to_bin(self):
        self._check()
        return [self.command, self.value%256]

class Push16(PushData):
    command = 0x9a
    nargs = 2
    def __init__(self, value):
        self.value = value

    def set_from_data(self, data, offset):
        self.value = signext((data[offset+1]<<8)+data[offset+2], 0xffff)

    def _check(self):
        assert_signexted(self.value, 0xffff)

    def to_bin(self):
        self._check()
        return [self.command, ((self.value & 0xffff) >> 8)%256, (self.value & 0xff)%256]

class Return(ByteCodeCommand): command = 0x9b

class Return0(Return): command = 0x9c

class DropValue(ByteCodeCommand): command = 0x9d

class CallAddress(ByteCodeCommand): command = 0x9e
class JumpToAddress(ByteCodeCommand): command = 0x9f

class VariableAddressCommand(VariableLengthCommand):
    def __init__(self, address):
        self.address = address
    nargs = 2 # worst case

    def prebake(self):
        if -128 <= self.reladdr < 128:
            self.nargs = 1
        else:
            self.nargs = 2

    def _get_real_command(self):
        if self.nargs == 1:
            return self.shortcommand(reladdr=self.reladdr)
        else:
            return self.longcommand(reladdr=self.reladdr)

class RelativeAddressCommand(ByteCodeCommand):
    def __init__(self, reladdr):
        self.reladdr = reladdr

    def generalize(self, own_position):
        return self.generalized(address=own_position + self.reladdr)

class RelativeAddressCommand1(RelativeAddressCommand):
    nargs = 1
    def set_from_data(self, data, offset):
        self.reladdr = signext(data[offset+1], 0xff)

    def _check(self):
        assert_signexted(self.reladdr, 0xff)

    def to_bin(self):
        self._check()
        return [self.command, self.reladdr % 256]

class RelativeAddressCommand2(RelativeAddressCommand):
    nargs = 2
    def set_from_data(self, data, offset):
        self.reladdr = signext((data[offset+1]<<8)+data[offset+2], 0xffff)

    def _check(self):
        assert_signexted(self.reladdr, 0xffff)

    def to_bin(self):
        self._check()
        return [self.command, ((self.reladdr & 0xffff) >> 8)%256, (self.reladdr & 0xff)%256]

class JumpCommand(object):
    pass
class UnconditionalJumpCommand(JumpCommand):
    pass
class JumpV(UnconditionalJumpCommand, VariableAddressCommand):
    pass
class JumpRel1(UnconditionalJumpCommand, RelativeAddressCommand1):
    command = 0xa0
    generalized = JumpV
class JumpRel2(UnconditionalJumpCommand, RelativeAddressCommand2):
    command = 0xa1
    generalized = JumpV
JumpV.shortcommand, JumpV.longcommand = JumpRel1, JumpRel2
class CallCommand(object):
    pass
class CallV(CallCommand, VariableAddressCommand):
    pass
class CallRel1(CallCommand, RelativeAddressCommand1):
    command = 0xa2
    generalized = CallV
class CallRel2(CallCommand, RelativeAddressCommand2):
    command = 0xa3
    generalized = CallV
CallV.shortcommand, CallV.longcommand = CallRel1, CallRel2
class JumpIfCommand(JumpCommand):
    pass
class JumpVIf(JumpIfCommand, VariableAddressCommand):
    pass
class JumpRel1If(JumpIfCommand, RelativeAddressCommand1):
    command = 0xa4
    generalized = JumpVIf
class JumpRel2If(JumpIfCommand, RelativeAddressCommand2):
    command = 0xa5
    generalized = JumpVIf
JumpVIf.shortcommand, JumpVIf.longcommand = JumpRel1If, JumpRel2If
class JumpIfNotCommand(JumpCommand):
    pass
class JumpVIfNot(JumpIfNotCommand, VariableAddressCommand):
    pass
class JumpRel1IfNot(JumpIfNotCommand, RelativeAddressCommand1):
    command = 0xa6
    generalized = JumpVIfNot
class JumpRel2IfNot(JumpIfNotCommand, RelativeAddressCommand2):
    command = 0xa7
    generalized = JumpVIfNot
JumpVIfNot.shortcommand, JumpVIfNot.longcommand = JumpRel1IfNot, JumpRel2IfNot

class CompareLT(BinaryOperator): command = 0xa8
class CompareLE(BinaryOperator): command = 0xa9
class CompareEE(BinaryOperator): command = 0xaa
class CompareNE(BinaryOperator): command = 0xab
class CompareGE(BinaryOperator): command = 0xac
class CompareGT(BinaryOperator): command = 0xad

class StackPointer(ByteCodeCommand):
    command = 0xae
class StackFramePointer(ByteCodeCommand):
    command = 0xaf

class CallUserFunction(ByteCodeCommand):
    command = 0xb0
    commandmask = 0xf0

    def __init__(self, funcid):
        self.funcid = funcid

    def set_from_data(self, data, offset):
        self.funcid = data[offset] & 0x0f

    def _check(self):
        assert self.funcid in xrange(16)

    def to_bin(self):
        self._check()
        return [self.command | (self.funcid & 0x0f)]

class GlobalAccess(ByteCodeCommand):
    commandmask = 0xf8
    nargs = 2 # or 1 or 0, will be overwritten by instances which know their exact mode

    M2NARGSPOP = {0: (1, False), 1: (2, False), 2: (0, True), 3: (1, True), 4: (2, True)}
    NARGSPOP2M = dict((v, k) for (k, v) in M2NARGSPOP.items())

    def __init__(self, nargs, popoffset, address=None):
        self.popoffset = popoffset
        self.nargs = nargs
        self.address = address # may be None if nargs == 0, in which case popoffset has to be true

    def set_from_data(self, data, offset):
        m = data[offset] & 0x07

        self.nargs, self.popoffset = self.M2NARGSPOP[m]

        if self.nargs == 0:
            self.address = None
        elif self.nargs == 1:
            self.address = data[offset+1]
        elif self.nargs == 2:
            self.address = (data[offset+1] << 8) | data[offset+2]

    def _check(self):
        if self.nargs == 0:
            assert self.address == None
            assert self.popoffset
        elif self.nargs == 1:
            assert self.address in xrange(1<<8)
        elif self.nargs == 2:
            assert self.address in xrange(1<<16)

    @classmethod
    def check_match(cls, command):
        return super(GlobalAccess, cls).check_match(command) and command & 0x7 in (0, 1, 2, 3, 4)

    def to_bin(self):
        self._check()
        if self.nargs == 0:
            return [self.command | self.NARGSPOP2M[self.nargs, self.popoffset]]
        elif self.nargs == 1:
            return [self.command | self.NARGSPOP2M[self.nargs, self.popoffset], self.address]
        elif self.nargs == 2:
            return [self.command | self.NARGSPOP2M[self.nargs, self.popoffset], self.address>>8, self.address%256]

class GlobalLoad(GlobalAccess): pass
class GlobalStore(GlobalAccess): pass
class GlobalU8(GlobalAccess): pass
class GlobalS8(GlobalAccess): pass
class Global16(GlobalAccess): pass
class GlobalLoadU8(GlobalLoad, GlobalU8): command = 0xc0
class GlobalStoreU8(GlobalStore, GlobalU8): command = 0xc8
class GlobalLoadS8(GlobalLoad, GlobalS8): command = 0xd0
class GlobalStoreS8(GlobalStore, GlobalS8): command = 0xd8
class GlobalLoad16(GlobalLoad, Global16): command = 0xe0
class GlobalStore16(GlobalStore, Global16): command = 0xe8

class StackAccess(ByteCodeCommand):
    commandmask = 0xc7

    def __init__(self, k):
        self.k = k

    def set_from_data(self, data, offset):
        self.k = (data[offset] & 0x38) >> 3

    def _check(self):
        assert self.k in xrange(6)

    @classmethod
    def check_match(cls, command):
        return super(StackAccess, cls).check_match(command) and command & 0x7 in (5, 6) and ((command & 0x38) >> 3) in xrange(6)

    def to_bin(self):
        self._check()
        return [self.command | (self.k & 0x07) << 3]

class Bury(StackAccess): command = 0xc5
class Dig(StackAccess): command = 0xc6

class StackShoveling(ByteCodeCommand):
    commandmask = 0xf8

    def __init__(self, n):
        self.n = n

    def set_from_data(self, data, offset):
        self.n = data[offset] & 0x07

    def _check(self):
        assert self.n in range(8)

    def to_bin(self):
        self._check()
        return [self.command | (self.n & 0x07)]

class PushZeros(StackShoveling):
    command = 0xf0

class PopMany(StackShoveling):
    command = 0xf8

class Label(ByteCodeCommand):
    """Like a byte code, but results in null-length bytecode and can be used
    for jump calculations"""
    __instancecounter = 0

    nargs = None
    length = 0
    export = None

    def __init__(self, descr=None, id=None, export=None):
        if descr is not None:
            self.descr = descr # for debugging purposes
        type(self).__instancecounter += 1
        self.id = id or "label%d"%self.__instancecounter
        if export is not None:
            self.export = export

    def to_bin(self):
        return []

    def get_ref(self):
        return self.LabelRef(self)

    class LabelRef(object):
        """Reference to a label"""

        def __init__(self, ref):
            self.ref = ref

        def __repr__(self):
            # this is not how they are constructed, but they can't be constructed directly anyway
            return "LabelRef(%r)"%self.ref.id

def interpret(commandbuffer, index):
    command = commandbuffer[index]
    candidates = []
    for c in globals().values():
        if type(c) == type and issubclass(c, ByteCodeCommand):
            if c.check_match(command):
                candidates.append(c)
    if not candidates:
        raise UnknownCommand(command)
    if len(candidates) > 1:
        raise Exception("Multiple matches for command %x"%command)

    (commandclass, ) = candidates

    return commandclass.from_bin(commandbuffer, index)

def test():
    for c in range(256):
        commandbuffer = [c, 233, 253]
        try:
            command = interpret(commandbuffer, 0)
        except UnknownCommand:
            print "Command %02x is unknown"%c
            continue
        r = repr(command)
        print r
        assert repr(eval(r)) == r
        b = command.to_bin()
        assert repr(interpret(b, 0)) == r
        assert b == commandbuffer[:command.length]

if __name__ == "__main__":
    test()
