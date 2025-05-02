from memoryReg import *

class State:
    def __init__(self):
        self.IF = {"nop": False, "PC": 0, "taken": False}
        self.ID = {"nop": True, "instr": 0, "PC": 0, "hazard_nop": False}
        self.EX = {"nop": True, "instr": 0, "Read_data1": 0, "Read_data2": 0, "Imm": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "is_I_type": False, "rd_mem": False, "wrt_mem": False, "alu_op": "00", "wrt_enable": False}
        self.MEM = {"nop": True, "ALUresult": 0, "Store_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "rd_mem": False, "wrt_mem": False, "wrt_enable": False}
        self.WB = {"nop": True, "Wrt_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "wrt_enable": False}

class Core:
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

class FiveStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super().__init__(ioDir + os.sep + "FS_", imem, dmem)
        self.opFilePath = ioDir + os.sep + "StateResult_FS.txt"

    def step(self):
        # === WRITE BACK ===
        if not self.state.WB["nop"] and self.state.WB["wrt_enable"]:
            self.myRF.writeRF(self.state.WB["Wrt_reg_addr"], self.state.WB["Wrt_data"])

        # === MEMORY ===
        if not self.state.MEM["nop"]:
            if self.state.MEM["rd_mem"]:
                read_val = self.ext_dmem.readDataMem(self.state.MEM["ALUresult"])
                self.nextState.WB["Wrt_data"] = int(read_val, 16)
            elif self.state.MEM["wrt_mem"]:
                self.ext_dmem.writeDataMem(self.state.MEM["ALUresult"], self.state.MEM["Store_data"])
            else:
                self.nextState.WB["Wrt_data"] = self.state.MEM["ALUresult"]
            self.nextState.WB["Wrt_reg_addr"] = self.state.MEM["Wrt_reg_addr"]
            self.nextState.WB["wrt_enable"] = self.state.MEM["wrt_enable"]
            self.nextState.WB["nop"] = False

        # === EXECUTE ===
        if not self.state.EX["nop"]:
            op1 = self.state.EX["Read_data1"]
            op2 = self.state.EX["Imm"] if self.state.EX["is_I_type"] else self.state.EX["Read_data2"]
            alu_op = self.state.EX["alu_op"]

            if alu_op == "00":
                result = op1 + op2
            elif alu_op == "01":
                result = op1 & op2
            elif alu_op == "10":
                result = op1 | op2
            elif alu_op == "11":
                result = op1 ^ op2
            else:
                result = 0

            self.nextState.MEM.update({
                "ALUresult": result,
                "Store_data": self.state.EX["Read_data2"],
                "Wrt_reg_addr": self.state.EX["Wrt_reg_addr"],
                "wrt_enable": self.state.EX["wrt_enable"],
                "rd_mem": self.state.EX["rd_mem"],
                "wrt_mem": self.state.EX["wrt_mem"],
                "nop": False
            })

        # === DECODE ===
        if not self.state.ID["nop"]:
            instr = self.state.ID["instr"]
            opcode = instr & 0x7F
            rd = (instr >> 7) & 0x1F
            funct3 = (instr >> 12) & 0x7
            rs1 = (instr >> 15) & 0x1F
            rs2 = (instr >> 20) & 0x1F
            funct7 = (instr >> 25) & 0x7F

            data_rs1 = self.myRF.readRF(rs1)
            data_rs2 = self.myRF.readRF(rs2)

            control = {
                "alu_op": "00", "is_I_type": False,
                "rd_mem": False, "wrt_mem": False,
                "wrt_enable": False, "imm": 0
            }

            if opcode == 0b0110011:  # R-type
                control["wrt_enable"] = True
                if funct3 == 0b000:
                    control["alu_op"] = "00" if funct7 == 0 else "00"  # ADD or SUB
                    if funct7 == 0b0100000:
                        data_rs2 *= -1  # for SUB
                elif funct3 == 0b111:
                    control["alu_op"] = "01"
                elif funct3 == 0b110:
                    control["alu_op"] = "10"
                elif funct3 == 0b100:
                    control["alu_op"] = "11"

            elif opcode == 0b0010011:  # I-type
                control["is_I_type"] = True
                control["wrt_enable"] = True
                imm = (instr >> 20) & 0xFFF
                control["imm"] = self.convertToSignedInt(imm, 11)
                if funct3 == 0b000:
                    control["alu_op"] = "00"
                elif funct3 == 0b111:
                    control["alu_op"] = "01"
                elif funct3 == 0b110:
                    control["alu_op"] = "10"
                elif funct3 == 0b100:
                    control["alu_op"] = "11"

            elif opcode == 0b0000011:  # LW
                control["is_I_type"] = True
                control["rd_mem"] = True
                control["wrt_enable"] = True
                imm = (instr >> 20) & 0xFFF
                control["imm"] = self.convertToSignedInt(imm, 11)

            elif opcode == 0b0100011:  # SW
                control["is_I_type"] = True
                control["wrt_mem"] = True
                imm = ((instr >> 25) << 5) | ((instr >> 7) & 0x1F)
                control["imm"] = self.convertToSignedInt(imm, 11)

            self.nextState.EX.update({
                "instr": instr,
                "Rs": rs1, "Rt": rs2,
                "Read_data1": data_rs1,
                "Read_data2": data_rs2,
                "Imm": control["imm"],
                "alu_op": control["alu_op"],
                "is_I_type": control["is_I_type"],
                "rd_mem": control["rd_mem"],
                "wrt_mem": control["wrt_mem"],
                "wrt_enable": control["wrt_enable"],
                "Wrt_reg_addr": rd,
                "nop": False
            })

        # === FETCH ===
        if not self.state.IF["nop"]:
            instr = int(self.ext_imem.readInstr(self.state.IF["PC"]), 16)
            self.nextState.ID["instr"] = instr
            self.nextState.ID["PC"] = self.state.IF["PC"]
            self.nextState.ID["nop"] = False
            self.nextState.IF["PC"] = self.state.IF["PC"] + 4

        # === HALT CONDITION ===
        if all([self.state.IF["nop"], self.state.ID["nop"], self.state.EX["nop"], self.state.MEM["nop"], self.state.WB["nop"]]):
            self.halted = True

        # === CYCLE COMMIT ===
        self.myRF.outputRF(self.cycle)
        self.printState(self.state, self.cycle)
        self.state = self.nextState
        self.nextState = State()
        self.cycle += 1
        self.inst += 1

    def convertToSignedInt(self, value, sign_bit_index):
        if value & (1 << sign_bit_index):
            value -= (1 << (sign_bit_index + 1))
        return value

    def printState(self, state, cycle):
        lines = []
        lines.append("----------------------------------------------------\n")
        lines.append(f"State after executing cycle: {cycle}\n\n")

        # IF stage
        lines.append("IF.PC: " + str(state.IF["PC"]) + "\n")
        lines.append("IF.nop: " + str(state.IF["nop"]) + "\n\n")

        # ID stage
        lines.append("ID.PC: " + str(state.ID["PC"]) + "\n")
        lines.append("ID.instr: " + str(state.ID["instr"]) + "\n")
        lines.append("ID.nop: " + str(state.ID["nop"]) + "\n")
        lines.append("ID.hazard_nop: " + str(state.ID["hazard_nop"]) + "\n\n")

        # EX stage
        lines.append("EX.Read_data1: " + str(state.EX["Read_data1"]) + "\n")
        lines.append("EX.Read_data2: " + str(state.EX["Read_data2"]) + "\n")
        lines.append("EX.Imm: " + str(state.EX["Imm"]) + "\n")
        lines.append("EX.Rs: " + str(state.EX["Rs"]) + "\n")
        lines.append("EX.Rt: " + str(state.EX["Rt"]) + "\n")
        lines.append("EX.Wrt_reg_addr: " + str(state.EX["Wrt_reg_addr"]) + "\n")
        lines.append("EX.is_I_type: " + str(int(state.EX["is_I_type"])) + "\n")
        lines.append("EX.rd_mem: " + str(int(state.EX["rd_mem"])) + "\n")
        lines.append("EX.wrt_mem: " + str(int(state.EX["wrt_mem"])) + "\n")
        lines.append("EX.alu_op: " + str(state.EX["alu_op"]) + "\n")
        lines.append("EX.wrt_enable: " + str(int(state.EX["wrt_enable"])) + "\n")
        lines.append("EX.nop: " + str(state.EX["nop"]) + "\n\n")

        # MEM stage
        lines.append("MEM.ALUresult: " + str(state.MEM["ALUresult"]) + "\n")
        lines.append("MEM.Store_data: " + str(state.MEM["Store_data"]) + "\n")
        lines.append("MEM.Rs: " + str(state.MEM["Rs"]) + "\n")
        lines.append("MEM.Rt: " + str(state.MEM["Rt"]) + "\n")
        lines.append("MEM.Wrt_reg_addr: " + str(state.MEM["Wrt_reg_addr"]) + "\n")
        lines.append("MEM.rd_mem: " + str(int(state.MEM["rd_mem"])) + "\n")
        lines.append("MEM.wrt_mem: " + str(int(state.MEM["wrt_mem"])) + "\n")
        lines.append("MEM.wrt_enable: " + str(int(state.MEM["wrt_enable"])) + "\n")
        lines.append("MEM.nop: " + str(state.MEM["nop"]) + "\n\n")

        # WB stage
        lines.append("WB.Wrt_data: " + str(state.WB["Wrt_data"]) + "\n")
        lines.append("WB.Rs: " + str(state.WB["Rs"]) + "\n")
        lines.append("WB.Rt: " + str(state.WB["Rt"]) + "\n")
        lines.append("WB.Wrt_reg_addr: " + str(state.WB["Wrt_reg_addr"]) + "\n")
        lines.append("WB.wrt_enable: " + str(int(state.WB["wrt_enable"])) + "\n")
        lines.append("WB.nop: " + str(state.WB["nop"]) + "\n")

        lines.append("----------------------------------------------------\n")

        mode = "w" if cycle == 0 else "a"
        with open(self.opFilePath, mode) as f:
            f.writelines(lines)



        # === HAZARD DETECTION: Load-Use ===
        hazard = False
        if not self.state.EX["nop"] and self.state.EX["rd_mem"]:
            ex_dest = self.state.EX["Wrt_reg_addr"]
            id_instr = self.state.ID["instr"]
            rs1 = (id_instr >> 15) & 0x1F
            rs2 = (id_instr >> 20) & 0x1F
            if ex_dest != 0 and (ex_dest == rs1 or ex_dest == rs2):
                hazard = True

        if hazard:
            # Insert a NOP in EX, stall ID and IF by keeping their state
            self.nextState.EX = {k: self.state.EX[k] for k in self.state.EX}  # bubble: same as EX but nop=True
            self.nextState.EX["nop"] = True
            self.nextState.ID = {k: self.state.ID[k] for k in self.state.ID}  # hold ID
            self.nextState.IF = {k: self.state.IF[k] for k in self.state.IF}  # hold IF
            self.myRF.outputRF(self.cycle)
            self.printState(self.state, self.cycle)
            self.state = self.nextState
            self.nextState = State()
            self.cycle += 1
            return


        # === FORWARDING LOGIC ===
        # The goal of forwarding is to avoid unnecessary stalls.
        # If the instruction in the EX stage depends on a register that is being written by MEM or WB,
        # we forward the value directly instead of waiting.

        # First, extract the destination registers from MEM and WB
        mem_dest = self.state.MEM["Wrt_reg_addr"]
        wb_dest = self.state.WB["Wrt_reg_addr"]

        # Forward to EX operand 1 (Read_data1)
        if not self.state.EX["nop"]:
            # Check if rs1 matches a destination in MEM stage
            if mem_dest != 0 and mem_dest == self.state.EX["Rs"] and self.state.MEM["wrt_enable"]:
                # Forward result from MEM to EX operand 1
                self.state.EX["Read_data1"] = self.state.MEM["ALUresult"]

            # Check if rs1 matches a destination in WB stage
            elif wb_dest != 0 and wb_dest == self.state.EX["Rs"] and self.state.WB["wrt_enable"]:
                # Forward result from WB to EX operand 1
                self.state.EX["Read_data1"] = self.state.WB["Wrt_data"]

            # Forward to EX operand 2 (Read_data2)
            if not self.state.EX["is_I_type"] and not self.state.EX["wrt_mem"]:
                # Check if rs2 matches a destination in MEM stage
                if mem_dest != 0 and mem_dest == self.state.EX["Rt"] and self.state.MEM["wrt_enable"]:
                    self.state.EX["Read_data2"] = self.state.MEM["ALUresult"]

                # Check if rs2 matches a destination in WB stage
                elif wb_dest != 0 and wb_dest == self.state.EX["Rt"] and self.state.WB["wrt_enable"]:
                    self.state.EX["Read_data2"] = self.state.WB["Wrt_data"]

        # === HAZARD DETECTION: Load-Use ===
        hazard = False
        if not self.state.EX["nop"] and self.state.EX["rd_mem"]:
            ex_dest = self.state.EX["Wrt_reg_addr"]
            id_instr = self.state.ID["instr"]
            rs1 = (id_instr >> 15) & 0x1F
            rs2 = (id_instr >> 20) & 0x1F
            if ex_dest != 0 and (ex_dest == rs1 or ex_dest == rs2):
                hazard = True

        if hazard:
            # Insert a NOP in EX, stall ID and IF by keeping their state
            self.nextState.EX = {k: self.state.EX[k] for k in self.state.EX}  # bubble: same as EX but nop=True
            self.nextState.EX["nop"] = True
            self.nextState.ID = {k: self.state.ID[k] for k in self.state.ID}  # hold ID
            self.nextState.IF = {k: self.state.IF[k] for k in self.state.IF}  # hold IF
            self.myRF.outputRF(self.cycle)
            self.printState(self.state, self.cycle)
            self.state = self.nextState
            self.nextState = State()
            self.cycle += 1
            return



        # === BRANCH HANDLING (BEQ, BNE) ===
        # We check in the ID stage if the instruction is a conditional branch.
        # If so, we compare the operands and may redirect the PC (change the control flow).
        # If the branch is taken, we set IF.taken to True and flush the ID stage.

        if not self.state.ID["nop"]:
            instr = self.state.ID["instr"]
            opcode = instr & 0x7F

            # Only handle branch opcodes
            if opcode == 0b1100011:
                funct3 = (instr >> 12) & 0x7
                rs1 = (instr >> 15) & 0x1F
                rs2 = (instr >> 20) & 0x1F

                data_rs1 = self.myRF.readRF(rs1)
                data_rs2 = self.myRF.readRF(rs2)

                # Extract immediate fields for branch offset (signed)
                imm_11 = (instr >> 7) & 0x1
                imm_4_1 = (instr >> 8) & 0xF
                imm_10_5 = (instr >> 25) & 0x3F
                imm_12 = (instr >> 31) & 0x1
                offset = (imm_12 << 12) | (imm_11 << 11) | (imm_10_5 << 5) | (imm_4_1 << 1)
                offset = self.convertToSignedInt(offset, 12)

                # Check branch condition
                take_branch = False
                if funct3 == 0b000 and data_rs1 == data_rs2:  # BEQ
                    take_branch = True
                elif funct3 == 0b001 and data_rs1 != data_rs2:  # BNE
                    take_branch = True

                if take_branch:
                    # Update PC with branch target
                    self.nextState.IF["PC"] = self.state.ID["PC"] + offset
                    self.nextState.IF["taken"] = True

                    # Flush the current ID stage
                    self.nextState.ID = {k: self.state.ID[k] for k in self.state.ID}
                    self.nextState.ID["nop"] = True

                    # Optionally flush IF as well — though usually just halting decode suffices 



        # === JUMP HANDLING (JAL) ===
        # This handles jump-and-link (JAL) instructions.
        # It is processed in the ID stage just like branches, because JAL is unconditional.
        # It sets the PC to the jump target and stores the return address in rd.

        if not self.state.ID["nop"]:
            instr = self.state.ID["instr"]
            opcode = instr & 0x7F

            if opcode == 0b1101111:  # JAL opcode
                rd = (instr >> 7) & 0x1F

                # Decode immediate using J-type format
                imm_20 = (instr >> 31) & 0x1
                imm_10_1 = (instr >> 21) & 0x3FF
                imm_11 = (instr >> 20) & 0x1
                imm_19_12 = (instr >> 12) & 0xFF

                offset = (imm_20 << 20) | (imm_19_12 << 12) | (imm_11 << 11) | (imm_10_1 << 1)
                offset = self.convertToSignedInt(offset, 20)

                # Store return address into rd (PC + 4)
                self.myRF.writeRF(rd, self.state.ID["PC"] + 4)

                # Jump to target address
                self.nextState.IF["PC"] = self.state.ID["PC"] + offset
                self.nextState.IF["taken"] = True

                # Flush the ID stage
                self.nextState.ID = {k: self.state.ID[k] for k in self.state.ID}
                self.nextState.ID["nop"] = True


        # Pass NOP status forward unless the next stage was written this cycle.
        if self.state.EX["nop"] and self.nextState.MEM["nop"]:
            self.nextState.MEM["nop"] = True

        if self.state.MEM["nop"] and self.nextState.WB["nop"]:
            self.nextState.WB["nop"] = True

        # === INSTRUCTION COUNTING ===
        # Only increment instruction count for instructions that complete in WB stage.
        # That means the instruction must not be a NOP and must have a write-back action.

        if not self.state.WB["nop"]:
            self.inst += 1

        