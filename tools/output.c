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

void write_binfile(FILE *f, struct evm_insn_s *insn)
{
	int i;

	if (!insn)
		return;

	write_binfile(f, insn->left);

	for (i = 0; i < insn->data_len; i++)
		fputc(0, f);

	if (insn->has_opcode) {
		fputc(insn->opcode, f);
		if (insn->has_arg_data == 2)
			fputc((insn->arg_val >> 8) & 0xff, f);
		if (insn->has_arg_data >= 1)
			fputc(insn->arg_val & 0xff, f);
	}
	
	write_binfile(f, insn->right);
}

