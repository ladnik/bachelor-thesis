#!/usr/bin/python

import subprocess
import sys
from Config import AUTOPAS_DIR, BUILD_DIR, DATA_DIR, CONFIG_DIR, MD_FLEX_BINARY, IS_HPC
from SimulationRun import *
from enum import Enum


class CollectionType(Enum):
    STATIC = 0
    DYNAMIC = 1
    SPECIAL = 2
    OPTIMUM = 3

    def __str__(self):
        if self.value == CollectionType.STATIC:
            return "static"
        elif self.value == CollectionType.DYNAMIC:
            return "dynamic"
        elif self.value == CollectionType.SPECIAL:
            return "special"
        elif self.value == CollectionType.OPTIMUM:
            return "optimum"
        return str(self.value)


def rebuild_autopas(use_dynamic_tuning=False, add_cmake_flags=[], target="md-flexible"):
    """Rebuild the target binary using AutoPas.

    Args:
        use_dynamic_tuning (bool, optional): Whether or not to enable the DYNAMIC_TUNING_INTERVALS option. Defaults to False.
        add_cmake_flags (list, optional): Additional CMake flags for the build process. Defaults to [].
        target (str, optional): Target to build. Defaults to "md-flexible".
    """
    subprocess.run(
        ["cmake"]
        + add_cmake_flags
        + [
            f"-DAUTOPAS_DYNAMIC_TUNING_INTERVALS={'ON' if use_dynamic_tuning else 'OFF'}",
            "-DAUTOPAS_LOG_ITERATIONS=ON",
            "-DAUTOPAS_LOG_LIVEINFO=ON",
            "-DAUTOPAS_FORMATTING_TARGETS=ON",
        ]
        + [".."],
        cwd=BUILD_DIR,
    )
    subprocess.run(
        [
            "cmake",
            "--build",
            ".",
            "--target",
            target,
            "--parallel",
            "12",
        ],
        cwd=BUILD_DIR,
    )


def generate_slurm(mail, collection_type):
    """Generates a slurm job file to be run on CoolMUC4.

    Args:
        mail (str): Mail to notify on job end.
        dynamic (bool): Wether to generate the slurm file for dynamic jobs or static jobs.
    """
    filename = f"jobs_{str(collection_type.name).lower()}.slurm"
    with open(filename, "w") as f:
        f.write(
            f"""#!/bin/bash
#SBATCH --job-name=AP_RUN{collection_type.name[:2]}
#SBATCH --get-user-env
#SBATCH --export=NONE
#SBATCH --clusters=cm4
#SBATCH --partition=cm4_tiny
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=28
#SBATCH --time=10:00:00
#SBATCH --output=logOutput_%j.log
#SBATCH --mail-type=end
#SBATCH --mail-user={mail}"""
        )
        f.write("\n\n")
        f.write(
            '''echo "#==================================================#"
echo " num nodes: " $SLURM_JOB_NUM_NODES
echo " num tasks: " $SLURM_NTASKS
echo " cpus per task: " $SLURM_CPUS_PER_TASK
echo " nodes used: " $SLURM_JOB_NODELIST
echo " job cpus used: " $SLURM_JOB_CPUS_PER_NODE
echo "#==================================================#"'''
        )
        f.write("\n\n")
        f.write("module load slurm_setup\n")
        f.write("export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK\n")
        f.write("export OMP_PLACES=cores\n")
        f.write("export OMP_PROC_BIND=true\n")
        f.write("\n\n")

        f.write(f"MD_FLEX_BINARY={MD_FLEX_BINARY}\n")
        f.write("\n\n")

        f.write("mkdir -p output\n")
        f.write("cd output\n")
        f.write("\n\n")

        jobs = {}
        if collection_type == CollectionType.STATIC:
            jobs = static_jobs.items()
        elif collection_type == CollectionType.DYNAMIC:
            jobs = dynamic_jobs.items()
        elif collection_type == CollectionType.SPECIAL:
            jobs = special_jobs.items()
        elif collection_type == CollectionType.OPTIMUM:
            jobs = optimum_jobs.items()

        for n, j in jobs:
            f.write(f"mkdir -p {n} && cd {n}\n")
            f.write(f"{j.generate_command()}\n")
            f.write(f"wait\n")
            f.write(f"cd ..\n")
            f.write("\n")


def main():
    if not IS_HPC:
        # run default pipeline
        # print("Rebuilding AutoPas to use static tuning")
        # rebuild_autopas()

        # # static jobs
        # print("Running jobs with static tuning intervals")
        # for name, job in static_jobs.items():
        #     job.run_job()

        # for name, job in test_job.items():
        #     job.run_job()

        print("Rebuilding AutoPas to use dynamic tuning")
        rebuild_autopas(True)

        # dynamic jobs
        # print("Running jobs with dynamic tuning intervals")
        # for name, job in dynamic_jobs.items():
        #     job.run_job()
    else:
        # generate a slurm job
        if len(sys.argv) < 2:
            print("Please provide an e-mail that should receive notifications")
            exit(1)
        generate_slurm(sys.argv[1], CollectionType.STATIC)
        generate_slurm(sys.argv[1], CollectionType.DYNAMIC)
        generate_slurm(sys.argv[1], CollectionType.SPECIAL)
        generate_slurm(sys.argv[1], CollectionType.OPTIMUM)


if __name__ == "__main__":
    main()
