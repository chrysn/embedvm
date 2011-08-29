from .bytecode import signext, assert_signexted
from . import bytecode
from .python import CodeObject, raising_int, UnboundSetter
from .asm import DataBlock
from collections import namedtuple
import ast
from math import ceil

class Importable(CodeObject):
    """All objects that are supposed to be imported into a EVM Python program
    need to subclass this to indicate that they will react properly to code
    generation requests."""

class Ignore(Importable):
    """Parent class for objects that are supposed to be imported, but will only
    be used in __name__ == "__main__" guarded code (that is never parsed by the
    compiler)."""
    def _raise(self):
        raise Exception("Trying to compile ignored code.")

class ignore(Ignore):
    """Function decorator for functions that are supposed to behave like
    Ignore'd objects"""

    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

class _UserfuncWrapper(Importable):
    def __init__(self, which, func):
        self.__which = which
        self.__func = func

    def __call__(self, *args, **kwargs):
        return self.__func(*args, **kwargs)

    def call(self, context, args, keywords, starargs, kwargs):
        return self.PushableUserfunc(self.__which, args, keywords, starargs, kwargs)

    class PushableUserfunc(Importable, namedtuple("PushableData", "which args keywords starargs kwargs")):
        def push_value(self, context):
            if self.keywords or self.starargs or self.kwargs:
                raise Exception("Can not call wrapped user function with non-positional arguments.")
            argv = self.args

            real_args = argv if self.which is not None else argv[1:]
            for a in real_args[::-1]:
                context.append_push(a)
            context.append_push(len(real_args))
            if self.which is None:
                which = raising_int(argv[0].n)
            else:
                which = self.which
            context.code.append(bytecode.CallUserFunction(which))
def UserfuncWrapper(which=None):
    return lambda func: _UserfuncWrapper(which, func)

class _C_Division(Importable):
    """When you need Python to behave like C with respect to divisions, write
    c_division(a, b) instead of a/b. C's behavior with respect to negative
    values of b will be used, as it is used in the VM."""
    def __call__(self, a, b):
        if a > 0 and b < 0:
            return -(a/(-b))
        elif a < 0 and b < 0:
            return a / b
        elif a < 0 and b > 0:
            return -((-a)/b)
        else:
            return a / b
    def call(self, context, args, keywords, starargs, kwargs):
        if keywords or starargs or kwargs or len(args) != 2:
            raise Exception("c_division requires exactly two arguments.")
        return self.Pushable(args)
    class Pushable(Importable):
        def __init__(self, args):
            self.a, self.b = args

        def push_value(self, context):
            context.append_push(self.a)
            context.append_push(self.b)
            context.code.append(bytecode.Div())
c_division = _C_Division()

