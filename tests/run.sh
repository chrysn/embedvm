#!/bin/bash

verbose=false
evmopt=""

count=0
count_ok=0
count_warn=0
count_error=0

make -s -C ../tools
make -s -C ../vmsrc

while [[ "$1" == -* ]]; do
	if [ "$1" = -v ]; then
		verbose=true
		shift
	fi
	if [ "$1" = -V ]; then
		evmopt="-v"
		shift
	fi
done

if [ $# -eq 0 ]; then
	set -- test_*.evm
fi

function v() {
	echo "+ $*" >&2; "$@"
}

for fn; do
	if [ $# -gt 1 ]; then
		echo; echo "=== $fn ==="
	fi
	v ../tools/evmcomp $fn || exit 1
	v ../pysrc/evm-disasm ${fn%.evm}.bin || echo "WARNING: Disassembling ${fn%.evm}.bin failed." && (( count_warn++ ))
	start=$( grep ' main ' ${fn%.evm}.sym | cut -f1 -d' ' ) 
	if $verbose; then
		v ../vmsrc/evmdemo $evmopt ${fn%.evm}.bin $start
	else
		v ../vmsrc/evmdemo $evmopt ${fn%.evm}.bin $start > ${fn%.evm}.out
		if [ -f ${fn%.evm}.expect ]; then
			if cmp ${fn%.evm}.out ${fn%.evm}.expect; then
				echo "OK: Passed $fn."
				(( count_ok++ ))
			else
				echo "ERROR: Output of $fn was not as expected!"
				(( count_error++ ))
			fi
		else
			echo "WARNING: Can't find ${fn%.evm}.expect."
			(( count_warn++ ))
		fi
		(( count++ ))
	fi
done

if [ $# -gt 1 ]; then
	echo
fi

if [ $count -gt 1 ]; then
	echo "Total: $count, Ok: $count_ok, Warnings: $count_warn, Errors: $count_error"
	echo
fi

[ $count_error -eq 0 ]

