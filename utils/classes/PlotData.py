import csv
import random
import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.ticker import ScalarFormatter

from classes.Config import PLOT_DATA_DIR
from classes.TuningConfig import TuningConfig

matplotlib.use("Agg")
matplotlib.rcParams["text.usetex"] = True
matplotlib.rcParams["font.family"] = "serif"

# format y axis in plots as 10^x
exp_formatter = ScalarFormatter(useMathText=True)
exp_formatter.set_scientific(True)
exp_formatter.set_powerlimits((0, 0))

random.seed(12345)

AVAIL_COLS = list(mcolors.TABLEAU_COLORS.values())
CONFIG_COL_MAP = {}
LIVEINFO_PARAMS = [
    "avgParticlesPerCell",
    "cutoff",
    "domainSizeX",
    "domainSizeY",
    "domainSizeZ",
    "estimatedNumNeighborInteractions",
    "homogeneity",
    "maxDensity",
    "maxParticlesPerCell",
    "minParticlesPerCell",
    "numCells",
    "numEmptyCells",
    "numHaloParticles",
    "numParticles",
    "particleSize",
    "particleSizeNeededByFunctor",
    "particlesPerBlurredCellStdDev",
    "particlesPerCellStdDev",
    "rebuildFrequency",
    "skin",
    "threadCount",
]


def remove_tuning_its(elems, tune):
    if len(elems) != len(tune):
        print(
            "Found length difference in remove_tuning_its. Data seems to be corrupted."
        )
    return [el for i, el in enumerate(elems) if not tune[i]]


def map_cfg_to_col(config):
    if config in CONFIG_COL_MAP.keys():
        return CONFIG_COL_MAP[config]

    color = (
        AVAIL_COLS.pop()
        if len(AVAIL_COLS) > 0
        else "#{:06x}".format(random.randint(0, 0xFFFFFF))
    )
    CONFIG_COL_MAP[config] = color
    return color


