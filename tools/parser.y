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

%{

#include <stdlib.h>
#include <string.h>
#include "evmcomp.h"

void yyerror (char const *s) {
	fprintf(stderr, "Parser error in line %d: %s\n", yyget_lineno(), s);
	exit(1);
}

struct nametab_entry_s {
	char *name;
	int type, index;
	struct evm_insn_s *addr;
	struct nametab_entry_s *next;
};

struct nametab_entry_s *local_ids;
struct nametab_entry_s *global_ids;

static void add_nametab_local(char *name, int index);
static void add_nametab_global(char *name, int type, struct evm_insn_s *addr);
static struct nametab_entry_s *find_nametab_entry(char *name);
static struct nametab_entry_s *find_global_nametab_entry(char *name);

struct func_call_args_desc_s {
	struct evm_insn_s *insn;
	int num;
};

%}

%union {
	int number;
	char *string;
	struct evm_insn_s *insn;
	struct func_call_args_desc_s *fc;
}

%token <number> TOK_NUMBER TOK_USERFUNC
%token <string> TOK_ID

%token TOK_IF TOK_ELSE TOK_DO TOK_FOR TOK_WHILE TOK_RETURN TOK_FUNCTION
%token TOK_LOCAL TOK_GLOBAL TOK_ARRAY_8U TOK_ARRAY_8S TOK_ARRAY_16

%left TOK_LOR
%left TOK_LAND

%right '?' ':'

%left '|'
%left '^'
%left '&'

%left TOK_EQ TOK_NE
%left '<' TOK_LE TOK_GE '>'

%left TOK_SHL TOK_SHR
%left '+' '-'
%left '*' '/' '%'

%right NEG

%type <insn> program global_data function_def function_body
%type <insn> statement_list statement core_statement lvalue expression

%type <number> function_args function_vars function_var_list;
%type <fc> func_call_args

%expect 1
%debug

%%

input:
	program {
		codegen($1);
	};

program:
	/* empty */ {
		$$ = NULL;
	} |
/*
	program meta_statement {
		$$ = new_insn($1, $2);
	} |
*/
	program global_data {
		$$ = new_insn($1, $2);
	} |
	program function_def {
		$$ = new_insn($1, $2);
	};

global_data:
	TOK_GLOBAL TOK_ID ';' {
		$$ = new_insn_data(2, NULL, NULL);
		$$->symbol = strdup($2);
		add_nametab_global($2, VARTYPE_GLOBAL_16, $$);
	} |
	TOK_ARRAY_8U TOK_ID '[' TOK_NUMBER ']' ';' {
		$$ = new_insn_data($4, NULL, NULL);
		$$->symbol = strdup($2);
		add_nametab_global($2, VARTYPE_GLOBAL_8U, $$);
	} |
	TOK_ARRAY_8S TOK_ID '[' TOK_NUMBER ']' ';' {
		$$ = new_insn_data($4, NULL, NULL);
		$$->symbol = strdup($2);
		add_nametab_global($2, VARTYPE_GLOBAL_8S, $$);
	} |
	TOK_ARRAY_16 TOK_ID '[' TOK_NUMBER ']' ';' {
		$$ = new_insn_data(2 * $4, NULL, NULL);
		$$->symbol = strdup($2);
		add_nametab_global($2, VARTYPE_GLOBAL_16, $$);
	};

function_def:
	TOK_FUNCTION { local_ids=NULL; } TOK_ID '(' function_args ')' '{' function_vars function_body '}' {
		int local_vars = $8;
		struct evm_insn_s *alloc_local = NULL;
		while (local_vars > 0) {
			int this_num = local_vars > 8 ? 8 : local_vars;
			alloc_local = new_insn_op(0xf8 + (this_num-1), alloc_local, NULL);
			local_vars -= this_num;
		}
		$$ = new_insn(alloc_local, $9);
		struct evm_insn_s *last_insn = $$;
		while (last_insn->right != NULL)
			last_insn = last_insn->right;
		if (last_insn->opcode != 0x9b && last_insn->opcode != 0x9c)
			$$ = new_insn_op(0x9c, $$, NULL);
		add_nametab_global($3, VARTYPE_FUNC, $$);
		$$->symbol = strdup($3);
	};

