# Z8E v4.2. One image, assembled with z88dk-z80asm.
# src/config.inc is the configuration. The other *.inc files are samples.

.PHONY: all clean

all: ../build/z8e.com

../build/z8e.com: z8e.asm config.inc terminal.inc ansi.tty adm3a.tty vt52.tty d8227.tty
	mkdir -p ../build
	PATH=/data/z88dk/bin:$$PATH ZCCCFG=/data/z88dk/lib/config \
		z88dk-z80asm -mz80 -ucase -b -l -s z8e.asm
	mv -f z8e_CODE.bin ../build/z8e.com
	rm -f z8e.bin
	mv -f z8e.o z8e.lis z8e.sym ../build/

clean:
	rm -f z8e.bin z8e.o z8e.lis z8e.sym
	rm -f ../build/z8e.com ../build/z8e.o ../build/z8e.lis ../build/z8e.sym
