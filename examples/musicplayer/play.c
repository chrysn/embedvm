#include <math.h>
#include <stdio.h>
#include <unistd.h>
#include <arpa/inet.h>
#include "embedvm.h"
#include "vmcode.hdr"

#undef DEBUG

#define UNUSED __attribute__((unused))

FILE *aplay_pipe = NULL;

uint8_t vm_mem[512] = { EMBEDVM_SECT_SRAM_DATA };
struct embedvm_s vm;

int t, f;

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

int16_t call_user(uint8_t funcid, uint8_t argc, int16_t *argv, void *ctx UNUSED)
{
#ifdef DEBUG
	if (funcid == 0) {
		int i;
		fprintf(stderr, " d");
		for (i=0; i<argc; i++)
			fprintf(stderr, ":%d", argv[i]);
	}
#endif
	if (funcid == 1 && argc == 1) {
#ifdef DEBUG
		fprintf(stderr, " f:%d", argv[0]);
#endif
		f = argv[0];
	}
	if (funcid == 2 && argc == 1) {
		int start = t;
#ifdef DEBUG
		fprintf(stderr, " w:%d", argv[0]);
#endif
		while (((t++)-start) < argv[0]*44) {
			double v = sin(2*M_PI*t*f/44100.0);
			v = f == 0 ? 0 : (v > 0 ? 1 : -1);
			int16_t sample = htons(3000*v);
			fwrite(&sample, 2, 1, aplay_pipe);
		}
	}
	return 0;
}

int main()
{
	aplay_pipe = popen("aplay -fS16_BE -c1 -r44100", "w");

	vm.ip = 0xffff;
	vm.sp = vm.sfp = sizeof(vm_mem);
	vm.mem_read = &mem_read;
	vm.mem_write = &mem_write;
	vm.call_user = &call_user;

	embedvm_interrupt(&vm, EMBEDVM_SYM_main);

	while (vm.ip != 0xffff) {
		embedvm_exec(&vm);
	}

#ifdef DEBUG
	fprintf(stderr, "\n");
#endif

	return 0;
}

