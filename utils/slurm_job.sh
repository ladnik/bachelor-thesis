#!/bin/bash

#SBATCH --job-name=AUTOPAS_RUNNER # specifies a user-defined job name
#SBATCH --nodes=1 # number of compute nodes to be used
#SBATCH --ntasks-per-node=1 # number of MPI processes per node
#SBATCH --partition=small # partition (small_shared, small, medium, small_fat, small_gpu)
# special partitions: large (for selected users only!)
# job configuration testing partition: dev
#SBATCH --cpus-per-task=36 # number of cores per process
#SBATCH --time=00:20:00 # maximum wall clock limit for job execution
#SBATCH --output=logOutput_%j.log # log file which will contain all output

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


export OMP_NUM_THREADS=36
export OMP_PLACES=cores
export OMP_PROC_BIND=true

python run_joby.py