function_args:
	/* empty */ {
		$$ = 0;
	} |
	TOK_ID {
		add_nametab_local($1, -1);
		$$ = 1;
	} |
	function_args ',' TOK_ID {
		add_nametab_local($3, -($1 + 1));
		$$ = $1 + 1;
	};

function_vars:
	/* empty */ {
		$$ = 0;
	} |
	function_var_list ';' {
		$$ = $1;
	};

function_var_list:
	TOK_LOCAL TOK_ID {
		add_nametab_local($2, 0);
		$$ = 1;
	} |
	function_var_list ',' TOK_ID {
		add_nametab_local($3, $1);
		$$ = $1 + 1;
	} |
	function_var_list ';' TOK_LOCAL TOK_ID {
		add_nametab_local($4, $1);
		$$ = $1 + 1;
	};

function_body:
	/* empty */ {
		$$ = NULL;
	} |
	function_body statement {
		$$ = new_insn($1, $2);
	};

statement_list:
	/* empty */ {
		$$ = NULL;
	} |
	statement_list statement {
		$$ = new_insn($1, $2);
	};

statement:
	core_statement ';' {
		$$ = $1;
	} |
	'{' statement_list '}' {
		$$ = $2;
	} |
	TOK_IF '(' expression ')' statement {
		struct evm_insn_s *end = new_insn(NULL, NULL);
		$$ = new_insn_op_reladdr(0xa0 + 7, end, $3, new_insn($5, end));
	} |
	TOK_IF '(' expression ')' statement TOK_ELSE statement {
		struct evm_insn_s *end = new_insn(NULL, NULL);
		struct evm_insn_s *wrap_else = new_insn($7, end);
		struct evm_insn_s *wrap_then = new_insn_op_reladdr(0xa0 + 1, end, $5, wrap_else);
		$$ = new_insn_op_reladdr(0xa0 + 7, wrap_else, $3, wrap_then);
	} |
	TOK_DO statement TOK_WHILE '(' expression ')' ';' {
		$$ = new_insn_op_reladdr(0xa0 + 5, $2, new_insn($2, $5), NULL);
	} |
	TOK_WHILE '(' expression ')' statement {
		struct evm_insn_s *end = new_insn(NULL, NULL);
		$$ = new_insn_op_reladdr(0xa0 + 7, end, $3, new_insn_op_reladdr(0xa0 + 1, $3, $5, end));
	} |
	TOK_FOR '(' core_statement ';' expression ';' core_statement ')' statement {
		struct evm_insn_s *end = new_insn(NULL, NULL);
		struct evm_insn_s *loop = new_insn_op_reladdr(0xa0 + 7, end, $5,
				new_insn_op_reladdr(0xa0 + 1, $5, new_insn($9, $7), end));
		$$ = new_insn($3, loop);
	} |
	TOK_RETURN expression ';' {
		$$ = new_insn_op(0x9b, $2, NULL);
	} |
	TOK_RETURN ';' {
		$$ = new_insn_op(0x9c, NULL, NULL);
	};

core_statement:
	expression {
		$$ = new_insn_op(0x9d, $1, NULL);
	} |
	lvalue '=' expression {
		$$ = new_insn($3, $1);
	};

lvalue:
	TOK_ID {
		struct nametab_entry_s *e = find_nametab_entry($1);
		if (!e) {
			fprintf(stderr, "Unkown identifier `%s' in line %d!\n", $1, yyget_lineno());
			exit(1);
		}
		switch (e->type)
		{
		case VARTYPE_LOCAL:
			$$ = new_insn_op(0x40 + (e->index & 0x3f), NULL, NULL);
			break;
		case VARTYPE_GLOBAL_8U:
			$$ = new_insn_op_absaddr(0xc8 + 1, e->addr, NULL, NULL);
			break;
		case VARTYPE_GLOBAL_8S:
			$$ = new_insn_op_absaddr(0xd8 + 1, e->addr, NULL, NULL);
			break;
		case VARTYPE_GLOBAL_16:
			$$ = new_insn_op_absaddr(0xe8 + 1, e->addr, NULL, NULL);
			break;
		default:
			abort();
		}
	} |
	TOK_ID '[' expression ']' {
		struct nametab_entry_s *e = find_global_nametab_entry($1);
		if (!e) {
			fprintf(stderr, "Unkown global identifier `%s' in line %d!\n", $1, yyget_lineno());
			exit(1);
		}
		switch (e->type)
		{
		case VARTYPE_GLOBAL_8U:
			$$ = new_insn_op_absaddr(0xc8 + 4, e->addr, $3, NULL);
			break;
		case VARTYPE_GLOBAL_8S:
			$$ = new_insn_op_absaddr(0xd8 + 4, e->addr, $3, NULL);
			break;
		case VARTYPE_GLOBAL_16:
			$$ = new_insn_op_absaddr(0xe8 + 4, e->addr, $3, NULL);
			break;
		default:
			abort();
		}
	};

