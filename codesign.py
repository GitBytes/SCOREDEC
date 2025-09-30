import pandas as pd
import numpy as np
import os
from singularity import Singularity
from utils import SystemSetup
from sbatch import Sbatch
from slurm import SlurmManager
from simulator import Simulator
from algorithm import algs


class Codesign:

    def __init__(
            self,
            simulator,
            evaluator,
            algorithm='bo',
            alg_params='./data/alg_params.json',
            opt_params='./bldg_data/opt_params.json',
            opt_params_key="opt_domain"
    ):
        """
        High-level class to handle co-design experiments
        :param num_instances: (int) - total number of scenarios to handle
        :param json_dir: (str) - full path to the directory containing the output jsons
        :param sbatch_data: (str) - full path to the json containing the sbatch data
        """

        self.simulator = simulator
        self.evaluator = evaluator

        self.algorithm = algs[algorithm](simulator, evaluator, algorithm, alg_params, opt_params, opt_params_key)

    def __call__(self):
        self.algorithm.run()
        self.cleanup()

    def run(self):
        trained_model = self.algorithm.run()
        return trained_model

    def log(self, plot=False):
        self.evaluator.create_logs(plot=plot)
        return None
        


if __name__ == "__main__":
    params = {
        "num_instances": 2,
        "sim_input": "./json_out/out.json",
        "sim_params": "./data/sbatch.json"
    }
    
    print(f"Initializing {params['num_instances']} instances of the simulator")

    simulator = Simulator(**params)
    codesign = Codesign(simulator, chiller_objective, algorithm='bo')

    res = codesign.run()

    # optimal vars and cost for current value of n (n is number of chillers)
    thresh_opt = res.x_opt[0:1]  # optimal thresholds
    chillers_opt, cap_opt = utils.get_chillers(res.x_opt[1:3])  # optimal capacities
    yOpt = res.fx_opt  # optimal BO cost

    n = 2
    # Print optimal solution and cost
    print("=" * 70)
    print("For n ={}, value of (c,t) that minimises the objective: ({}, {})".format(n, cap_opt, thresh_opt))

