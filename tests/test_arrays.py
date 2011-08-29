from embedvm.runtime import Globals
from testsuite import userfunc, end

gv = Globals()
gv.a8u = gv.array8u(init=[1, 2, 3, 4, 5])
gv.a8s = gv.array8s(init=[-1, -2, -3, -4, -5])
gv.a16 = gv.array16(init=[1000, 2000, 3000, 4000, 5000])

def pr():
    for i in range(5):
        userfunc(1, gv.a8u[i], gv.a8s[i], gv.a16[i])
    userfunc(2)

def main():
    pr()

    for i in range(5):
        gv.a8u[i] = gv.a8u[i] + 1 # TBD: +=
        gv.a8s[i] = gv.a8s[i] - 1
        gv.a16[i] = gv.a16[i] - gv.a8s[i] # TBD: -=, --

    pr()

    for i in range(5):
        gv.a8u[i] = 200 + i
        if i & 1: # TBD: b if a else c
            gv.a8s[i] = 100 * -1
        else:
            gv.a8s[i] = 100 * 1
        gv.a16[i] = 111 * (i+1)

    pr()

if __name__ == "__main__":
    main()
    end()
