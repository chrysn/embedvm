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

#define _GNU_SOURCE

#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "evmcomp.h"

void yyerror (char const *s) {
	fprintf(stderr, "Parser error in line %d: %s\n", yyget_lineno(), s);
	exit(1);
}

struct nametab_entry_s {
	char *name;
	int type, index, num_args;
	struct evm_insn_s *addr;
	struct nametab_entry_s *next;
	bool is_forward_decl;
};

struct nametab_entry_s *goto_ids;
struct nametab_entry_s *local_ids;
struct nametab_entry_s *global_ids;

static struct nametab_entry_s *add_nametab_goto(char *name);
static struct nametab_entry_s *add_nametab_local(char *name, int index);
static struct nametab_entry_s *add_nametab_global(char *name, int type, struct evm_insn_s *addr);
static struct nametab_entry_s *find_nametab_goto(char *name);
static struct nametab_entry_s *find_nametab_entry(char *name);
static struct nametab_entry_s *find_global_nametab_entry(char *name);

struct loopcontext_s {
	struct evm_insn_s *break_insn;
	struct evm_insn_s *continue_insn;
	struct evm_insn_s *body_insn;
	struct loopcontext_s *next;
};

struct loopcontext_s *loopctx_stack;

struct evm_section_s *sections;

static struct evm_insn_s *generate_pre_post_inc_dec(struct evm_insn_s *lv,
		bool is_pre, bool is_inc, bool is_expr);

static struct evm_insn_s *generate_combined_assign(struct evm_insn_s *lv,
		struct evm_insn_s *action, bool is_pre, bool is_expr);

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
	struct loopcontext_s *loopctx;
	struct array_init_s ainit;
	void *vp;
}

%token <number> TOK_NUMBER TOK_USERFUNC
%token <string> TOK_ID

%token TOK_IF TOK_ELSE TOK_DO TOK_FOR TOK_WHILE
%token TOK_BREAK TOK_CONTINUE TOK_GOTO TOK_RETURN TOK_FUNCTION
%token TOK_LOCAL TOK_GLOBAL TOK_GLOBAL_8U TOK_GLOBAL_8S
%token TOK_ARRAY_8U TOK_ARRAY_8S TOK_ARRAY_16
%token TOK_EXTERN TOK_MEMADDR TOK_SECTION TOK_TRAMPOLINE
%token TOK_LINE TOK_VMIP TOK_VMSP TOK_VMSFP
%token TOK_PTR_8U TOK_PTR_8S TOK_PTR_16 TOK_PTR_F

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

%left TOK_INC TOK_DEC

%token TOK_ASSIGN_ADD TOK_ASSIGN_SUB TOK_ASSIGN_MUL TOK_ASSIGN_DIV TOK_ASSIGN_MOD
%token TOK_ASSIGN_SHL TOK_ASSIGN_SHR TOK_ASSIGN_AND TOK_ASSIGN_OR TOK_ASSIGN_XOR

%type <insn> program meta_statement global_data function_def function_body
%type <insn> statement_list statement core_statement lvalue func_expression
%type <insn> maybe_core_statement expression ptr_index

%type <number> function_args function_vars function_var_list
%type <number> array_type global_type ptr_type combined_assign number
%type <number> maybe_extern function_head
%type <ainit> array_init array_init_data
%type <loopctx> loop_body
%type <vp> global_var_init
%type <fc> func_call_args

%expect 1
%debug

%%

input:
	program {
		struct nametab_entry_s *e;
		for (e = global_ids; e != NULL; e = e->next) {
			if (e->is_forward_decl) {
				fprintf(stderr, "Got forward declaration but no implementation for function `%s'!\n", e->name);
				exit(1);
			}
		}

		struct evm_insn_s *end = new_insn(NULL, NULL);
		end->symbol = strdup("_end");
		codegen(new_insn($1, end));
	};

program:
	/* empty */ {
		$$ = NULL;
		sections = NULL;
		goto_ids = NULL;
		local_ids = NULL;
		global_ids = NULL;
		loopctx_stack = NULL;
	} |
	program meta_statement {
		$$ = new_insn($1, $2);
	} |
	program global_data {
		$$ = new_insn($1, $2);
	} |
	program function_def {
		$$ = new_insn($1, $2);
	};

