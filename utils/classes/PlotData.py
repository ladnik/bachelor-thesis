import csv, sys, random, re, bisect, ast
import numpy as np


import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.ticker import ScalarFormatter
from matplot2tikz import save as tikzsave

from classes.Config import PLOT_DATA_DIR
from classes.TuningConfig import TuningConfig

# https://tex.stackexchange.com/a/391078
pgf_with_latex = {
    "pgf.texsystem": "pdflatex",
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": [],
    "font.sans-serif": [],  # onherit fonts
    "font.monospace": [],
    "axes.labelsize": 22,  # default 10pt
    "font.size": 16,
    "legend.fontsize": 8,  # default 8pt
    "xtick.labelsize": 16,  # default 8pt
    "ytick.labelsize": 16,
}
mpl.rcParams.update(pgf_with_latex)


# mpl.use("Agg")

# format y axis in plots as 10^x
exp_formatter = ScalarFormatter(useMathText=True)
exp_formatter.set_scientific(True)
exp_formatter.set_powerlimits((0, 0))

plot_width = 172 / 72
plot_height = plot_width / 1.62


random.seed(12345)

axis_cols = list(mcolors.TABLEAU_COLORS.values())

# AVAIL_COLS = list(mcolors.TABLEAU_COLORS.values())
AVAIL_COLS = ["tab:blue", "tab:purple", "tab:red", "tab:orange", "tab:green"]
AVAIL_COLS.reverse()

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


scenario_name_map = {
    "equilibrium": "Equilibrium",
    "exploding-liquid": "Exploding Liquid",
    "heating-sphere": "Heating Sphere",
}

scenario_iterations = {
    "equilibrium": 150000,
    "exploding-liquid": 150000,
    "heating-sphere": 60000,
}


def generate_plot_title(job_str, rank):
    tokens = job_str.split("_")
    triggerstr = ""
    lambdastr = ""
    nstr = ""
    rank_str = f" ({rank})" if "exploding-liquid" in job_str else ""

    if tokens[1] == "dynamic":
        triggerstr = f" with {tokens[2]}"
        lambdastr = f"\n$\\lambda = {tokens[3]}$"
        nstr = f", $n = {tokens[4]}$" if tokens[2] != "TimeBasedSimple" else ""

    return scenario_name_map[tokens[0]] + triggerstr + lambdastr + nstr + rank_str


