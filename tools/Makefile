
CC = gcc
CFLAGS += -MD -Wall -Wextra -Os -ggdb

evmcomp: evmcomp.o parser.tab.o lex.yy.o

parser.tab.c parser.tab.h: parser.y
	bison -d parser.y

lex.yy.c: lexer.l
	flex lexer.l

clean:
	rm -f evmcomp *.d *.o core
	rm -f parser.tab.c parser.tab.h lex.yy.c

-include *.d