expression:
	TOK_NUMBER {
		$$ = new_insn_op_val(0x9a, $1, NULL, NULL);
	} |
	'(' expression ')' {
		$$ = $2;
	} |
	TOK_ID {
		struct nametab_entry_s *e = find_nametab_entry($1);
		if (!e) {
			fprintf(stderr, "Unkown identifier `%s' in line %d!\n", $1, yyget_lineno());
			exit(1);
		}
		switch (e->type)
		{
		case VARTYPE_LOCAL:
			$$ = new_insn_op(0x00 + (e->index & 0x3f), NULL, NULL);
			break;
		case VARTYPE_GLOBAL_8U:
			$$ = new_insn_op_absaddr(0xc0 + 1, e->addr, NULL, NULL);
			break;
		case VARTYPE_GLOBAL_8S:
			$$ = new_insn_op_absaddr(0xd0 + 1, e->addr, NULL, NULL);
			break;
		case VARTYPE_GLOBAL_16:
			$$ = new_insn_op_absaddr(0xe0 + 1, e->addr, NULL, NULL);
			break;
		default:
			abort();
		}
	} |
	TOK_ID '[' expression ']' {
		struct nametab_entry_s *e = find_global_nametab_entry($1);
		if (!e) {
			fprintf(stderr, "Unkown global identifier `%s' in line %d!\n", $1, yyget_lineno());
			exit(1);
		}
		switch (e->type)
		{
		case VARTYPE_GLOBAL_8U:
			$$ = new_insn_op_absaddr(0xc0 + 4, e->addr, $3, NULL);
			break;
		case VARTYPE_GLOBAL_8S:
			$$ = new_insn_op_absaddr(0xd0 + 4, e->addr, $3, NULL);
			break;
		case VARTYPE_GLOBAL_16:
			$$ = new_insn_op_absaddr(0xe0 + 4, e->addr, $3, NULL);
			break;
		default:
			abort();
		}
	} |
	TOK_ID '(' func_call_args ')' {
		struct nametab_entry_s *e = find_global_nametab_entry($1);
		if (!e || e->type != VARTYPE_FUNC) {
			fprintf(stderr, "Unkown function `%s' in line %d!\n", $1, yyget_lineno());
			exit(1);
		}
		struct evm_insn_s *popargs = NULL;
		while ($3->num > 0) {
			int this_num = $3->num > 8 ? 8 : $3->num;
			popargs = new_insn_op(0xf0 + (this_num-1), popargs, NULL);
			$3->num -= this_num;
		}
		$$ = new_insn_op_reladdr(0xa0 + 3, e->addr, $3->insn, popargs);
	} |
	TOK_USERFUNC '(' func_call_args ')' {
		struct evm_insn_s *popargs = NULL;
		while ($3->num > 0) {
			int this_num = $3->num > 8 ? 8 : $3->num;
			popargs = new_insn_op(0xf0 + (this_num-1), popargs, NULL);
			$3->num -= this_num;
		}
		$$ = new_insn_op(0xb0 + $1, $3->insn, popargs);
	} |
	'+' expression %prec NEG {
		$$ = $2;
	} |
	expression '+' expression {
		$$ = new_insn_op(0x80 + 0, new_insn($1, $3), NULL);
	} |
	expression '-' expression {
		$$ = new_insn_op(0x80 + 1, new_insn($1, $3), NULL);
	} |
	expression '*' expression {
		$$ = new_insn_op(0x80 + 2, new_insn($1, $3), NULL);
	} |
	expression '/' expression {
		$$ = new_insn_op(0x80 + 3, new_insn($1, $3), NULL);
	} |
	expression '%' expression {
		$$ = new_insn_op(0x80 + 4, new_insn($1, $3), NULL);
	} |
	expression TOK_SHL expression {
		$$ = new_insn_op(0x80 + 5, new_insn($1, $3), NULL);
	} |
	expression TOK_SHR expression {
		$$ = new_insn_op(0x80 + 6, new_insn($1, $3), NULL);
	} |
	expression '&' expression {
		$$ = new_insn_op(0x80 + 7, new_insn($1, $3), NULL);
	} |
	expression '|' expression {
		$$ = new_insn_op(0x80 + 8, new_insn($1, $3), NULL);
	} |
	expression '^' expression {
		$$ = new_insn_op(0x80 + 9, new_insn($1, $3), NULL);
	} |
	'~' expression %prec NEG {
		$$ = new_insn_op(0x80 + 10, $2, NULL);
	} |
	'-' expression %prec NEG {
		$$ = new_insn_op(0x80 + 11, $2, NULL);
	} |
	expression TOK_LAND expression {
		// TBD: Skip 2nd expr if 1st is already false
		$$ = new_insn_op(0x80 + 12, new_insn($1, $3), NULL);
	} |
	expression TOK_LOR expression {
		// TBD: Skip 2nd expr if 1st is already true
		$$ = new_insn_op(0x80 + 13, new_insn($1, $3), NULL);
	} |
	'!' expression %prec NEG {
		$$ = new_insn_op(0x80 + 14, $2, NULL);
	} |
	expression '<' expression {
		$$ = new_insn_op(0xa8 + 0, new_insn($1, $3), NULL);
	} |
	expression TOK_LE expression {
		$$ = new_insn_op(0xa8 + 1, new_insn($1, $3), NULL);
	} |
	expression TOK_EQ expression {
		$$ = new_insn_op(0xa8 + 2, new_insn($1, $3), NULL);
	} |
	expression TOK_NE expression {
		$$ = new_insn_op(0xa8 + 3, new_insn($1, $3), NULL);
	} |
	expression TOK_GE expression {
		$$ = new_insn_op(0xa8 + 4, new_insn($1, $3), NULL);
	} |
	expression '>' expression {
		$$ = new_insn_op(0xa8 + 5, new_insn($1, $3), NULL);
	} |
	expression '?' expression ':' expression {
		struct evm_insn_s *end = new_insn(NULL, NULL);
		struct evm_insn_s *wrap_false = new_insn($5, end);
		struct evm_insn_s *wrap_true = new_insn_op_reladdr(0xa0 + 1, end, $3, wrap_false);
		$$ = new_insn_op_reladdr(0xa0 + 7, wrap_false, $1, wrap_true);
	};

