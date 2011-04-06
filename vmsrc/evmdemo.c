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

#include "embedvm.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#define UNUSED __attribute__((unused))

static bool stop;
static uint8_t memory[64*1024];

static int16_t mem_read(uint16_t addr, bool is16bit, void *ctx UNUSED)
{
	if (is16bit)
		return (memory[addr] << 8) | memory[addr+1];
	return memory[addr];
}

static void mem_write(uint16_t addr, int16_t value, bool is16bit, void *ctx UNUSED)
{
	if (is16bit) {
		memory[addr] = value >> 8;
		memory[addr+1] = value;
	} else
		memory[addr] = value;
}

static int16_t call_user(uint8_t funcid, uint8_t argc, int16_t *argv, void *ctx UNUSED)
{
	int16_t ret = 0;
	int i;

	if (funcid == 0) {
		stop = true;
		printf("Called user function 0 => stop.\n");
		fflush(stdout);
		return ret;
	}

	printf("Called user function %d with %d args:", funcid, argc);

	for (i = 0; i < argc; i++) {
		printf(" %d", argv[i]);
		ret += argv[i];
	}

	printf("\n");
	fflush(stdout);

	return ret ^ funcid;
}

struct embedvm_s vm = {
	0xffff, 0, 0, NULL,
	&mem_read, &mem_write, &call_user
};

int main(int argc, char **argv)
{
	FILE *f;
	int ch, addr;
	char *prog = argv[0];
	bool verbose = false;

	if (argc >= 2 && !strcmp(argv[1], "-v")) {
		verbose = true;
		argc--, argv++;
	}

	if (argc != 3) {
exit_with_helpmsg:
		fprintf(stderr, "Usage: %s [-v] {binfile} {hex-start-addr}\n", prog);
		return 1;
	}

	memset(memory, 0, sizeof(memory));
	f = fopen(argv[1], "rb");
	if (!f)
		goto exit_with_helpmsg;
	for (addr = 0; (ch = fgetc(f)) != -1; addr++)
		memory[addr] = ch;
	fclose(f);

	embedvm_interrupt(&vm, strtol(argv[2], NULL, 16));

	stop = false;
	while (!stop) {
		if (vm.ip == 0xffff) {
			printf("Main function returned => Terminating.\n");
			if (vm.sp != 0 || vm.sfp != 0)
				printf("Unexpected stack configuration on program exit: SP=%04x, SFP=%04x\n", vm.sp, vm.sfp);
			fflush(stdout);
			break;
		}
		if (verbose) {
			fprintf(stderr, "IP: %04x (%02x %02x %02x %02x),  ", vm.ip,
					memory[vm.ip], memory[vm.ip+1], memory[vm.ip+2], memory[vm.ip+3]);
			fprintf(stderr, "SP: %04x (%02x%02x %02x%02x %02x%02x %02x%02x), ", vm.sp,
					memory[vm.sp + 0], memory[vm.sp + 1],
					memory[vm.sp + 2], memory[vm.sp + 3],
					memory[vm.sp + 4], memory[vm.sp + 5],
					memory[vm.sp + 6], memory[vm.sp + 7]);
			fprintf(stderr, "SFP: %04x\n", vm.sfp);
			fflush(stderr);
		}
		embedvm_exec(&vm);
	}

	f = fopen("evmdemo.core", "wb");
	if (f) {
		fwrite(memory, sizeof(memory), 1, f);
		fclose(f);
	}

	return 0;
}

