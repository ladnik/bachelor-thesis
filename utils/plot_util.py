#!/usr/bin/python

import csv
import os
import re
import sys

from classes.Config import PLOT_DATA_DIR
from classes.PlotData import PlotData


def clean_up_files(abs_path):
    tuning_log_pattern = re.compile(r".*tuningLog.*Rank(\d+).*")
    iteration_log_pattern = re.compile(r".*iterationPerformance.*Rank(\d+)*")
    liveinfo_log_pattern = re.compile(r".*liveInfoLogger.*Rank(\d+)*")
    plot_pattern = re.compile(r".*png")

    skip = False
    for f in os.listdir(abs_path):
        m = tuning_log_pattern.match(f)
        if m:
            os.rename(
                os.path.join(abs_path, f),
                os.path.join(abs_path, f"tuningLog_Rank{m.group(1)}.txt"),
            )
        m = iteration_log_pattern.match(f)
        if m:
            os.rename(
                os.path.join(abs_path, f),
                os.path.join(abs_path, f"iterationLog_Rank{m.group(1)}.csv"),
            )
        m = liveinfo_log_pattern.match(f)
        if m:
            os.rename(
                os.path.join(abs_path, f),
                os.path.join(abs_path, f"liveinfoLog_Rank{m.group(1)}.csv"),
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
            f"TimeBasedSimple dynamic tuning with a retuning factor of {factor} would have lead to an estimated {len(timestamps)} tuning triggers at times {timestamps}"
        )


def collect_runtimes(parent_path, output_name):
    """Collects the total runtimes for all jobs in parent_path"""

    print("Collecting runtimes")
    iterations = {
        "equilibrium": 150000,
        "exploding-liquid": 150000,
        "heating-sphere": 60000,
    }
    data = {}
    baseline = {}
    
    # collect baseline runs
    for job in os.listdir(parent_path):
        if not os.path.isdir(os.path.join(parent_path, job)):
            continue
        log = os.path.join(os.path.join(parent_path, job), "job_log.txt")
        if not os.path.isfile(log):
            continue

        if not "static" in job.lower():
            continue
        
        scenario = next((s for s in iterations.keys() if s in job), "")

        with open(log, "r") as logfile:
            lines = logfile.readlines()
            line = "".join(lines[len(lines) - 26 :])
            runtime = re.search(r"Total accumulated\s*:\s([0-9]+)", line)
            runtime = -1 if runtime is None else int(runtime.group(1))
            tuning_its = re.search(r"Tuning iterations\s*:\s*(\d+)", line)
            tuning_its = -1 if tuning_its is None else int(tuning_its.group(1))
            tuning_its_perc = round(tuning_its/iterations[scenario]*100, 2)
            data[job] = {"runtime": runtime, "tuning_its": tuning_its, "runtime_speedup_perc": 0, "tuning_its_perc" : tuning_its_perc, "runtime_delta_abs": 0, "runtime_delta_abs_it" : 0}
            if runtime == -1 or tuning_its == -1:
                print(f"Incomplete job: {job}")

    # collect dynamic runs
    for job in os.listdir(parent_path):
        if not os.path.isdir(os.path.join(parent_path, job)):
            continue
        log = os.path.join(os.path.join(parent_path, job), "job_log.txt")
        if not os.path.isfile(log):
            continue

        if not "dynamic" in job:
            continue

        scenario = next((s for s in iterations.keys() if s in job), "")

        with open(log, "r") as logfile:
            lines = logfile.readlines()
            line = "".join(lines[len(lines) - 26 :])
            runtime = re.search(r"Total accumulated\s*:\s([0-9]+)", line)
            runtime = -1 if runtime is None else int(runtime.group(1))
            runtime_baseline = data[f"{scenario}_dynamic_StaticSimple_1.0_10"]["runtime"]
            runtime_perc = round((runtime_baseline/runtime -1)*100, 0)
            runtime_delta_abs = round(runtime-runtime_baseline,0)
            runtime_delta_abs_it = round(runtime_delta_abs/iterations[scenario], 0)
            tuning_its = re.search(r"Tuning iterations\s*:\s*(\d+)", line)
            tuning_its = -1 if tuning_its is None else int(tuning_its.group(1))
            tuning_its_perc = round(tuning_its/iterations[scenario]*100, 2)
            data[job] = {"runtime": runtime, "tuning_its": tuning_its, "runtime_speedup_perc": runtime_perc, "tuning_its_perc" : tuning_its_perc, "runtime_delta_abs": runtime_delta_abs, "runtime_delta_abs_it": runtime_delta_abs_it}
            if runtime == -1 or tuning_its == -1:
                print(f"Incomplete job: {job}")

    def sort_fn(k):
        parts = k.split("_")
        if "StaticSimple" in parts or "static" in parts:
            return (parts[0], "", 0, float("inf"))
        return (parts[0], parts[2], -int(parts[4]), float(parts[3]))

    data = dict(sorted(data.items(), key=lambda kv: sort_fn(kv[0])))
    # print(data)
    with open(output_name, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            ["job", "total_runtime", "tuning_iterations", "runtime_speedup_perc", "tuning_its_perc", "runtime_delta_abs", "runtime_delta_abs_it"]
        )
        for job, d in data.items():
            writer.writerow([job, d["runtime"], d["tuning_its"], d["runtime_speedup_perc"], d["tuning_its_perc"], d["runtime_delta_abs"], d["runtime_delta_abs_it"]])


