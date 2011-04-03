#!/bin/bash
set -xe
make -C ../../tools
../../tools/evmcomp vmcode.evm
ln -sf ../../vmsrc/embedvm.c embedvm.c
ln -sf ../../vmsrc/embedvm.h embedvm.h
arduino-cc -o firmware hostapp.cc embedvm.c
