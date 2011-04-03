#!/bin/bash
set -xe
make -C ../../tools
../../tools/evmcomp vmcode.evm
arduino-cc -o firmware hostapp.cc embedvm.c
