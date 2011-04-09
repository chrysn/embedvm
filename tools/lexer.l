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
#include "evmcomp.h"
#include "parser.tab.h"
%}

%option yylineno
%option noyywrap

%x comment

%%

"if"		return TOK_IF;
"else"		return TOK_ELSE;

"do"		return TOK_DO;
"for"		return TOK_FOR;
"while"		return TOK_WHILE;
"break"		return TOK_BREAK;
"continue"	return TOK_CONTINUE;
"goto"		return TOK_GOTO;
"return"	return TOK_RETURN;
"function"	return TOK_FUNCTION;

"local"		return TOK_LOCAL;
"global"	return TOK_GLOBAL;
"global8u"	return TOK_GLOBAL_8U;
"global8s"	return TOK_GLOBAL_8S;

"array8u"	return TOK_ARRAY_8U;
"array8s"	return TOK_ARRAY_8S;
"array16"	return TOK_ARRAY_16;

"$ptr8u"	return TOK_PTR_8U;
"$ptr8s"	return TOK_PTR_8S;
"$ptr16"	return TOK_PTR_16;
"$ptrf"		return TOK_PTR_F;

"$line"		return TOK_LINE;
"$vmip"		return TOK_VMIP;
"$vmsp"		return TOK_VMSP;
"$vmsfp"	return TOK_VMSFP;

"$extern"	return TOK_EXTERN;
"$memaddr"	return TOK_MEMADDR;
"$section"	return TOK_SECTION;
"$trampoline"	return TOK_TRAMPOLINE;

"$uf"[0-8]	{ yylval.number = yytext[3] - '0'; return TOK_USERFUNC; }

"<<"		return TOK_SHL;
">>"		return TOK_SHR;

"&&"		return TOK_LAND;
"||"		return TOK_LOR;

"<="		return TOK_LE;
"=="		return TOK_EQ;
"!="		return TOK_NE;
">="		return TOK_GE;

"++"		return TOK_INC;
"--"		return TOK_DEC;

"+="		return TOK_ASSIGN_ADD;
"-="		return TOK_ASSIGN_SUB;
"*="		return TOK_ASSIGN_MUL;
"/="		return TOK_ASSIGN_DIV;
"%="		return TOK_ASSIGN_MOD;
"<<="		return TOK_ASSIGN_SHL;
">>="		return TOK_ASSIGN_SHR;
"&="		return TOK_ASSIGN_AND;
"|="		return TOK_ASSIGN_OR;
"^="		return TOK_ASSIGN_XOR;

"true"			{ yylval.number = 1; return TOK_NUMBER; }
"false"			{ yylval.number = 0; return TOK_NUMBER; }

[1-9][0-9]*		{ yylval.number = atoi(yytext); return TOK_NUMBER; }
"0"[0-7]*		{ yylval.number = strtol(yytext+1, NULL, 8); return TOK_NUMBER; }
"0b"[01]+		{ yylval.number = strtol(yytext+2, NULL, 2); return TOK_NUMBER; }
"0x"[0-9a-fA-F]+	{ yylval.number = strtol(yytext+2, NULL, 16); return TOK_NUMBER; }

[a-zA-Z_][a-zA-Z0-9_]* { yylval.string = strdup(yytext); return TOK_ID; }

"/*" BEGIN(comment);
<comment>"*/" BEGIN(INITIAL);
<comment>.|\n

"//"[^\n]*\n

"$include"[ \t]+\"[^\"]+\" {
	char *fn = strdup(yytext);
	fn = strtok(fn, "\"");
	fn = strtok(NULL, "\"");
	yyin = fopen(fn, "r" );
	if (yyin == NULL) {
		fprintf(stderr, "Can't open include file `%s'!\n", fn);
		exit(1);
	}
	yypush_buffer_state(yy_create_buffer(yyin, YY_BUF_SIZE));
}

<<EOF>> {
	yypop_buffer_state();
	if (!YY_CURRENT_BUFFER)
		yyterminate();
}


[ \t\n\r]	/* ignore whitespaces */
.		return *yytext;

%%

// this is a hack to force gcc not to generate the following error msgs:
//   lex.yy.c:1327: warning: ‘yyunput’ defined but not used
//   lex.yy.c:1372: warning: ‘input’ defined but not used
void *avoid_gcc_yyunput_input_warnings(int i) {
	return i ? (void*)&yyunput : (void*)&input;
}

