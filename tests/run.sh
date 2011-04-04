#!/bin/bash

make -s -C ../tools
make -s -C ../vmsrc

if [ $# -eq 0 ]; then
	set -- test_*.evm
fi

function v() {
	echo "+ $*" >&2; "$@"
}

for fn; do
	echo; echo "=== $fn ==="
	start=$( grep ' main$' ${fn%.evm}.sym | cut -f1 -d' ' ) 
	v ../tools/evmcomp $fn
	v ../vmsrc/evmdemo ${fn%.evm}.bin $start > ${fn%.evm}.out
	if [ -f ${fn%.evm}.expect ]; then
		if cmp ${fn%.evm}.out ${fn%.evm}.expect; then
			echo "OK: Passed $fn."
		else
			echo "ERROR: Output of $fn was not as expected!"
			exit 1
		fi
	else
		echo "WARNING: Can't find ${fn%.evm}.expect."
	fi
done

