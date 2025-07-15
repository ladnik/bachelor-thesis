import os
import re
import subprocess
import shutil
import tempfile
from datetime import datetime

from classes.Config import DATA_DIR, CONFIG_DIR, MD_FLEX_BINARY


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

    def generate_command(self, use_mpi):
        return f"""cp {self.config_file} tempconfig.yaml
echo \"\n{self.append_to_config}\" >> tempconfig.yaml
{"mpirun -np $SLURM_NTASKS " if use_mpi else ""}$MD_FLEX_BINARY {' '.join(self.add_run_options)} --yaml-filename tempconfig.yaml > {self.log_name}
    """


sim_names = [
    #"equilibrium",
    # "spinodial-decomposition",
    "exploding-liquid",
    #"heating-sphere",
]

trigger_types = [
    # "TimeBasedSimple",
    # "TimeBasedAverage",
    "TimeBasedSplit",
]

single_configs = [
    "lc_c04_n3l-aos-csf1",
    "vl_list_iter-non3l-aos",
]

factors = [1.25, 1.5, 2.0]
n_samples = [20, 30, 50]

special_dict = {
    "equilibrium_150k_short_interval": "equilibrium/short_interval.yaml",
}

static_jobs = {
    f"{sim_name}_static": SimulationRun(
        f"{sim_name}_static",
        CONFIG_DIR + f"{sim_name}/default.yaml",
        "",
    )
    for sim_name in sim_names
}

static_mpi_jobs = {
    f"{sim_name}_static_mpi": SimulationRun(
        f"{sim_name}_static_mpi",
        CONFIG_DIR + f"{sim_name}/default.yaml",
        "",
    )
    for sim_name in sim_names
}

optimum_jobs = {
    f"{sim_name}_static_optimum": SimulationRun(
        f"{sim_name}_static_optimum", CONFIG_DIR + f"{sim_name}/optimum.yaml"
    )
    for sim_name in sim_names
}

dynamic_jobs = {
    f"{sim_name}_dynamic_{trigger_type}_{factor}_{n_sample}": SimulationRun(
        f"{sim_name}_dynamic_{trigger_type}_{factor}",
        CONFIG_DIR + f"{sim_name}/default.yaml",
        f"""
tuning-trigger:
  trigger-type                   : {trigger_type}
  trigger-factor                 : {str(factor)}
  trigger-n-samples              : {str(n_sample)}""",
    )
    for factor in factors
    for n_sample in n_samples
    for sim_name in sim_names
    for trigger_type in trigger_types
}

special_jobs = {
    f"{special_name}": SimulationRun(
        special_name,
        CONFIG_DIR + special_config,
        "",
    )
    for special_name, special_config in special_dict.items()
}


single_config_jobs = {
    f"hs_{config}": SimulationRun(
        f"hs_{config}", CONFIG_DIR + f"heating-sphere/{config}.yaml"
    )
    for config in single_configs
}
