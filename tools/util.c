
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

