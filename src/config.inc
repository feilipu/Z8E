;-----------------------------------------------------------------------------
;		  Z80 debugger, ANSI console and auxiliary, CP/M 2.2
;-----------------------------------------------------------------------------

; Setting Z180 to TRUE enables Hitachi HD64180/Z180 support. Set it to FALSE
; for a Z80-only version of Z8E.

z180	equ	false		; Z80 only

; Define the console terminal

conterm	equ	ansi

; Second terminal, also ANSI. CP/M-IDE sends the reader (BDOS function 3)
; and the punch (BDOS function 4) to Z80 SIO channel B when those IOBYTE
; fields are TTY. The auxiliary status sample in the terminal file is left
; as shipped.

auxterm	equ	ansi

; If you are running under CP/M Plus then you can set CPM3 to true in which
; case the auxiliary input status routine will be a simple BDOS call.
; CP/M-IDE is CP/M 2.2.

CPM3	equ	false

; CP/M-IDE uses address 0038h for the SIO interrupt. Breakpoints use RST 30h.

brkvec	equ	30h
