;-----------------------------------------------------------------------------
; Terminal types.
;-----------------------------------------------------------------------------

 if	termdef			; Once only table definition

;-----------------------------------------------------------------------------
; This just assigns a number to each terminal type.  The numbers themselves
; don't matter just so long as there are no duplicates.  If you add a terminal
; then make up a new entry for it here and add an entry to the inclusion
; list.
;
; Any synonyms should be defined in this section.  For example, the ADM3A,
; Soroc and and Televideo terminals use the same control sequences so they
; should be given the same number.  When soroc is called for, the ADM3A
; definitions will be used.
;-----------------------------------------------------------------------------

none	equ	0
adm3a	equ	1
ansi	equ	2
d8227	equ	3
vt52	equ	4
soroc	equ	4		; Soroc is a synonym for adm3a
tvi	equ	4		; Televideo also

;-----------------------------------------------------------------------------

termdef	defl	false		; Don't touch this

 else	; termdef

;-----------------------------------------------------------------------------
; Include console terminal code or data upon request
;-----------------------------------------------------------------------------

  if	((terminal)=(console))

    if	((conterm)=(adm3a))
	include	"adm3a.tty"
    endif

    if	((conterm)=(ansi))
	include	"ansi.tty"
    endif

    if	((conterm)=(d8227))
	include	"d8227.tty"
    endif

    if	((conterm)=(vt52))
	include	"vt52.tty"
    endif

  endif ; console

;-----------------------------------------------------------------------------
; Include auxiliary terminal code or data upon request
;-----------------------------------------------------------------------------

  if	((terminal)=(auxiliary))

    if	((auxterm)=(adm3a))
	include	"adm3a.tty"
    endif

    if	((auxterm)=(ansi))
	include	"ansi.tty"
    endif

    if	((auxterm)=(d8227))
	include	"d8227.tty"
    endif

    if	((auxterm)=(vt52))
	include	"vt52.tty"
    endif

  endif ; auxiliary

 endif ; termdef
