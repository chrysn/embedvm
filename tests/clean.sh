#!/bin/bash
for x in test_*.evm; do
	x=${x%.evm}
	rm -f $x.bin $x.sym $x.ihx $x.dbg $x.ast $x.hdr $x.out $x.asm
done
for x in test_*.py; do
	rm -f $x.bin $x.sym $x.out $x.out-native $x.asm $x.asm-fix
done
rm -f evmdemo.core
rm -f testsuite.pyc testsuite_extended.pyc
