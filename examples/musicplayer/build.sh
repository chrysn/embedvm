#!/bin/bash
set -xe
make -C ../../tools
splrun melody2evm.spl < melody.csv > vmcode.evm
../../tools/evmcomp vmcode.evm
ln -sf ../../vmsrc/embedvm.c embedvm.c
ln -sf ../../vmsrc/embedvm.h embedvm.h
gcc -o play -Wall -Wextra -ggdb -Os -lm play.c embedvm.c
arduino-cc firmware.cc embedvm.c