class PlotData:
    """Represents the data collected by various loggers for a single simulation run.

    Args:
            job_name (str): Job name to print as title of plots.
            liveinfo_log (str): Path to the .csv file containing the liveinfo log of the simulation.
            iteration_log (str): Path to the .csv file containing the iteration log of the simulation.
            range_start (int): Start of iteration range to plot.
            range_end (int): End of iteration range to plot.
    """

    def __init__(
        self,
        job_name,
        liveinfo_file,
        iteration_file,
        tuning_file,
        rank,
        range_start=0,
        range_end=sys.maxsize,
    ):
        self.job_name = job_name
        self.rank = rank
        self.config_col_map = {}
        self.avail_cols = AVAIL_COLS

        with open(liveinfo_file, newline="") as lfile, open(
            iteration_file, newline=""
        ) as ifile, open(tuning_file, newline="") as tfile:
            lreader = csv.DictReader(lfile, delimiter=",")
            lrows = list(lreader)[range_start:range_end]

            ireader = csv.DictReader(ifile, delimiter=",")
            irows = list(ireader)[range_start:range_end]

            self.iteration = [int(row["Iteration"]) for row in lrows]
            self.runtime = [
                int(row["computeInteractionsTotal[ns]"])
                - int(row["rebuildNeighborLists[ns]"])
                for row in irows
            ]
            self.rebuildtime = [int(row["rebuildNeighborLists[ns]"]) for row in irows]
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

            self.first_tuning_its = []
            for i, cfg in enumerate(self.configs):
                if i == 0:
                    if self.configs[i].tuning:
                        self.first_tuning_its += [i]
                    continue
                if cfg.tuning and not self.configs[i - 1].tuning:
                    self.first_tuning_its += [i]

            # throw out runtimes of tuning iterations
            self.iteration = remove_tuning_its(self.iteration, self.tune)
            self.rebuildtime = remove_tuning_its(self.rebuildtime, self.tune)
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

            # set scenario for scenario-specific settings
            self.scenario = job_name.split("_")[0]
            self.plot_title = generate_plot_title(job_name, self.rank)

            # read in selected configurations
            trows = [
                row
                for row in tfile
                if not row.startswith(("liveInfo", "reset", "tune"))
            ]
            tdicts = []
            for row in trows:
                parts = re.findall(r"{[^}]*}|\S+", row)
                # print(parts)
                # d = dict(zip(parts[::2], parts[1::2]))
                cdict = dict(
                    item.split(": ", 1) for item in parts[3].strip("{}").split(" , ")
                )
                cstr = str(
                    TuningConfig.from_strs(
                        functor="LJFunctorAVX",
                        interaction=cdict["Interaction Type"],
                        container=cdict["Container"],
                        csf=cdict["CellSizeFactor"],
                        traversal=cdict["Traversal"],
                        layout=cdict["Data Layout"],
                        n3=cdict["Newton 3"],
                        tuning="true",
                    )
                )
                d = {
                    "evidence": int(parts[1]),
                    "iteration": int(parts[2]),
                    "configuration": cstr,
                }
                tdicts.append(d)

            self.tuning_evidence = tdicts
            self.tuning_results = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def map_cfg_to_col(self, config):
        if config in self.config_col_map.keys():
            return self.config_col_map[config]

        color = (
            self.avail_cols.pop()
            if len(self.avail_cols) > 0
            else "#{:06x}".format(random.randint(0, 0xFFFFFF))
        )
        self.config_col_map[config] = color
        return color

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

        # scenario_ylims = {
        #     "equilibrium": 800000,
        #     "exploding-liquid": 1000000,
        #     "heating-sphere": 16000000,
        # }

        for param_name in param_names:
            print(f"Plotting liveInfo for {param_name}")
            fig, ax = plt.subplots()
            ax.yaxis.set_major_formatter(exp_formatter)
            # ax.set_ylim(top=scenario_ylims[self.scenario])

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
                        color=self.map_cfg_to_col(unique_config),
                        rasterized=True,
                    )
            else:
                ax.scatter(
                    self.iteration,
                    self.liveinfo[param_name],
                    marker="x",
                    s=10,
                    rasterized=True,
                )

            ax.set(xlabel=r"iteration", ylabel=rf"{param_name}")
            # ax.grid()
            ax.set_title(
                f"{self.job_name}\n{param_name}",
                loc="center",
            )
            fig.savefig(
                f"{output_prefix}{param_name}.png", dpi=300, bbox_inches="tight"
            )
            fig.savefig(
                f"{output_prefix}{param_name}.pdf",
                format="pdf",
                dpi=600,
                bbox_inches="tight",
            )
            plt.close(fig)

    def plot_iteration_runtime(
        self,
        output_prefix,
        mark_configs=True,
        mark_tuning_phases=True,
    ):
        """Generates a bar plot of a the iteration runtimes as recored in the iterationLog.

        Args:
            output_prefix (str): Prefix of the output png.
            mark_configs (bool, optional): Whether to plot the different optimal configurations found in different colors. Defaults to True.
            mark_tuning_phases (bool, optional): Whether to draw a vertical line at the beginning of a tuning phase. Defaults to True.
        """

        print(f"Plotting runtime vs. iteration")

        scenario_ylims = {
            "equilibrium": 800000,
            "exploding-liquid": 2000000,
            "heating-sphere": 22000000,
        }

        fig, ax = plt.subplots()
        ax.yaxis.set_major_formatter(exp_formatter)
        ax.set_ylim(top=scenario_ylims[self.scenario])

        # mark distinct configurations
        if mark_configs:
            custom_lines = []
            custom_descriptors = []
            for unique_config in set(self.stringified_configs):
                mask = np.array(
                    [cfg == unique_config for cfg in self.stringified_configs]
                )
                true_idx = np.where(mask)[0]
                iterations = np.array(self.iteration)
                gaps = np.where(np.diff(iterations[true_idx]) != 1)[0] + 1
                for seg in np.split(true_idx, gaps):
                    ax.fill_between(
                        iterations[seg],
                        scenario_ylims[self.scenario],
                        facecolor=self.map_cfg_to_col(unique_config),
                        alpha=0.5,
                    )
                custom_lines += [
                    Line2D(
                        [0],
                        [0],
                        marker="o",
                        color="white",
                        markerfacecolor=self.map_cfg_to_col(unique_config),
                        markersize=10,
                    )
                ]
                custom_descriptors = [unique_config] + custom_descriptors
            ax.legend(
                custom_lines,
                custom_descriptors,
                loc="upper left",
                bbox_to_anchor=(0, -0.3, 1, 0.2),
                mode="expand",
                ncols=2,
            )

        if mark_tuning_phases:
            for i in self.first_tuning_its:
                ax.axvline(
                    x=i + 1,
                    color="gray",
                    linestyle="dashed",
                    alpha=0.75,
                    linewidth=1,
                    zorder=0,
                )

        # plot iteration runtimes
        ax.scatter(
            self.iteration,
            self.runtime,
            s=0.25,
            color=axis_cols[0],
            rasterized=True,
            zorder=1,
        )

        ax.set(xlabel=r"Iteration", ylabel=r"Iteration Run Time in ns")
        ax.grid(visible=False)
        ax.set_title(
            f"{self.plot_title}",
            loc="center",
        )
        # fig.set_size_inches(plot_width, plot_height)
        fig.savefig(f"{output_prefix}.png", dpi=300, bbox_inches="tight")
        fig.savefig(f"{output_prefix}.pdf", format="pdf", dpi=600, bbox_inches="tight")
        # fig.savefig(f"{output_prefix}.pgf", format="pgf")
        plt.close(fig)

    def plot_rebuild_times(
        self,
        output_prefix,
    ):
        """Generates a scatter plot of a the iteration runtimes and rebuild times as recored in the iterationLog.

        Args:
            output_prefix (str): Prefix of the output png.
            x_start (int, optional): Beginning of x axis. Defaults to 0.
            x_end (int, optional): End of x axis, -1 means full range. Defaults to -1.
        """

        print(f"Plotting rebuild times")

        scenario_ylims = {
            "equilibrium": 1200000,
            "exploding-liquid": 1000000,
            "heating-sphere": 8000000,
        }
        fig, ax = plt.subplots()
        ax.yaxis.set_major_formatter(exp_formatter)
        ax.set_ylim(top=scenario_ylims[self.scenario])
        ax.grid(visible=False)

        beta = np.polyfit(self.iteration, self.runtime, 1)
        reg_fun = np.poly1d(beta)

        ax.scatter(
            self.iteration,
            self.runtime,
            label="Run Time excl. Rebuild",
            s=0.25,
            color=axis_cols[0],
            marker=".",
            rasterized=True,
        )

        ax.scatter(
            self.iteration,
            self.rebuildtime,
            label="Rebuild Time",
            s=0.25,
            color=axis_cols[1],
            marker="^",
            rasterized=True,
        )

        # ax.scatter(
        #     self.iteration,
        #     [sum(x) for x in zip(self.runtime, self.rebuildtime)],
        #     label="Total Run Time",
        #     s=0.25,
        #     color=axis_cols[2],
        #     marker=".",
        #     rasterized=True,
        # )

        # ax.plot(self.iteration, reg_fun(self.iteration), "--", color=axis_cols[2])
        # print(f"BETA: {beta}")
        # print(f"NORM: {1+(x_end-x_start)*beta[0]/(2*np.average(self.runtime[x_start: x_end]))}")
        # print(f"NORM: {(2*self.runtime[x_end]+(x_end-x_start)*beta[0])/(2*np.average(self.runtime))}")

        x = np.array(self.iteration)
        y = np.array(self.rebuildtime)
        mask = y != 0
        beta2 = np.polyfit(x[mask], y[mask], 1)
        reg_fun2 = np.poly1d(beta2)
        # ax.plot(self.iteration, reg_fun2(self.iteration), "--", color=axis_cols[3])

        ax.set(xlabel=r"iteration", ylabel=r"Iteration Run Time in ns")
        ax.set_title(
            f"{scenario_name_map[self.scenario]}\nRebuild and Non-Rebuild Times",
            loc="center",
        )
        # fig.set_size_inches(plot_width, plot_height)
        # fig.legend(["Run Time excl. Rebuild", "Rebuild Time", "Total Run Time"], loc="upper left")
        fig.legend(loc="upper left")
        fig.savefig(f"{output_prefix}.png", dpi=300, bbox_inches="tight")
        fig.savefig(f"{output_prefix}.pdf", format="pdf", dpi=600, bbox_inches="tight")
        # tikzsave(f"{output_prefix}.tex", figure=fig)
        plt.close(fig)

    def gather_tuning_results(self):
        print(f"Gathering tuning phase results")

        n_samples = 10
        results = []

        last_phase_start = 0
        last_sample_iteration = 0
        ranking = []

        for d in self.tuning_evidence:
            if d["iteration"] > last_sample_iteration + n_samples:
                # write back data from old phase, truncating to the top 10 configs
                ranking = ranking[0:10]
                results.append(
                    {
                        "start": last_phase_start,
                        "end": d["iteration"] - 1,
                        "ranking": ranking,
                    }
                )
                last_phase_start = d["iteration"]
                ranking = []

            bisect.insort(ranking, (d["evidence"], d["configuration"]))
            last_sample_iteration = d["iteration"]

        if not ranking == []:
            # write back data from last phase
            ranking = ranking[0:10]
            results.append(
                {
                    "start": last_phase_start,
                    "end": scenario_iterations[self.scenario],
                    "ranking": ranking,
                }
            )

        self.tuning_results = results

    def compare_tuning_results(self, infile, outfile):
        print(f"Comparing optimality of tuning results vs {infile}")
        if self.tuning_results is None:
            self.gather_tuning_results()

        histogramm_data = [0] * 10

        with open(infile, newline="") as tfile:
            treader = csv.DictReader(tfile, delimiter=",")
            trows = list(treader)

            for static_idx in range(len(trows)):
                # calculate interval for which this config was deemed optimal (static run)
                stat_start = int(trows[static_idx]["start"])

                if static_idx == len(trows) - 1:
                    stat_end = scenario_iterations[self.scenario]
                else:
                    stat_end = int(trows[static_idx + 1]["start"])

                static_ranking = ast.literal_eval(trows[static_idx]["ranking"])

                for it in range(stat_start, stat_end):
                    # check which configs were selected for this interval (dynamic run)
                    for dynamic_idx in range(len(self.tuning_results)):
                        dyn_start = int(self.tuning_results[dynamic_idx]["start"])

                        if dynamic_idx == len(self.tuning_results) - 1:
                            dyn_end = scenario_iterations[self.scenario]
                        else:
                            dyn_end = int(self.tuning_results[dynamic_idx + 1]["start"])
                        dyn_interval = dyn_end - dyn_start

                        if it < dyn_start or it > dyn_end:
                            continue

                        selected_config = self.tuning_results[dynamic_idx]["ranking"][
                            0
                        ][1]
                        for rank, static_config in enumerate(static_ranking):
                            # print(f"Comparing (static) {static_config[1]} and {selected_config}")
                            if static_config[1] == selected_config:
                                histogramm_data[rank] += 1
                                break
        perc_histogramm = [num / sum(histogramm_data) for num in histogramm_data]
        print(f"histogramm: {histogramm_data}")
        print(f"histogramm (%): {perc_histogramm}")
        with open(f"{outfile}.txt", "w", newline="") as f:
            f.write(f"{histogramm_data}\n")
            f.write(f"{perc_histogramm}\n")

    def write_tuning_results(self, outfile):
        print("Writing tuning results")
        if self.tuning_results is None:
            self.gather_tuning_results()

        with open(f"{outfile}.csv", "w", newline="") as f:
            fieldnames = ["start", "end", "ranking"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.tuning_results)
