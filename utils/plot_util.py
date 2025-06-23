#!/usr/bin/python

import csv
import os
import re

from classes.Config import PLOT_DATA
from classes.PlotData import PlotData


def clean_up_files(abs_path):
    tuning_log_pattern = re.compile(r"tuningLog.*")
    iteration_log_pattern = re.compile(r".*iterationPerformance.*")
    liveinfo_log_pattern = re.compile(r".*liveInfoLogger.*")
    plot_pattern = re.compile(r".*png")

    skip = False
    for f in os.listdir(abs_path):
        if tuning_log_pattern.match(f):
            os.rename(
                os.path.join(abs_path, f),
                os.path.join(abs_path, "tuningLog.txt"),
            )
        if iteration_log_pattern.match(f):
            os.rename(
                os.path.join(abs_path, f),
                os.path.join(abs_path, "iterationLog.csv"),
            )
        if liveinfo_log_pattern.match(f):
            os.rename(
                os.path.join(abs_path, f),
                os.path.join(abs_path, "liveinfoLog.csv"),
            )
        if plot_pattern.match(f):
            skip = True
    return skip


def estimate_tuning_triggers(param_name, iteration_log, factor):
    with open(iteration_log, newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=",")
        rows = list(reader)

        param = [int(row[param_name]) for row in rows]

        timestamps = []
        for i in range(1, len(param)):
            if param[i] >= factor * param[i - 1]:
                timestamps += [i]

        print(
            f"TimeBasedSimply dynamic tuning with a retuning factor of {factor} would have lead to an estimated {len(timestamps)} tuning triggers at times {timestamps}"
        )


def collect_runtimes(parent_path, output_name):
    """Collects the total runtimes for all jobs in parent_path"""

    data = {}

    for job in os.listdir(parent_path):
        # print(f"job: {job}")
        if not os.path.isdir(os.path.join(parent_path, job)):
            continue
        log = os.path.join(os.path.join(parent_path, job), "job_log.txt")
        # print(f"log: {log}")
        if not os.path.isfile(log):
            continue

        with open(log, "r") as logfile:
            lines = logfile.readlines()
            line = "".join(lines[len(lines) - 26 :])
            runtime = re.search(r"Total accumulated\s*:\s([0-9]+)", line).group(1)
            data[job] = runtime

    data = dict(sorted(data.items()))
    print(data)
    with open(output_name, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["job", "total_runtime"])
        for job, runtime in data.items():
            writer.writerow([job, runtime])


def main():

    all_dirs = os.listdir(os.path.join(PLOT_DATA, "output"))

    for job_dir in all_dirs:
        abs_path = os.path.join(os.path.join(PLOT_DATA, "output"), job_dir) + "/"
        skip = clean_up_files(abs_path)
        # if skip:
        #     continue
        print(f"Working on {job_dir}")

        iteration_log = os.path.join(abs_path, "iterationLog.csv")
        liveinfo_log = os.path.join(abs_path, "liveinfoLog.csv")

        with PlotData(job_dir, liveinfo_log, iteration_log) as plot_instance:
            plot_instance.plot_iteration_runtime(abs_path + "runtime", False, False)

            plot_instance.plot_iteration_runtime(
                abs_path + "runtime_mark_tuning", False
            )
            plot_instance.plot_iteration_runtime(abs_path + "configs")
            plot_instance.plot_iteration_runtime(
                abs_path + "configs_nomark", True, False
            )

            plot_instance.plot_liveinfo_params(
                [
                    "avgParticlesPerCell",
                    "estimatedNumNeighborInteractions",
                    "maxDensity",
                    "particlesPerCellStdDev",
                    "numEmptyCells",
                ],
                abs_path + f"liveinfo_",
            )
        # estimate_tuning_triggers("computeInteractionsTotal[ns]", abs_path+ "iterationLog.csv", 45.0)
        # collect_runtimes(os.path.join(PLOT_DATA, "output"), "runtimes.csv")


if __name__ == "__main__":
    main()
