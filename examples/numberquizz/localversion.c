#include <stdio.h>
#include <stdlib.h>
#include "embedvm.h"

#include "vmcode.hdr"

#define UNUSED __attribute__((unused))

uint8_t vm_mem[256] = { EMBEDVM_SECT_SRAM_DATA };
struct embedvm_s vm = { };

int16_t mem_read(uint16_t addr, bool is16bit, void *ctx)
{
	if (addr + (is16bit ? 1 : 0) >= sizeof(vm_mem))
		return 0;
	if (is16bit)
		return (vm_mem[addr] << 8) | vm_mem[addr+1];
	return vm_mem[addr];
}

void mem_write(uint16_t addr, int16_t value, bool is16bit, void *ctx)
{
	if (addr + (is16bit ? 1 : 0) >= sizeof(vm_mem))
		return;
	if (is16bit) {
		vm_mem[addr] = value >> 8;
		vm_mem[addr+1] = value;
	} else
		vm_mem[addr] = value;
}

int16_t call_user(uint8_t funcid, uint8_t argc, int16_t *argv, void *ctx)
{
	if (funcid == 0)
		return (random()%99)+1;
	if (funcid == 1) {
		int16_t val = 0;
		printf("Guess the number (two decimal digits): ");
		while (1) {
			int ch = getchar();
			if (ch >= '0' && ch <= '9') {
				putchar(ch);
				val += (ch - '0') * 10;
				break;
			}
		}
		while (1) {
			int ch = getchar();
			if (ch >= '0' && ch <= '9') {
				putchar(ch);
				val += ch - '0';
				break;
			}
		}
		printf("\n");
		return val;
	}
	if (funcid == 2 && argc >= 1) {
		if (argv[0] > 0)
			printf("Try larger numbers.\n");
		else
			printf("Try smaller numbers.\n");
		return 0;
	}
	if (funcid == 3) {
		printf("This is correct!\n");
		return 0;
	}
	if (funcid == 4) {
		printf("\n");
		printf("You currently have %d points.\n", mem_read(EMBEDVM_SYM_points, true, ctx));
		return 0;
	}
}

void setup()
{
	vm.ip = EMBEDVM_SYM_main;
	vm.sp = vm.sfp = sizeof(vm_mem);
	vm.mem_read = &mem_read;
	vm.mem_write = &mem_write;
	vm.call_user = &call_user;
}

void loop()
{
	// Serial.print("<");
	// Serial.print(vm.ip, DEC);
	// Serial.print(">");
	embedvm_exec(&vm);
}


int main(void) {
	setup();
	while(1)
		loop();
}
