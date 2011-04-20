def assert_signexted(val, mask):
    """Assert that val fits in the range you can get when signext'ing with the
    given mask"""
    assert bin(mask).rstrip('1') == '0b'
    max = mask >> 1
    min = (mask & ~max) | ~mask
    assert min <= val <= max

def signext(val, mask):
    """Use the part of val which is covered by mask (required to be all zeros
    followed by all ones) as a signed value (two's complement)"""
    val = val & mask
    if val & ~(mask>>1):
        val |= ~mask
    return val

class ByteCodeCommand(object):
    # defaul values
    nargs = 0
    commandmask = 0xff

    def __init__(self, command=None):
        pass

    @classmethod
    def check_match(cls, command):
        if not hasattr(cls, 'command'):
            # happens for command groups
            return False
        return (command & cls.commandmask) == cls.command

    def __repr__(self):
        return '%s(%s)'%(type(self).__name__, ', '.join('%s=%s'%(k, v) for (k, v) in vars(self).items()))

    def to_bin(self):
        assert self.commandmask == 0xff
        assert self.nargs == 0
        return [self.command]

class SFACommand(ByteCodeCommand):
    def __init__(self, command=None, sfa=None):
        if command is None:
            self.sfa = int(sfa)
        else:
            self.sfa = signext(command, 0x3f)

        assert_signexted(self.sfa, 0x3f)

    def to_bin(self):
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

def PushConstant(n):
    if -4 <= n < 4:
        return PushImmediate(val=n)
    elif -128 <= n < 127:
        return PushS8(value=n)
    elif 0 <= n < 256:
        return PushU8(value=n)
    elif 0 <= n < 0x10000:
        return Push16(value=n)
    else:
        raise ValueError("Integer overflow")

class PushImmediate(ByteCodeCommand):
    command = 0x90
    commandmask = 0xf8

    def __init__(self, command=None, val=None):
        if command is None:
            self.val = val
        else:
            self.val = signext(command, 0x07)

        assert_signexted(self.val, 0x07)

    def to_bin(self):
        return [self.command | (self.val & 0x07)]

class PushData(ByteCodeCommand):
    pass
class PushU8(PushData):
    command = 0x98
    nargs = 1
    def __init__(self, command=None, arg0=None, value=None):
        if command is None:
            self.value = int(value)
        else:
            self.value = arg0
        assert self.value in xrange(256)

    def to_bin(self):
        return [self.command, self.value]
class PushS8(PushData):
    command = 0x99
    nargs = 1
    def __init__(self, command=None, arg0=None, value=None):
        if command is None:
            self.value = int(value)
        else:
            self.value = signext(arg0, 0xff)
        assert_signexted(self.value, 0xff)

    def to_bin(self):
        return [self.command, self.value%256]
class Push16(PushData):
    command = 0x9a
    nargs = 2
    def __init__(self, command=None, arg0=None, arg1=None, value=None):
        if command is None:
            self.value = int(value)
        else:
            self.value = signext((arg0<<8)+arg1, 0xffff)
        assert_signexted(self.value, 0xffff)

    def to_bin(self):
        return [self.command, ((self.value & 0xffff) >> 8)%256, (self.value & 0xff)%256]

class Return(ByteCodeCommand): command = 0x9b

class Return0(Return): command = 0x9c

class DropValue(ByteCodeCommand): command = 0x9d

class CallAddress(ByteCodeCommand): command = 0x9e
class JumpToAddress(ByteCodeCommand): command = 0x9f

class AddressCommand(ByteCodeCommand):
    def __init__(self, command=None, arg0=None, arg1=None, reladdr=None):
        argmask = 0xffff if self.nargs == 2 else 0xff
        if not command:
            self.reladdr = int(reladdr)
        else:
            self.reladdr = signext((arg0<<8)+arg1 if self.nargs == 2 else arg0, argmask)
        assert_signexted(self.reladdr, argmask)

    def to_bin(self):
        if self.nargs == 2:
            return [self.command, ((self.reladdr & 0xffff) >> 8)%256, (self.reladdr & 0xff)%256]
        else:
            return [self.command, self.reladdr % 256]

class JumpCommand(AddressCommand):
    pass
class UnconditionalJumpCommand(JumpCommand):
    pass
