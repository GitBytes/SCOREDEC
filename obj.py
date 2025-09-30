import os, glob
import json
import pandas as pd
import numpy as np

from sympy import symbols, sympify

class CSVObj:
    """
    Class to compute the objective function based on a list of CSVs

    :param metric_json:                                     full path to the JSOn file containing the config parameters
                                                            needed to compute the aggregate
    :type metric_json:                                      str

    """

    def __init__(
            self,
            obj_expression: str,
            metric_json: str = "./bldg_data/metric.json",
    ):

        self.json_file = metric_json
        self.obj_expression = obj_expression
        self.obj_params = self._read_json()

        #compute the time series aggregate for each metric
        #self.metrics = self._compute_aggregates()
        #print("metrics: ", self.metrics)

    def _read_json(self):
        with open(self.json_file) as jf:
            data = json.loads(jf.read())
        return data

    def _compute_aggregates(self):
        """
        Method to compute aggregates of each individual metric based on a time serires
        """
        agg_dict = dict() #Initialize dictionary containing the TS aggregates, same key as obj_params
        for key, param in self.obj_params.items():
            agg_val = None
            agg_list = []
            #Get all the filenames corresponding to all the scenarios
            _files = glob.glob(param["csv"]) #pd.read_csv(param["csv"])
            print(f"files; {_files}")
            for file in _files:
                df = pd.read_csv(file, sep=",")
                print(df.columns)
                _metric_ts = df[param["header"]].values

                #compute the aggregate
                if param["aggregate"] == "mean":
                    agg_val = np.mean(_metric_ts)
                elif param["aggregate"] == "sum":
                    agg_val = np.sum(_metric_ts)

                assert agg_val is not None
                agg_list.append(agg_val)

            agg_dict[key] = np.mean(np.asarray(agg_list))

        return agg_dict

    def evaluate(self):
        #first amke sure there is an expression to evaluate
        assert self.obj_expression is not None
        #join all the keys so that they can be used with sympy
        #re-compute metrics
        self.metrics = self._compute_aggregates()
        res = ' '.join(key for key in self.metrics.keys())
        #Create a sympy exppression
        vars = symbols(res) #vars: {keys -> variable names}
        _sym_dict = dict() #initialize dictionary, same as metrics but with variable names as keys

        for var in vars:
            _sym_dict[var] = self.metrics[str(var)]
        #convert the str expression -> sympy obj
        _expr = sympify(self.obj_expression)

        #Now we can sub the values in the expression
        obj_val = _expr.subs(_sym_dict)
        return obj_val

    def clean(self):
        """
        Clean up old files
        :return:
        """
        for key, param in self.obj_params.items():
            _files = glob.glob(param["csv"]) #pd.read_csv(param["csv"])
            for file in _files:
                os.remove(file)
        return None





if __name__ == "__main__":
    #test out the CSVObj class
    expression = "load_curtailment + 0.1*attack_val + 0.1*mim_attack"
    metric_json = "/qfs/projects/scoredec/scoredec_sim/natig_data/metric.json"

    TestObj = CSVObj(
        obj_expression=expression,
        metric_json=metric_json
    )
    TestObj.evaluate()