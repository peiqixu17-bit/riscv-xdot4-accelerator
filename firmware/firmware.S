.option norvc
.option norelax
.section .text
.globl _start, scalar_kernel, dot4_kernel, empty_kernel
_start:
    li sp, 0x700
    li a5, 0x700
    lw a4, 0(a5)
    lw a2, 4(a5)
    li a0, 0x800
    li a1, 0xc00
cycle_start:
    .word 0xc0002473 /* rdcycle s0 */
inst_start:
    .word 0xc02024f3 /* rdinstret s1 */
call_kernel:
    jalr ra, a4, 0
inst_end:
    .word 0xc0202973 /* rdinstret s2 */
cycle_end:
    .word 0xc00029f3 /* rdcycle s3 */
    li a5, 0x700
    lw a6, 8(a5)
    bne a0, a6, fail
    sub s3, s3, s0
    sub s2, s2, s1
    li a7, 0x10000000
    sw a0, 0(a7)
    sw s3, 4(a7)
    sw s2, 8(a7)
    li t0, 1
    sw t0, 12(a7)
done:
    j done
fail:
    li a7, 0x10000000
    li t0, 2
    sw t0, 12(a7)
    j fail
.balign 4
scalar_kernel:
    li a3, 0
scalar_word:
    lw t0, 0(a0)
    lw t1, 0(a1)
    li t2, 4
scalar_lane:
    slli t3, t0, 24
    srai t3, t3, 24
    slli t4, t1, 24
    srai t4, t4, 24
scalar_multiply_begin:
    mul t5, t3, t4
    add a3, a3, t5
scalar_multiply_end:
    srli t0, t0, 8
    srli t1, t1, 8
    addi t2, t2, -1
    bnez t2, scalar_lane
    addi a0, a0, 4
    addi a1, a1, 4
    addi a2, a2, -1
    bnez a2, scalar_word
    mv a0, a3
    ret
scalar_end:
dot4_kernel:
    li a3, 0
dot4_word:
    lw t0, 0(a0)
    lw t1, 0(a1)
dot4_instruction:
    .insn r 0x0b, 0, 0, t2, t0, t1
    add a3, a3, t2
    addi a0, a0, 4
    addi a1, a1, 4
    addi a2, a2, -1
    bnez a2, dot4_word
    mv a0, a3
    ret
dot4_end:
empty_kernel:
    li a0, 0
    ret
empty_end:

.globl s2_kernel, s2_end
s2_kernel:
    li a3, 0
s2_word:
    lb t0, 0(a0)
    lb t1, 0(a1)
    mul t2, t0, t1
    add a3, a3, t2
    lb t0, 1(a0)
    lb t1, 1(a1)
    mul t2, t0, t1
    add a3, a3, t2
    lb t0, 2(a0)
    lb t1, 2(a1)
    mul t2, t0, t1
    add a3, a3, t2
    lb t0, 3(a0)
    lb t1, 3(a1)
    mul t2, t0, t1
    add a3, a3, t2
    addi a0, a0, 4
    addi a1, a1, 4
    addi a2, a2, -1
    bnez a2, s2_word
    mv a0, a3
    ret
s2_end:
