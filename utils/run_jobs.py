#!/usr/bin/python

import sys
import csv
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import subprocess
import os
import re
from datetime import datetime

matplotlib.use("Qt5Agg")

AUTOPAS_DIR = "../../AutoPas/"
BUILD_DIR = "../../AutoPas/build/"

# where to store the result run data and plots
DATA_DIR = "../../data/"


class SimulationRun:
    def __init__(self, job_name, cmake_flags, autopas_target, run_binary, run_cli_options):
        self.job_name = job_name
        self.cmake_flags = cmake_flags
        self.autopas_target = autopas_target
        self.run_binary = run_binary
        self.run_cli_options = run_cli_options
        self.output_plot_name = "plot.png"
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
        
        self.tuning_log = [f for f in os.listdir('.') if tuning_log_pattern.match(f)][0]
        self.iteration_log = [f for f in os.listdir('.') if iteration_log_pattern.match(f)][0]
        self.config_log = [f for f in os.listdir('.') if config_log_pattern.match(f)][0]
        
        print("Creating runtime vs. iteration plot")
        with open(self.iteration_log, newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            rows = list(reader)

            iteration = [int(row["Iteration"]) for row in rows]
            runtime = [int(row["computeInteractionsTotal[ns]"]) for row in rows]
            tune = [row["inTuningPhase"].lower() in ["true"] for row in rows]

            fig, ax = plt.subplots()
            ax.plot(iteration, runtime)
            ax.fill_between(iteration, max(runtime), where=tune, facecolor='red', alpha=.5)

            ax.set(xlabel="iteration", ylabel="Runtime (ns)",
            title="Runtime vs Iteration")
            ax.grid()
            fig.savefig(self.output_plot_name, dpi=300, bbox_inches='tight')
           
    def __archive_data(self):
        print("Archiving outputs")
        dirname = datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
        dir_path = os.path.join(DATA_DIR, dirname) 
        try:
            os.mkdir(dir_path, mode = 0o755,)
        except Exception as e:
            print(f"Could not create directory {dir_path}: {e}")
            return

        for f in [self.tuning_log, self.iteration_log, self.config_log, self.output_plot_name, self.output_log_name]:
            old_path = os.path.join(BUILD_DIR, f)
            new_path = os.path.join(dir_path, f) 
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
        self.__run_autopas()
        self.__create_plots()
        self.__archive_data()
        self.output_log_fd.close()
            
            


def main():
    testrun = SimulationRun(
        "testrun",
        ["-DAUTOPAS_DYNAMIC_TUNING_INTERVALS=OFF", "-DAUTOPAS_LOG_ITERATIONS=ON"],
        "md-flexible",
        "/home/niklas/Documents/ba/AutoPas/build/examples/md-flexible/md-flexible",
        [
            "--iterations",
            "10000",
            "--dynamic-retune-time-factor",
            "1.25",
            "--use-tuning-logger",
            "true",
        ],
    )
    testrun.run_job()


if __name__ == "__main__":
    main()
