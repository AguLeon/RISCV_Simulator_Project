# This is the main file

import os
import argparse
from memoryReg import *
from singleStage import *
from fiveStage import *


def Performance_metrics(opFilePath: str, ss: SingleStageCore, fs: FiveStageCore):
    ss_metrics = [
        "Performance of Single Stage: ",
        f"#Cycles -> {ss.cycle}",
        f"CPI ->  {ss.cycle / ss.inst:.8f}",
        f"IPC ->  {ss.inst / ss.cycle:.8f}",
    ]


    fs_metrics = [
        "Performance of Five Stage: ",
        f"#Cycles -> {fs.cycle}",
        f"CPI ->  {fs.cycle / fs.num_instr:.8f}",
        f"IPC ->  {fs.num_instr / fs.cycle:.8f}",
    ]

    with open(opFilePath + os.sep + "PerformanceMetrics.txt", "w") as f:
        f.write("\n".join(ss_metrics) + "\n\n" + "\n".join(fs_metrics))



# main
if __name__ == "__main__":

    #parse arguments for input file location

    parser = argparse.ArgumentParser(description='RV32I single stage processor')
    parser.add_argument('--iodir', default="", type=str, help='Directory containing the input files.')
    args, unknown = parser.parse_known_args()

    # the current directory for code
    ioDir = os.path.join("./inputOutput_files", args.iodir)

    # create the input directory if it doesn't exist
    if not os.path.exists(ioDir):
        os.makedirs(ioDir)

    # Show input files directory
    print("IO Directory:", ioDir)
    
    # for testing
    # ioDir = "./content"


    # Show input files directory
    print("IO Directory:", ioDir)

    # common imem
    imem = InsMem("Imem", ioDir)

    # Single Stage
    dmem_ss = DataMem("SS", ioDir)

    ssCore = SingleStageCore(ioDir, imem, dmem_ss)

    while(True):
        if not ssCore.halted:
            ssCore.step()

        if ssCore.halted:
            ssCore.myRF.outputRF(ssCore.cycle) # registers after last cycle
            ssCore.printState(ssCore.nextState, ssCore.cycle) # register states
            ssCore.cycle += 1
            break

    # Flush SingleStage data memory
    dmem_ss.outputDataMem()


    # Five Stage implementation!
    dmem_fs = DataMem("FS", ioDir)
    fsCore = FiveStageCore(ioDir, imem, dmem_fs)

    while(True):
        if not fsCore.halted:
            fsCore.step()

        if fsCore.halted:
            break
    
    # dump FS data mem.
    dmem_fs.outputDataMem()


    # print in terminal
    print("Single Stage Core Performance Metrics:")
    print("Number of Cycles taken: {:.2f}".format(ssCore.cycle), end=", ")
    print("Number of Instruction in Imem: {:.2f}".format(ssCore.inst), end="\n\n")

    print("Five Stage Core Performance Metrics:")
    print("Number of Cycles taken: {:.2f}".format(fsCore.cycle), end=", ")
    # incrementing num of instructions because of an extra HALT instruction which is never decoded
    fsCore.num_instr += 1
    print("Number of Instruction in Imem: {:.2f}".format(fsCore.num_instr), end="\n\n")


    # print performance metrics in file
    Performance_metrics(ioDir, ssCore, fsCore)