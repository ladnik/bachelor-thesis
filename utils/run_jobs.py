#!/usr/bin/python

import matplotlib
import matplotlib.pyplot as plt
import subprocess
import os
import re
from datetime import datetime
from dotenv import load_dotenv

import plot_util as pu
from config import AUTOPAS_DIR, BUILD_DIR, DATA_DIR, CONFIG_DIR, MD_FLEX_BINARY

matplotlib.use("Agg")


class SimulationRun:
    def __init__(
        self, job_name, cmake_flags, autopas_target, run_binary, run_cli_options
    ):
        self.job_name = job_name
        self.cmake_flags = cmake_flags
        self.autopas_target = autopas_target
        self.run_binary = run_binary
        self.run_cli_options = run_cli_options
        self.output_plots_suffix = "_plot.png"
        self.plot_files = []
        self.output_log_name = "job_log.txt"

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
            if tuning_log_pattern.match(f) or iteration_log_pattern.match(f) or config_log_pattern.match(f):
                os.remove(os.path.join(BUILD_DIR, f))
        

    def __run_autopas(self):
        print("Running simulation")
        subprocess.run(
            [self.run_binary] + self.run_cli_options,
            cwd=BUILD_DIR,
            stdout=self.output_log_fd,
            stderr=self.output_log_fd,
        )

    def __create_plots(self):
        tuning_log_pattern = re.compile(r"tuningLog.*")
        iteration_log_pattern = re.compile(r".*iterationPerformance.*")
        config_log_pattern = re.compile(r".*\.yaml")

        self.tuning_log = os.path.join(
            BUILD_DIR,
            [f for f in os.listdir(BUILD_DIR) if tuning_log_pattern.match(f)][0],
        )
        self.iteration_log = os.path.join(
            BUILD_DIR,
            [f for f in os.listdir(BUILD_DIR) if iteration_log_pattern.match(f)][0],
        )
        self.config_log = os.path.join(
            BUILD_DIR,
            [f for f in os.listdir(BUILD_DIR) if config_log_pattern.match(f)][0],
        )

        print("Creating runtime vs. iteration plot")
        pu.plot_runtime(
            self.iteration_log, os.path.join(BUILD_DIR, "runtime" + self.output_plots_suffix), self.job_name
        )
        self.plot_files.append("runtime" + self.output_plots_suffix)

        print("Creating configurations vs. iteration plot")
        pu.plot_config_phases(
            self.iteration_log, os.path.join(BUILD_DIR, "configs" + self.output_plots_suffix), self.job_name
        )
        self.plot_files.append("configs" + self.output_plots_suffix)

    def __archive_data(self):
        print("Archiving outputs")
        dirname = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
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
            self.output_log_name,
        ] + self.plot_files:
            old_path = os.path.join(BUILD_DIR, f)
            new_path = os.path.join(dir_path, f)
            print(f"moving {old_path} to {new_path}")
            os.rename(old_path, new_path)

        settings_file = os.path.join(dir_path, "settings.txt")
        with open(settings_file, "x") as f:
            f.write(f"Job name: {self.job_name}\n")
            f.write(f"CMake flags used: {self.cmake_flags}\n")
            f.write(f"CMake target: {self.autopas_target}\n")
            f.write(f"AutoPas binary run: {self.run_binary}\n")
            f.write(f"AutoPas binary CLI options: {self.run_cli_options}\n")
            f.write(f"Final output dir: {dir_path}\n")

    def run_job(self):
        self.output_log_fd = open(os.path.join(BUILD_DIR, self.output_log_name), "w")
        self.__run_cmake()
        self.__clean_build_dir()
        self.__run_autopas()
        self.__create_plots()
        self.__archive_data()
        self.__clean_build_dir()
        self.output_log_fd.close()


def main():
    equilibrium_100k_static = SimulationRun(
        "equilibrium_100k_static",
        ["-DAUTOPAS_DYNAMIC_TUNING_INTERVALS=OFF", "-DAUTOPAS_LOG_ITERATIONS=ON"],
        "md-flexible",
        MD_FLEX_BINARY,
        [
            "--iterations",
            "100000",
            "--use-tuning-logger",
            "true",
        ],
    )
    
    equilibrium_100k_dynamic_1_25 = SimulationRun(
        "equilibrium_100k_dynamic_1_25",
        ["-DAUTOPAS_DYNAMIC_TUNING_INTERVALS=ON", "-DAUTOPAS_LOG_ITERATIONS=ON"],
        "md-flexible",
        MD_FLEX_BINARY,
        [
            "--iterations",
            "100000",
            "--dynamic-retune-time-factor",
            "1.25",
            "--use-tuning-logger",
            "true",
        ],
    )

    heating_sphere_100k_static = SimulationRun(
        "heating_sphere_100k_static",
        ["-DAUTOPAS_DYNAMIC_TUNING_INTERVALS=OFF", "-DAUTOPAS_LOG_ITERATIONS=ON"],
        "md-flexible",
        MD_FLEX_BINARY,
        [
            "--use-tuning-logger",
            "true",
            "--yaml-filename",
            CONFIG_DIR + "heatingSphere/predTune/heatingSphere.yaml",
        ],
    )

    #equilibrium_100k_static.run_job()
    equilibrium_100k_dynamic_1_25.run_job()

    # heating_sphere_100k_static.run_job()


if __name__ == "__main__":
    main()
