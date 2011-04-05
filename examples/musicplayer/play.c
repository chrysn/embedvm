#include <math.h>
#include <stdio.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/time.h>
#include <sys/resource.h>

#include "embedvm.h"
#include "vmcode.hdr"

#undef DEBUG
#undef PROFILE

#define UNUSED __attribute__((unused))

#ifndef PROFILE
FILE *aplay_pipe = NULL;
#endif

uint8_t vm_mem[256] = { EMBEDVM_SECT_SRAM_DATA };
struct embedvm_s vm;

int t, insncount;

int16_t mem_read(uint16_t addr, bool is16bit, void *ctx UNUSED)
{
	if (addr + (is16bit ? 1 : 0) >= (uint16_t)sizeof(vm_mem))
		return 0;
	if (is16bit)
		return (vm_mem[addr] << 8) | vm_mem[addr+1];
	return vm_mem[addr];
}

void mem_write(uint16_t addr, int16_t value, bool is16bit, void *ctx UNUSED)
{
	if (addr + (is16bit ? 1 : 0) >= (uint16_t)sizeof(vm_mem))
		return;
	if (is16bit) {
		vm_mem[addr] = value >> 8;
		vm_mem[addr+1] = value;
	} else
		vm_mem[addr] = value;
}

void gentone(uint16_t hz, uint16_t ms)
{
	int start = t;
	while (((t++)-start) < ms*44) {
		double v = sin(2*M_PI*t*hz/44100.0);
		v = hz == 0 ? 0 : (v > 0 ? 1 : -1);
		int16_t sample = htons(3000*v);
		fwrite(&sample, 2, 1, aplay_pipe);
	}
}

int16_t call_user(uint8_t funcid UNUSED, uint8_t argc UNUSED, int16_t *argv UNUSED, void *ctx UNUSED)
{
#ifndef PROFILE
#  ifdef DEBUG
	if (funcid == 0) {
		int i;
		fprintf(stderr, " d");
		for (i=0; i<argc; i++)
			fprintf(stderr, ":%d", argv[i]);
	}
#  endif
	if (funcid == 1 && argc == 3) {
#  ifdef DEBUG
		fprintf(stderr, " t:%d:%d:%d", argv[0], argv[1], argv[2]);
#  endif
		gentone(argv[0], argv[1]);
		gentone(0, argv[2]);
	}
#endif
	return 0;
}

int main()
{
#ifndef PROFILE
	aplay_pipe = popen("aplay -fS16_BE -c1 -r44100", "w");
#endif

	vm.ip = 0xffff;
	vm.sp = vm.sfp = sizeof(vm_mem);
	vm.mem_read = &mem_read;
	vm.mem_write = &mem_write;
	vm.call_user = &call_user;

#ifdef PROFILE
	int i;
	for (i=0; i<1000; i++) {
#endif
		embedvm_interrupt(&vm, EMBEDVM_SYM_main);

		while (vm.ip != 0xffff) {
			insncount++;
			embedvm_exec(&vm);
		}
#ifdef PROFILE
	}
#endif

#ifdef DEBUG
	fprintf(stderr, "\n");
#endif

#ifndef PROFILE
	fclose(aplay_pipe);
#endif

#ifdef PROFILE
	struct rusage ru;
	getrusage(RUSAGE_SELF, &ru);

	double cpu_us = ru.ru_utime.tv_sec*1e6 + ru.ru_utime.tv_usec + 1;
	double mips = insncount / cpu_us;
	int cpu_us_exp = 0, mips_exp = 0;

	while (cpu_us > 1000)
		cpu_us /= 1000, cpu_us_exp += 3;
	while (cpu_us < 1)
		cpu_us *= 1000, cpu_us_exp -= 3;

	while (mips > 1000)
		mips /= 1000, mips_exp += 3;
	while (mips < 1)
		mips *= 1000, mips_exp -= 3;

	fprintf(stderr, "Executed %d VM instructions in %.2fe%d us CPU time (%.2fe%d MIPS).\n",
		insncount, cpu_us, cpu_us_exp, mips, mips_exp);
#endif

	return 0;
}

