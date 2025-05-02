# Single Stage Implementation

from memoryReg import *

class State(object):
    def __init__(self):
        self.IF = {"nop": bool(False), "PC": int(0), "taken": bool(False)}
        self.ID = {"nop": bool(False), "instr": str("0"*32), "PC": int(0), "hazard_nop": bool(False)}
        self.EX = {"nop": bool(False), "instr": str("0"*32), "Read_data1": str("0"*32), "Read_data2": str("0"*32), "Imm": str("0"*32), "Rs": str("0"*5), "Rt": str("0"*5), "Wrt_reg_addr": str("0"*5), "is_I_type": bool(False), "rd_mem": bool(False),
                   "wrt_mem": bool(False), "alu_op": str("00"), "wrt_enable": bool(False)} # alu_op 00 -> add, 01 -> and, 10 -> or, 11 -> xor
        self.MEM = {"nop": bool(False), "ALUresult": str("0"*32), "Store_data": str("0"*32), "Rs": str("0"*5), "Rt": str("0"*5), "Wrt_reg_addr": str("0"*5), "rd_mem": bool(False),
                   "wrt_mem": bool(False), "wrt_enable": bool(False)}
        self.WB = {"nop": bool(False), "Wrt_data": str("0"*32), "Rs": str("0"*5), "Rt": str("0"*5), "Wrt_reg_addr": str("0"*5), "wrt_enable": bool(False)}


class Core(object):
    def __init__(self, ioDir, imem, dmem):
        self.myRF = RegisterFile(ioDir)
        self.cycle = 0
        self.inst = 0
        self.halted = False
        self.ioDir = ioDir
        self.state = State()
        self.nextState = State()
        self.ext_imem = imem
        self.ext_dmem = dmem




# Single Stage


# R-Type Instructions
def R_Type_Instr(rs1, rs2, funct7, funct3):

  rd = 0

  # ADD
  if funct3 == 0b000 and funct7 == 0b0000000:
      rd = rs1 + rs2

  # SUB
  if funct3 == 0b000 and funct7 == 0b0100000:
      rd = rs1 - rs2

  # AND
  if funct3 == 0b111 and funct7 == 0b0000000:
      rd = rs1 & rs2

  # OR
  if funct3 == 0b110 and funct7 == 0b0000000:
      rd = rs1 | rs2

  # XOR
  if funct3 == 0b100 and funct7 == 0b0000000:
      rd = rs1 ^ rs2

  return rd

# Utility function for converting to signed integers
def convertToSignedInt(value, sign_bit_index):

    if (value & (1 << sign_bit_index)) != 0:
        value = value - (1 << (sign_bit_index + 1))
    return value

# I-Type Instructions
def Calculate_I(funct3, rs1, imm):
    rd = 0

    # ADDI
    if funct3 == 0b000:
        rd = rs1 + convertToSignedInt(imm, 11)


    # ANDI
    if funct3 == 0b111:
        rd = rs1 & convertToSignedInt(imm, 11)

    # ORI
    if funct3 == 0b110:
        rd = rs1 | convertToSignedInt(imm, 11)


    # XORI
    if funct3 == 0b100:
        rd = rs1 ^ convertToSignedInt(imm, 11)


    return rd


# Core class for Single Stage

class SingleStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(SingleStageCore, self).__init__(ioDir + os.sep + "SS_", imem, dmem)
        self.opFilePath = ioDir + os.sep + "StateResult_SS.txt"

    def step(self):
        # implementation of each instruction

        currInstr = int(self.ext_imem.readInstr(self.state.IF["PC"]), 16) # hex into integer
        opcode = currInstr & (2 ** 7 - 1) # least significant 7 bits

        # decode instruction and then execute
        self.DecodeInstr(opcode, currInstr)

        self.halted = False
        if self.state.IF["nop"]:
            self.halted = True

        if not self.state.IF["taken"] and self.state.IF["PC"] + 4 < len(self.ext_imem.IMem):
            self.nextState.IF["PC"] = self.state.IF["PC"] + 4
        else:
            self.state.IF["taken"] = False # take branch, then set taken to False again

        self.myRF.outputRF(self.cycle) # output file of registers after each cycle
        self.printState(self.nextState, self.cycle) # print states after each cycle

        self.state = self.nextState #The end of the cycle and updates the current state with the values calculated in this cycle
        self.cycle += 1
        self.inst += 1 # instruction counter

    def DecodeInstr(self, opcode, currInstr):
        # R-type
        if opcode == 0b0110011:


            # rd
            rd = (currInstr >> 7) & ((1 << 5) - 1)
            # rs1
            rs1 = (currInstr >> 15) & ((1 << 5) - 1)
            # rs2
            rs2 = (currInstr >> 20) & ((1 << 5) - 1)
            # funct3
            funct3 = (currInstr >> 12) & ((1 << 3) - 1)
            # funct7
            funct7 = currInstr >> 25



            # data in rs1
            data_rs1 = self.myRF.readRF(rs1)
            # data in rs2
            data_rs2 = self.myRF.readRF(rs2)
            # result data
            data_rd = R_Type_Instr(data_rs1, data_rs2, funct7, funct3, )
            # store data
            self.myRF.writeRF(rd, data_rd)

        # I Type
        elif opcode == 0b0010011:

            # immediate
            imm = currInstr >> 20 & ((1 << 12) - 1)

            # funct3
            funct3 = (currInstr >> 12) & ((1 << 3) - 1)
            # rs1
            rs1 = (currInstr >> 15) & ((1 << 5) - 1)
            # rd
            rd = (currInstr >> 7) & ((1 << 5) - 1)

            # data in rs1
            data_rs1 = self.myRF.readRF(rs1)
            # result data
            data_rd = Calculate_I(funct3, data_rs1, imm)
            # result data in rd register
            self.myRF.writeRF(rd, data_rd)

        # J Type Jal
        elif opcode == 0b1101111:

            # imm
            imm19_12 = (currInstr >> 12) & ((1 << 8) - 1)
            imm11 = (currInstr >> 20) & 1
            imm10_1 = (currInstr >> 21) & ((1 << 10) - 1)
            imm20 = (currInstr >> 31) & 1
            imm = (imm20 << 20) | (imm10_1 << 1) | (imm11 << 11) | (imm19_12 << 12)

            # rd
            rd = (currInstr >> 7) & ((1 << 5) - 1)

            self.myRF.writeRF(rd, self.state.IF["PC"] + 4)
            self.nextState.IF["PC"] = self.state.IF["PC"] + convertToSignedInt(imm, 20)
            self.state.IF["taken"] = True

        # B Type
        elif opcode == 0b1100011:

            # imm
            imm11 = (currInstr >> 7) & 1
            imm4_1 = (currInstr >> 8) & ((1 << 4) - 1)
            imm10_5 = (currInstr >> 25) & ((1 << 6) - 1)
            imm12 = (currInstr >> 31) & 1
            imm = (imm11 << 11) | (imm4_1 << 1) | (imm10_5 << 5) | (imm12 << 12)

            # rs2
            rs2 = (currInstr >> 20) & ((1 << 5) - 1)
            # rs1
            rs1 = (currInstr >> 15) & ((1 << 5) - 1)
            # funct3
            funct3 = (currInstr >> 12) & ((1 << 3) - 1)

            # BEQ
            if funct3 == 0b000:
                data_rs1 = self.myRF.readRF(rs1)
                data_rs2 = self.myRF.readRF(rs2)
                if data_rs1 == data_rs2:
                    self.nextState.IF["PC"] = self.state.IF["PC"] + convertToSignedInt(imm, 12)
                    self.state.IF["taken"] = True

            # BNE
            else:
                data_rs1 = self.myRF.readRF(rs1)
                data_rs2 = self.myRF.readRF(rs2)
                if data_rs1 != data_rs2:
                    self.nextState.IF["PC"] = self.state.IF["PC"] + convertToSignedInt(imm, 12)
                    self.state.IF["taken"] = True

        # LW
        elif opcode == 0b0000011:

            # imm
            imm = currInstr >> 20
            # rs1
            rs1 = (currInstr >> 15) & ((1 << 5) - 1)
            # rd
            rd = (currInstr >> 7) & ((1 << 5) - 1)

            self.myRF.writeRF(Reg_addr=rd,
                              Wrt_reg_data=int(self.ext_dmem.readDataMem(
                                  ReadAddress=self.myRF.readRF(rs1) + convertToSignedInt(imm, 11)), 16))

        # SW
        elif opcode == 0b0100011:

            # imm
            imm11_5 = currInstr >> 25
            imm4_0 = (currInstr >> 7) & ((1 << 5) - 1)
            imm = (imm11_5 << 5) | imm4_0

            # funct3
            funct3 = currInstr & (((1 << 3) - 1) << 12)
            # rs1
            rs1 = (currInstr >> 15) & ((1 << 5) - 1)
            # rd
            rs2 = (currInstr >> 20) & ((1 << 5) - 1)

            self.ext_dmem.writeDataMem(Address=(rs1 + convertToSignedInt(imm, 11)) & ((1 << 32) - 1),
                                       WriteData=self.myRF.readRF(rs2))

        # HALT
        else:
            self.state.IF["nop"] = True

    # print StateResult_SS.txt
    def printState(self, state, cycle):
        printstate = ["State after executing cycle: " + str(cycle) + "\n"] # "-"*70+"\n",    dividing line
        printstate.append("IF.PC: " + str(state.IF["PC"]) + "\n")
        printstate.append("IF.nop: " + str(state.IF["nop"]) + "\n")
        printstate.append("---------------------------------------------------\n")

        if(cycle == 0):
            perm = "w"
        else:
            perm = "a"

        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)