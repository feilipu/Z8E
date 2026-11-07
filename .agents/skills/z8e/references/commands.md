# Z8E commands

The prompt is `*`. A command is one letter. Square brackets are optional. Full narrative is in `z8e.md`. This build's breakpoint vector is `brkvec` in `src/config.inc` (see the z8e skill).

```
A   assemble at StartAddr
B   breakpoint Addr [,pass] [Addr ...]     up to 16; a hit prints *BP*XXXX
C   clear Addr [Addr ...]                  C * clears all
D   dump [Start] [End or count]
E   examine / modify Start
F   find Start Match
G   go [Addr]
H   symbol table [FirstSymbol]
I   initialise the default FCB and tail [text]
J   full-screen step [/] [*] [Addr] [Timeout]
K   memory window Start [Size]             for J
L   load File [,address]
M   move SourceStart SourceEnd DestStart
N   port output, no pre-read [(] Port [)]
O   show breakpoints
P   flags
Q   port query [(] Port [)]
R   registers
S   single-step [/] [Count]
T   debug terminal A or C
U   write symbols File
V   verify SourceStart SourceEnd DestStart
W   write memory File [Start] [End]
X   machine state
Y   fill From To Data
Z   disassemble Start End/Count [File]
?   evaluate Expression
>   user number
```

`[/]` does not trace into a subroutine. `[*]` does not trace a BDOS call. `[(]` `)]` is port-monitor mode.

## Arguments

Hex is the default. Only the right-most four digits count for a 16-bit value, or two digits for an 8-bit value. A number that looks like a symbol (DEAD, AF, BC, DE) needs a leading 0 when a symbol table is loaded.

A decimal ends with `#`. `*E 512#` is address 200h.

Registers as arguments: AF BC DE HL SP IX IY. `P` is the program counter only when it is not inside an expression. Inside an expression the program counter is `PC`. Prime register names are only valid in R. One register per expression, and it has to be the first term. `(HL)` and `(SP)` are the word at that register.

Expressions are `+` and `-`, evaluated left to right. No parentheses.

An argument error prints `?`.

## A — assemble

```
LABEL: opcode [operand] [,operand]
```

The label is optional and ends with a colon. The first 6 characters are significant. Directives: ORG, DEFB, DDB, EQU, DEFW. One pass, so no forward references. In this assembler, `$` is the location counter.
