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
#include <string.h>

int main(int argc, char **argv)
{
	FILE *f;
	char *prefix;
	int prefix_len;

	if (argc != 2 || *argv[1] == '-') {
abort_with_help_msg:
		fprintf(stderr, "Usage: %s [filename].evm\n", argv[0]);
		return 1;
	}

	prefix = strdup(argv[1]);
	prefix_len = strlen(prefix);

	if (prefix_len < 5 || strcmp(".evm", prefix+prefix_len-4))
		goto abort_with_help_msg;

	stdin = fopen(prefix, "rt");
	if (!stdin)
		goto abort_with_help_msg;

	// yydebug = 1;
	yyparse();

	strcpy(prefix+prefix_len-4, ".ast");
	f = fopen(prefix, "wt");
	insn_dump(f, codegen_insn, "ROOT", 0);
	fclose(f);

	strcpy(prefix+prefix_len-4, ".dbg");
	f = fopen(prefix, "wt");
	fprintf(f, "\nTotal code and data length: %d", codegen_len);
	write_debug(f, codegen_insn);
	fprintf(f, "\n\n");
	fclose(f);

	strcpy(prefix+prefix_len-4, ".sym");
	f = fopen(prefix, "wt");
	write_symbols(f, codegen_insn);
	fclose(f);

	strcpy(prefix+prefix_len-4, ".bin");
	f = fopen(prefix, "wb");
	write_binfile(f, codegen_insn);
	fclose(f);

	strcpy(prefix+prefix_len-4, ".hdr");
	f = fopen(prefix, "wb");
	if (!sections) {
		static struct evm_section_s default_sect = { "SRAM", 0, 0xffff, NULL };
		sections = &default_sect;
	}
	write_header(f);
	fclose(f);

	strcpy(prefix+prefix_len-4, ".ihx");
	f = fopen(prefix, "wb");
	write_intelhex(f);
	fclose(f);

	return 0;
}