meta_statement:
	TOK_MEMADDR TOK_NUMBER {
		$$ = new_insn(NULL, NULL);
		if (asprintf(&$$->symbol, "_memaddr_%04x", $2) < 0)
			abort();
		$$->has_set_addr = true;
		$$->set_addr = $2;
	} |
	TOK_TRAMPOLINE TOK_NUMBER TOK_ID {
		struct nametab_entry_s *e = find_global_nametab_entry($3);
		if (!e || e->type != VARTYPE_FUNC) {
			fprintf(stderr, "Unkown function `%s' in line %d!\n", $3, yyget_lineno());
			exit(1);
		}
		$$ = new_insn_op_reladdr(0xa0 + 1, e->addr, NULL, NULL);
		if (asprintf(&$$->symbol, "_trampoline_%s", $3) < 0)
			abort();
		$$->has_set_addr = true;
		$$->set_addr = $2;
	} |
	TOK_SECTION TOK_NUMBER TOK_NUMBER TOK_ID {
		struct evm_section_s *sect = calloc(1, sizeof(struct evm_section_s));
		sect->begin = $2;
		sect->end = $3;
		sect->name = strdup($4);
		sect->next = sections;
		sections = sect;
		$$ = new_insn(NULL, NULL);
		if (asprintf(&$$->symbol, "_section_%s", $4) < 0)
			abort();
		$$->has_set_addr = true;
		$$->set_addr = $2;
	};

array_type:
	TOK_ARRAY_8U { $$ = VARTYPE_ARRAY_8U; } |
	TOK_ARRAY_8S { $$ = VARTYPE_ARRAY_8S; } |
	TOK_ARRAY_16 { $$ = VARTYPE_ARRAY_16; };

global_type:
	TOK_GLOBAL { $$ = VARTYPE_GLOBAL; } |
	TOK_GLOBAL_8U { $$ = VARTYPE_GLOBAL_8U; } |
	TOK_GLOBAL_8S { $$ = VARTYPE_GLOBAL_8S; };

number:
	TOK_NUMBER { $$ = $1; } |
	'+' TOK_NUMBER { $$ = $2; } |
	'-' TOK_NUMBER { $$ = -$2; };

array_init_data:
	/* empty */ {
		$$.len = 0;
		$$.data = NULL;
	} |
	number {
		$$.len = 1;
		$$.data = malloc(64 * sizeof(int));
		$$.data[0] = $1;
	} |
	array_init_data ',' number {
		$$ = $1;
		$$.len++;
		$$.data = realloc($$.data, 64 * ($$.len/64 + 1) * sizeof(int));
		$$.data[$$.len-1] = $3;
	};

array_init:
	/* empty */ { $$.len = -1; $$.data = NULL; } |
	'=' '{' array_init_data '}' { $$ = $3; };

global_var_init:
	/* empty */ { $$ = NULL; } |
	'=' number {
		uint8_t *p = malloc(2);
		p[0] = $2 >> 8;
		p[1] = $2;
		$$ = p;
	};

maybe_extern:
	/* empty */ { $$ = -1; } |
	TOK_EXTERN TOK_NUMBER { $$ = $2; };

global_data:
	maybe_extern global_type TOK_ID global_var_init ';' {
		$$ = new_insn_data($2 == VARTYPE_GLOBAL ? 2 : 1, NULL, NULL);
		$$->symbol = strdup($3);
		$$->initdata = $4;
		add_nametab_global($3, $2, $$);
		if ($1 >= 0) {
			if ($4 != NULL) {
				fprintf(stderr, "Error in line %d: Extern declaration of `%s' with initializer!\n", yyget_lineno(), $3);
				exit(1);
			}
			$$->addr = $1;
			$$ = NULL;
		}
	} |
	maybe_extern array_type TOK_ID '[' TOK_NUMBER ']' array_init ';' {
		int i, wordsize = $2 == VARTYPE_ARRAY_16 ? 2 : 1;
		$$ = new_insn_data(wordsize * $5, NULL, NULL);
		$$->symbol = strdup($3);
		if ($7.len >= 0) {
			$$->initdata = calloc($5, wordsize);
			for (i=0; i < $5 && i < $7.len; i++) {
				if ($2 == VARTYPE_ARRAY_16) {
					$$->initdata[2*i] = $7.data[i] >> 8;
					$$->initdata[2*i + 1] = $7.data[i];
				} else {
					$$->initdata[i] = $7.data[i];
				}
			}
		}
		add_nametab_global($3, $2, $$);
		if ($1 >= 0) {
			if ($7.len >= 0) {
				fprintf(stderr, "Error in line %d: Extern declaration of `%s' with initializer!\n", yyget_lineno(), $3);
				exit(1);
			}
			$$->addr = $1;
			$$ = NULL;
		}
	};

