from simulator import Simulator
from evaluator import Evaluator
from codesign import Codesign


if __name__ == "__main__":
    #Step 1: Define the simulator
    natig_params = {
        "num_instances": 1,
        "key": "natig",
        "build_from_recipe": False,
        "sim_input": "/qfs/projects/scoredec/scoredec_sim/natig/json/input.json",
        "sim_params": "./data/sbatch.json"
    }

    NatigSim = Simulator(**natig_params)

    #Define the Evaluator
    #Steo 2L Define the scenarios
    base_json = "./natig/json/input.json"
    json_dir = "./natig/json/"

    scenarios = [
        {
            "scenario_id": 1
        }
    ]

    #Define the objectives and the Evaluator Arguments
    #expression = "0.05*attack_val + 0.05*mim_attack - load_curtailment"
    expression = "0.20*attack_val - 0.80*load_curtailment"
    metric_json = "/qfs/projects/scoredec/scoredec_sim/natig/data/metric.json"
    opt_params = "./natig/data/opt_params.json"
    opt_params_key = "opt_domain_e3"  # key for accessing opt_params.json. I'd recommend not changing this even if you create a new opt_params.json

    #Set up the evaluator arguments
    evaluator_args = {
        "simulator": NatigSim,
        "scenarios": scenarios,
        "opt_json": opt_params,
        "opt_key": opt_params_key,
        "base_json": base_json,
        "json_dir": json_dir,
        "obj_expression": expression,
        "metric_json": metric_json
    }

    EvaluatorObj = Evaluator(**evaluator_args)

    #Step 3: Define the algorithm
    # Step 3: Define the algorithm
    algorithm = 'bo'  # define the algorithm to use. Currently only Bayesian Optimization (BO) is supported.
    alg_params = './data/alg_params.json'  # define parameters associated with the algorithm

    # Step 4: Integrate all of them in the codesign class
    print(f"alg_params: {alg_params}")

    # Step 4: Integrate all of them in the codesign class
    print(f"alg_params: {alg_params}")
    Codesign = Codesign(NatigSim, EvaluatorObj, algorithm, alg_params, opt_params, opt_params_key)
    model = Codesign.run()

    print(f"optimal value is: {model.x_opt}")
    # create logs
    Codesign.log(plot=True)