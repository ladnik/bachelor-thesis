#!/bin/bash

module load user_spack
spack load /4diiov7
cd /dss/dsshome1/09/ge92hed2/AutoPas/build
cmake -DAUTOPAS_DYNAMIC_TUNING_INTERVALS=OFF -DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX -DAUTOPAS_ENABLE_ENERGY_MEASUREMENTS=OFF -DAUTOPAS_LOG_ITERATIONS=ON ..
cmake --build . --target md-flexible --parallel 12