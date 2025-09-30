# Scoredec Codesign Platform

## Overview

Provides a modular codesign platform where we can use a generic simulator in a plug-and-play-manner and optimize for best design.

## Folder Structure
The high-level folder structure is provided here. Details on the key components of the codebase are provided later
~~~
.
├── sbatch   # contains maps and python scripts pertaining to the environment
  ├──template.txt  # template .txt file based on which .sh/.sbatch files are to be generated for each scenario  
  ├──out  # .sh/.sbatch files generated specific to each scenario, will be parallelized
├── data   # contains data specific to parameters of design/control vars and parameters related to slurm/singularity
  ├── sbatch.json  # parameters specific to slurm/singularity
  ├── alg_params.json # parameters for optimization algorithm (for codesign)
├── algorithm.py  # library of built-in optimization algorithms + high-level abstraction for user-developed optimization algorithm
├── codesign.py # High-level codesign class -- which the user has access to.
├── inputs.py # parses scenario-specific inputs and provides consistency checks
├── sbatch.py # Generates .sh/sbatch from template
├── slurm.py #starts simulation and handles timeout and erros
├── utils.py # sets up and removes cloned directories. Contains helper functions.
~~~

## Key Components/Functionalities

Main_file: codesign.py
Description: 
- Initializes the simulator
- Initializes algorithm with parameter files
- Defines the user-specified evaluation function
- Starting point for beginning the optimization process
- Gathers the final results

Simulator: simulator.py
- Builds  simulation .sif file from singularity recipe
- Links the plant simulation to the SlurmManager
- Allows creation of parallel instances
- Sets up input and output directories for each instance


Algorithm: algorithm.py
- Implements BO (and other) algorithm based on parameter files
- Expects a user-defined objective function evaluation module
- Uses GPyOpt for BO to define surrogate model and optimize for best design
- Run function returns trained model


Objective function:
System: chiller; File: chiller_objective.py
- Reads in input chosen by the algorithm
- Crates multiple input files for each instance of the simulator
- Runs simulation on the inputs
- Evaluates user-defined objective function
- Saves results for each function evaluation and final cost for each input


Simulation Setup/Parallelization: sbatch.py
System: chiller; File: chiller_objective.py

- Sets up directories ready for input/output processing
- Creates multiple .sh scripts ready for job submission
  -  Currently each .sh file corresponds to a different scenario that can be submitted as a single job to a distinct node on HPC.


Simultion Monitoring: slurm.py
- Starts multiple simulations (each simulation corresponding to a given scenario)
- Handles timeout (when simulation time > threshold))
- Handles error 


## Using Codesign Module

The codesign module can be called as follows:

- Import codesign and simulator modues:

``from codesign import Codesign``

``from simulator import Simulator``

- Define inputs (will be described in a bit)

```
params = {
        "num_instances": 3,
        "sim_input": "./json_out/sim_input.json",
        "sim_params": "./data/sbatch.json"
    }
```

- Set up simulator with input params and run codesign

```

    simulator = Simulator(**params)
    codesign = Codesign(simulator, chiller_objective, algorithm='bo')
    res = codesign.run()


```

## Input Parameters


[1] ``num_instances``: Number of parallel scenerios to run

[2] ``sim_input``: JSON containing variables for design optimization (check ./json_out/sim_input.json). Note that this will vary between simulators, but the codesign module is agnostic as long as  a .json is provided.

[3] ``sim_params``: JSON containing parameters associated with the simulator + HPC environment


``sim_params`` contains the simulator file and other paramters needed to run the codesign module. Some key parameters within this module are:

- ``sif_file``: This is the Apptainer/SIngularity image containing the simulator that will be run.
- ``entrypoint_file``: This is a .sh script or a python script needed to run the simulation engine once we enter the local environment inside the container. Note that the entrypoint must allow design optimzation parameters as inputs via  a JSON file
-  ``output_dir``: Output directory in the host container. This will be bound to the outputs and collect output files from each of the N parallel running containers.
- ``recipe_file``: A .recipe or a .def file from which a singularity/apptainer image can be built
- ``template_file``: This is the template file which would be used to create multiple parallel .sh files to be submitted as jobs






