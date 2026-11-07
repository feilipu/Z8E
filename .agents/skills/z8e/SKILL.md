---
name: z8e
description: >
  Z8E v4.2, the Z80 debugger built in this tree for CP/M-IDE: ANSI
  console, ANSI auxiliary, CP/M 2.2, RST 30h breakpoints. Use when
  working in /data/Z8E, assembling z8e.asm, or answering questions
  about Z8E commands, breakpoints, symbols, or the second terminal.
---

# Z8E

Z8E is a screen-oriented symbolic debugger. This tree builds one Z80 image. The printed manual is `z8e.md`. Command syntax and typing rules are `references/commands.md`. Appendix B of the manual is the mnemonic list. Do not copy it into a skill.

## This build

`src/config.inc` is the configuration:

| Symbol | Value |
|--------|--------|
| `z180` | false |
| `conterm` | ansi |
| `auxterm` | ansi |
| `CPM3` | false |
| `brkvec` | 30h |

Assemble with `make -C src` (or `sh z88dk/build.sh`, which runs that makefile). The product is `build/z8e.com` (load address 100h, 11995 bytes, banner `Z8E v4.2`). `src/config.inc` is the image that is built. `18e1.inc`, `18e2.inc`, `z8e1.inc`, and `z8e2.inc` are samples. `src/z8e.z80` is the original MACRO-80 source and is not assembled.

CP/M-IDE uses address 0038h for the SIO interrupt. Breakpoints are RST 30h. Init reads the patchable byte `rstVec` and plants that RST. The manual's 38h is the upstream default.

The auxiliary character path is BDOS function 3 (reader) and function 4 (punch). The CP/M-IDE SIO BIOS sends those to channel B when the IOBYTE reader and punch fields are TTY. The auxiliary status sample in `src/*.tty` still reads port 4, bit 7. On the RC2014 SIO, receiver-ready is bit 0 of channel B control port 82h, so that sample does not see the SIO. Do not retarget it.

## Run

```
Z8E
Z8E file.COM
Z8E (32) file.COM file.SYM
```

`(32)` must be the first argument. It reserves space for that many keyboard symbols. The first filename is the program, loaded at 100h. Later names are SYM, PRN, or LST files, each with an optional bias.

Z8E reads the BDOS address at 0006h, lowers it by the monitor size, and relocates under BDOS. The user's PC starts at 100h. The user's SP is the base of relocated Z8E minus 2, and those two bytes are 0000 (RET warm-boots through 0000).

Do not breakpoint inside BDOS or BIOS after CP/M has saved the user SP.

## Ticks

`z88dk-ticks -mz80 build/z8e.com` loads the COM at 0100h. For a `.com` it plants BDOS as `ED FE C9` at 0005h. That trap enters the CP/M hook only when the PC becomes 0007h, so the trap has to stay at 0005h. The word at 0006h is `C9FEh`. On CP/M-IDE the BDOS is at F206h and 0005h is `JP F206h`.

Z8E reads the word at 0006h, page-aligns it, and relocates below it. `nmem` is 2500h, so the ticks base is A400h and the CP/M-IDE base is CD00h. In `load` it stores the new entry over the word at 0006h. On CP/M that word is the operand of the `JP` at 0005h. Under ticks the store replaces the `FE` of the trap, `call 5` executes `ED 00`, and console output stops. The banner is printed before the store. The memory map and the `*` prompt use the same print path after it.

SIO ports are not implemented in ticks. Startup does not execute RST 30h. Do not nop the store at 0006h in the shipped image.

A throwaway copy can nop `ld (06),hl` in `load` (this COM: file offset 062Fh, `22 06 00`). That copy keeps the trap, prints the map and the `*` prompt, and runs commands. `X` shows the machine state. The user PC is 0100h, still this image, until a program is loaded. The map follows the fake vector: base A400h, end 0000h, top C9FDh. ticks leaves the default FCB at 005Ch as 00h, so startup prints `Loading:` and `File Not Found` before the prompt.
