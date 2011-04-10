from bytecode import signext, assert_signexted

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
            # if neither init_value nor length are set, we are either in disassembled code or it is a null length array

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

def userfunc(whichone, *argv):
    print "calling userfunc %d with arguments %s"%(whichone, argv)
    return 1234

    print "what should i return?"
    i = raw_input()
    return int(i) if i else 0
