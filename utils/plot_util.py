#!/usr/bin/python

import sys
import csv
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import random

matplotlib.use("Qt5Agg")
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


def plot_config_phases(infile, outfile):
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

        ax.set(
            xlabel="Iteration", ylabel="Runtime (s)", title="Selected Configurations"
        )
        ax.grid()
        fig.savefig(outfile, dpi=300, bbox_inches="tight")
        fig.show()


def plot_runtime(infile, outfile):
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

        ax.set(xlabel="Iteration", ylabel="Runtime (ns)", title="Runtime vs Iteration")
        ax.grid()
        fig.savefig(outfile, dpi=300, bbox_inches="tight")


def main():
    if len(sys.argv) < 2:
        print("Please provide an input .csv file")
        exit(1)

    plot_config_phases(sys.argv[1], "plot.png")
    input()


if __name__ == "__main__":
    main()
