import json
import GPyOpt as gp
from itertools import permutations
import bo_utils as utils
from timeit import default_timer as timer


class Algorithm:
    def __init__(self, simulator, evaluator, algorithm='bo', alg_params='./data/alg_params.json', plant_params='./chiller_params.json'):
        self.alg_name = algorithm  # choices could be bo, rl, ga

        # Read in algorithm- and plant-specific parameters

        with open(alg_params, "r") as f:
            self.alg_params = json.load(f)[algorithm]

        with open(plant_params, "r") as f:
            self.plant_params = json.load(f)

        self.simulator = simulator
        self.evaluator = evaluator
        self.eval_idx = 0                  # global counter for obj function evaluations

    def run(self):

        pass


class BO(Algorithm):
    def __init__(
            self,
            simulator,
            evaluator,
            algorithm = 'bo',
            alg_params='./data/alg_params.json',
            opt_params='./chiller_params.json',
            opt_params_key="plant_domain"
    ):

        super().__init__(simulator, evaluator, algorithm, alg_params, opt_params)
        self.domain = self.plant_params[opt_params_key]

    def run(self):
        # initialize BayesOpt model
        model = gp.methods.BayesianOptimization(f=self.objective,
                                                domain=self.domain,
                                                model_type=self.alg_params['model_type'],
                                                acquisition_type=self.alg_params['acquisition'],
                                                exact_feval=True,
                                                normalize_Y=True,
                                                de_duplication=True)

        # run model
        model.run_optimization(max_iter=self.alg_params['max_iter'], verbosity=False)

        return model

    def objective(self, x):
        self.eval_idx += 1
        cost = self.evaluator.evaluate(x)
        return cost

algs = {'bo': BO}

