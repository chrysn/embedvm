#!/usr/bin/env python

import os.path
import optparse

from embedvm import asm

def main():
    p = optparse.OptionParser(description="Disassemble a binary EmbedVM program using the symbol table to determine entry points", usage="%prog file.bin [file.sym [file.asm]]")
    p.add_option("--keep-fixed", action='store_true', help="Keep variable-length commands at their fixed length")
    (opts, args) = p.parse_args()

    symfile = asmfile = None
    if len(args) == 1:
        (binfile, ) = args
    elif len(args) == 2:
        (binfile, symfile) = args
    elif len(args) == 3:
        (binfile, symfile, asmfile) = args
    else:
        p.error("Wrong number of arguments")

    if asmfile is None:
        basename, ext = os.path.splitext(binfile)
        if ext != ".bin":
            p.error("If the binary file does not end in '.bin', symbol and assembly file names have to be explicitly given.")
        asmfile = basename + '.asm'
        if symfile is None:
            symfile = basename + '.sym'

    a = asm.ASM()
    data = map(ord, open(binfile).read())
    entrypoints = [int(addr, 16) for (addr, name, type) in map(str.split, open(symfile)) if type.strip() in ('(code)', '(other)') and name != '_end']
    a.read_binary(data, entrypoints)
    if not opts.keep_fixed:
        a.unfix_all()
    converted = a.to_asm()
    with open(asmfile, 'w') as f:
        f.write(converted)

if __name__ == "__main__":
    main()
