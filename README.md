# Z8E Debugger

Z8E is a full-screen symbolic debugger for the Z80 CPU, known from the
former CP/M User Groups.

Main features:

* Screen-oriented.
* Animated debugging.
* Z80 and Z180 versions.
* Auxiliary terminal support.

The current version is 4.2, which fixes an obscure bug that affected reading
of symbol table files that ended exactly at a record boundary without an
explicit end-of-file character (a valid CP/M condition).

More details [here](http://p112.sourceforge.net/index.php?z8e).

This tree's `src/config.inc` builds one Z80 image for CP/M 2.2: an ANSI console, an ANSI auxiliary terminal, and breakpoints on RST 30h. CP/M-IDE uses address 0038h for the SIO interrupt. The auxiliary character path is BDOS reader and punch, which the CP/M-IDE SIO BIOS sends to channel B when those IOBYTE fields are TTY. The terminal files in `src/*.tty` are configurations and are not rewritten for the SIO.

Assemble that image with z88dk:

```bash
make -C src
```

`sh z88dk/build.sh` runs the same makefile. The COM is `build/z8e.com`. `src/config.inc` is the configuration that is built. `18e1.inc`, `18e2.inc`, `z8e1.inc`, and `z8e2.inc` are sample configurations. `src/z8e.z80` is the original MACRO-80 source, kept beside `src/z8e.asm`, and is not assembled. The formatted manual is `z8e.md`.
