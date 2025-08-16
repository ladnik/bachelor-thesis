from dataclasses import dataclass, field
from jinja2 import Template
import yaml, hashlib

from classes.Config import CONFIG_DIR


@dataclass
class ConfigEnvironment:
    """Represents the environment variables set for a parametrized run."""

    iterations: int = 150000
    tuning_strategies: list = field(default_factory=lambda: [])
    tuning_interval: int = 5000
    tuning_samples: int = 10
    cell_size: list = field(default_factory=lambda: [1.0])
    use_dynamic_tuning: bool = True
    trigger_type: str = ""
    trigger_factor: float = 0.0
    trigger_n_samples: int = 0
    use_vtk: bool = False
    vtk_filename: str = "vtk_file"
    vtk_output_folder: str = "vtk_output"
    vtk_write_frequency: int = 1000

    def generate_config_file(self, template_dir, template_name):
        with open(template_dir + "/" + template_name) as f:
            template = Template(f.read())

        context = {
            "iterations": self.iterations,
            "tuning_strategies": self.tuning_strategies,
            "tuning_interval": self.tuning_interval,
            "tuning_samples": self.tuning_samples,
            "cell_size": self.cell_size,
            "use_dynamic_tuning": self.use_dynamic_tuning,
            "trigger_type": self.trigger_type,
            "trigger_factor": self.trigger_factor,
            "trigger_n_samples": self.trigger_n_samples,
            "use_vtk": self.use_vtk,
            "vtk_filename": self.vtk_filename,
            "vtk_output_folder": self.vtk_output_folder,
            "vtk_write_frequency": self.vtk_write_frequency,
        }

        rendered = template.render(**context)
        hash_str = hashlib.md5(yaml.dump(context, sort_keys=True).encode()).hexdigest()
        outfile = template_dir + "/gen/" + hash_str + ".yaml"

        with open(outfile, "w") as f:
            f.write(rendered)
        return outfile


@dataclass
class SimulationRun:
    """Represents a parametrized run of a simulation."""

    job_name: str
    template_dir: str
    template_name: str
    config_env: ConfigEnvironment
    log_name: str = "job_log.txt"
    run_options: list = field(default_factory=list)

    def get_job_name(self):
        return self.job_name

    def generate_command(self, use_mpi):
        config_path = self.config_env.generate_config_file(
            self.template_dir, self.template_name
        )
        copy_cfg = f"cp {config_path} config.yaml\n"
        rm_cfg = f"rm {config_path}\n"
        mpi = "mpirun -np $SLURM_NTASKS " if use_mpi else ""
        binary = f"$MD_FLEX_BINARY {' '.join(self.run_options)} --yaml-filename config.yaml > {self.log_name}"
        return copy_cfg + rm_cfg + mpi + binary


scenarios = [
    "equilibrium",
    #"spinodial-decomposition",
    #"exploding-liquid",
    "heating-sphere",
]

trigger_factors = {
    "equilibrium": [1.25, 1.5, 2.75],
    "spinodial-decomposition": [1.25, 1.5, 2.75],
    "exploding-liquid": [1.25, 1.5, 2.75],
    "heating-sphere": [1.25, 1.5, 2.75],
}

trigger_n_samples = {
    "equilibrium": [1000, 1500, 2000],
    "spinodial-decomposition": [1000, 1500, 2000],
    "exploding-liquid": [1000, 1500, 2000],
    "heating-sphere": [1000, 1500, 2000],
}

# trigger_types = {
#     "equilibrium": [
#         "TimeBasedSimple",
#         "TimeBasedAverage",
#         "TimeBasedSplit",
#         "TimeBasedRegression",
#     ],
#     "spinodial-decomposition": [
#         "TimeBasedSimple",
#         "TimeBasedAverage",
#         "TimeBasedSplit",
#         "TimeBasedRegression",
#     ],
#     "exploding-liquid": [
#         "TimeBasedSimple",
#         "TimeBasedAverage",
#         "TimeBasedSplit",
#         "TimeBasedRegression",
#     ],
#     "heating-sphere": [
#         "TimeBasedSimple",
#         "TimeBasedAverage",
#         "TimeBasedSplit",
#         "TimeBasedRegression",
#     ],
# }
trigger_types = [
    "TimeBasedSimple",
    "TimeBasedAverage",
    "TimeBasedSplit",
    "TimeBasedRegression",
]


single_configs = [
    "lc_c04_n3l-aos-csf1",
    "vl_list_iter-non3l-aos",
]

# optimum_jobs = {
#     f"{sim_name}_static_optimum": SimulationRun(
#         f"{sim_name}_static_optimum", CONFIG_DIR + f"{sim_name}/optimum.yaml"
#     )
#     for sim_name in sim_names
# }

static_jobs = [
    SimulationRun(
        f"{scenario}_static",
        CONFIG_DIR + scenario,
        "template.jinja",
        ConfigEnvironment(
            use_dynamic_tuning=False
        ),
    )
    for scenario in scenarios
]

dynamic_jobs = [
    SimulationRun(
        f"{scenario}_dynamic_{trigger_type}_{trigger_factor}",
        CONFIG_DIR + scenario,
        "template.jinja",
        ConfigEnvironment(
            trigger_type=trigger_type,
            trigger_factor=trigger_factor,
            trigger_n_samples=trigger_n,
        ),
    )
    for scenario in scenarios
    for trigger_type in trigger_types
    for trigger_factor in trigger_factors[scenario]
    for trigger_n in trigger_n_samples[scenario]
]

# single_config_jobs = {
#     f"hs_{config}": SimulationRun(
#         f"hs_{config}", CONFIG_DIR + f"heating-sphere/{config}.yaml"
#     )
#     for config in single_configs
# }