function_head:
	maybe_extern TOK_FUNCTION { goto_ids=NULL; local_ids=NULL; $$ = $1; };

function_def:
	function_head TOK_ID '(' function_args ')' ';' {
		struct nametab_entry_s *e = add_nametab_global($2, VARTYPE_FUNC, $$);
		e->num_args = $4;
		e->addr = new_insn(NULL, NULL);
		if ($1 >= 0)
			e->addr->addr = $1;
		else {
			e->is_forward_decl = true;
		}
		$$ = NULL;
	} |
	function_head TOK_ID '(' function_args ')' '{' function_vars function_body '}' {
		if ($1 >= 0) {
			fprintf(stderr, "Error in line %d: Extern declaration of `%s' with implementation!\n", yyget_lineno(), $2);
			exit(1);
		}
		int local_vars = $7;
		struct evm_insn_s *alloc_local = NULL;
		while (local_vars > 0) {
			int this_num = local_vars > 8 ? 8 : local_vars;
			alloc_local = new_insn_op(0xf0 + (this_num-1), alloc_local, NULL);
			local_vars -= this_num;
		}
		$$ = new_insn(alloc_local, $8);
		struct evm_insn_s *last_insn = $$;
		while (last_insn->right != NULL)
			last_insn = last_insn->right;
		if (last_insn->opcode != 0x9b && last_insn->opcode != 0x9c)
			$$ = new_insn_op(0x9c, $$, NULL);
		struct nametab_entry_s *e = find_global_nametab_entry($2);
		if (e) {
			if (!e->is_forward_decl) {
				fprintf(stderr, "Error in line %d: Re-declaration of identifier `%s'\n", yyget_lineno(), $2);
				exit(1);
			}
			if (e->num_args != $4) {
				fprintf(stderr, "Error in line %d: Declaration and implementation of `%s'\nhave a different number of arguments!\n", yyget_lineno(), $2);
				exit(1);
			}
			e->is_forward_decl = false;
			$$ = new_insn(e->addr, $$);
			e->addr = $$;
		} else {
			e = add_nametab_global($2, VARTYPE_FUNC, $$);
			e->num_args = $4;
		}
		$$->symbol = strdup($2);
		for (e = goto_ids; e != NULL; e = e->next) {
			if (e->is_forward_decl) {
				fprintf(stderr, "Error in line %d: Goto label `%s' used but not declared!\n", yyget_lineno(), e->name);
				exit(1);
			}
		}
		assert(loopctx_stack == NULL);
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
	TOK_ID ':' statement {
		struct nametab_entry_s *e = find_nametab_goto($1);
		if (e && e->is_forward_decl)
			e->is_forward_decl = false;
		else
			e = add_nametab_goto($1);
		$$ = new_insn(e->addr, $3);
	} |
	TOK_GOTO TOK_ID ';' {
		struct nametab_entry_s *e = find_nametab_goto($2);
		if (!e) {
			e = add_nametab_goto($2);
			e->is_forward_decl = true;
		}
		$$ = new_insn_op_reladdr(0xa0 + 1, e->addr, NULL, NULL);
	} |
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
	TOK_DO loop_body TOK_WHILE '(' expression ')' ';' {
		struct evm_insn_s *body = new_insn($2->body_insn, $2->continue_insn);
		$$ = new_insn_op_reladdr(0xa0 + 5, body, new_insn(body, $5), NULL);
		$$ = new_insn($$, $2->break_insn);
	} |
	TOK_WHILE '(' expression ')' loop_body {
		struct evm_insn_s *end = new_insn(NULL, NULL);
		$$ = new_insn_op_reladdr(0xa0 + 7, end, $3,
				new_insn_op_reladdr(0xa0 + 1, $3, $5->body_insn, end));
		$$ = new_insn(new_insn($5->continue_insn, $$), $5->break_insn);
	} |
	TOK_FOR '(' maybe_core_statement ';' expression ';' maybe_core_statement ')' loop_body {
		struct evm_insn_s *end = $9->break_insn;
		struct evm_insn_s *loop = new_insn_op_reladdr(0xa0 + 7, end, $5,
				new_insn_op_reladdr(0xa0 + 1, $5, new_insn($9->body_insn,
				new_insn($9->continue_insn, $7)), end));
		$$ = new_insn($3, loop);
	} |
	TOK_FOR '(' maybe_core_statement ';' ';' maybe_core_statement ')' loop_body {
		$$ = new_insn($3, new_insn_op_reladdr(0xa0 + 1, $8->body_insn,
				new_insn($8->body_insn, new_insn($8->continue_insn, $6)), NULL));
		$$ = new_insn($$, $8->break_insn);
	} |
	TOK_BREAK ';' {
		if (!loopctx_stack) {
			fprintf(stderr, "Fond break outside loop in line %d!\n", yyget_lineno());
			exit(1);
		}
		$$ = new_insn_op_reladdr(0xa0 + 1, loopctx_stack->break_insn, NULL, NULL);
	} |
	TOK_CONTINUE ';' {
		if (!loopctx_stack) {
			fprintf(stderr, "Fond continue outside loop in line %d!\n", yyget_lineno());
			exit(1);
		}
		$$ = new_insn_op_reladdr(0xa0 + 1, loopctx_stack->continue_insn, NULL, NULL);
	} |
	TOK_RETURN expression ';' {
		$$ = new_insn_op(0x9b, $2, NULL);
	} |
	TOK_RETURN ';' {
		$$ = new_insn_op(0x9c, NULL, NULL);
	};

loop_body: {
		struct loopcontext_s *ctx = malloc(sizeof(struct loopcontext_s));
		ctx->break_insn = new_insn(NULL, NULL);
		ctx->continue_insn = new_insn(NULL, NULL);
		ctx->next = loopctx_stack;
		loopctx_stack = ctx;
	} statement {
		$$ = loopctx_stack;
		loopctx_stack = loopctx_stack->next;
		$$->body_insn = $2;
		$$->next = NULL;
	};

combined_assign:
	TOK_ASSIGN_ADD { $$ = 0x80; } |
	TOK_ASSIGN_SUB { $$ = 0x81; } |
	TOK_ASSIGN_MUL { $$ = 0x82; } |
	TOK_ASSIGN_DIV { $$ = 0x83; } |
	TOK_ASSIGN_MOD { $$ = 0x84; } |
	TOK_ASSIGN_SHL { $$ = 0x85; } |
	TOK_ASSIGN_SHR { $$ = 0x86; } |
	TOK_ASSIGN_AND { $$ = 0x87; } |
	TOK_ASSIGN_OR  { $$ = 0x88; } |
	TOK_ASSIGN_XOR { $$ = 0x89; };
	
core_statement:
	func_expression {
		$$ = new_insn_op(0x9d, $1, NULL);
	} |
	TOK_INC lvalue {
		$$ = generate_pre_post_inc_dec($2, true, true, false);
	} |
	TOK_DEC lvalue {
		$$ = generate_pre_post_inc_dec($2, true, false, false);
	} |
	lvalue TOK_INC {
		$$ = generate_pre_post_inc_dec($1, false, true, false);
	} |
	lvalue TOK_DEC {
		$$ = generate_pre_post_inc_dec($1, false, false, false);
	} |
	lvalue combined_assign expression {
		$$ = generate_combined_assign($1, new_insn_op($2, $3, NULL), false, false);
	} |
	lvalue '=' expression {
		$$ = new_insn($3, $1);
	};

maybe_core_statement:
	/* empty */ { $$ = NULL; } |
	core_statement { $$ = $1; };

ptr_type:
	/* TOK_PTR_F  { $$ = VARTYPE_FUNC; } | */
	TOK_PTR_8U { $$ = VARTYPE_ARRAY_8U; } |
	TOK_PTR_8S { $$ = VARTYPE_ARRAY_8S; } |
	TOK_PTR_16 { $$ = VARTYPE_ARRAY_16; };

ptr_index:
	/* empty */ { $$ = NULL; } |
	',' expression { $$ = $2; };

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
		case VARTYPE_GLOBAL:
			$$ = new_insn_op_absaddr(0xe8 + 1, e->addr, NULL, NULL);
			break;
		case VARTYPE_GLOBAL_8U:
			$$ = new_insn_op_absaddr(0xc8 + 1, e->addr, NULL, NULL);
			break;
		case VARTYPE_GLOBAL_8S:
			$$ = new_insn_op_absaddr(0xd8 + 1, e->addr, NULL, NULL);
			break;
		default:
			fprintf(stderr, "Identifier `%s' used incorrectly in line %d!\n", $1, yyget_lineno());
			exit(1);
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
		case VARTYPE_ARRAY_8U:
			$$ = new_insn_op_absaddr(0xc8 + 4, e->addr, $3, NULL);
			break;
		case VARTYPE_ARRAY_8S:
			$$ = new_insn_op_absaddr(0xd8 + 4, e->addr, $3, NULL);
			break;
		case VARTYPE_ARRAY_16:
			$$ = new_insn_op_absaddr(0xe8 + 4, e->addr, $3, NULL);
			break;
		default:
			fprintf(stderr, "Identifier `%s' used incorrectly in line %d!\n", $1, yyget_lineno());
			exit(1);
		}
	} |
	ptr_type '[' expression ptr_index ']' {
		$$ = $3;
		if ($4) {
			$$ = new_insn($$, $4);
			if ($1 == VARTYPE_ARRAY_16) {
				$$ = new_insn_op(0x90 + 1, $$, NULL);
				$$ = new_insn_op(0x80 + 5, $$, NULL);
			}
			$$ = new_insn_op(0x80, $$, NULL);
		}
		switch ($1)
		{
		case VARTYPE_ARRAY_8U:
			$$ = new_insn_op(0xc8 + 2, $$, NULL);
			break;
		case VARTYPE_ARRAY_8S:
			$$ = new_insn_op(0xd8 + 2, $$, NULL);
			break;
		case VARTYPE_ARRAY_16:
			$$ = new_insn_op(0xe8 + 2, $$, NULL);
			break;
		default:
			fprintf(stderr, "Pointer used incorrectly in line %d!\n", yyget_lineno());
			exit(1);
		}
	};

