/*
 *  EmbedVM - Embedded Virtual Machine for uC Applications
 *
 *  Copyright (C) 2011  Clifford Wolf <clifford@clifford.at>
 *  
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *  
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */

#include "evmcomp.h"
#include <stdlib.h>
#include <string.h>
#include <assert.h>

void write_debug(FILE *f, struct evm_insn_s *insn)
{
	if (!insn)
		return;

	if (insn->symbol)
		fprintf(f, "\n\n%s @ %04X:", insn->symbol, insn->addr);

	write_debug(f, insn->left);

	if (insn->has_opcode || insn->data_len)
	{
		if (insn->data_len > 0)
			fprintf(f, " D[%d]", insn->data_len);

		if (insn->has_opcode)
			fprintf(f, " %02X", insn->opcode);

		if (insn->has_arg_data == 1)
			fprintf(f, ".%02X", insn->arg_val & 0xff);

		if (insn->has_arg_data == 2)
			fprintf(f, ".%04X", insn->arg_val & 0xffff);

		if (insn->arg_is_relative)
			fprintf(f, "r");
		else if (insn->arg_addr)
			fprintf(f, "a");
	}

	write_debug(f, insn->right);
}

void write_symbols(FILE *f, struct evm_insn_s *insn)
{
	if (!insn)
		return;

	if (insn->symbol)
		fprintf(f, "%04X %s\n", insn->addr, insn->symbol);

	write_symbols(f, insn->left);
	write_symbols(f, insn->right);
}

uint16_t bindata_len;
uint8_t bindata_data[64*1024];
bool bindata_written[64*1024];

void write_bindata(int addr, uint8_t data)
{
	if (bindata_written[addr]) {
		fprintf(stderr, "Double-write on memory cell 0x%04x!\n", addr);
		exit(1);
	}
	bindata_data[addr] = data;
	bindata_written[addr] = true;
	bindata_len = bindata_len > addr+1 ? bindata_len : addr+1;
}

uint16_t prep_bindata(struct evm_insn_s *insn, uint16_t addr)
{
	int i;

	if (!insn)
		return addr;

	if (insn->has_set_addr)
		addr = insn->set_addr;
	assert(addr == insn->addr);

	addr = prep_bindata(insn->left, addr);
	assert(addr == insn->inner_addr);

	for (i = 0; i < insn->data_len; i++)
		write_bindata(addr++, 0);

	if (insn->has_opcode)
		write_bindata(addr++, insn->opcode);

	if (insn->has_arg_data == 2)
		write_bindata(addr++, (insn->arg_val >> 8) & 0xff);

	if (insn->has_arg_data >= 1)
		write_bindata(addr++, insn->arg_val & 0xff);

	addr = prep_bindata(insn->right, addr);
	return addr;
}

void write_binfile(FILE *f, struct evm_insn_s *insn)
{
	bindata_len = 0;
	memset(bindata_data, 0, sizeof(bindata_data));
	memset(bindata_written, 0, sizeof(bindata_written));
	prep_bindata(insn, 0);

	fwrite(bindata_data, bindata_len, 1, f);

#if 0
	int i;
	for (i=0; i<bindata_len; i++)
		putchar(bindata_written[i] ? 'x' : '.');
	putchar('\n');
#endif
}

