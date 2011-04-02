#ifndef EVM_TOOLS_H
#define EVM_TOOLS_H

#include <stdint.h>

struct evm_insn_s {
	uint8_t opcode;
	int16_t argument;
	char *arg_label;
	struct evm_insn_s *left, *right;
};

extern int yydebug;
extern int yylex(void);
extern int yyget_lineno(void);
extern int yyparse(void);

#endif
