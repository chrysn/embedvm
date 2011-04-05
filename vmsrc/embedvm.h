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

#ifndef EMBEDVM_H
#define EMBEDVM_H

#include <stdint.h>
#include <stdbool.h>

#ifdef  __cplusplus
extern "C" {
#endif

struct embedvm_s
{
	uint16_t ip, sp, sfp;
	void *user_ctx;

	int16_t (*mem_read)(uint16_t addr, bool is16bit, void *ctx);
	void (*mem_write)(uint16_t addr, int16_t value, bool is16bit, void *ctx);
	int16_t (*call_user)(uint8_t funcid, uint8_t argc, int16_t *argv, void *ctx);
};

extern void embedvm_exec(struct embedvm_s *vm);
extern void embedvm_interrupt(struct embedvm_s *vm, uint16_t addr);

int16_t embedvm_pop(struct embedvm_s *vm);
void embedvm_push(struct embedvm_s *vm, int16_t value);

int16_t embedvm_local_read(struct embedvm_s *vm, int8_t sfa);
void embedvm_local_write(struct embedvm_s *vm, int8_t sfa, int16_t value);

#ifdef __cplusplus
}
#endif

#endif