class Globals(list):
    """Enhanced list of uint8 values that supports the access modes needed for
    the EVM. It also supports views on global arrays and variables.

    While write access to views on arrays can be implemented easily (like
    ``my_array = gv.array16(0); my_array[23] = 42``, a trick is employed to
    implement write access single variables (assigning to which would overwrite
    the binding): If something is assigned to a Globals, it is remembered in
    _known_view. On later assignments, instead of re-assigning, the previously
    assigned value's set function is called with the new value::

        >>> gv = Globals([0]*16)
        >>> gv.foo = gv.array8s(address=0)
        >>> gv.bar = gv.int8s(address=8)
        >>> gv.foo[7] = 10
        >>> gv.bar = 9
    """

    def __init__(self, *args):
        super(Globals, self).__init__(*args)
        self.__dict__['_known_view'] = {}

    def __setattr__(self, key, value):
        if key in self._known_view:
            self.__dict__['_known_view'][key].set(value)
        else:
            self.__dict__['_known_view'][key] = value

    def __getattr__(self, key):
        return self.__dict__['_known_view'][key].get()

    def get16(self, address):
        if len(self) < address+2:
            self.extend([0]*(address+2-len(self)))
        return signext((self[address]<<8) + self[address+1], 0xffff)
    def get8s(self, address):
        if len(self) < address+1:
            self.extend([0]*(address+1-len(self)))
        return signext(self[address], 0xff)
    def get8u(self, address):
        if len(self) < address+1:
            self.extend([0]*(address+1-len(self)))
        return self[address]
    def set16(self, address, value):
        if len(self) < address+2:
            self.extend([0]*(address+2-len(self)))
        assert_signexted(value, 0xffff)
        self[address:address+2] = divmod(value, 0x100)
    def set8s(self, address, value):
        if len(self) < address+1:
            self.extend([0]*(address+1-len(self)))
        assert_signexted(value, 0xff)
        self[address] = value%256
    def set8u(self, address, value):
        if len(self) < address+1:
            self.extend([0]*(address+1-len(self)))
        self[address] = value & 0xff

    array16 = lambda self, address=None, init=None, length=None: self.ArrayView16(self, address, init, length)
    array8u = lambda self, address=None, init=None, length=None: self.ArrayView8u(self, address, init, length)
    array8s = lambda self, address=None, init=None, length=None: self.ArrayView8s(self, address, init, length)
    int16 = lambda self, address=None, init=None: self.SingleView16(self, address, init)
    int8u = lambda self, address=None, init=None: self.SingleView8u(self, address, init)
    int8s = lambda self, address=None, init=None: self.SingleView8s(self, address, init)

    class View(object):
        def __init__(self, gv, address):
            self.gv = gv
            self.address = address if address is not None else len(gv)

    class SingleView(View):
        def __init__(self, gv, address, init_value):
            super(gv.SingleView, self).__init__(gv, address)
            if init_value is None:
                self.set(self.get()) # make sure gv is sized appropriately
            else:
                self.set(init_value)

    class SingleView8s(SingleView):
        get  = lambda self: self.gv.get8s(self.address)
        set = lambda self, value: self.gv.set8s(self.address, value)
    class SingleView8u(SingleView):
        get  = lambda self: self.gv.get8u(self.address)
        set = lambda self, value: self.gv.set8u(self.address, value)
    class SingleView16(SingleView):
        get  = lambda self: self.gv.get16(self.address)
        set = lambda self, value: self.gv.set16(self.address, value)

    class ArrayView(View):
        def __init__(self, gv, address, init_value, length):
            super(gv.ArrayView, self).__init__(gv, address)

            if init_value is not None:
                for (i, x) in enumerate(init_value):
                    self[i] = x
            if length is not None:
                for i in range(length):
                    self[i] = self[i] # make sure gv is long enough
                self.length = length
            if length is None and init_value is None:
                raise Exception("Undespecified array")

        def get(self):
            return self

    class ArrayView8s(ArrayView):
        sizeofelement = 1
        __getitem__ = lambda self, index: self.gv.get8s(self.address + index)
        __setitem__ = lambda self, index, value: self.gv.set8s(self.address + index, value)
    class ArrayView8u(ArrayView):
        sizeofelement = 1
        __getitem__ = lambda self, index: self.gv.get8u(self.address + index)
        __setitem__ = lambda self, index, value: self.gv.set8u(self.address + index, value)
    class ArrayView16(ArrayView):
        sizeofelement = 2
        __getitem__ = lambda self, index: self.gv.get16(self.address + 2*index)
        __setitem__ = lambda self, index, value: self.gv.set16(self.address + 2*index, value)

    @classmethod
    def import_to_codeobject(cls, self):
        # this is a very crude hack
        if cls is self:
            return cls.GlobalCodeObject
        else:
            assert isinstance(self, cls)
            ret = cls.GlobalCodeObject()
            for name, view in sorted(self.__dict__['_known_view'].items(), key=lambda (k, v): v.address):
                viewtype = getattr(ret, type(view).__name__) # luckily they use the same names
                accessor = viewtype(ret).call(None, [ast.Num(n=view.address)], [ast.keyword('length', ast.Num(n=view.length))] if hasattr(view, 'length') else [], None, None)
                ret.getattr(None, name).global_assign(accessor)
            return ret

    @classmethod
    def _raise(self):
        raise Exception("This is a live object, it can't be handled (should have be import_to_codeobject'd by now)")

    class GlobalCodeObject(CodeObject, DataBlock):
        def __init__(self):
            self.assigned = []
            self.named = {} # name -> view object
            self.pos = 0

        length = property(lambda self: self.pos)

        @classmethod
        def call(cls, context, args, keywords, starargs, kwargs):
            if args or keywords or starargs or kwargs:
                raise Exception("Global object can't take any arguments")
            gco = cls()
            context.blocks.append(gco)
            return gco

        def getattr(self, context, attr):
            if attr in self.accessor_types:
                return self.accessor_types[attr](self)
            elif attr in self.named:
                return self.named[attr]
            else:
                def assign_value(value):
                    self.named[attr] = value
                    value.pos = self.pos
                    if value.specified_pos is not None and value.specified_pos != value.pos:
                        raise Exception("Following forced memory alignment is only supported if it fits.")
                    self.pos += value.bytes
                return UnboundSetter(assign_value)

        def to_binary(self, startpos):
            data = [0] * self.pos

            for view in self.named.values():
                view.store_initial_value(data)

            return data

        class View(CodeObject):
            def __init__(self, gv):
                self.gv = gv

            def call(self, context, args, keywords, starargs, kwargs):
                if starargs or kwargs:
                    raise Exception("Can't handle those arguments")
                if len(args) not in (0, 1) or len(args) == 1 and not isinstance(args[0], ast.Num):
                    raise Exception("Can't handle those arguments")
                if args:
                    self.specified_pos = raising_int(args[0].n)
                else:
                    self.specified_pos = None
                keywords_converted = {}
                for k in keywords:
                    keywords_converted[k.arg] = ast.literal_eval(k.value)

                self.init = keywords_converted.pop('init', None)
                if 'length' in keywords_converted:
                    self.length = keywords_converted.pop('length', None)
                if self.length is None and self.init is None:
                    raise Exception("Global variable is underspecified.")

                if self.length is None: # never happens for arrays
                    self.length = len(self.init)

                self.bytes = self.length * self.bytes_per_item

                return self

        class SingleView(View):
            length = 1
            def pop_set(self, context):
                context.code.append(self.store_code(address=self.pos, nargs=1 if self.pos < 256 else 2, popoffset=False))
            def push_value(self, context):
                context.code.append(self.load_code(address=self.pos, nargs=1 if self.pos < 256 else 2, popoffset=False))
        class ArrayView(View):
            length = None
            def getslice(self, context, slice):
                return self.SliceView(self, slice)

            class SliceView(CodeObject):
                def __init__(self, array, slice):
                    self.array = array
                    if not isinstance(slice, ast.Index):
                        raise Exception("Can not deal with non-index slice.")
                    self.slice = slice.value
                def pop_set(self, context):
                    context.append_push(self.slice)
                    context.code.append(self.array.store_code(address=self.array.pos, nargs=1 if self.array.pos < 256 else 2, popoffset=True))
                def push_value(self, context):
                    context.append_push(self.slice)
                    context.code.append(self.array.load_code(address=self.array.pos, nargs=1 if self.array.pos < 256 else 2, popoffset=True))

        class SingleView8s(SingleView):
            bytes_per_item = 1
            store_code = bytecode.GlobalStoreS8
            load_code = bytecode.GlobalLoadS8
            def store_initial_value(self, list):
                if self.init is not None:
                    list[self.pos] = self.init % 256
        class SingleView8u(SingleView):
            bytes_per_item = 1
            store_code = bytecode.GlobalStoreU8
            load_code = bytecode.GlobalLoadU8
            def store_initial_value(self, list):
                if self.init is not None:
                    list[self.pos] = self.init % 256
        class SingleView16(SingleView):
            bytes_per_item = 2
            store_code = bytecode.GlobalStore16
            load_code = bytecode.GlobalLoad16
            def store_initial_value(self, list):
                if self.init is not None:
                    a, b = divmod(self.init, 0x100)
                    a = a % 0x100
                    list[self.pos:self.pos+2] = a, b
        class ArrayView8s(ArrayView):
            bytes_per_item = 1
            store_code = bytecode.GlobalStoreS8
            load_code = bytecode.GlobalLoadS8
            def store_initial_value(self, list):
                if self.init is not None:
                    for (i, v) in enumerate(self.init):
                        list[self.pos + i] = v % 256
        class ArrayView8u(ArrayView):
            bytes_per_item = 1
            store_code = bytecode.GlobalStoreU8
            load_code = bytecode.GlobalLoadU8
            def store_initial_value(self, list):
                if self.init is not None:
                    for (i, v) in enumerate(self.init):
                        list[self.pos + i] = v % 256
        class ArrayView16(ArrayView):
            bytes_per_item = 2
            store_code = bytecode.GlobalStore16
            load_code = bytecode.GlobalLoad16
            def store_initial_value(self, list):
                if self.init is not None:
                    for (i, v) in enumerate(self.init):
                        a, b = divmod(v, 0x100)
                        a = a % 0x100
                        list[self.pos + 2*i:self.pos + 2*i + 2] = a, b

        accessor_types = {
                'int8s': SingleView8s,
                'int8u': SingleView8u,
                'int16': SingleView16,
                'array8s': ArrayView8s,
                'array8u': ArrayView8u,
                'array16': ArrayView16,
                }
