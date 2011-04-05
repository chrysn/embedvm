
// Using http://svn.clifford.at/tools/trunk/arduino-cc.sh:
// arduino-cc -P /dev/ttyACM0 -X 57600 firmware.cc embedvm.c

#include <WProgram.h>
#include "embedvm.h"
#include "vmcode.hdr"

struct embedvm_s vm = { };
uint8_t vm_mem[256] = { EMBEDVM_SECT_SRAM_DATA };
uint16_t vm_counter, vm_millis;

struct tone_s {
	uint16_t freq, on, off;
};

struct tone_s tone_buf[4];
uint8_t tone_buf_out, tone_buf_fill;
uint16_t last_freq, last_time;
bool tone_buf_empty_silent;

void buzzer_setup()
{
        TCCR1A = 0;
        TCCR1B = _BV(WGM12) | _BV(CS11) | _BV(CS10);
        TCCR1C = 0;

        OCR1A  = 0;
        OCR1B  = 0;
        ICR1   = 0;
        TIMSK1 = 0;
        TIFR1  = 0;
	TCNT1  = 0;
}

void buzzer(uint16_t freq)
{
	if (freq == last_freq)
		return;

        TCCR1A = (freq > 0 ? _BV(COM1A0) : 0);
        OCR1A  = freq > 0 ? 0xffff / (freq >> 1) : 0;
	TCNT1  = 0;

	last_freq = freq;
}

int16_t vm_mem_read(uint16_t addr, bool is16bit, void *ctx)
{
	if (addr < sizeof(vm_mem)-1) {
		if (is16bit)
			return (vm_mem[addr] << 8) | vm_mem[addr+1];
		return vm_mem[addr];
	}
	return 0;
}

void vm_mem_write(uint16_t addr, int16_t value, bool is16bit, void *ctx)
{
	if (addr < sizeof(vm_mem)-1) {
		if (is16bit) {
			vm_mem[addr] = value >> 8;
			vm_mem[addr+1] = value;
		} else
			vm_mem[addr] = value;
	}
}

int16_t vm_call_user(uint8_t funcid, uint8_t argc, int16_t *argv, void *ctx)
{
	if (funcid == 1 && argc == 3) {
		uint8_t idx = (tone_buf_out+tone_buf_fill) % 4;
		tone_buf[idx].freq = argv[0];
		tone_buf[idx].on = argv[1];
		tone_buf[idx].off = argv[2];
		tone_buf_fill++;
	}
}

void setup()
{
	Serial.begin(57600);
	Serial.println("Inititalizing...");

	vm.ip = 0xffff;
	vm.sp = sizeof(vm_mem);
	vm.sfp = sizeof(vm_mem);
	vm.mem_read = &vm_mem_read;
	vm.mem_write = &vm_mem_write;
	vm.call_user = &vm_call_user;
	embedvm_interrupt(&vm, EMBEDVM_SYM_main);

	vm_counter = 0;
	vm_millis = 0;

	pinMode(9, OUTPUT);
	digitalWrite(9, LOW);
	buzzer_setup();
	buzzer(0);

	tone_buf_empty_silent = true;
	last_time = millis();
	last_freq = 0;

	Serial.println("Init done. Now playing the song..");

	while (1)
	{
		if (tone_buf_fill == 0) {
			buzzer(0);
			if (!tone_buf_empty_silent)
				Serial.println("Tone buffer is empty!");
			tone_buf_empty_silent = true;
			last_time = millis();
			if (vm.ip == 0xffff)
				break;
		} else {
			uint16_t time_delta = millis() - last_time;
			if (time_delta <  tone_buf[tone_buf_out].on) {
				buzzer(tone_buf[tone_buf_out].freq);
			}
			else if (time_delta-tone_buf[tone_buf_out].on <  tone_buf[tone_buf_out].off) {
				buzzer(0);
			}
			else {
				last_time += time_delta;
				tone_buf_out = (tone_buf_out + 1) % 4;
				tone_buf_fill--;
			}
			tone_buf_empty_silent = false;
		}
		if (vm.ip != 0xffff && tone_buf_fill < 4) {
			uint16_t time_start = millis();
			embedvm_exec(&vm);
			vm_millis += millis() - time_start;
			vm_counter++;
		}
	}

	Serial.print("Executed ");
	Serial.print(vm_counter, DEC);
	Serial.print(" VM instructions in ");
	Serial.print(vm_millis, DEC);
	Serial.println("ms CPU time.");

	Serial.println("Have a nice day!");
}

void loop()
{
}