func_expression:
	TOK_ID '(' func_call_args ')' {
		struct nametab_entry_s *e = find_global_nametab_entry($1);
		if (!e || e->type != VARTYPE_FUNC) {
			fprintf(stderr, "Unkown function `%s' in line %d!\n", $1, yyget_lineno());
			exit(1);
		}
		if (e->num_args != $3->num) {
			fprintf(stderr, "Call of function `%s' with incorrect number of arguments in line %d!\n", $1, yyget_lineno());
			exit(1);
		}
		struct evm_insn_s *popargs = NULL;
		while ($3->num > 0) {
			int this_num = $3->num > 8 ? 8 : $3->num;
			popargs = new_insn_op(0xf8 + (this_num-1), popargs, NULL);
			$3->num -= this_num;
		}
		$$ = new_insn_op_reladdr(0xa0 + 3, e->addr, $3->insn, popargs);
	} |
	TOK_USERFUNC '(' func_call_args ')' {
		$$ = new_insn_op_val(0x9a, $3->num, $3->insn, NULL);
		$$ = new_insn_op(0xb0 + $1, $$, NULL);
	} |
	TOK_PTR_F '[' expression ']' '(' func_call_args ')' {
		struct evm_insn_s *popargs = NULL;
		while ($6->num > 0) {
			int this_num = $6->num > 8 ? 8 : $6->num;
			popargs = new_insn_op(0xf8 + (this_num-1), popargs, NULL);
			$6->num -= this_num;
		}
		$$ = new_insn_op(0x9e, new_insn($6->insn, $3), popargs);
	};

