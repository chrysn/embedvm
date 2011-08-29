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
	int i;

	if (!insn)
		return;

	if (insn->symbol)
		fprintf(f, "\n\n%s @ %04X:", insn->symbol, insn->addr);

	write_debug(f, insn->left);

	if (insn->has_opcode || insn->data_len)
	{
		if (insn->data_len > 0)
			fprintf(f, " D[%d]", insn->data_len);

		if (insn->initdata) {
			fprintf(f, "=");
			for (i=0; i<insn->data_len; i++)
				fprintf(f, "%02X", insn->initdata[i]);
		}

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

struct symbol_s {
	char *name;
	uint16_t addr;
	struct symbol_s *next;
};

struct symbol_s *symbols;

void write_symbols(FILE *f, struct evm_insn_s *insn)
{
	if (!insn)
		return;

	if (insn->symbol) {
		struct symbol_s *sym = calloc(1, sizeof(struct symbol_s));
		sym->name = strdup(insn->symbol);
		sym->addr = insn->addr;
		sym->next = symbols;
		symbols = sym;
		fprintf(f, "%04X %s (%s)\n", insn->addr, insn->symbol, insn->data_len ? "data" : insn->opcode ? "code" : insn->set_addr ? "address" : "other");
	}

	write_symbols(f, insn->left);
	write_symbols(f, insn->right);
}

uint16_t bindata_len;
uint8_t bindata_data[64*1024];
bool bindata_written[64*1024];
bool bindata_covered[64*1024];

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

	if (insn->initdata)
		for (i = 0; i < insn->data_len; i++)
			write_bindata(addr++, insn->initdata[i]);
	else
		addr += insn->data_len;

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

extern void write_header(FILE *f)
{
	struct evm_section_s *sect = sections;
	struct symbol_s *sym = symbols;
	int i;

	memset(bindata_covered, 0, sizeof(bindata_data));

	while (sym) {
		fprintf(f, "#define EMBEDVM_SYM_%s 0x%04x\n", sym->name, sym->addr);
		sym = sym->next;
	}

	while (sect) {
		int real_end = sect->end;
		while (real_end >= sect->begin && !bindata_written[real_end])
			real_end--;
		fprintf(f, "#define EMBEDVM_SECT_%s_BEGIN 0x%04x\n", sect->name, sect->begin);
		fprintf(f, "#define EMBEDVM_SECT_%s_END 0x%04x\n", sect->name, sect->end);
		fprintf(f, "#define EMBEDVM_SECT_%s_DATA", sect->name);
		for (i = sect->begin; i <= real_end; i++) {
			fprintf(f, "%s%d", i ? "," : " ", bindata_data[i]);
			bindata_covered[i] = 1;
		}
		fprintf(f, "\n");
		sect = sect->next;
	}

	for (i = 0; i < (int)sizeof(bindata_data); i++) {
		if (bindata_covered[i])
			continue;
		if (!bindata_written[i])
			continue;
		fprintf(stderr, "Data at 0x%04x is not covered by any section!\n", i);
		exit(1);
	}
}

void ihex_line(FILE *f, uint8_t len, uint16_t addr, uint8_t type, uint8_t *data)
{
	uint8_t buffer[len+5];
	int i, j;

	buffer[0] = len;
	buffer[1] = addr >> 8;
	buffer[2] = addr & 0xff;
	buffer[3] = type;

	for (i = 0; i < len; i++)
		buffer[4+i] = data[i];

	for (i = j = 0; i < len+4; i++)
		j += buffer[i];

	buffer[len+4] = -j;

	fprintf(f, ":");
	for (i = 0; i < len+5; i++)
		fprintf(f, "%02x", buffer[i]);
	fprintf(f, "\n");
}

extern void write_intelhex(FILE *f)
{
	struct evm_section_s *sect = sections;
	int i, len;

	while (sect) {
		int real_end = sect->end;
		while (real_end >= sect->begin && !bindata_written[real_end])
			real_end--;
		for (i = sect->begin; i <= real_end; i += 0x20) {
			len = (real_end-i+1) < 0x20 ? (real_end-i+1) : 0x20;
			ihex_line(f, len, i, 0, bindata_data+i);
		}
		sect = sect->next;
	}
	ihex_line(f, 0, 0, 1, NULL);

}

