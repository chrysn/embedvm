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
#include <assert.h>

uint16_t assign_addr(struct evm_insn_s *insn, uint16_t addr)
{
	if (!insn)
		return addr;

	insn->addr = addr;

	addr = assign_addr(insn->left, addr);
	addr += insn->data_len + insn->has_opcode + insn->has_arg_data;
	addr = assign_addr(insn->right, addr);

	return addr;
}

bool analyze_data_insn(struct evm_insn_s *insn)
{
	bool did_something = false;

	if (!insn)
		return did_something;

	if (analyze_data_insn(insn->left))
		did_something = true;

	if (analyze_data_insn(insn->right))
		did_something = true;

	if (insn->opcode >= 0x90 && insn->opcode <= 0x99) {
		/* already optimal - nothing to do */
		return did_something;
	}

	if (insn->opcode == 0x9a)
	{
		if (-4 <= insn->arg_val && insn->arg_val <= 3) {
			insn->opcode = 0x90 + (insn->arg_val & 0x0007);
			insn->has_arg_data = 0;
			did_something = true;
		}
		else if (0 <= insn->arg_val && insn->arg_val <= 255) {
			insn->opcode = 0x98;
			insn->has_arg_data = 1;
			did_something = true;
		}
		else if (-128 <= insn->arg_val && insn->arg_val <= 127) {
			insn->opcode = 0x99;
			insn->has_arg_data = 1;
			did_something = true;
		}
		return did_something;
	}

	if (insn->has_arg_data)
	{
		assert(insn->arg_addr != NULL);

		int16_t new_val = insn->arg_addr->addr;
		if (insn->arg_is_relative)
			new_val -= insn->addr;

		if (new_val != insn->arg_val) {
			insn->arg_val = new_val;
			did_something = true;
		}

		uint8_t needed_bytes = 2;

		if (insn->arg_is_relative) {
			if (-128 <= new_val && new_val <= 127)
				needed_bytes = 1;
		} else {
			if (0 <= new_val && new_val <= 255)
				needed_bytes = 1;
		}

		if (needed_bytes != insn->has_arg_data) {
			insn->has_arg_data = needed_bytes;
			did_something = true;
		}
	}

	return did_something;
}

uint16_t codegen_len;
struct evm_insn_s *codegen_insn;

void codegen(struct evm_insn_s *insn)
{
	int i;
	codegen_insn = insn;
	for (i=0; i<10; i++) {
		codegen_len = assign_addr(insn, 0);
		if (!analyze_data_insn(insn))
			return;
	}
	codegen_len = assign_addr(insn, 0);
	return;
}

