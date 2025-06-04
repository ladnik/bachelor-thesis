#!/usr/bin/python

import sys
import csv
import os
import re
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import random

matplotlib.use("Agg")
matplotlib.rcParams["text.usetex"] = True
matplotlib.rcParams["font.family"] = "serif"
random.seed(12345)

availiable_colors = list(mcolors.TABLEAU_COLORS.values())
config_color_mapping = {}


class TuningConfig:
    def __init__(
        self,
        functor,
        interaction_type,
        container,
        cellsize_factor,
        traversal,
        data_layout,
        newton3,
        tuning,
    ):
        self.functor = functor
        self.interaction_type = interaction_type
        self.container = container
        self.cellsize_factor = cellsize_factor
        self.traversal = traversal
        self.data_layout = data_layout
        self.newton3 = newton3
        self.tuning = tuning

    def __str__(self):
        return f"functor: {self.functor}, interaction type: {self.interaction_type}, container: {self.container}, cellsize factor: {self.cellsize_factor}, traversal: {self.traversal}, data layout: {self.data_layout}, newton 3: {self.newton3}"

    def __eq__(self, other):
        return str(self) == str(other)

    def was_tuning(self):
        # print(self.tuning)
        return self.tuning.lower() == "true"


def map_cfg_to_col(config):
    if config in config_color_mapping.keys():
        return config_color_mapping[config]

    color = (
        availiable_colors.pop()
        if len(availiable_colors) > 0
        else "#{:06x}".format(random.randint(0, 0xFFFFFF))
    )
    config_color_mapping[config] = color
    return color


def plot_config_phases(infile, outfile, job_name, plot_tuning_runtime=False):
    """Plots the different optimal configurations found in different colors.
    Takes in a path to a .csv file containting iterationPerformance logs and
    a path to where the plout should be output to."""

    with open(infile, newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=",")
        rows = list(reader)

        iteration = [int(row["Iteration"]) for row in rows]
        runtime = [int(row["computeInteractionsTotal[ns]"]) for row in rows]

        configs = [
            TuningConfig(
                row["Functor"],
                row["Interaction Type"],
                row["Container"],
                row["CellSizeFactor"],
                row["Traversal"],
                row["Data Layout"],
                row["Newton 3"],
                row["inTuningPhase"],
            )
            for row in rows
        ]

        # throw out tuning iterations
        if not plot_tuning_runtime:
            runtime = [
                el for i, el in enumerate(runtime) if not configs[i].was_tuning()
            ]
            iteration = [
                el for i, el in enumerate(iteration) if not configs[i].was_tuning()
            ]
            configs = [c for c in configs if not c.was_tuning()]

        hashed_configs = [hash(str(cfg)) for cfg in configs]

        fig, ax = plt.subplots()
        ax.plot(iteration, runtime)

        # color in all unique configurations
        for unique_config in set(hashed_configs):
            # tuning configs just take up too many colors
            skip = True
            for cfg_object in reversed(configs):
                if (
                    unique_config == hash(str(cfg_object))
                    and not cfg_object.was_tuning()
                ):
                    skip = False
                    break
            if skip:
                continue

            mask = [cfg == unique_config for cfg in hashed_configs]
            # print(f"filling {unique_config} with {map_cfg_to_col(unique_config)}")
            ax.fill_between(
                iteration,
                max(runtime),
                where=mask,
                facecolor=map_cfg_to_col(unique_config),
                alpha=0.5,
            )

        ax.set(xlabel=r"iteration", ylabel=r"runtime (ns)")
        ax.grid()
        ax.set_title(
            rf"""\centering \Large{{{job_name}}} \newline
                     \centering \normalsize{{Selected Configurations}}"""
        )
        fig.savefig(outfile, dpi=300, bbox_inches="tight")


def plot_runtime(infile, outfile, job_name):
    """Plots runtime over iterations.
    Takes in a path to a .csv file containting iterationPerformance logs and
    a path to where the plout should be output to."""

    with open(infile, newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=",")
        rows = list(reader)

        iteration = [int(row["Iteration"]) for row in rows]
        runtime = [int(row["computeInteractionsTotal[ns]"]) for row in rows]
        tune = [row["inTuningPhase"].lower() in ["true"] for row in rows]

        fig, ax = plt.subplots()
        ax.plot(iteration, runtime)
        ax.fill_between(iteration, max(runtime), where=tune, facecolor="red", alpha=0.5)

        ax.set(xlabel=r"iteration", ylabel=r"runtime (ns)")
        ax.grid()
        ax.set_title(
            rf"""\centering \Large{{{job_name}}} \newline
                     \centering \normalsize{{Runtime vs. Iteration}}"""
        )
        fig.savefig(outfile, dpi=300, bbox_inches="tight")


def plot_data_from_dirs(root_path):
    iteration_log_pattern = re.compile(r".*iterationPerformance.*")

    for data_dir in os.scandir(root_path):
        if data_dir.is_dir():
            print(f"Entering data from {data_dir.name}")
            settings_file = os.path.join(data_dir, "settings.txt")
            match = re.search(r"Job name:\s*(.*)", open(settings_file).readline())
            job_name = "Job" if match is None else match.group(1)

            iteration_log = [
                f.path
                for f in os.scandir(data_dir)
                if iteration_log_pattern.match(f.name)
            ][0]

            print("Creating runtime vs. iteration plot")
            plot_runtime(
                iteration_log, os.path.join(data_dir, "runtime_plot.png"), job_name
            )

            print("Creating configurations vs. iteration plot")
            plot_config_phases(
                iteration_log, os.path.join(data_dir, "configs_plot.png"), job_name
            )


def main():
    # if len(sys.argv) < 2:
    # print("Please provide a data root dir")
    # exit(1)

    # plot_data_from_dirs(sys.argv[1])
    # plot_config_phases(sys.argv[1], "config_plot.png", sys.argv[2])
    # plot_runtime(sys.argv[1], "runtime_plot.png", sys.argv[2])
    # plot_config_phases(
    #     "/home/niklas/Documents/ba/data/unplotted-data/cm4/equilibrium_100k_static-2025-05-30-20:19:07/AutoPas_iterationPerformance_Rank0_null_2025-05-30_20-04-20.csv",
    #     "testplot.png",
    #     "equilibrium_100k_static",
    # )

    plot_config_phases(
        "/home/niklas/Documents/ba/data/unplotted-data/cm4/unplotted-data/exploding_liquid_12k_static-2025-06-01-21:16:12/AutoPas_iterationPerformance_Rank0_2025-06-01_21-13-14.csv",
        "testplot.png",
        "exploding_liquid_12k_static",
    )


if __name__ == "__main__":
    main()
