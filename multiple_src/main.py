import os
import sys
import itertools
import time
import lzma
from base64 import b85decode
from platform import system

default64mbdtb: bytearray = bytearray(b85decode(b'&<+0W000I60000u000F50000e0000H0000G000000002v000EY0000000000000000000000001000000000300004000000000200003000040000F00002000030000K0000Ra%pp8b}embZfR{{Y%OkYZEbY`000030000P0000ca%pp8b}embZfR{{Y%OkYZEbZdab<0F0000000001V`y)4Wo`ff000030000u0000iWnpq`d1G&GJ#}GnbT~3KFf46tX>Tkrcrh?AFfcGMFf1`JFfcGMFd$=ZZgX#JWj%Csc~dX|0000200001ZDnn5a(O^FFfcGMFfcFx00003000070000rZDnn5a(Ms%000030000G0000%00000fB*mh000001OLDP0000200001V{mnI000000000300004000000000100003000040000F0000000003000040000*01rYy00001V{mmqFaQ7m0000300004000130000100003000040000rV{ml<00003000040000%0000000003000050001BZ);(B0000000003000060000Ra%pp8b^rhX00003000080001Ia&|K^X>DNu000030000B0001Sa%pp8b}VjhZe;)f00001X>N37a&mQWbS-0VZgg^QY;0w60000000003000040001b0000100003000000001s000030000F0000Ra%pp8b}VCXbuDRbbYlPj00003000040001300002000020000200001V{mmXZDDW#00001V{CPEbY*fd0000000001V{dY0FaQ7m00003000040001>000010000200002000020000200001b8lk+0000300004000000000200003000040000F00002000030000B0000Rb7^gGY-KHCb#nj!00003000000001_00001bzyRJKrt{dFfcGMFaQ7m0000300004000210RR91000030000G0000%000005C8xG000000003100003000080000RZgVj<I5jW;0000200001aBp{Ia&Km40000000003000040002H0032000003000040002N0000000003000040002U00004000030000G0000Rb9r-PZ*DDcZ+B&KZ)Roy0000200001a%Ey~Z*%|v00003000040002H004J)00003000040002N0000000003000040002U00004000030000E0000Rb9r-PZ*DDeWnyn{bN~PV0000200001b9r-PZ*D*_F)=VOFfcFx00003000040001300004000030000G0000%000005fA_X00000000mG00003000070000Rb9r-PZ*Bkp0000200001V{B<|bU-mNFfcGMFfafB000030000G0002b00002000030000200007000030000G0000%000005dZ)H0000000961000030000R0000Rb7^L2c4aJMY-w(EFaUCCb7OWaV{B<|bT9w_00002000020000200009BVlA@a%FRKEn{VDY;yo3b7^{IEn{VDY;yo(Z*6d4bZKI2WdLn&WMymsVsCGBVRC140Ayu$X=7zyba`-P0CHt#0CZ_>Wny7-Wi4iMWpQ<7Zew`>aA;v}WNc*sb97;Jb#nl6X>((CENOFL0Bvn`Ep&NsWdI{-ZggdGa&>TYEn{VDY;yo<ZggdGa&>TYEn{zPbaHQOY-Mr)V{ml<a$#;~Wpe;yY;R+0EoO3Madl;GV|f5}VQh6}0B>eyb7gb@a%E?2VQ>IxZggdGa&>TYb1h|fbY*U2Wn=&V00000000000000000000000000000000000'))



# https://stackoverflow.com/questions/2408560/non-blocking-console-input
# https://www.darkcoding.net/software/non-blocking-console-io-is-not-possible/

if system() == 'Windows':
    import msvcrt

    def read_key():
        if msvcrt.kbhit():
            return msvcrt.getch().encode('utf-8')
        else:
            return 0xffffffff

    def tty_prepare():
        import os
        # Apparently this is how to put "cmd" interpreter into VT100 mode
        # Otherwise we will see VT100 escape sequences when running from cmd
        os.system("")

    def tty_release():
        pass

