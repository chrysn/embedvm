from bytecode import *

PushLocal.to_python = lambda self: ("lv.append(arguments[%d])" if self.sfa < 0 else "lv.append(lv[%d])")%self.sfa
PopLocal.to_python = lambda self: ("arguments[%d] = lv.pop()" if self.sfa < 0 else "lv[%d] = lv.pop()")%self.sfa

UnaryOperator.to_python = lambda self: "lv.append(%slv.pop())"%self.python_operator
BitwiseNot.python_operator = '~',
ArithmeticInvert.python_operator = '-'
LogicNot.python_operator = '!'

BinaryOperator.to_python = lambda self: "swap = lv.pop(); lv.append(lv.pop() %s swap)"%self.python_operator
Add.python_operator = '+'
Sub.python_operator = '-'
Mul.python_operator = '*'
Div.python_operator = '/'
Mod.python_operator = '%'
ShiftLeft.python_operator = '<<'
ShiftRight.python_operator = '>>'
BitwiseAnd.python_operator = '&'
BitwiseOr.python_operator = '|'
BitwiseXor.python_operator = '^'
LogicAnd.python_operator = 'and'
LogicOr.python_operator = 'or'

CompareLT.python_operator = '<'
CompareLE.python_operator = '<='
CompareEE.python_operator = '=='
CompareNE.python_operator = '!='
CompareGE.python_operator = '>='
CompareGT.python_operator = '>'

PushImmediate.to_python = lambda self: "lv.append(%d)"%self.val
PushData.to_python = lambda self: "lv.append(%d)"%self.value

# can also be done using function calling convention
Return.to_python = lambda self: "return lv.pop()"
Return0.to_python = lambda self: "return 0"

DropValue.to_python = lambda self: "lv.pop()"

CallAddress.to_python = lambda self: "raise Exception(\"Can't call address %d.\"%lv.pop())"
JumpToAddress.to_python = lambda self: "raise Exception(\"Can't jump to address %d.\"%lv.pop())"

JumpCommand.to_python = lambda self: "goto .%s"%self.address
CallCommand.to_python = lambda self: "lv.append(%s([], lv))"%self.address
JumpIfCommand.to_python = lambda self: "if lv.pop():\n    goto .%s"%self.address # linebreak: python goto module has problems with one-line if/goto statemeents
JumpIfNotCommand.to_python = lambda self: "if not lv.pop():\n    goto .%s"%self.address

CallUserFunction.to_python = lambda self: "lv.append(userfunc(%d, *(lv.pop() for x in range(lv.pop()))))"%self.funcid

def _GA_to_python(self):
    if self.m < 2:
        accessor = "gv.%s"%self.address
    else:
        if isinstance(self, GlobalStore):
            accessor = "index = lv.pop(); gv.%s[index]"%self.address
        else:
            accessor = "gv.%s[lv.pop()]"%self.address

    if isinstance(self, GlobalLoad):
        return 'lv.append(%s)'%accessor
    else:
        return '%s = lv.pop()'%accessor

GlobalAccess.to_python = _GA_to_python

Bury.to_python = lambda self: "lv.insert(-%d, lv[-1])"%(self.k+1)
Dig.to_python = lambda self: "lv.append(lv.pop(-%d))"%(self.k+2)

PushZeros.to_python = lambda self: "lv.extend([0]*%d)"%(self.n+1)
PopMany.to_python = lambda self: "lv[-%d:-1] = []"%(self.n+2)

from asm import ASM, joining, flipped

@joining
def _ASM_get_python(self):
    header = """\
from goto import goto, label
from evm import userfunc, Globals

lv = []
"""

    yield header
    yield "gv = Globals(%r)"%self.data

    classification = dict(
            int8s=self.accessed_as_s8,
            int8u=self.accessed_as_u8,
            int16=self.accessed_as_16,
            array8s=self.accessed_as_s8_array,
            array8u=self.accessed_as_u8_array,
            array16=self.accessed_as_16_array,
            )
    if len(reduce(lambda a, b: a.union(b), classification.values())) < sum(len(x) for x in classification.values()):
        raise Exception("Can't handle global that is accessed in different ways.")
    for (funcname, points) in classification.items():
        for addr in points:
            yield "gv.%s = gv.%s(%d)"%(addr, funcname, flipped(self.datalabels)[addr])

    indent = 0
    previous_command = None
    for (l, c) in self.code:
        if l in self.code_points_called:
            assert previous_command is None or isinstance(previous_command, UnconditionalJumpCommand) or isinstance(previous_command, Return)
            indent = 0
            yield "def %s(lv, arguments):"%self.jumplabels[l]
            indent = 1
        if l in self.code_points_jumped_to:
            yield "    "*indent + "label .%s"%self.jumplabels[l]

        if indent or not isinstance(c, Return):
            yield "    "*indent + c.to_python().replace('\n', '\n'+"    "*indent)
        else:
            yield "# main quit"

        if isinstance(c, Return):

            # exit the function if this is unconditional -- this is only needed
            # for the last function which is followed by the first body code

            is_unconditional = True
            for start, end in self.conditional_jumps + self.unconditional_jumps:
                if end > l and start < l:
                    is_unconditional = False

            if is_unconditional:
                indent = 0

        previous_command = c

ASM.get_python = _ASM_get_python
