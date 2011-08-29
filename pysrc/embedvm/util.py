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

flipped = lambda d: dict((v, k) for (k, v) in d.items())

# decorators
joining = lambda f: lambda self: "\n".join(f(self))
adding = lambda f: lambda *args, **kwargs: sum(f(*args, **kwargs), [])