elif system() == "Linux":
    import select
    import tty
    import termios

    old_settings = None

    def InputIsAvailable():
            return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

    def read_key():
        # We first check if Input is available, so that stdin.read does not block waiting on input
        if InputIsAvailable():
            return sys.stdin.read(1).encode('utf-8')
        else:
            return 0xffffffff

    def tty_prepare():
        global old_settings
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        pass

    def tty_release():
        global old_settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        pass


def init():
    ram_amt = 64*1024*1024  # 64MB
    MINI_RV32_RAM_SIZE = ram_amt
    MINI_RV32_RAM_SIZE_3 = ram_amt - 3

    outputBuffer = bytearray(10240)
    outputBufferCount = 0
    
    inputBuffer = bytearray(512)
    inputBufferIdx = 0
    lastInputBufferIdx = 0
    ram_image = bytearray(ram_amt)

    with open('Linux.image', 'rb') as f:
        data = f.read()
    ram_image[:len(data)] = data
    dtb_ptr = ram_amt - len(default64mbdtb) - 48*4
    ram_image[dtb_ptr: dtb_ptr+len(default64mbdtb)] = default64mbdtb.copy()
    ram_memoryview = memoryview(ram_image)
    ram_image_uint32 = ram_memoryview.cast('I')
    ram_image_uint16 = ram_memoryview.cast('H')

    # 内核位于RAM的末端。
    core = memoryview(ram_image[ram_amt - 48 * 4:]).cast('I')
    core[32] = 0x80000000
    core[10] = 0x00  # hart ID
    core[11] = dtb_ptr + 0x80000000 if dtb_ptr else 0  # dtb_pa (Must be valid pointer) (Should be pointer to dtb)
    core[47] |= 3  # Machine-mode.

    # Update system ram size in DTB (but if and only if we're using the default DTB)
    # Warning - this will need to be updated if the skeleton DTB is ever modified.
    dtb = memoryview(ram_image[dtb_ptr:]).cast('I')
    if dtb[0x13c // 4] == 0x00c0ff03:
        validram: int = dtb_ptr
        dtb[0x13c // 4] = (validram >> 24) | (((validram >> 16) & 0xff) << 8) | (((validram >> 8) & 0xff) << 16) | ((validram & 0xff) << 24)

    def MiniRV32IMAStep(state: memoryview, image: bytearray, image_uint32: memoryview, image_uint16: memoryview) -> int:
        nonlocal outputBufferCount, inputBufferIdx, lastInputBufferIdx, last_time
        currentTime = int(time.time() * 1e6)
        new_timer: int = (state[36] + currentTime - last_time) & 0xFFFFFFFF  # 模拟 32 位无符号整数
        last_time = currentTime
        
        if new_timer < state[36]:
            state[37] = (state[37] + 1) & 0xFFFFFFFF
        state[36] = new_timer
    
        # 处理定时器中断
        if (state[37] > state[39] or (state[37] == state[39] and state[36] > state[38])) and (state[39] or state[38]):
            state[47] &= (-5)  # Clear WFI
            state[43] |= 128  # MTIP of MIP // https://stackoverflow.com/a/61916199/2926815  Fire interrupt.
        else:
            state[43] &= (-129)
    
        # If WFI, don't run processor.
        if state[47] & 4:
            return 1
    
        trap: int = 0
        rval: int = 0
        pc: int = state[32]
        cycle: int = state[34]
    
        if (state[43] & 128) and (state[42] & 128) and (state[33] & 0x8):
            # Timer interrupt.
            trap = 0x80000007
            pc = (pc - 4) % 0x100000000
        else:  # 没有定时器中断？执行一堆指令
            for _ in itertools.repeat(None, 1024):
                ir: int = 0
                rval = 0
                cycle = (cycle + 1) % 0x100000000  # cycle数值一般较小，不使用位运算
                ofs_pc: int = (pc - 0x80000000) % 0x100000000
    
                if ofs_pc >= MINI_RV32_RAM_SIZE:
                    trap = 1 + 1  # 指令读取访问违规
                    break
                if ofs_pc % 4:  # 不使用位运算一般更快
                    trap = 1 + 0  # 处理PC未对齐访问
                    break
                
                ir = image_uint32[ofs_pc // 4]
                rdid: int = (ir >> 7) & 0x1f

                _switch: int = ir & 0x7f
                # start_t = time.time()
                if _switch == 0x03:  # Load (0b0000011)
                    rs1: int = state[(ir >> 15) & 0x1f] - 0x80000000
                    imm: int = ir >> 20
                    rsval: int = (rs1 + (imm + 0xfffff000 if imm > 0x7ff else imm)) & 0xFFFFFFFF
                    if rsval >= MINI_RV32_RAM_SIZE_3:
                        rsval = (rsval + 0x80000000) & 0xFFFFFFFF
                        if 0x10000000 <= rsval < 0x12000000:  # UART, CLNT
                            if rsval == 0x10000005:
                                rval = 0x60 + (inputBufferIdx > lastInputBufferIdx)
                            elif rsval == 0x10000000 and inputBufferIdx > lastInputBufferIdx:
                                rval = inputBuffer[lastInputBufferIdx]
                                lastInputBufferIdx += 1
                            elif rsval == 0x1100bffc:  # https://chromitem-soc.readthedocs.io/en/latest/clint.html
                                rval = state[37]
                            elif rsval == 0x1100bff8:
                                rval = state[36]
                            # else:
                            #     rval = 0
                        else:
                            trap = 5+1
                            rval = rsval
                    else:
                        __switch: int = (ir >> 12) & 0x7
                        #LB, LH, LW, LBU, LHU
                        if __switch == 0:
                            rval = image[rsval]
                            if rval > 0x7f: rval = (rval - 0x100) % 0x100000000
                        elif __switch == 1:
                            rval = image_uint16[rsval // 2]
                            if rval > 0x7fff: rval = (rval - 0x10000) % 0x100000000
                        elif __switch == 2: rval = image_uint32[rsval // 4]  # 未对齐的情况暂不考虑
                        elif __switch == 4: rval = image[rsval]
                        elif __switch == 5: rval = image_uint16[rsval // 2]
                        else: trap = 2+1
                elif _switch == 0x23:  # Store 0b0100011
                    rs2: int = state[(ir >> 20) & 0x1f]
                    addy: int = ((ir >> 7) & 0x1f) + ((ir & 0xfe000000) >> 20)
                    if addy > 0x7ff: addy += 0xfffff000
                    addy = (addy + state[(ir >> 15) & 0x1f] - 0x80000000) & 0xFFFFFFFF

                    if addy < MINI_RV32_RAM_SIZE_3:
                        __switch = (ir >> 12) & 0x7
                        # SB, SH, SW
                        if __switch == 0: image[addy] = rs2 & 0xFF
                        elif __switch == 1: image_uint16[addy // 2] = rs2 & 0xFFFF
                        elif __switch == 2: image_uint32[addy // 4] = rs2
                        else: trap = 2+1
                    else:
                        addy = (addy + 0x80000000) & 0xFFFFFFFF
                        if 0x10000000 <= addy < 0x12000000:
                            if addy == 0x10000000:  # UART 8250 / 16550 Data Buffer
                                outputBuffer[outputBufferCount] = rs2 & 0xff
                                outputBufferCount += 1
                            elif addy == 0x11004004:  # CLNT
                                state[39] = rs2
                            elif addy == 0x11004000:  # CLNT
                                state[38] = rs2
                            elif addy == 0x11100000:  # SYSCON (reboot, poweroff, etc.)
                                state[32] = (state[32] + 4) & 0xFFFFFFFF
                                if rs2: return rs2
                        else:
                            trap = 7+1  # Store access fault.
                            rval = addy
                    rdid = 0
                elif _switch == 0x37:  # LUI (0b0110111)
                    rval = ir & 0xfffff000
                elif _switch == 0x6F:  # JAL (0b1101111)
                    reladdy: int = ((ir & 0x80000000)>>11) + ((ir & 0x7fe00000)>>20) + ((ir & 0x00100000)>>9) + (ir&0x000ff000)
                    if reladdy > 0xfffff: reladdy += 0xffe00000
                    rval = (pc + 4) & 0xFFFFFFFF
                    pc = (pc + reladdy - 4) & 0xFFFFFFFF
                elif _switch == 0x67:  # JALR (0b1100111)
                    imm: int = ir >> 20
                    rval = (pc + 4) & 0xFFFFFFFF
                    pc = (((state[(ir >> 15) & 0x1f] + (imm + 0xfffff000 if imm > 0x7ff else imm)) & ~1) - 4) & 0xFFFFFFFF
                elif _switch == 0x63:  # Branch (0b1100011)
                    rs1_u: int = state[(ir >> 15) & 0x1f]
                    rs2_u: int = state[(ir >> 20) & 0x1f]
                    rdid = 0
                    __switch = (ir >> 12) & 0x7
                    # BEQ, BNE, BLT, BGE, BLTU, BGEU
                    if __switch == 0:
                        if rs1_u == rs2_u:
                            immm4: int = ((ir & 0xf00)>>7) + ((ir & 0x7e000000)>>20) + ((ir & 0x80) * 16) + ((ir >> 31)*(2**12))
                            if immm4 > 0xfff: immm4 += 0xffffe000
                            pc = (pc + immm4 - 4) & 0xFFFFFFFF
                    elif __switch == 1:
                        if rs1_u != rs2_u:
                            immm4: int = ((ir & 0xf00)>>7) + ((ir & 0x7e000000)>>20) + ((ir & 0x80) * 16) + ((ir >> 31)*(2**12))
                            if immm4 > 0xfff: immm4 += 0xffffe000
                            pc = (pc + immm4 - 4) & 0xFFFFFFFF
                    elif __switch == 4:
                        if (rs1_u - 0x100000000 if rs1_u > 0x7fffffff else rs1_u) < (rs2_u - 0x100000000 if rs2_u > 0x7fffffff else rs2_u):
                            immm4: int = ((ir & 0xf00)>>7) + ((ir & 0x7e000000)>>20) + ((ir & 0x80) * 16) + ((ir >> 31)*(2**12))
                            if immm4 > 0xfff: immm4 += 0xffffe000
                            pc = (pc + immm4 - 4) & 0xFFFFFFFF
                    elif __switch == 5:
                        if (rs1_u - 0x100000000 if rs1_u > 0x7fffffff else rs1_u) >= (rs2_u - 0x100000000 if rs2_u > 0x7fffffff else rs2_u):
                            immm4: int = ((ir & 0xf00)>>7) + ((ir & 0x7e000000)>>20) + ((ir & 0x80) * 16) + ((ir >> 31)*(2**12))
                            if immm4 > 0xfff: immm4 += 0xffffe000
                            pc = (pc + immm4 - 4) & 0xFFFFFFFF  # BGE
                    elif __switch == 6:
                        if rs1_u < rs2_u:
                            immm4: int = ((ir & 0xf00)>>7) + ((ir & 0x7e000000)>>20) + ((ir & 0x80) * 16) + ((ir >> 31)*(2**12))
                            if immm4 > 0xfff: immm4 += 0xffffe000
                            pc = (pc + immm4 - 4) & 0xFFFFFFFF  # BLTU
                    elif __switch == 7:
                        if rs1_u >= rs2_u:
                            immm4: int = ((ir & 0xf00)>>7) + ((ir & 0x7e000000)>>20) + ((ir & 0x80) * 16) + ((ir >> 31)*(2**12))
                            if immm4 > 0xfff: immm4 += 0xffffe000
                            pc = (pc + immm4 - 4) & 0xFFFFFFFF  # BGEU
                    else:
                        trap = 2+1
                elif _switch == 0x13 or _switch == 0x33: 
                    # Op-immediate 0b0010011
                    # Op           0b0110011
                    imm: int = ir >> 20
                    rs1: int = state[(ir >> 15) & 0x1f]
                    is_reg: bool = _switch == 0x33  # bool(ir & 0x20)
                    rs2: int = state[imm & 0x1f] if is_reg else ((imm + 0xfffff000) if imm > 0x7ff else imm)
    
                    if is_reg and (ir & 0x02000000):
                        __switch: int = (ir>>12)&7  # 0x02000000 = RV32M
                        if __switch == 0: rval = (rs1 * rs2) & 0xFFFFFFFF  # MUL
                        elif __switch == 1:
                            rval = (((rs1 - 0x100000000 if rs1 > 0x7fffffff else rs1) * (rs2 - 0x100000000 if rs2 > 0x7fffffff else rs2)) >> 32) & 0xFFFFFFFF  # MULH
                        elif __switch == 2:
                            rval = (((rs1 - 0x100000000 if rs1 > 0x7fffffff else rs1) * rs2) >> 32) & 0xFFFFFFFF  # MULHSU
                        elif __switch == 3:
                            rval = (rs1 * rs2) >> 32  # MULHU
                        elif __switch == 4:  # 经测试，这是已知最快的除法算法
                            if rs2 == 0:
                                rval = 0xFFFFFFFF
                            else:
                                if rs1 <= 0x7fffffff:  # 第一个数是正数
                                    if rs2 <= 0x7fffffff:  # 第二个数是正数
                                        rval = rs1 // rs2
                                    else:  # 第二个数是负数
                                        rval = (0x100000000 - rs1 // (0x100000000 - rs2)) % 0x100000000
                                elif rs2 <= 0x7fffffff:  # 第一个数是负数，第二个数是正数
                                    rval = (0x100000000 - (0x100000000 - rs1) // rs2) % 0x100000000
                                else:  # 第一个数是负数，第二个数是负数
                                    rval = (rs1 - 0x100000000) // (rs2 - 0x100000000)
                        elif __switch == 5:  # DIVU
                            if rs2 == 0:
                                rval = 0xffffffff
                            else:
                                rval = rs1 // rs2
                        elif __switch == 6:  # REM
                            if rs2 == 0:
                                rval = rs1
                            else:
                                if rs1 <= 0x7fffffff:  # 第一个数是正数
                                    if rs2 <= 0x7fffffff:  # 第二个数是正数
                                        rval = rs1 % rs2
                                    else:  # 第二个数是负数
                                        rval = rs1 % (0x100000000 - rs2)
                                elif rs2 <= 0x7fffffff:  # 第一个数是负数，第二个数是正数
                                    rval = (0x100000000 - (0x100000000 - rs1) % rs2) % 0x100000000
                                else:  # 第一个数是负数，第二个数是负数
                                    rval = (0x100000000 - (0x100000000 - rs1) % (0x100000000 - rs2)) % 0x100000000
                        elif __switch == 7:  # REMU
                            if rs2 == 0:
                                rval = rs1
                            else:
                                rval = rs1 % rs2
                    else:
                        __switch: int = (ir>>12)&7  # These could be either op-immediate or op commands.  Be careful.
                        if __switch == 0: rval = (rs1 - rs2) % 0x100000000 if is_reg and (ir & 0x40000000) else (rs1 + rs2) & 0xFFFFFFFF
                        elif __switch == 1: rval = (rs1 << (rs2 & 0x1F)) & 0xFFFFFFFF
                        elif __switch == 2: rval = (rs1 - 0x100000000 if rs1 > 0x7fffffff else rs1) < (rs2 - 0x100000000 if rs2 > 0x7fffffff else rs2)
                        elif __switch == 3: rval = rs1 < rs2
                        elif __switch == 4: rval = rs1 ^ rs2
                        elif __switch == 5: rval = ((rs1 - 0x100000000 if rs1 > 0x7fffffff else rs1) >> (rs2 & 0x1F)) & 0xFFFFFFFF if ir & 0x40000000 else (rs1 >> (rs2 & 0x1F))
                        elif __switch == 6: rval = rs1 | rs2
                        elif __switch == 7: rval = rs1 & rs2
                elif _switch == 0x73:  # Zifencei+Zicsr  (0b1110011)
                    csrno: int = ir >> 20
                    microop: int = (ir >> 12) & 0x7
                    if (microop & 3):  # It's a Zicsr function.
                        rs1imm = (ir >> 15) & 0x1f  # 有符号，但一定为整数
                        rs1: int = state[rs1imm]
                        writeval: int = rs1

                        if csrno == 0x340: rval = state[40]
                        elif csrno == 0x305: rval = state[41]
                        elif csrno == 0x304: rval = state[42]
                        elif csrno == 0xC00: rval = cycle
                        elif csrno == 0x344: rval = state[43]
                        elif csrno == 0x341: rval = state[44]
                        elif csrno == 0x300: rval = state[33]  # mstatus
                        elif csrno == 0x342: rval = state[46]
                        elif csrno == 0x343: rval = state[45]
                        elif csrno == 0xf11: rval = 0xff0ff0ff  # mvendorid
                        elif csrno == 0x301: rval = 0x40401101  # misa (XLEN=32, IMA+X)
                        # else: rval = 0 由于 rval 默认是 0，这里可以注释掉
                            
                        if microop == 1: writeval = rs1  # CSRRW
                        elif microop == 2: writeval = rval | rs1  # CSRRS
                        elif microop == 3: writeval = rval & ~rs1  # CSRRC
                        elif microop == 5: writeval = rs1imm  # CSRRWI
                        elif microop == 6: writeval = rval | rs1imm  # CSRRSI
                        elif microop == 7: writeval = rval & ~rs1imm  # CSRRCI
    
                        if csrno == 0x340: state[40] = writeval
                        elif csrno == 0x305: state[41] = writeval
                        elif csrno == 0x304: state[42] = writeval
                        elif csrno == 0x344: state[43] = writeval
                        elif csrno == 0x341: state[44] = writeval
                        elif csrno == 0x300: state[33] = writeval  # mstatus
                        elif csrno == 0x342: state[46] = writeval
                        elif csrno == 0x343: state[45] = writeval
                    elif microop == 0x0:  # "SYSTEM" 0b000
                        rdid = 0
                        if csrno == 0x105:  # WFI (Wait for interrupts)
                            state[33] |= 8  # Enable interrupts
                            state[47] |= 4  # Infor environment we want to go to sleep.
                            state[32] = (pc + 4) & 0xFFFFFFFF
                            return 1
                        elif (csrno & 0xff) == 0x02:  # MRET
                            startmstatus: int = state[33]
                            startextraflags: int = state[47]
                            state[33] = ((startmstatus & 0x80) >> 4) + ((startextraflags&3) << 11) + 0x80
                            state[47] = (startextraflags & ~3) + ((startmstatus >> 11) & 3)
                            pc = (state[44] - 4) & 0xFFFFFFFF
                        elif csrno == 0:
                            trap = 11+1 if state[47] & 3 else 8+1  # ECALL; 8 = "Environment call from U-mode"; 11 = "Environment call from M-mode"
                        elif csrno == 1:
                            trap = 3+1  # EBREAK 3 = "Breakpoint"
                        else:
                            trap = 2+1  # Illegal opcode.
                    else:
                        trap = 2+1  # Note micrrop 0b100 == undefined.
                elif _switch == 0x2f:  # RV32A (0b00101111)
                    rs1: int = (state[(ir >> 15) & 0x1f] - 0x80000000) % 0x100000000
                    irmid: int = (ir>>27) & 0x1f

                    if rs1 >= MINI_RV32_RAM_SIZE-3:
                        trap = 7+1  # Store/AMO access fault
                        rval = (rs1 + 0x80000000) & 0xFFFFFFFF
                    else:
                        rs2: int = state[(ir >> 20) & 0x1f]
                        rval = image_uint32[rs1 // 4]
        
                        dowrite: int = 1
                        if irmid == 2:  # LR.W (0b00010)
                            dowrite = 0
                            state[47] = ((state[47] & 0x07) + (rs1 * 8)) & 0xFFFFFFFF
                        elif irmid == 3:  # SC.W (0b00011) (Make sure we have a slot, and, it's valid)
                            rval = (state[47] >> 3) != (rs1 & 0x1fffffff)  # Validate that our reservation slot is OK.
                            dowrite = not rval  # Only write if slot is valid.
                        elif irmid == 1:  # AMOSWAP.W (0b00001)
                            pass
                        elif irmid == 0: rs2 = (rs2 + rval) & 0xFFFFFFFF  # AMOADD.W (0b00000)
                        elif irmid == 4: rs2 ^= rval  # AMOXOR.W (0b00100)
                        elif irmid == 12: rs2 &= rval  # AMOAND.W (0b01100)
                        elif irmid == 8: rs2 |= rval  # AMOOR.W (0b01000)
                        elif irmid == 16: 
                            if (rs2 - 0x100000000 if rs2 > 0x7fffffff else rs2) >= (rval - 0x100000000 if rval > 0x7fffffff else rval): rs2 = rval  # AMOMIN.W (0b10000)
                        elif irmid == 20: 
                            if (rs2 - 0x100000000 if rs2 > 0x7fffffff else rs2) <= (rval - 0x100000000 if rval > 0x7fffffff else rval): rs2 = rval  # AMOMAX.W (0b10100)
                        elif irmid == 24:
                            if rs2 >= rval: rs2 = rval  # AMOMINU.W (0b11000)
                        elif irmid == 28: 
                            if rs2 <= rval: rs2 = rval  # AMOMAXU.W (0b11100)
                        else:
                            trap = 2+1
                            dowrite = 0  # Not supported.
                        if dowrite:
                            image_uint32[rs1 // 4] = rs2
                elif _switch == 0x17:  # AUIPC (0b0010111)
                    rval = (pc + (ir & 0xfffff000)) & 0xFFFFFFFF
                elif _switch == 0x0f:  # 0b0001111
                    rdid = 0  # fencetype = (ir >> 12) & 0b111; We ignore fences in this impl.
                else:
                    trap = 2+1  # Fault: Invalid opcode.
                # all_opcode[_switch]['time'] += time.time()-start_t
                # all_opcode[_switch]['count'] += 1
        
                # If there was a trap, do NOT allow register writeback.
                if trap:
                    state[32] = pc
                    break
        
                if rdid:
                    state[rdid] = rval  # Write back register.
                pc = (pc + 4) & 0xFFFFFFFF
    
        # Handle traps and interrupts.
        if trap:
            if trap  > 0x7fffffff:  # If prefixed with 1 in MSB, it's an interrupt, not a trap.
                state[46] = trap
                state[45] = 0
                pc = (pc + 4) & 0xFFFFFFFF  # PC needs to point to where the PC will return to.
            else:
                state[46] = trap - 1
                state[45] = rval if 5 < trap <= 8 else pc
            state[44] = pc
            state[33] = (state[33] & 0x08) * 16 + (state[47] & 3) * 2048
            pc = (state[41] - 4) & 0xFFFFFFFF
    
            state[47] |= 3

            trap = 0
            pc = (pc + 4) & 0xFFFFFFFF
    
        # if state[34] > cycle:
        #     state[35] += 1  # cycleh 似乎从未被使用
        state[34] = cycle
        state[32] = pc
        return 0

    def PrintOutputBuffer():
        nonlocal outputBufferCount
        if outputBufferCount:
            try:
                string = outputBuffer[:outputBufferCount].decode('utf-8')
                print(string, flush=True, end='')
                outputBufferCount = 0
            except UnicodeDecodeError:
                return
    
    def SetInputBufferSymbol(ch):
        nonlocal inputBufferIdx
        inputBuffer[inputBufferIdx] = ch
        inputBufferIdx += 1

    def NextStep():
        start_time = time.time()
        while time.time() - start_time < 1 / 30:
            MiniRV32IMAStep(core, ram_image, ram_image_uint32, ram_image_uint16)
    
    last_time = int(time.time() * 1e6)
    
    return NextStep, PrintOutputBuffer, SetInputBufferSymbol


next_step, print_output, set_input = init()
tty_prepare()
while True:
    s = read_key()
    if s != 0xffffffff:
        for i in s: set_input(i)
    next_step()
    print_output()
    
tty_release()
