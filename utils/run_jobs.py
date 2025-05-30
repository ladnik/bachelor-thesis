#!/usr/bin/python

import subprocess
import os
import re
from datetime import datetime
import shutil

from config import (
    AUTOPAS_DIR,
    BUILD_DIR,
    DATA_DIR,
    CONFIG_DIR,
    MD_FLEX_BINARY
)

def rebuild_autopas(use_dynamic_tuning=False, add_cmake_flags=[], target="md-flexible"):
    subprocess.run(
            ["cmake"] + add_cmake_flags + [
            f"-DAUTOPAS_DYNAMIC_TUNING_INTERVALS={'ON' if use_dynamic_tuning else 'OFF'}",
            "-DAUTOPAS_LOG_ITERATIONS=ON",
        ] + [".."],
            cwd=BUILD_DIR
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
            cwd=BUILD_DIR
    )


class SimulationRun:
    def __init__(
        self,
        job_name,
        config_file,
        use_dynamic_tuning=False,
        rebuild_autopas=False,
        add_cmake_flags=[],
        add_run_options=[],
        log_name="job_log.txt",
        autopas_target="md-flexible",
    ):
        self.job_name = job_name
        self.rebuild_autopas = rebuild_autopas
        self.cmake_flags = add_cmake_flags + [
            f"-DAUTOPAS_DYNAMIC_TUNING_INTERVALS={'ON' if use_dynamic_tuning else 'OFF'}",
            "-DAUTOPAS_LOG_ITERATIONS=ON",
        ]
        self.run_cli_options = add_run_options + ["--yaml-filename", config_file]
        self.log_name = log_name
        self.autopas_target = autopas_target

    def __run_cmake(self):
        print("Setting CMake options")
        subprocess.run(
            ["cmake"] + self.cmake_flags + [".."],
            cwd=BUILD_DIR,
            stdout=self.output_log_fd,
            stderr=self.output_log_fd,
        )
        print("Building AutoPas")
        subprocess.run(
            [
                "cmake",
                "--build",
                ".",
                "--target",
                self.autopas_target,
                "--parallel",
                "12",
            ],
            cwd=BUILD_DIR,
            stdout=self.output_log_fd,
            stderr=self.output_log_fd,
        )

    def __clean_build_dir(self):
        print("Cleaning build dir")
        tuning_log_pattern = re.compile(r"tuningLog.*")
        iteration_log_pattern = re.compile(r".*iterationPerformance.*")
        config_log_pattern = re.compile(r".*\.yaml")

        for f in os.listdir(BUILD_DIR):
            if (
                tuning_log_pattern.match(f)
                or iteration_log_pattern.match(f)
                or config_log_pattern.match(f)
            ):
                os.remove(os.path.join(BUILD_DIR, f))

    def __run_autopas(self):
        print("Running simulation")
        subprocess.run(
            [MD_FLEX_BINARY] + self.run_cli_options,
            cwd=BUILD_DIR,
            stdout=self.output_log_fd,
            stderr=self.output_log_fd,
        )

    def __find_files(self):
        tuning_log_pattern = re.compile(r"tuningLog.*")
        iteration_log_pattern = re.compile(r".*iterationPerformance.*")
        config_log_pattern = re.compile(r".*\.yaml")

        t = [f for f in os.listdir(BUILD_DIR) if tuning_log_pattern.match(f)]
        if len(t) > 0:
            self.tuning_log = os.path.join(BUILD_DIR, t[0])

        self.iteration_log = os.path.join(
            BUILD_DIR,
            [f for f in os.listdir(BUILD_DIR) if iteration_log_pattern.match(f)][0],
        )

        c = [f for f in os.listdir(BUILD_DIR) if config_log_pattern.match(f)]
        if len(c) > 0:
            self.config_log = os.path.join(BUILD_DIR, c[0])

        print(f"Found tuning log at {self.tuning_log}")
        print(f"Found iteration log at {self.iteration_log}")
        print(f"Found config log at {self.config_log}")

    def __archive_data(self):
        dirname = f"{self.job_name}-{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}"
        print(f"Archiving outputs to {dirname}")
        dir_path = os.path.join(DATA_DIR, dirname)
        try:
            os.mkdir(
                dir_path,
                mode=0o755,
            )
        except Exception as e:
            print(f"Could not create directory {dir_path}: {e}")
            return

        for f in [
            self.tuning_log,
            self.iteration_log,
            self.config_log,
        ]:
            new_path = os.path.join(dir_path, os.path.basename(f))
            os.rename(f, new_path)

        os.rename(
            os.path.join(BUILD_DIR, self.log_name),
            os.path.join(dir_path, self.log_name),
        )

        settings_file = os.path.join(dir_path, "settings.txt")
        with open(settings_file, "x") as f:
            f.write(f"Job name: {self.job_name}\n")
            f.write(f"CMake flags used: {self.cmake_flags}\n")
            f.write(f"CMake target: {self.autopas_target}\n")
            f.write(f"AutoPas binary run: {MD_FLEX_BINARY}\n")
            f.write(f"AutoPas binary CLI options: {self.run_cli_options}\n")
            f.write(f"Final output dir: {dir_path}\n")

        subprocess.run(["chmod", "-R", "0755", "."], cwd=dir_path)

    def run_job(self):
        print("-" * shutil.get_terminal_size().columns)
        print(f"Running job {self.job_name}")
        print("-" * shutil.get_terminal_size().columns)
        self.output_log_fd = open(os.path.join(BUILD_DIR, self.log_name), "w")
        if self.rebuild_autopas:
            self.__run_cmake()
        self.__clean_build_dir()
        self.__run_autopas()
        self.__find_files()
        # self.__create_plots()
        self.__archive_data()
        self.__clean_build_dir()
        self.output_log_fd.close()
        print("-" * shutil.get_terminal_size().columns)


