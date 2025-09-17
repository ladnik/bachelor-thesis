#!/usr/bin/python

import subprocess, sys
from jinja2 import Template


from classes.Config import BUILD_DIR, MD_FLEX_BINARY, IS_HPC
from classes.SimulationRun import static_jobs, dynamic_jobs, single_config_jobs, optimum_jobs
from classes.TuningConfig import JobCollectionType



def rebuild_autopas(
    use_dynamic_tuning=False, use_mpi=False, add_cmake_flags=[], target="md-flexible"
):
    """Rebuild the target binary using AutoPas.

    Args:
        use_dynamic_tuning (bool, optional): Whether or not to enable the DYNAMIC_TUNING_INTERVALS option. Defaults to False.
        multisite (bool, optional): Whether or not to compile for runs with MPI (MD_FLEXIBLE_MODE=MULTISITE). Defaults to False.
        add_cmake_flags (list, optional): Additional CMake flags for the build process. Defaults to [].
        target (str, optional): Target to build. Defaults to "md-flexible".
    """
    subprocess.run(
        ["cmake"]
        + add_cmake_flags
        + [
            f"-DAUTOPAS_DYNAMIC_TUNING_INTERVALS={'ON' if use_dynamic_tuning else 'OFF'}",
            f"-DMD_FLEXIBLE_USE_MPI={'ON' if use_mpi else 'OFF'}",
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

def generate_slurm(mail, collection_type, collection, use_mpi=False):
    """Generates a slurm job file to be run on CoolMUC4."""

    with open("slurm_template.jinja") as f:
        template = Template(f.read())

    context = {
        "slurm_job_name": "AP_RUN"+collection_type.name[:2],
        "partition": "cm4_tiny", #if not use_mpi else "cm4_std",
        "qos": "cm4_tiny", # if not use_mpi else "cm4_std",
        "num_nodes": 1,
        "num_tasks": 1 if not use_mpi else 6,
        "num_cpus": 38 if not use_mpi else 24,
        "mail": mail,
        "use_mpi": use_mpi,
        "binary": MD_FLEX_BINARY,
        "jobs" : collection,
    }

    rendered = template.render(**context)

    with open(f"jobs_{str(collection_type.name).lower()}.slurm", "w") as f:
        f.write(rendered)


def main():
    # generate a slurm job
    if len(sys.argv) < 2:
        print("Please provide an e-mail that should receive notifications")
        exit(1)

    generate_slurm(sys.argv[1], JobCollectionType.STATIC, static_jobs)
    generate_slurm(sys.argv[1], JobCollectionType.DYNAMIC, dynamic_jobs, True)
    generate_slurm(sys.argv[1], JobCollectionType.OPTIMUM, optimum_jobs)
    generate_slurm(sys.argv[1], JobCollectionType.SPECIAL, single_config_jobs)


if __name__ == "__main__":
    main()
