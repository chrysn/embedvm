
%{
#include "evm_tools.h"
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
"return"	return TOK_RETURN;
"function"	return TOK_FUNCTION;

"local"		return TOK_LOCAL;
"global"	return TOK_GLOBAL;

"array8u"	return TOK_ARRAY_8U;
"array8s"	return TOK_ARRAY_8S;
"array16"	return TOK_ARRAY_16;

"<<"		return TOK_SHL;
">>"		return TOK_SHL;

"&&"		return TOK_LAND;
"||"		return TOK_LOR;

"<="		return TOK_LE;
"=="		return TOK_EQ;
"!="		return TOK_NE;
">="		return TOK_GE;

[1-9][0-9]* { yylval.number = atoi(yytext); return TOK_NUMBER; }
"0"[0-7]* { yylval.number = strtol(yytext+2, NULL, 8); return TOK_NUMBER; }
"0b"[01]+ { yylval.number = strtol(yytext+2, NULL, 2); return TOK_NUMBER; }
"0x"[0-9a-fA-F]+ { yylval.number = strtol(yytext+2, NULL, 16); return TOK_NUMBER; }

[a-zA-Z_][a-zA-Z0-9_]* { yylval.string = strdup(yytext); return TOK_ID; }

"/*" BEGIN(comment);
<comment>"*/" BEGIN(INITIAL);
<comment>.|\n

"//"[^\n]*\n

[ \t\n\r]	/* ignore whitespaces */
.		return *yytext;

