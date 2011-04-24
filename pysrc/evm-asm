#!/usr/bin/env python

import os.path
import optparse

from embedvm import asm

def main():
    p = optparse.OptionParser(description="Assemble an EmbedVM program", usage="%prog file.asm [file.bin]")
    (opts, args) = p.parse_args()

    binfile = None
    if len(args) == 1:
        (asmfile, ) = args
    elif len(args) == 2:
        (asmfile, binfile) = args
    else:
        p.error("Wrong number of arguments")

    if binfile is None:
        basename, ext = os.path.splitext(asmfile)
        if ext != ".asm":
            p.error("If the assembly file does not end in '.asm', the binary file name has to be explicitly given.")
        binfile = basename + '.bin'

    a = asm.ASM()
    data = open(asmfile).read()
    a.read_asm(data)
    a.fix_all()
    converted = "".join(map(chr, a.to_binary()))
    with open(binfile, 'w') as f:
        f.write(converted)

if __name__ == "__main__":
    main()
