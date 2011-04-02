#ifndef EVM_TOOLS_H
#define EVM_TOOLS_H

#include <stdint.h>

enum evm_var_type {
	VARTYPE_LOCAL = 1,
	VARTYPE_GLOBAL_8U = 2,
	VARTYPE_GLOBAL_8S = 3,
	VARTYPE_GLOBAL_16 = 4,
	VARTYPE_FUNC = 5
};

struct evm_insn_s {
	int has_opcode : 1;
	int has_arg_data : 2;
	int arg_is_relative : 1;
	uint8_t opcode;
	int16_t arg_val;
	uint16_t data_len;
	struct evm_insn_s *arg_addr;
	struct evm_insn_s *left, *right;
};

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

extern void codegen(struct evm_insn_s *insn);

extern int yydebug;
extern int yylex(void);
extern int yyget_lineno(void);
extern int yyparse(void);

#endif
