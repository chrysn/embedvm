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

#ifndef EVM_TOOLS_H
#define EVM_TOOLS_H

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

enum evm_var_type {
	VARTYPE_LOCAL,
	VARTYPE_GLOBAL,
	VARTYPE_GLOBAL_8U,
	VARTYPE_GLOBAL_8S,
	VARTYPE_ARRAY_8U,
	VARTYPE_ARRAY_8S,
	VARTYPE_ARRAY_16,
	VARTYPE_FUNC
};

struct array_init_s {
	int len;
	int *data;
};

struct evm_insn_s {
	bool has_opcode;
	bool arg_is_relative;
	bool arg_did_grow_again;
	bool has_set_addr;
	uint8_t has_arg_data;
	uint8_t opcode;
	int16_t arg_val;
	uint16_t data_len;
	uint8_t *initdata;
	struct evm_insn_s *arg_addr;
	struct evm_insn_s *left, *right;
	uint16_t addr, set_addr, inner_addr;
	char *symbol;
};

struct evm_section_s {
	char *name;
	uint16_t begin, end;
	struct evm_section_s *next;
};

extern struct evm_section_s *sections;

extern struct evm_insn_s *new_insn(struct evm_insn_s *left, struct evm_insn_s *right);

extern struct evm_insn_s *new_insn_op(uint8_t opcode,
		struct evm_insn_s *left, struct evm_insn_s *right);

extern struct evm_insn_s *new_insn_op_reladdr(uint8_t opcode, struct evm_insn_s *addr,
		struct evm_insn_s *left, struct evm_insn_s *right);

extern struct evm_insn_s *new_insn_op_absaddr(uint8_t opcode, struct evm_insn_s *addr,
		struct evm_insn_s *left, struct evm_insn_s *right);

extern struct evm_insn_s *new_insn_op_val(uint8_t opcode, int16_t val,
		struct evm_insn_s *left, struct evm_insn_s *right);

extern struct evm_insn_s *new_insn_data(uint16_t len,
		struct evm_insn_s *left, struct evm_insn_s *right);

extern void insn_dump(FILE *f, struct evm_insn_s *insn, char *type, int indent);

extern uint16_t codegen_len;
extern struct evm_insn_s *codegen_insn;
extern void codegen(struct evm_insn_s *insn);

extern void write_debug(FILE *f, struct evm_insn_s *insn);
extern void write_symbols(FILE *f, struct evm_insn_s *insn);
extern void write_binfile(FILE *f, struct evm_insn_s *insn);
extern void write_header(FILE *f);
extern void write_intelhex(FILE *f);

extern FILE *yyin;
extern int yydebug;
extern int yylex(void);
extern int yyget_lineno(void);
extern int yyparse(void);

#endif
