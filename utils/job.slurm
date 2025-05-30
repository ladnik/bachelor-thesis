#!/bin/bash

#SBATCH --job-name=AP_RUN # specifies a user-defined job name
#SBATCH --clusters=serial
#SBATCH --partition=serial_std
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12 # number of cores per process
#SBATCH --time=01:00:00 # maximum wall clock limit for job execution
#SBATCH --output=logOutput_%j.log # log file which will contain all output
#SBATCH --mail-type=end
#SBATCH --mail-user=ge92hed@mytum.de

### some additional information (you can delete those lines)
echo "#==================================================#"
echo " num nodes: " $SLURM_JOB_NUM_NODES
echo " num tasks: " $SLURM_NTASKS
echo " cpus per task: " $SLURM_CPUS_PER_TASK
echo " nodes used: " $SLURM_JOB_NODELIST
echo " job cpus used: " $SLURM_JOB_CPUS_PER_NODE
echo "#==================================================#"
# commands to be executed
# modify the following line to load a specific MPI implementation

module load slurm_setup

#export OMP_NUM_THREADS=12
#export OMP_PLACES=cores
#export OMP_PROC_BIND=true

python run_jobs.py