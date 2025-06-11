import os
import re
import subprocess
import shutil
import tempfile
from datetime import datetime

from Config import AUTOPAS_DIR, BUILD_DIR, DATA_DIR, CONFIG_DIR, MD_FLEX_BINARY, IS_HPC


class SimulationRun:
    def __init__(
        self,
        job_name,
        config_file,
        append_to_config="",
        add_run_options=[],
        log_name="job_log.txt",
        autopas_target="md-flexible",
    ):
        self.job_name = job_name
        self.config_file = config_file
        self.append_to_config = append_to_config
        self.add_run_options = add_run_options
        self.run_cli_options = add_run_options + ["--yaml-filename"]
        self.log_name = log_name
        self.autopas_target = autopas_target

    def __run_autopas(self):
        print("Running simulation")
        code = subprocess.run(
            [MD_FLEX_BINARY] + self.run_cli_options,
            cwd=self.out_dir,
            stdout=self.output_log_fd,
            stderr=self.output_log_fd,
        ).returncode
        # print(f"Subprocess exited with code {code}")

    def __setup_output(self):
        dirname = f"{self.job_name}-{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}"
        self.out_dir = os.path.join(DATA_DIR, dirname)
        try:
            os.mkdir(
                self.out_dir,
                mode=0o755,
            )
        except Exception as e:
            print(f"Could not create directory {self.out_dir}: {e}")
            return

    def __rename_outfiles(self):
        # TODO: adapt this for multiple ranks
        tuning_log_pattern = re.compile(r"tuningLog.*")
        iteration_log_pattern = re.compile(r".*iterationPerformance.*")
        liveinfo_log_pattern = re.compile(r".*liveInfoLogger.*")

        for f in os.listdir(self.out_dir):
            if tuning_log_pattern.match(f):
                os.rename(
                    os.path.join(self.out_dir, f),
                    os.path.join(self.out_dir, "tuningLog.txt"),
                )
            if iteration_log_pattern.match(f):
                os.rename(
                    os.path.join(self.out_dir, f),
                    os.path.join(self.out_dir, "iterationLog.csv"),
                )
            if liveinfo_log_pattern.match(f):
                os.rename(
                    os.path.join(self.out_dir, f),
                    os.path.join(self.out_dir, "liveinfoLog.csv"),
                )

    def run_job(self):
        print("-" * shutil.get_terminal_size().columns)
        print(f"Running job {self.job_name}")
        print("-" * shutil.get_terminal_size().columns)

        self.__setup_output()
        self.output_log_fd = open(os.path.join(self.out_dir, self.log_name), "w")

        with tempfile.NamedTemporaryFile(mode="w+") as tmp:
            shutil.copyfile(self.config_file, tmp.name)
            tmp.seek(0, 2)
            tmp.write("\n" + self.append_to_config)
            tmp.flush()
            self.run_cli_options += [tmp.name]
            self.__run_autopas()

        self.output_log_fd.close()
        self.__rename_outfiles()
        print("-" * shutil.get_terminal_size().columns)

    def generate_command(self):
        # TODO: create temporary file for config
        return f"""cp {self.config_file} tempconfig.yaml
echo \"\n{self.append_to_config}\" >> tempconfig.yaml
$MD_FLEX_BINARY {' '.join(self.add_run_options)} --yaml-filename tempconfig.yaml > {self.log_name}
    """


sim_names = [
    "equilibrium",
    "spinodial-decomposition",
    "exploding-liquid",
    #"heating-sphere"
]

iterations = [150]
trigger_types = [
    "TimeBasedSimple",
    "TimeBasedAverage",
]
factors = [45.0]

special_dict = {
    "equilibrium_150k_short_interval" : "equilibrium/short_interval.yaml",
}

static_jobs = {
    f"{sim_name}_{its}k_static": SimulationRun(
        f"{sim_name}_{its}k_static",
        CONFIG_DIR + f"{sim_name}/default.yaml",
        f"""iterations                       : {str(its*1000)}""",
    )
    for sim_name in sim_names
    for its in iterations
}

dynamic_jobs = {
    f"{sim_name}_{its}k_dynamic_{trigger_type}_{factor}": SimulationRun(
        f"{sim_name}_{its}k_dynamic_{trigger_type}_{factor}",
        CONFIG_DIR + f"{sim_name}/default.yaml",
        f"""
iterations                       : {str(its*1000)}
tuning-trigger:
  trigger-type                   : {trigger_type}
  trigger-factor                 : {str(factor)}
  trigger-n-samples              : {str(10)}""",
    )
    for sim_name in sim_names
    for its in iterations
    for trigger_type in trigger_types
    for factor in factors
}

special_jobs = {
    f"{special_name}_{its}": SimulationRun(
        special_name,
        CONFIG_DIR + special_config,
        f"""iterations                       : {str(its*1000)}""",
    )
    for special_name, special_config in special_dict.items()
    for its in iterations
}
