#!/usr/bin/python

import sys
from Config import AUTOPAS_DIR, BUILD_DIR, DATA_DIR, CONFIG_DIR, MD_FLEX_BINARY, IS_HPC
from SimulationRun import *


def generate_slurm(mail):
    with open("job.slurm", "w") as f:
        f.write(
            f"""#!/bin/bash
#SBATCH --job-name=AP_RUN # specifies a user-defined job name
#SBATCH --clusters=serial
#SBATCH --partition=serial_std
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12 # number of cores per process
#SBATCH --time=45:00:00 # maximum wall clock limit for job execution
#SBATCH --output=logOutput_%j.log # log file which will contain all output
#SBATCH --mail-type=end
#SBATCH --mail-user={mail})"""
        )
        f.write("\n\n")
        f.write(
            """echo "#==================================================#"
echo " num nodes: " $SLURM_JOB_NUM_NODES
echo " num tasks: " $SLURM_NTASKS
echo " cpus per task: " $SLURM_CPUS_PER_TASK
echo " nodes used: " $SLURM_JOB_NODELIST
echo " job cpus used: " $SLURM_JOB_CPUS_PER_NODE
echo "#==================================================#"""
        )
        f.write("\n\n")
        f.write("module load slurm_setup\n")
        f.write("export OMP_NUM_THREADS=12\n")
        f.write("export OMP_PLACES=cores\n")
        f.write("export OMP_PROC_BIND=true\n")
        f.write("\n\n")
        
        f.write(f"MD_FLEX_BINARY={MD_FLEX_BINARY}\n")
        f.write("\n\n")

        for n, j in static_jobs.items():
            f.write(f"mkdir {n} && cd {n}\n")
            f.write(f"{j.generate_command()}\n")
            f.write(f"cd ..\n")
            f.write("\n")


def main():
    if not IS_HPC:
        # run default pipeline
        print("Rebuilding AutoPas to use static tuning")
        rebuild_autopas()

        # static jobs
        print("Running jobs with static tuning intervals")
        for name, job in static_jobs:
            job.run_job()

        print("Rebuilding AutoPas to use dynamic tuning")
        rebuild_autopas(True)

        # dynamic jobs
        print("Running jobs with dynamic tuning intervals")
        for name, job in static_jobs:
            job.run_job()
    else:
        if len(sys.argv) < 2:
            print("Please provide an e-mail that should receive notifications")
            exit(1)
        generate_slurm(sys.argv[1])


if __name__ == "__main__":
    main()
