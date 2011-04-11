from base_evm import Globals
import sys

def userfunc(which, *args):
    if which == 0:
        print "Called user function 0 => stop."
        sys.exit(1)

    sys.stdout.write("Called user function %d with %d args:"%(which, len(args)))

    print "".join(" %s"%x for x in args)

    return sum(args) ^ which
