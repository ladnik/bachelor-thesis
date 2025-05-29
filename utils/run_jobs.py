#!/usr/bin/python

import subprocess
import os
import re
from datetime import datetime

from config import AUTOPAS_DIR, BUILD_DIR, DATA_DIR, CONFIG_DIR, MD_FLEX_BINARY

#        self.output_plots_suffix = "_plot.png"


class SimulationRun:
    def __init__(
        self,
        job_name,
        cmake_flags,
        run_cli_options,
        log_name="job_log.txt",
        autopas_target="md-flexible",
    ):
        self.job_name = job_name
        self.cmake_flags = cmake_flags
        self.run_cli_options = run_cli_options
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
        dirname = f"{self.job_name}-{datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}"
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
        
        os.rename(os.path.join(BUILD_DIR, self.log_name), os.path.join(dir_path, self.log_name))

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
        self.output_log_fd = open(os.path.join(BUILD_DIR, self.log_name), "w")
        self.__run_cmake()
        self.__clean_build_dir()
        self.__run_autopas()
        self.__find_files()
        # self.__create_plots()
        self.__archive_data()
        self.__clean_build_dir()
        self.output_log_fd.close()


def main():
    equilibrium_100k_static = SimulationRun(
        "equilibrium_100k_static",
        ["-DAUTOPAS_DYNAMIC_TUNING_INTERVALS=OFF", "-DAUTOPAS_LOG_ITERATIONS=ON"],
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
        [
            "--use-tuning-logger",
            "true",
            "--yaml-filename",
            CONFIG_DIR + "heatingSphere/predTune/heatingSphere.yaml",
        ],
    )

    equilibrium_100k_static.run_job()
    # equilibrium_100k_dynamic_1_25.run_job()

    # heating_sphere_100k_static.run_job()


if __name__ == "__main__":
    main()
