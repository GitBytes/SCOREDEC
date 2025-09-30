import os.path
import time
from scenarios import InputJSON
from simulator import Simulator
from obj import CSVObj

import datetime
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class Evaluator:
    """
    Method to set up integrate inputs, pass on BO parameters and perform simulation runs
    """

    def __init__(
            self,
            simulator: object,
            scenarios: list,
            base_json: str,
            opt_json: str = "./natig/data/opt_params.json",
            opt_key: str = "opt_domain",
            obj_expression: str = None,
            metric_json: str = None,
            json_dir: str = "./json_out/",
            log_dir = "logs",
            time_to_sleep = 90
    ):

        self.simulator = simulator
        self.scenarios = scenarios
        self.base_json = base_json
        self.opt_json = opt_json
        self.opt_key = opt_key

        self.obj_expression = obj_expression
        self.metric_json = metric_json
        self.json_dir = json_dir
        self.log_dir = log_dir
        self.time_to_sleep = time_to_sleep

        #set up the InputParser and the Objective
        self.InputParser = self.set_input_obj()
        self.Objective = self.set_objective()

        #Initialize log values
        self._init_log_values()

    def _init_log_values(self):
        """
        Method to log values for initialization
        :return:
        """
        # initialize object_val for logging
        self.obj_val = []
        self.solution = []

        #initialize metrics log
        self._metrics_log = dict()
        for metric in self.Objective.obj_params.keys():
            self._metrics_log[metric] = []
        return None

    def set_input_obj(self):
        InputParser = InputJSON(
            inputs=self.scenarios,
            base_json=self.base_json,
            opt_json=self.opt_json,
            opt_key=self.opt_key,
            json_dir=self.json_dir
        )
        return InputParser


    def set_objective(self):
        Objective = CSVObj(
            obj_expression=self.obj_expression,
            metric_json=self.metric_json
        )
        return Objective

    def evaluate(self, x):
        self.InputParser.update_opt_params(x) #update the dictionary with BO parameters
        self.InputParser.scenarios() #set up all the scenarios

        print(f"Setting up inputs for multiple scenarios")
        self.simulator.run()

        time.sleep(self.time_to_sleep)
        #Troubleshoot timestamp
        self._get_datetime()

        objective_value = self.Objective.evaluate()
        objective_value = objective_value[0] if isinstance(objective_value, list) else objective_value
        print(f"objective value: {objective_value}")

        #set log values
        self._set_log_values(objective_value, x[0])

        #Troubleshoot:
        print(f"obj_val: {self.obj_val}")
        print(f"solution: {self.solution}")
        print(f"Metrics log: {self._metrics_log}")

        #log intermittently
        self.create_logs()

        #Clean up files
        #self.Objective.clean()
        return objective_value

    def _get_datetime(self):
        # ct stores current time
        ts = time.time()
        curr_time = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        print(f"curr_time: {curr_time}")
        return None

    def _set_log_values(self, objective_value, x_opt):
        """
        Method to
        :param objective_value: (float) - value of the cost function
        :param x_opt: (float) - optimum value of the optimum value
        :return:
        """

        self.obj_val.append(float(objective_value))
        self.solution.append(x_opt)

        #keep track of all the metrics
        for key, val in self.Objective.metrics.items():
            self._metrics_log[key].append(val)
        return None


    def create_logs(self, plot=False):
        """
        Method to create logs files and plot the cost function as the number of iterations
        """
        #create thje log directory if not already created
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        t = np.arange(len(self.obj_val),)

        _out = {
            "iterations": t,
            "opt_vars": self.solution,
            "objective_value": self.obj_val,
        }

        #change to self._metric_logs
        _out = {**_out, **self._metrics_log}

        #add the metrics to the dictionary of output

        df = pd.DataFrame(_out)
        df.to_csv(os.path.join(self.log_dir, "log.csv"))

        if plot:
            self.plotter(t, np.asarray(self.obj_val))

        return None

    def plotter(self, t, value):
        params = {
            "xlabel": "Iterations",
            "ylabel": "Objective Value"
        }

        # TO DO: Extend to multilple time series, i.e a list of lists
        fig, axs = plt.subplots(1, 1, layout="constrained")
        fig.set_figheight(4)
        fig.set_figwidth(20)
        axs.plot(t, value, 'k-', linewidth=3)
        axs.set_xlabel(params["xlabel"])
        axs.set_ylabel(params["ylabel"])
        axs.grid(True)

        filename = "objective.svg"
        plt.savefig(os.path.join(self.log_dir, filename))
        plt.close()


        return None

def _test_bldg():
    #Define the scenarios for which the optimization is going to be generated ]
    #Step 1: Define the scenarios
    base_json = "./bldg_data/input.json"
    json_dir = "./bldg_json_out/"
    scenarios = [
        {
            "T_inf": 35.0
        },
        {
            "T_inf": 40.0
        }
    ]

    #Step 2: define the simulator
    _bldg_thermal_args = {
        "sim_input": "./bldg_json_out/input_1.json",
        "container_mode": "docker",
        "docker_json": "./data/docker_sim.json",
        "image_name": "bldg_thermal",
        "cleanup_image": False
    }

    BldgSim = Simulator(**_bldg_thermal_args)

    ##Step 3: Define the objective function
    expression =  "0.5*energy + 0.5*thermal_comfort",
    metric_json = "./bldg_data/metric.json"

    #Step 4: Set up the evaluator arguments
    evaluator_args = {
        "simulator": BldgSim,
        "scenarios": scenarios,
        "base_json": base_json,
        "json_dir": json_dir,
        "obj_expression": expression,
        "metric_json": metric_json
    }

    EvaluatorObj = Evaluator(**evaluator_args)
    x = [[26.0]]
    EvaluatorObj.evaluate(x)
    return None


def _test_natig():
    #DFunction to test out the natig simulator
    #Step 1: Define the scenarios
    base_json = "./natig/json/input.json"
    json_dir = "./natig/json/"
    opt_params = "./natig/data/opt_params.json"

    scenarios = [
        {
            "scenario_id": 1
        }
    ]

    #Step 2: define the simulator
    _natig_params = {
        "num_instances": 1,
        "key": "natig",
        "build_from_recipe": False,
        "sim_input": "/qfs/projects/scoredec/scoredec_sim/natig/json/input.json",
        "sim_params": "./data/sbatch.json"
    }

    NatigSim = Simulator(**_natig_params)

    ##Step 3: Define the objective function
    expression = "load_curtailment + 0.1*attack_val + 0.1*mim_attack"
    metric_json = "/qfs/projects/scoredec/scoredec_sim/natig/data/metric.json"

    #Step 4: Set up the evaluator arguments
    evaluator_args = {
        "simulator": NatigSim,
        "scenarios": scenarios,
        "opt_json": opt_params,
        "base_json": base_json,
        "json_dir": json_dir,
        "obj_expression": expression,
        "metric_json": metric_json
    }

    EvaluatorObj = Evaluator(**evaluator_args)
    #x = [[0.13133732403101883, 0.03232335385878471]]
    #x = [[0.510, 0.90]]
    #x = [[0.95, 0.05]]
    x = [[0.11744493, 0.6]]
    EvaluatorObj.evaluate(x)
    return None


if __name__ == "__main__":
    #block of code to test out the evaluator function
    _test_natig()
