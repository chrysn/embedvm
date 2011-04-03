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

struct evm_insn_s *new_insn(struct evm_insn_s *left, struct evm_insn_s *right)
{
	struct evm_insn_s *insn = calloc(1, sizeof(struct evm_insn_s));
	insn->left = left;
	insn->right = right;
	return insn;
}

struct evm_insn_s *new_insn_op(uint8_t opcode,
		struct evm_insn_s *left, struct evm_insn_s *right)
{
	struct evm_insn_s *insn = new_insn(left, right);
	insn->has_opcode = 1;
	insn->opcode = opcode;
	return insn;
}

struct evm_insn_s *new_insn_op_reladdr(uint8_t opcode, struct evm_insn_s *addr,
		struct evm_insn_s *left, struct evm_insn_s *right)
{
	struct evm_insn_s *insn = new_insn(left, right);
	insn->has_opcode = 1;
	insn->opcode = opcode;
	insn->has_arg_data = 2;
	insn->arg_is_relative = 1;
	insn->arg_addr = addr;
	return insn;
}

struct evm_insn_s *new_insn_op_absaddr(uint8_t opcode, struct evm_insn_s *addr,
		struct evm_insn_s *left, struct evm_insn_s *right)
{
	struct evm_insn_s *insn = new_insn(left, right);
	insn->has_opcode = 1;
	insn->opcode = opcode;
	insn->has_arg_data = 2;
	insn->arg_addr = addr;
	return insn;
}

struct evm_insn_s *new_insn_op_val(uint8_t opcode, int16_t val,
		struct evm_insn_s *left, struct evm_insn_s *right)
{
	struct evm_insn_s *insn = new_insn(left, right);
	insn->has_opcode = 1;
	insn->opcode = opcode;
	insn->has_arg_data = 2;
	insn->arg_val = val;
	return insn;
}

extern struct evm_insn_s *new_insn_data(uint16_t len,
		struct evm_insn_s *left, struct evm_insn_s *right)
{
	struct evm_insn_s *insn = new_insn(left, right);
	insn->data_len = len;
	return insn;
}

void insn_dump(struct evm_insn_s *insn, char *type, int indent)
{
	if (!insn)
		return;

	insn_dump(insn->left, "LEFT", indent+1);

	printf("%*s%s %p @ %04x %04x:", indent, "", type, insn, insn->addr, insn->inner_addr);

	if (insn->symbol)
		printf(" sym=%s", insn->symbol);

	if (insn->has_set_addr)
		printf(" setaddr=%04x", insn->set_addr);

	if (insn->has_opcode)
		printf(" op=%02x", insn->opcode);

	if (insn->has_arg_data == 1)
		printf(" arg=%02x", insn->arg_val & 0xff);

	if (insn->has_arg_data == 2)
		printf(" arg=%04x", insn->arg_val);

	if (insn->arg_is_relative)
		printf(" rel");

	if (insn->arg_addr != NULL)
		printf(" argaddr=%p", insn->arg_addr);

	if (insn->arg_did_grow_again)
		printf(" regrow");

	if (insn->data_len)
		printf(" datalen=%d", insn->data_len);

	printf("\n");

	insn_dump(insn->right, "RIGHT", indent+1);
}

