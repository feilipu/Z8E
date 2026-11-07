#!/bin/sh
# Assemble the CP/M-IDE configuration with z88dk-z80asm.
# src/config.inc selects Z80, ANSI console, ANSI auxiliary, CP/M 2.2.
set -e
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
export PATH=/data/z88dk/bin:${PATH}
export ZCCCFG=/data/z88dk/lib/config
cd "$root/src"
exec make
