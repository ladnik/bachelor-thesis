#!/bin/bash

module load gcc
module load intel-toolkit
export CXX=$(which g++)
echo $CXX

#AUTOPAS=/dss/dsshome1/09/ge92hed2/AutoPas
AUTOPAS=/dss/dsshome1/09/ge92hed2/NoMod_AutoPas

echo "Building ${AUTOPAS}"

cd ${AUTOPAS}/build
cmake -DAUTOPAS_DYNAMIC_TUNING_INTERVALS=OFF \
    -DMD_FLEXIBLE_USE_MPI=OFF \
    -DCMAKE_C_COMPILER=$CC \
    -DCMAKE_CXX_COMPILER=$CXX \
    -DAUTOPAS_ENABLE_ENERGY_MEASUREMENTS=OFF \
    -DAUTOPAS_ENABLE_DYNAMIC_CONTAINERS=OFF \
    -DAUTOPAS_LOG_ITERATIONS=ON \
    -DAUTOPAS_LOG_LIVEINFO=ON \
    -DAUTOPAS_MIN_LOG_LVL=OFF \
    -DAUTOPAS_ENABLE_FUZZY_AND_RULES_BASED_TUNING=OFF \
    -DAUTOPAS_LOG_TUNINGDATA=ON \
    ${AUTOPAS}/
cmake --build ${AUTOPAS}/build --target md-flexible --parallel 12