expression:
	func_expression {
		$$ = $1;
	} |
	'(' expression ')' {
		$$ = $2;
	} |
	TOK_NUMBER {
		$$ = new_insn_op_val(0x9a, $1, NULL, NULL);
	} |
	TOK_LINE {
		$$ = new_insn_op_val(0x9a, yyget_lineno(), NULL, NULL);
	} |
	TOK_VMIP {
		struct evm_insn_s *here = new_insn(NULL, NULL);
		$$ = new_insn_op_absaddr(0x9a, here, here, NULL);
	} |
	TOK_VMSP {
		$$ = new_insn_op(0xae, NULL, NULL);
	} |
	TOK_VMSFP {
		$$ = new_insn_op(0xaf, NULL, NULL);
	} |
	lvalue {
		/* convert store op to load op */
		struct evm_insn_s *insn = $1;
		if (insn->opcode >= 0xc0 && insn->opcode < 0xf0) {
			insn->opcode -= 0x08;
		}
		else if (insn->opcode >= 0x40 && insn->opcode < 0x80) {
			insn->opcode -= 0x40;
		}
		else
			abort();
		$$ = insn;
	} |
	'&' TOK_ID {
		struct nametab_entry_s *e = find_nametab_entry($2);
		if (!e) {
			fprintf(stderr, "Unkown global identifier `%s' in line %d!\n", $2, yyget_lineno());
			exit(1);
		}
		switch (e->type)
		{
		case VARTYPE_FUNC:
		case VARTYPE_GLOBAL:
		case VARTYPE_GLOBAL_8U:
		case VARTYPE_GLOBAL_8S:
		case VARTYPE_ARRAY_8U:
		case VARTYPE_ARRAY_8S:
		case VARTYPE_ARRAY_16:
			$$ = new_insn_op_absaddr(0x9a, e->addr, NULL, NULL);
			break;
		case VARTYPE_LOCAL:
			$$ = new_insn_op(0xaf, NULL, NULL);
			$$ = new_insn_op_val(0x9a, 2 * (e->index + 1), $$, NULL);
			$$ = new_insn_op(0x80 + 1, $$, NULL);
			break;
		default:
			fprintf(stderr, "Identifier `%s' used incorrectly in line %d!\n", $2, yyget_lineno());
			exit(1);
		}
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
	expression TOK_LAND expression {
		$$ = new_insn_op(0x80 + 10, new_insn($1, $3), NULL);
	} |
	expression TOK_LOR expression {
		$$ = new_insn_op(0x80 + 11, new_insn($1, $3), NULL);
	} |
	'~' expression %prec NEG {
		if ($2->opcode == 0x9a) {
			$2->arg_val = ~$2->arg_val;
			$$ = $2;
		} else
			$$ = new_insn_op(0x80 + 12, $2, NULL);
	} |
	'-' expression %prec NEG {
		if ($2->opcode == 0x9a) {
			$2->arg_val = -$2->arg_val;
			$$ = $2;
		} else
			$$ = new_insn_op(0x80 + 13, $2, NULL);
	} |
	'!' expression %prec NEG {
		if ($2->opcode == 0x9a) {
			$2->arg_val = !$2->arg_val;
			$$ = $2;
		} else
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
	TOK_INC lvalue {
		$$ = generate_pre_post_inc_dec($2, true, true, true);
	} |
	TOK_DEC lvalue {
		$$ = generate_pre_post_inc_dec($2, true, false, true);
	} |
	lvalue TOK_INC {
		$$ = generate_pre_post_inc_dec($1, false, true, true);
	} |
	lvalue TOK_DEC {
		$$ = generate_pre_post_inc_dec($1, false, false, true);
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
		$$->insn = new_insn($3, $$->insn);
		$$->num++;
	};

%%

static struct evm_insn_s *generate_pre_post_inc_dec(struct evm_insn_s *lv,
		bool is_pre, bool is_inc, bool is_expr)
{
	struct evm_insn_s *action = new_insn_op(0x90 + 1, NULL, NULL);
	action = new_insn_op(is_inc ? 0x80 : 0x81 , action, NULL);

	return generate_combined_assign(lv, action, is_pre, is_expr);
}

static struct evm_insn_s *generate_combined_assign(struct evm_insn_s *lv,
		struct evm_insn_s *action, bool is_pre, bool is_expr)
{
	struct evm_insn_s *insn = lv;
	bool lvalue_prep = false;
	uint8_t store_opcode;

	/* convert lvalue to load op and save store opcode */
	store_opcode = insn->opcode;
	if (insn->opcode >= 0xc0 && insn->opcode < 0xf0) {
		insn->opcode -= 0x08;
	}
	else if (insn->opcode >= 0x40 && insn->opcode < 0x80) {
		insn->opcode -= 0x40;
	}
	else
		abort();

	if (insn->left) {
		/* inject dup */
		insn->left = new_insn_op(0xc5, insn->left, NULL);
		lvalue_prep = true;
	}

	/* copy old value for postfix */
	if (is_expr && !is_pre)
		insn = new_insn_op(0xc5 + (lvalue_prep ? 1 : 0)*8, insn, NULL);

	/* perform operation */
	insn = new_insn(insn, action);

	/* copy new value for prefix */
	if (is_expr && is_pre)
		insn = new_insn_op(0xc5 + (lvalue_prep ? 1 : 0)*8, insn, NULL);

	/* shuffle address to top if needed */
	if (lvalue_prep)
		insn = new_insn_op(0xc6, insn, NULL);

	/* perform store operation */
	insn = new_insn_op(store_opcode, insn, NULL);
	insn->has_arg_data = lv->has_arg_data;
	insn->arg_addr = lv->arg_addr;

	return insn;
}

static struct nametab_entry_s *add_nametab_goto(char *name)
{
	struct nametab_entry_s *e = find_nametab_goto(name);
	if (e) {
		fprintf(stderr, "Error in line %d: Re-declaration of goto label `%s'\n", yyget_lineno(), name);
		exit(1);
	}
	e = calloc(1, sizeof(struct nametab_entry_s));
	e->name = name;
	e->addr = new_insn(NULL, NULL);
	e->next = goto_ids;
	goto_ids = e;
	return e;
}

static struct nametab_entry_s *add_nametab_local(char *name, int index)
{
	struct nametab_entry_s *e = find_nametab_entry(name);
	if (e) {
		fprintf(stderr, "Error in line %d: Re-declaration of identifier `%s'\n", yyget_lineno(), name);
		exit(1);
	}
	e = calloc(1, sizeof(struct nametab_entry_s));
	e->name = name;
	e->type = VARTYPE_LOCAL;
	e->index = index;
	e->next = local_ids;
	local_ids = e;
	return e;
}

static struct nametab_entry_s *add_nametab_global(char *name, int type, struct evm_insn_s *addr)
{
	struct nametab_entry_s *e = find_global_nametab_entry(name);
	if (e) {
		fprintf(stderr, "Error in line %d: Re-declaration of identifier `%s'\n", yyget_lineno(), name);
		exit(1);
	}
	e = calloc(1, sizeof(struct nametab_entry_s));
	e->name = name;
	e->type = type;
	e->addr = addr;
	e->next = global_ids;
	global_ids = e;
	return e;
}

struct nametab_entry_s *find_nametab_backend(struct nametab_entry_s *tab, char *name)
{
	for (; tab != NULL; tab = tab->next) {
		if (!strcmp(tab->name, name))
			return tab;
	}
	return NULL;
}

struct nametab_entry_s *find_nametab_goto(char *name)
{
	return find_nametab_backend(goto_ids, name);
}

struct nametab_entry_s *find_nametab_entry(char *name)
{
	struct nametab_entry_s *tab = find_nametab_backend(local_ids, name);
	if (!tab)
		tab = find_nametab_backend(global_ids, name);
	return tab;
}

struct nametab_entry_s *find_global_nametab_entry(char *name)
{
	return find_nametab_backend(global_ids, name);
}