def main():
    equilibrium_50k_static = SimulationRun(
        "equilibrium_50k_static", CONFIG_DIR + "equilibrium/50k.yaml", False
    )
    
    equilibrium_100k_static = SimulationRun(
        "equilibrium_100k_static", CONFIG_DIR + "equilibrium/100k.yaml", False
    )
    
    equilibrium_150k_static = SimulationRun(
        "equilibrium_150k_static", CONFIG_DIR + "equilibrium/150k.yaml", False
    )
    
    heating_sphere_100k_static = SimulationRun(
        "heating_sphere_100k_static", CONFIG_DIR + "heatingSphere/100k.yaml", False
    )
    
    heating_sphere_200k_static = SimulationRun(
        "heating_sphere_200k_static", CONFIG_DIR + "heatingSphere/200k.yaml", False
    )
    
    spinodial_decomposition_30k_static = SimulationRun(
        "spinodial_decomposition_30k_static", CONFIG_DIR + "spinodial-decomposition/30k.yaml", False
    )
    
    exploding_liquid_12k_static = SimulationRun(
        "exploding_liquid_12k_static", CONFIG_DIR + "exploding-liquid/12k.yaml", False
    )

    # equilibrium_100k_dynamic_1_25 = SimulationRun(
    #     "equilibrium_100k_dynamic_1_25", CONFIG_DIR + "equilibrium/100k.yaml", True
    # )


    print("Rebuilding AutoPas")
    rebuild_autopas()

    # static jobs
    print("Running jobs with static tuning intervals")
    equilibrium_50k_static.run_job()
    equilibrium_100k_static.run_job()
    equilibrium_150k_static.run_job()
    heating_sphere_100k_static.run_job()
    heating_sphere_200k_static.run_job()
    spinodial_decomposition_30k_static.run_job()
    exploding_liquid_12k_static.run_job()
    
    
    # dynamic jobs, rebuild autopas in first one
    #equilibrium_100k_static.run_job()
    #equilibrium_100k_dynamic_1_25.run_job()

    # heating_sphere_100k_static.run_job()


if __name__ == "__main__":
    main()
