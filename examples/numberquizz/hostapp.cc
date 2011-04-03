
#include <WProgram.h>
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
		return (millis() % 99) + 1;
	if (funcid == 1) {
		int16_t val = 0;
		Serial.print("Guess the number (two decimal digits): ");
		while (1) {
			int ch = Serial.read();
			if (ch >= '0' && ch <= '9') {
				Serial.write(ch);
				val += (ch - '0') * 10;
				break;
			}
		}
		while (1) {
			int ch = Serial.read();
			if (ch >= '0' && ch <= '9') {
				Serial.write(ch);
				val += ch - '0';
				break;
			}
		}
		Serial.println("");
		return val;
	}
	if (funcid == 2 && argc >= 1) {
		if (argv[0] > 0)
			Serial.println("Try larger numbers.");
		else
			Serial.println("Try smaller numbers.");
		return 0;
	}
	if (funcid == 3) {
		Serial.println("This is correct!");
		return 0;
	}
	if (funcid == 4) {
		Serial.println("");
		Serial.print("You currently have ");
		Serial.print(mem_read(EMBEDVM_SYM_points, true, ctx), DEC);
		Serial.println(" points.");
		return 0;
	}
}

void setup()
{
	Serial.begin(9600);
	Serial.println("Initializing...");

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

