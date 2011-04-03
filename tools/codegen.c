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
#include <assert.h>

uint16_t assign_addr_pass1(struct evm_insn_s *insn, uint16_t addr)
{
	if (!insn)
		return addr;

	if (insn->has_set_addr)
		addr = insn->set_addr;
	insn->addr = addr;

	insn->inner_addr = addr = assign_addr_pass1(insn->left, addr);
	addr += insn->data_len + insn->has_opcode + insn->has_arg_data;
	codegen_len = codegen_len > addr ? codegen_len : addr;
	addr = assign_addr_pass1(insn->right, addr);

	return addr;
}

void assign_addr_pass2(struct evm_insn_s *insn)
{
	if (!insn)
		return;

	if (insn->arg_addr) {
		insn->arg_val = insn->arg_addr->addr;
		if (insn->arg_is_relative)
			insn->arg_val -= insn->inner_addr;
	}

	assign_addr_pass2(insn->left);
	assign_addr_pass2(insn->right);
}

bool shrink_insn(struct evm_insn_s *insn)
{
	bool did_something = false;

	if (!insn)
		return did_something;

	if (shrink_insn(insn->left))
		did_something = true;

	if (shrink_insn(insn->right))
		did_something = true;

	if (insn->opcode >= 0x90 && insn->opcode <= 0x99) {
		/* already optimal - nothing to do */
		return did_something;
	}

	if (insn->opcode == 0x9a && insn->arg_addr != NULL) {
		/* always use the 2-bytes argument for this special case */
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

		uint8_t needed_bytes = 2;
		if (insn->arg_is_relative) {
			if (-128 <= insn->arg_val && insn->arg_val <= 127)
				needed_bytes = 1;
		} else {
			if (0 <= insn->arg_val && insn->arg_val <= 255)
				needed_bytes = 1;
		}

		if (needed_bytes != insn->has_arg_data)
		{
			if (needed_bytes == 1 && !insn->arg_did_grow_again) {
				insn->opcode -= 1;
				insn->has_arg_data = 1;
				did_something = true;
			}
			if (needed_bytes == 2) {
				insn->opcode += 1;
				insn->has_arg_data = 2;
				insn->arg_did_grow_again = true;
				did_something = true;
			}
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
		codegen_len = 0;
		assign_addr_pass1(insn, 0);
		assign_addr_pass2(insn);
		if (!shrink_insn(insn))
			return;
	}
	abort();
}