func_call_args:
	/* emtpy */ {
		$$ = calloc(1, sizeof(struct func_call_args_desc_s));
	} |
	expression {
		$$ = calloc(1, sizeof(struct func_call_args_desc_s));
		$$->insn = $1;
		$$->num = 1;
	} |
	func_call_args ',' expression {
		$$ = $1;
		$$->insn = new_insn($$->insn, $3);
		$$->num++;
	};

%%

static void add_nametab_local(char *name, int index)
{
	struct nametab_entry_s *e = calloc(1, sizeof(struct nametab_entry_s));
	e->name = name;
	e->type = VARTYPE_LOCAL;
	e->index = index;
	e->next = local_ids;
	local_ids = e;
}

static void add_nametab_global(char *name, int type, struct evm_insn_s *addr)
{
	struct nametab_entry_s *e = calloc(1, sizeof(struct nametab_entry_s));
	e->name = name;
	e->type = type;
	e->addr = addr;
	e->next = global_ids;
	global_ids = e;
}

struct nametab_entry_s *find_nametab_entry(char *name)
{
	struct nametab_entry_s *tab;
	for (tab = local_ids; tab != NULL; tab = tab->next) {
		if (!strcmp(tab->name, name))
			return tab;
	}
	return find_global_nametab_entry(name);
}

struct nametab_entry_s *find_global_nametab_entry(char *name)
{
	struct nametab_entry_s *tab;
	for (tab = global_ids; tab != NULL; tab = tab->next) {
		if (!strcmp(tab->name, name))
			return tab;
	}
	return NULL;
}