class PlotData:
    """Represents the data collected by various loggers for a single simulation run.

    Args:
            job_name (str): Job name to print as title of plots.
            liveinfo_log (str): Path to the .csv file containing the liveinfo log of the simulation.
            iteration_log (str): Path to the .csv file containing the iteration log of the simulation.
    """

    def __init__(self, job_name, liveinfo_file, iteration_file):
        self.job_name = job_name
        with open(liveinfo_file, newline="") as lfile, open(
            iteration_file, newline=""
        ) as ifile:
            lreader = csv.DictReader(lfile, delimiter=",")
            lrows = list(lreader)

            ireader = csv.DictReader(ifile, delimiter=",")
            irows = list(ireader)

            self.iteration = [int(row["Iteration"]) for row in lrows]
            self.runtime = [int(row["computeInteractions[ns]"]) for row in irows]
            self.tune = [row["inTuningPhase"].lower() in ["true"] for row in irows]

            self.configs = [
                TuningConfig.from_strs(
                    row["Functor"],
                    row["Interaction Type"],
                    row["Container"],
                    row["CellSizeFactor"],
                    row["Traversal"],
                    row["Data Layout"],
                    row["Newton 3"],
                    row["inTuningPhase"],
                )
                for row in irows
            ]

            self.first_tuning_its = [0]
            for i, cfg in enumerate(self.configs):
                if i == 0:
                    continue
                if cfg.tuning and not self.configs[i - 1].tuning:
                    self.first_tuning_its += [i]

            # throw out runtimes of tuning iterations
            self.iteration = remove_tuning_its(self.iteration, self.tune)
            self.runtime = remove_tuning_its(self.runtime, self.tune)
            self.configs = remove_tuning_its(self.configs, self.tune)
            self.stringified_configs = [str(cfg) for cfg in self.configs]

            # read in all liveinfo params we may plot later on
            self.liveinfo = {}
            for liveinfo_param_name in LIVEINFO_PARAMS:
                self.liveinfo[liveinfo_param_name] = [
                    float(row[liveinfo_param_name]) for row in lrows
                ]
                self.liveinfo[liveinfo_param_name] = remove_tuning_its(
                    self.liveinfo[liveinfo_param_name], self.tune
                )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def plot_liveinfo_params(
        self,
        param_names,
        output_prefix,
        mark_configs=True,
    ):
        """Generates a scatter plot for parameters in the liveinfoLog.

        Args:
            param_names (list): List of parameters in iteration log to plot.
            output_prefix (str): Prefix of the output png.
            mark_configs (bool, optional): Whether data points in different unique configs should be plotted in different colors. Defaults to True.
        """

        for param_name in param_names:
            print(f"Plotting liveInfo for {param_name}")

            # remove extreme outliers
            # TODO: notify if outlier has been found
            # q1, q3 = np.percentile(runtime, [25, 75])
            # iqr = q3 - q1
            # param = [
            #     param[i]
            #     for i, v in enumerate(runtime)
            #     if not (v < q1 - 10 * iqr or v > q3 + 10 * iqr)
            # ]
            # runtime = [
            #     v
            #     for i, v in enumerate(runtime)
            #     if not (v < q1 - 10 * iqr or v > q3 + 10 * iqr)
            # ]

            fig, ax = plt.subplots()

            if mark_configs:
                for unique_config in set(self.stringified_configs):
                    mask = [
                        i
                        for i, c in enumerate(self.stringified_configs)
                        if c == unique_config
                    ]
                    ax.scatter(
                        [self.iteration[i] for i in mask],
                        [self.liveinfo[param_name][i] for i in mask],
                        marker="x",
                        s=10,
                        color=map_cfg_to_col(unique_config),
                    )
            else:
                ax.scatter(self.iteration, self.liveinfo[param_name], marker="x", s=10)

            ax.set(xlabel=r"iteration", ylabel=rf"{param_name}")
            ax.grid()
            ax.set_title(
                f"{self.job_name}\niteration vs. {param_name}",
                loc="center",
                fontsize=10,
            )
            fig.savefig(
                f"{output_prefix}{param_name}.png", dpi=300, bbox_inches="tight"
            )
            plt.close(fig)

    def plot_iteration_runtime(
        self,
        output_prefix,
        mark_configs=True,
        mark_tuning_phases=True,
        use_low_pass=False,
        average_n=[1],
    ):
        """Generates a bar plot of a the iteration runtimes as recored in the iterationLog.

        Args:
            output_prefix (str): Prefix of the output png.
            mark_configs (bool, optional): Whether to plot the different optimal configurations found in different colors. Defaults to True.
            mark_tuning_phases (bool, optional): Whether to draw a vertical line at the beginning of a tuning phase. Defaults to True.
            average_n (list, optional): List of n's over which a moving average should be plotted. Defaults to [1].
        """

        print(f"Plotting runtime vs. iteration")
        fig, ax = plt.subplots()
        ax.yaxis.set_major_formatter(exp_formatter)

        # remove extreme outliers
        # TODO: notify if outlier has been found
        # q1, q3 = np.percentile(param, [25, 75])
        # iqr = q3 - q1
        # param = [iqr if (v < q1 - 10 * iqr or v > q3 + 10 * iqr) else v for v in param]
        # plot moving average of param for all n's

        if not use_low_pass:
            average_n.sort()
            colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
            for idx, n in enumerate(average_n):
                smoothed = self.runtime[: n - 1] + [
                    sum(self.runtime[i - n + 1 : i + 1]) / n
                    for i in range(n - 1, len(self.runtime))
                ]
                ax.vlines(self.iteration, 0, smoothed, linewidth=1, color=colors[idx])
        else:
            beta = 0.5
            # not entirely correct, should be y[i] = beta*y[i-1] + (1-beta)*(x[i] - y[i-1])
            smoothed = [self.runtime[0]] + [
                beta * self.runtime[i - 1] + (1 - beta) * self.runtime[i]
                for i in range(1, len(self.runtime))
            ]
            ax.vlines(self.iteration, 0, smoothed, linewidth=1)

        if mark_configs:
            # mark distinct configurations
            custom_lines = []
            custom_descriptors = []
            for unique_config in set(self.stringified_configs):
                mask = [cfg == unique_config for cfg in self.stringified_configs]
                ax.fill_between(
                    self.iteration,
                    max(self.runtime),
                    where=mask,
                    facecolor=map_cfg_to_col(unique_config),
                    alpha=0.5,
                )
                custom_lines += [
                    Line2D(
                        [0],
                        [0],
                        marker="o",
                        color="white",
                        markerfacecolor=map_cfg_to_col(unique_config),
                        markersize=10,
                    )
                ]
                custom_descriptors += [unique_config]
            ax.legend(
                custom_lines,
                custom_descriptors,
                loc="upper left",
                bbox_to_anchor=(0, -0.3, 1, 0.2),
                mode="expand",
                ncols=2,
            )

        # mark beginnings of tuning phases
        if mark_tuning_phases:
            for i in self.first_tuning_its:
                ax.axvline(
                    x=i,
                    ymin=0,
                    color="r",
                    linestyle="-",
                    linewidth=1,
                )

        ax.set(xlabel=r"iteration", ylabel=rf"computeInteractions[ns]")
        ax.grid()
        ax.set_title(
            f"{self.job_name}\ncomputeInteractions[ns] vs. iteration",
            loc="center",
            fontsize=10,
        )
        fig.savefig(f"{output_prefix}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)
