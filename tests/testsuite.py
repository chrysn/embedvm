from embedvm.runtime import UserfuncWrapper, ignore
import sys

@UserfuncWrapper()
def userfunc(which, *args):
    if which == 0:
        print "Called user function 0 => stop."
        sys.exit(1)

    sys.stdout.write("Called user function %d with %d args:"%(which, len(args)))

    print "".join(" %d"%x for x in args)

    return sum(args) ^ which

@ignore
def end():
    print "Main function returned => Terminating."
