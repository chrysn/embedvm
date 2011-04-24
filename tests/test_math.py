from embedvm.runtime import Globals, c_division
from testsuite import userfunc as uf, end

gv = Globals()
gv.ghundret = gv.int16(init=100)

def fibonacci(n, m=42):
    """this is probaly the stupidiest way to calculate a
    fibonacci number - but it is a nice recursion test.."""
    if n < 2:
        return n
    return fibonacci(n-2) + fibonacci(n-1)

def main():
    one = 1
    two = one
    two = two + 1 # TBD: ++

    thousand = two * 500
    negthousand = -thousand

    uf(1, 1+1*2)
    uf(1, one + one * two)
    uf(1, thousand / gv.ghundret)
    uf(1, c_division(0x7fff, negthousand))
    uf(1, c_division(-0x7fff, thousand))
    uf(1, c_division(-0x7fff, negthousand))

    uf(1, fibonacci(6))

if __name__ == "__main__":
    main()
    end()