def main():
    range_start = 0
    range_end = sys.maxsize
    if len(sys.argv) == 2:
        all_dirs = [sys.argv[1]]
        print(all_dirs)
    elif len(sys.argv) == 4:
        all_dirs = [sys.argv[1]]
        range_start = int(sys.argv[2])
        range_end = int(sys.argv[3])
        print(all_dirs)
    else:
        all_dirs = os.listdir(os.path.join(PLOT_DATA_DIR, "output"))

    # dir = os.path.join(PLOT_DATA_DIR, "output")
    # collect_runtimes(dir, os.path.join(dir, "runtimes.csv"))

    for job_dir in all_dirs:
        print(f"Working on {job_dir}")
        out_dir_path = os.path.join(PLOT_DATA_DIR, "output") + "/"
        abs_path = os.path.join(out_dir_path, job_dir) + "/"

        if not os.path.isdir(abs_path):
            continue
        skip = clean_up_files(abs_path)
        # if skip:
        #     continue

        # ranks = range(6) if "exploding-liquid" in job_dir else [0]
        ranks = [0]
        

        for rank in ranks:
            iteration_log = os.path.join(abs_path, f"iterationLog_Rank{rank}.csv")
            liveinfo_log = os.path.join(abs_path, f"liveinfoLog_Rank{rank}.csv")
            tuning_log = os.path.join(abs_path, f"tuningLog_Rank{rank}.txt")

            # with PlotData(job_dir, liveinfo_log, iteration_log, tuning_log, 5000, 20000) as plot_instance:
            with PlotData(
                job_dir,
                liveinfo_log,
                iteration_log,
                tuning_log,
                rank,
                range_start,
                range_end,
            ) as plot_instance:
                # plot_instance.plot_iteration_runtime(abs_path + "runtime", mark_configs=False, mark_tuning_phases=False)
                # plot_instance.plot_iteration_runtime(
                #     abs_path + "runtime_mark_tuning", mark_configs=False
                # )

                plot_instance.plot_iteration_runtime(abs_path + "configs_Rank"+str(rank))
                plot_instance.plot_rebuild_times(abs_path + "configs_rebuild")
                # plot_instance.plot_iteration_runtime(
                #     abs_path + "configs_nomark", mark_tuning_phases=False
                # )

                plot_instance.plot_liveinfo_params(
                    [
                        # "avgParticlesPerCell",
                        # "estimatedNumNeighborInteractions",
                        "maxDensity",
                        # "particlesPerCellStdDev",
                        # "numEmptyCells",
                    ],
                    abs_path + f"liveinfo_",
                    mark_configs=False
                )

                # plot_instance.write_tuning_results(abs_path + "tuning_results")

                # if not "static" in job_dir.lower():
                #     plot_instance.compare_tuning_results(
                #         out_dir_path
                #         + job_dir.split("_")[0]
                #         + "_dynamic_StaticSimple_1.0_10/tuning_results.csv",
                #         # + "_dynamic_StaticSimple_1.0_10_onlyforstaticconfigs/tuning_results.csv",
                #         abs_path + "tuning_histogramm",
                #     )

    # estimate_tuning_triggers("computeInteractionsTotal[ns]", abs_path+ "iterationLog.csv", 45.0)


if __name__ == "__main__":
    main()
