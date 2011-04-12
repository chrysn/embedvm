#
#  EmbedVM - Embedded Virtual Machine for uC Applications
#
#  Copyright (C) 2011  Clifford Wolf <clifford@clifford.at>
#  
#  Permission to use, copy, modify, and/or distribute this software for any
#  purpose with or without fee is hereby granted, provided that the above
#  copyright notice and this permission notice appear in all copies.
#  
#  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
#  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
#  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
#  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
#  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
#  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

CC = gcc
CFLAGS += -MD -Wall -Wextra -Os -ggdb

all: evmdemo

evmdemo: evmdemo.o embedvm.o

install: evmdemo
	install -TD evmdemo /usr/local/bin/evmdemo
	install -TD -m0644 embedvm.c /usr/local/share/embedvm/embedvm.c
	install -TD -m0644 embedvm.h /usr/local/share/embedvm/embedvm.h

clean:
	rm -f evmdemo evmdemo.core *.d *.o core

-include *.d

