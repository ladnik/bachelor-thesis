#!/usr/bin/python

import csv
import os
import re
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import random
import numpy as np

from Config import PLOT_DATA

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


def remove_tuning_its(elems, tune):
    return [el for i, el in enumerate(elems) if not tune[i]]


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


def plot_liveinfo_param(param_name, liveinfo_log, iteration_log, output_name, job_name):
    """Generates a scatter plot of a specific parameter in the liveinfoLog.

    Args:
        param_name (str): Parameter in iteration log to plot.
        liveinfo_log (path): Path to the .csv file containing the liveinfo log of the simulation.
        iteration_log (path): Path to the .csv file containing the iteration log of the simulation.
        output_name (str): Name of the output png.
        job_name (str): Job name to print as title of plot.
    """

    print("Plotting liveInfo")
    with open(liveinfo_log, newline="") as liveinfofile, open(
        iteration_log, newline=""
    ) as iterationfile:
        liveinfo_reader = csv.DictReader(liveinfofile, delimiter=",")
        liveinfo_rows = list(liveinfo_reader)

        iteration_reader = csv.DictReader(iterationfile, delimiter=",")
        iteration_rows = list(iteration_reader)

        iteration = [int(row["Iteration"]) for row in liveinfo_rows]
        param = [float(row[param_name]) for row in liveinfo_rows]
        tune = [row["inTuningPhase"].lower() in ["true"] for row in iteration_rows]
        runtime = [int(row["computeInteractions[ns]"]) for row in iteration_rows]

        # throw out runtimes of tuning iterations
        iteration = remove_tuning_its(iteration, tune)
        param = remove_tuning_its(param, tune)
        runtime = remove_tuning_its(runtime, tune)
        
        # remove extreme outliers
        # TODO: notify if outlier has been found
        q1, q3 = np.percentile(runtime, [25, 75])
        iqr = q3 - q1
        param = [param[i] for i, v in enumerate(runtime) if not (v < q1 - 10 * iqr or v > q3 + 10 * iqr)]
        runtime = [v for i, v in enumerate(runtime) if not (v < q1 - 10 * iqr or v > q3 + 10 * iqr)]
    
        fig, ax = plt.subplots()

        ax.scatter(param, runtime, marker="x", s=10)

        ax.set(xlabel=rf"{param_name}", ylabel=r"runtime")
        ax.grid()
        ax.set_title(
            rf"""\centering \Large{{{job_name}}} \newline
                     \centering \normalsize{{ {param_name} vs. computeInteractions[ns]}}"""
        )
        fig.savefig(output_name, dpi=300, bbox_inches="tight")
        plt.close(fig)


def plot_iteration_param(
    param_name,
    iteration_log,
    output_name,
    job_name,
    mark_configs=False,
    mark_tuning_phases=False,
    average_n=[1],
):
    """Generates a bar plot of a specific parameter in the iterationLog.

    Args:
        param_name (str): Parameter in iteration log to plot.
        iteration_log (path): Path to the .csv file containing the iteration log of the simulation.
        output_name (str): Name of the output png.
        job_name (str): Job name to print as title of plot.
        mark_configs (bool, optional): Whether to plot the different optimal configurations found in different colors. Defaults to False.
        mark_tuning_phases (bool, optional): Whether to draw a vertical line at the beginning of a tuning phase. Defaults to False.
        average_n (list, optional): List of n's over which a moving average should be plotted. Defaults to [1].
    """

    print(f"Plotting {param_name} vs. iteration")
    with open(iteration_log, newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=",")
        rows = list(reader)

        iteration = [int(row["Iteration"]) for row in rows]
        param = [int(row[param_name]) for row in rows]
        tune = [row["inTuningPhase"].lower() in ["true"] for row in rows]

        # throw out runtimes of tuning iterations
        iteration = remove_tuning_its(iteration, tune)
        param = remove_tuning_its(param, tune)

        fig, ax = plt.subplots()

        # remove extreme outliers
        # TODO: notify if outlier has been found
        q1, q3 = np.percentile(param, [25, 75])
        iqr = q3 - q1
        param = [iqr if (v < q1 - 10 * iqr or v > q3 + 10 * iqr) else v for v in param]

        # plot moving average of param for all n's
        average_n.sort()
        colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        for idx, n in enumerate(average_n):
            smoothed = param[: n - 1] + [
                sum(param[i - n + 1 : i + 1]) / n for i in range(n - 1, len(param))
            ]
            ax.vlines(iteration, 0, smoothed, linewidth=1, color=colors[idx])

        # mark distinct configurations
        if mark_configs:
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
            configs = remove_tuning_its(configs, tune)
            hashed_configs = [hash(str(cfg)) for cfg in configs]
            for unique_config in set(hashed_configs):
                mask = [cfg == unique_config for cfg in hashed_configs]
                ax.fill_between(
                    iteration,
                    max(param),
                    where=mask,
                    facecolor=map_cfg_to_col(unique_config),
                    alpha=0.5,
                )

        # mark beginnings of tuning phases
        if mark_tuning_phases:
            for i in range(1, len(iteration)):
                if iteration[i] > iteration[i - 1] + 1:
                    # iterations have been left out here - tuning phase started
                    ax.axvline(
                        x=iteration[i - 1],
                        ymin=0,
                        color="r",
                        linestyle="-",
                        linewidth=1,
                    )

        ax.set(xlabel=r"iteration", ylabel=rf"{param_name}")
        ax.grid()
        ax.set_title(
            rf"""\centering \Large{{{job_name}}} \newline
                     \centering \normalsize{{{param_name} vs. Iteration}}"""
        )
        fig.savefig(output_name, dpi=300, bbox_inches="tight")
        plt.close(fig)


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


