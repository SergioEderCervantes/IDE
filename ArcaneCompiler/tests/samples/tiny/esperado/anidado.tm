* TINY Compilation to TM Code
* File: anidado.tm
* Standard prelude:
  0:     LD  6,0(0) 	load maxaddress from location 0
  1:     ST  0,0(0) 	clear location 0
* End of standard prelude.
  2:     IN  0,0,0 	read integer value
  3:     ST  0,0(5) 	read: store value
* -> if
* -> Op
* -> Const
  4:    LDC  0,0(0) 	load const
* <- Const
  5:     ST  0,0(6) 	op: push left
* -> Id
  6:     LD  0,0(5) 	load id value
* <- Id
  7:     LD  1,0(6) 	op: load left
  8:    SUB  0,1,0 	op <
  9:    JLT  0,2(7) 	br if true
 10:    LDC  0,0(0) 	false case
 11:    LDA  7,1(7) 	unconditional jmp
 12:    LDC  0,1(0) 	true case
* <- Op
* if: jump to else belongs here
* -> repeat
* repeat: jump after body comes back here
* -> if
* -> Op
* -> Id
 14:     LD  0,0(5) 	load id value
* <- Id
 15:     ST  0,0(6) 	op: push left
* -> Const
 16:    LDC  0,2(0) 	load const
* <- Const
 17:     LD  1,0(6) 	op: load left
 18:    SUB  0,1,0 	op <
 19:    JLT  0,2(7) 	br if true
 20:    LDC  0,0(0) 	false case
 21:    LDA  7,1(7) 	unconditional jmp
 22:    LDC  0,1(0) 	true case
* <- Op
* if: jump to else belongs here
* -> Id
 24:     LD  0,0(5) 	load id value
* <- Id
 25:    OUT  0,0,0 	write ac
* if: jump to end belongs here
 23:    JEQ  0,3(7) 	if: jmp to else
* -> Const
 27:    LDC  0,99(0) 	load const
* <- Const
 28:    OUT  0,0,0 	write ac
 26:    LDA  7,2(7) 	jmp to end
* <- if
* -> assign
* -> Op
* -> Id
 29:     LD  0,0(5) 	load id value
* <- Id
 30:     ST  0,0(6) 	op: push left
* -> Const
 31:    LDC  0,1(0) 	load const
* <- Const
 32:     LD  1,0(6) 	op: load left
 33:    SUB  0,1,0 	op -
* <- Op
 34:     ST  0,0(5) 	assign: store value
* <- assign
* -> Op
* -> Id
 35:     LD  0,0(5) 	load id value
* <- Id
 36:     ST  0,0(6) 	op: push left
* -> Const
 37:    LDC  0,0(0) 	load const
* <- Const
 38:     LD  1,0(6) 	op: load left
 39:    SUB  0,1,0 	op ==
 40:    JEQ  0,2(7) 	br if true
 41:    LDC  0,0(0) 	false case
 42:    LDA  7,1(7) 	unconditional jmp
 43:    LDC  0,1(0) 	true case
* <- Op
 44:    JEQ  0,-31(7) 	repeat: jmp back to body
* <- repeat
* if: jump to end belongs here
 13:    JEQ  0,32(7) 	if: jmp to else
* -> Const
 46:    LDC  0,0(0) 	load const
* <- Const
 47:    OUT  0,0,0 	write ac
 45:    LDA  7,2(7) 	jmp to end
* <- if
* End of execution.
 48:   HALT  0,0,0 	