class JumpRel1(UnconditionalJumpCommand):
    command = 0xa0
    nargs = 1
class JumpRel2(UnconditionalJumpCommand):
    command = 0xa1
    nargs = 2
class CallCommand(AddressCommand):
    pass
class CallRel1(CallCommand):
    command = 0xa2
    nargs = 1
class CallRel2(CallCommand):
    command = 0xa3
    nargs = 2
class JumpIfCommand(JumpCommand):
    pass
class JumpRel1If(JumpIfCommand):
    command = 0xa4
    nargs = 1
class JumpRel2If(JumpIfCommand):
    command = 0xa5
    nargs = 2
class JumpIfNotCommand(JumpCommand):
    pass
class JumpRel1IfNot(JumpIfNotCommand):
    command = 0xa6
    nargs = 1
class JumpRel2IfNot(JumpIfNotCommand):
    command = 0xa7
    nargs = 2

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

    def __init__(self, command=None, funcid=None):
        if command is None:
            self.funcid = int(funcid)
        else:
            self.funcid = command & 0x0f

        assert self.funcid in xrange(16)

    def to_bin(self):
        return [self.command | (self.funcid & 0x0f)]

class GlobalAccess(ByteCodeCommand):
    commandmask = 0xf8
    nargs = 2 # or 1 or 0, will be overwritten by instances which know their exact mode

    M2NARGSPOP = {0: (1, False), 1: (2, False), 2: (0, True), 3: (1, True), 4: (2, True)}
    NARGSPOP2M = dict((v, k) for (k, v) in M2NARGSPOP.items())

    def __init__(self, command=None, arg0=None, arg1=None, nargs=None, popoffset=None, address=None):
        if command is None:
            self.popoffset = bool(popoffset)
            self.nargs = nargs
            self.address = None if nargs == 0 else address
        else:
            m = command & 0x07

            self.nargs, self.popoffset = self.M2NARGSPOP[m]

            if self.nargs == 0:
                self.address = None
            elif self.nargs == 1:
                self.address = arg0
            elif self.nargs == 2:
                self.address = (arg0 << 8) | arg1

        if self.nargs == 0:
            assert self.address == None
        elif self.nargs == 1:
            assert self.address in xrange(1<<8)
        elif self.nargs == 2:
            assert self.address in xrange(1<<16)

    @classmethod
    def check_match(cls, command):
        return super(GlobalAccess, cls).check_match(command) and command & 0x7 in (0, 1, 2, 3, 4)

    def to_bin(self):
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

    def __init__(self, command=None, k=None):
        if command is None:
            self.k = int(k)
        else:
            self.k = (command & 0x38) >> 3

        assert self.k in xrange(6)

    @classmethod
    def check_match(cls, command):
        return super(StackAccess, cls).check_match(command) and command & 0x7 in (5, 6) and ((command & 0x38) >> 3) in xrange(6)

    def to_bin(self):
        return [self.command | (self.k & 0x07) << 3]

class Bury(StackAccess): command = 0xc5
class Dig(StackAccess): command = 0xc6

class StackShoveling(ByteCodeCommand):
    commandmask = 0xf8

    def __init__(self, command=None, n=None):
        if command is None:
            self.n = int(n)
        else:
            self.n = command & 0x07

        assert self.n in range(8)

    def to_bin(self):
        return [self.command | (self.n & 0x07)]

class PushZeros(StackShoveling):
    command = 0xf0

class PopMany(StackShoveling):
    command = 0xf8

def interpret(commandbuffer, index):
    command = commandbuffer[index]
    candidates = []
    for c in globals().values():
        if type(c) == type and issubclass(c, ByteCodeCommand):
            if c.check_match(command):
                candidates.append(c)
    if not candidates:
        print "unknown command: %x"%command # FIXME
        return None
    if len(candidates) > 1:
        raise Exception("Multiple matches for command %x"%command)

    (commandclass, ) = candidates

    return commandclass(command, *commandbuffer[index+1:index+1+commandclass.nargs])

def test():
    for c in range(256):
        commandbuffer = [c, 233, 253]
        command = interpret(commandbuffer, 0)
        if command is None:
            continue
        r = repr(command)
        print r
        assert repr(eval(r)) == r
        assert repr(interpret(command.to_bin(), 0)) == r

if __name__ == "__main__":
    test()
