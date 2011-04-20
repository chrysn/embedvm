from evm import Globals, userfunc as uf

gv = Globals()
gv.toggling = gv.int8s(init=42)
gv.data = gv.array16(length=10)

def toggle():
    temporary = not gv.toggling
    gv.toggling = temporary

def main():
    for i in range(16):
        toggle()

    for i in xrange(16, 0, -2):
        uf(1, i)

    x = 42
    if x == 0:
        pass
    else:
        gv.data[1] = x + 4
    gv.data[4] = gv.data[5] + gv.data[1]
    x = x - gv.data[4] # TBD: -=
    uf(2, gv.data[4], x)
    x = 50
    while x > 0:
        y = x/2 + 1
        x = x - y # TBD: -=

if __name__ == "__main__":
    main()
