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
    dummy: str = "" # for special jobs

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
            "dummy": self.dummy,
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
        #rm_cfg = f"rm {config_path}\n"
        rm_cfg=""
        mpi = "mpiexec -np $SLURM_NTASKS " if use_mpi else "mpiexec -np 1 "
        binary = f"$MD_FLEX_BINARY {' '.join(self.run_options)} --yaml-filename config.yaml > {self.log_name}"
        return copy_cfg + rm_cfg + mpi + binary


scenarios = [
    #"equilibrium",
    "exploding-liquid",
    #"heating-sphere",
]

iterations = {
    "equilibrium": 150000,
    "exploding-liquid": 150000,
    "heating-sphere": 60000,
}

cell_sizes = {
    "equilibrium": [1.0],
    "exploding-liquid": [1.0],
    "heating-sphere": [0.5, 1.0],
}

tuning_interval = {
    "equilibrium": 5000,
    "exploding-liquid": 5000,
    "heating-sphere": 5000,
}

trigger_factors = {
    "StaticSimple": [1.0],
    "TimeBasedSimple": [1.25, 1.5, 1.75],
    #"TimeBasedSimple": [1.5],
    "TimeBasedAverage": [1.25, 1.5, 1.75],
    #"TimeBasedAverage": [1.5],
    "TimeBasedSplit": [1.25, 1.5, 1.75],
    #"TimeBasedSplit": [1.5],
    "TimeBasedRegression": [1.25, 1.5, 1.75],
    #"TimeBasedRegression": [1.5, 1.5],
}

trigger_types = [
    "StaticSimple",
    #"TimeBasedSimple",
    #"TimeBasedAverage",
    #"TimeBasedSplit",
    "TimeBasedRegression",
]

trigger_n_samples = {
    "StaticSimple" : [10],
    "TimeBasedSimple": [10],
    "TimeBasedAverage": [250, 500, 1000],
    #"TimeBasedAverage": [500],
    "TimeBasedSplit": [250, 500, 1000],
    #"TimeBasedSplit": [500],
    "TimeBasedRegression": [500, 1000, 1500],
    #"TimeBasedRegression": [500],
}


single_configs = [
    "lc_c04_n3l-aos-csf1",
    "vl_list_iter-non3l-aos",
]

optimum_jobs = [
    SimulationRun(
        f"{scenario}_optimum",
        CONFIG_DIR + scenario,
        "template.jinja",
        ConfigEnvironment(
            iterations=iterations[scenario],
            tuning_interval=tuning_interval[scenario],
            cell_size=cell_sizes[scenario],
            use_dynamic_tuning=False,
        ),
    )
    for scenario in scenarios
]


static_jobs = [
    SimulationRun(
        f"{scenario}_static",
        CONFIG_DIR + scenario,
        "template.jinja",
        ConfigEnvironment(
            iterations=iterations[scenario],
            tuning_interval=tuning_interval[scenario],
            cell_size=cell_sizes[scenario],
            use_dynamic_tuning=False,
        ),
    )
    for scenario in scenarios
]

dynamic_jobs = [
    SimulationRun(
        f"{scenario}_dynamic_{trigger_type}_{trigger_factor}_{trigger_n}",
        CONFIG_DIR + scenario,
        "template.jinja",
        ConfigEnvironment(
            iterations=iterations[scenario],
            tuning_interval=tuning_interval[scenario],
            trigger_type=trigger_type,
            trigger_factor=trigger_factor,
            trigger_n_samples=trigger_n,
            cell_size=cell_sizes[scenario],
        ),
    )
    for scenario in scenarios
    for trigger_type in trigger_types
    for trigger_factor in trigger_factors[trigger_type]
    for trigger_n in trigger_n_samples[trigger_type]
]

single_config_jobs = [
     SimulationRun(
         f"hs_{config}",
         CONFIG_DIR + "heating-sphere",
         f"{config}.yaml",
         ConfigEnvironment(dummy=config)
     )
     for config in single_configs
     ]

