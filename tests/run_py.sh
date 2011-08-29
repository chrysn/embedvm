#!/bin/bash

verbose=false
evmopt=""
export PYTHONPATH=../pysrc/:.

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
	set -- test_*.py
fi

function v() {
	echo "+ $*" >&2; "$@"
}

for fn; do
	if [ $# -gt 1 ]; then
		echo; echo "=== $fn ==="
	fi
        v python $fn > $fn.out-native

	v ../pysrc/evm-pycomp $fn ${fn}.bin ${fn}.sym --asmfile ${fn}.asm --asmfixfile ${fn}.asm-fix || exit 1
	start=$( grep ' main ' ${fn}.sym | cut -f1 -d' ' ) 
	if $verbose; then
		v ../vmsrc/evmdemo $evmopt ${fn}.bin $start
	else
		v ../vmsrc/evmdemo $evmopt ${fn}.bin $start > ${fn}.out
		if [ -f ${fn%.py}.expect ]; then
			if cmp ${fn%.evm}.out-native ${fn%.py}.expect; then
				echo "OK: Native passed $fn."
				(( count_ok++ ))
			else
				echo "ERROR: Native output of $fn was not as expected!"
				(( count_error++ ))
			fi

			if cmp ${fn%.evm}.out ${fn%.py}.expect; then
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