def main():
    tuning_log_pattern = re.compile(r"tuningLog.*")
    iteration_log_pattern = re.compile(r".*iterationPerformance.*")
    liveinfo_log_pattern = re.compile(r".*liveInfoLogger.*")

    all_dirs = [
        # "equilibrium_150k_static/",
        # "equilibrium_100k_static_short_interval/",
        # "exploding-liquid_100k_static/",
        # "equilibrium_100k_dynamic_TimeBasedSimple_100.0/",
        # "equilibrium_100k_dynamic_TimeBasedSimple_150.0/",
        # "exploding-liquid_100k_dynamic_TimeBasedSimple_200.0/",
        # "exploding-liquid_100k_dynamic_TimeBasedSimple_150.0/",
        # "heating-sphere_50k_static/",
        # "heating-sphere_50k_dynamic_TimeBasedSimple_100.0/",
        # "equilibrium_100k_dynamic_TimeBasedAverage_100.0/",
        # "equilibrium_100k_dynamic_TimeBasedAverage_100.0-2025-06-07-22:31:55/",
        # "output/equilibrium_150k_static/",
        # "output/exploding-liquid_150k_static/",
        # "output/heating-sphere_100k_static/",
        # "output/equilibrium_150k_dynamic_TimeBasedSimple_60.0/",
        # "output/equilibrium_150k_dynamic_TimeBasedAverage_60.0/",
        # "output/exploding-liquid_150k_dynamic_TimeBasedSimple_60.0/",
        "output/exploding-liquid_150k_dynamic_TimeBasedAverage_60.0/"
    ]

    for job_dir in all_dirs:
        abs_path = os.path.join(PLOT_DATA, job_dir)
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
        print(f"Working on {job_dir}")
        plot_iteration_param(
            "computeInteractionsTotal[ns]",
            PLOT_DATA + job_dir + "iterationLog.csv",
            PLOT_DATA + job_dir + "runtime.png",
            job_dir[:-1],
        )
        plot_iteration_param(
            "computeInteractionsTotal[ns]",
            PLOT_DATA + job_dir + "iterationLog.csv",
            PLOT_DATA + job_dir + "runtime_mark_tuning.png",
            job_dir[:-1],
            False,
            True,
        )
        plot_iteration_param(
            "computeInteractionsTotal[ns]",
            PLOT_DATA + job_dir + "iterationLog.csv",
            PLOT_DATA + job_dir + "runtime_smoothed.png",
            job_dir[:-1],
            False,
            False,
            [1, 10],
        )
        plot_iteration_param(
            "computeInteractionsTotal[ns]",
            PLOT_DATA + job_dir + "iterationLog.csv",
            PLOT_DATA + job_dir + "configs.png",
            job_dir[:-1],
            True,
            True,
        )
        plot_iteration_param(
            "computeInteractionsTotal[ns]",
            PLOT_DATA + job_dir + "iterationLog.csv",
            PLOT_DATA + job_dir + "configs_smoothed.png",
            job_dir[:-1],
            True,
            True,
            [1, 10],
        )
        for param in [
            "avgParticlesPerCell",
            "estimatedNumNeighborInteractions",
            "maxDensity",
            "particlesPerCellStdDev",
            "numEmptyCells",
        ]:
            plot_liveinfo_param(
                param,
                PLOT_DATA + job_dir + "liveinfoLog.csv",
                PLOT_DATA + job_dir + "iterationLog.csv",
                PLOT_DATA + job_dir + f"liveinfo_{param}.png",
                job_dir[:-1],
            )
        estimate_tuning_triggers("computeInteractionsTotal[ns]", PLOT_DATA + job_dir + "iterationLog.csv", 45.0)


if __name__ == "__main__":
    main()
