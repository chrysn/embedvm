
%{
#include <stdio.h>
#include <stdlib.h>
#include "evm_tools.h"
void yyerror (char const *s) {
        fprintf(stderr, "Parser error in line %d: %s\n", yyget_lineno(), s);
        exit(1);
}
%}

%union {
	int number;
	char *string;
}

%token <number> TOK_NUMBER
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

%expect 1
%debug

%%

input:
	/* empty */ |
//	input meta_statement |
	input global_data |
	input function_def;

global_data:
	TOK_GLOBAL TOK_ID ';' {
	} |
	TOK_ARRAY_8U TOK_ID '[' TOK_NUMBER ']' ';' {
	} |
	TOK_ARRAY_8S TOK_ID '[' TOK_NUMBER ']' ';' {
	} |
	TOK_ARRAY_16 TOK_ID '[' TOK_NUMBER ']' ';' {
	};

function_def:
	TOK_FUNCTION TOK_ID '(' function_args ')' '{' function_body '}' {
	};

function_args:
	/* empty */ |
	TOK_ID {
	} |
	function_args ',' TOK_ID {
	};

function_body:
	/* empty */ |
	function_body TOK_LOCAL TOK_ID ';' {
	} |
	function_body statement;

statement_list:
	/* empty */ |
	function_body statement;

statement:
	core_statement ';' |
	'{' statement_list '}' |
	TOK_IF '(' expression ')' statement |
	TOK_IF '(' expression ')' statement TOK_ELSE statement |
	TOK_DO statement TOK_WHILE '(' expression ')' ';' |
	TOK_WHILE '(' expression ')' statement |
	TOK_FOR '(' core_statement ';' expression ';' core_statement ')' statement |
	TOK_RETURN expression ';' |
	TOK_RETURN ';';

core_statement:
	expression |
	lvalue '=' expression;

lvalue:
	TOK_ID |
	TOK_ID '[' expression ']';

expression:
	TOK_NUMBER |
	'(' expression ')' |
	TOK_ID |
	TOK_ID '[' expression ']' |
	'+' expression %prec NEG |
	'-' expression %prec NEG |
	'~' expression %prec NEG |
	'!' expression %prec NEG |
	expression '+' expression |
	expression '-' expression |
	expression '*' expression |
	expression '/' expression |
	expression '%' expression |
	expression TOK_SHL expression |
	expression TOK_SHR expression |
	expression '&' expression |
	expression '|' expression |
	expression '^' expression |
	expression TOK_LAND expression |
	expression TOK_LOR expression |
	expression '<' expression |
	expression TOK_LE expression |
	expression TOK_EQ expression |
	expression TOK_NE expression |
	expression TOK_GE expression |
	expression '>' expression |
	expression '?' expression ':' expression;

