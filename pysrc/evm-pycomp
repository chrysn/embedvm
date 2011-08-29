#!/usr/bin/env python

import os.path
import optparse
from embedvm.python import PythonProgram

def main():
    p = optparse.OptionParser(description="Compile a simple Python program to EmbedVM byte code", usage="%prog file.py [file.bin [file.sym]]")
    p.add_option("--asmfile", help="Export the assembly code in F", metavar='F')
    p.add_option("--asmfixfile", help="Export the assembly code with fixed command lengths in F", metavar='F')
    (opts, args) = p.parse_args()

    binfile = symfile = None
    if len(args) == 1:
        (pyfile, ) = args
    elif len(args) == 2:
        (pyfile, binfile) = args
    elif len(args) == 3:
        (pyfile, binfile, symfile) = args
    else:
        p.error("Wrong number of arguments")

    if symfile is None:
        basename, ext = os.path.splitext(pyfile)
        if ext != ".py":
            p.error("If the Python file does not end in '.py', the binary and symbol file names have to be explicitly given.")
        symfile = basename + '.sym'
        if binfile is None:
            binfile = basename + '.bin'

    pb = PythonProgram()
    pb.read_python(open(pyfile).read())
    if opts.asmfile:
        converted = pb.to_asm()
        with open(opts.asmfile, 'w') as f:
            f.write(converted)
    pb.fix_all()
    if opts.asmfile:
        converted = pb.to_asm()
        with open(opts.asmfixfile, 'w') as f:
            f.write(converted)
    converted = pb.to_binary()
    with open(binfile, 'w') as f:
        f.write("".join(chr(x) for x in converted))
    with open(symfile, 'w') as f:
        f.write("".join("%04x %s (%s)\n"%(v, k, type) for (k, (v, type)) in pb.get_symbols().items()))

if __name__ == "__main__":
    main()
