#!/bin/bash

module load gcc
export CXX=$(which g++)
echo $CXX
module load openmpi

cd /dss/dsshome1/09/ge92hed2/AutoPas/build
cmake -DAUTOPAS_DYNAMIC_TUNING_INTERVALS=OFF \
    -DMD_FLEXIBLE_USE_MPI=ON  \
    -DMD_FLEXIBLE_MODE=SINGLESITE \
    -DCMAKE_C_COMPILER=$CC \
    -DCMAKE_CXX_COMPILER=$CXX \
    -DAUTOPAS_ENABLE_ENERGY_MEASUREMENTS=OFF \
    -DAUTOPAS_LOG_ITERATIONS=ON \
    -DAUTOPAS_LOG_LIVEINFO=ON \
    ..
cmake --build . --target md-flexible --parallel 12