import os
import json
import numpy as np
import pandas as pd

class InputParser:

    def __init__(
            self,
            bo_params,
            model_param_file,
            adversary_file,
            entry_point,
            sbatch_file
    ):

        """
        Class to manage inputs and create the .sh file for parallelization
        :param bo_params: (dict) - dictionary with (key, value) pairs representing (variable, trial_value)
        :param model_param_file: (str) - full path to a json file containing model parameters
        :param adversary_file: (str) - full path to a CSV, rows must correspond to different scenarios
        :param entry_point: (str) - full path to the .sh serving as the entry point
        """

        self.bo_params = bo_params
        self.bo_keys = self.bo_keys()
        self.model_params = self.load(model_param_file)
        self.model_keys = self.model_params.keys()

        self.adversary_file = adversary_file
        self.df_adv, self.adv_keys = self.parse_adversary_file()
        self.entry_point = entry_point
        self.sbatch_file = sbatch_file

    @staticmethod
    def load_json(filename):
        assert filename.endswith(".json")
        return json.open(filename)

    def parse_adversary_file(self):
        """
        Method to parse adversary file and
        """
        df_adversary = pd.read_csv(self.adversary_file)
        adv_keys = df_adversary.columns
        return df_adversary, adv_keys

    def match_args(self, n):
        """
        This method reads the entrypoint and matches it up with model keys and bo_params and adv scenario
        :param n: (int) - location of adversarial scenario
        """
        #First convert the selected adversarial scenario to a dict()
        adv_dict = self.df_adv.iloc[n].to_dict()
        print(adv_dict)

        #Initialize entire dictionary
        _all_dict = self.bo_params.copy()
        _all_dict.update(self.model_params)
        _all_dict.update(adv_dict)
        _all_keys = self.bo_keys + self.model_keys + adv_dict.keys()

        #Get all the keys and find the order in which they appear in the entrypoint.sh
        lines = self.read_entrypoint()
        _entry_keys = []  #all the keys with an argumment
        _arg_ids = np.zeros((len(_all_keys, )))
        for line in lines:
            if "=$" in line:
                _var_name = line.split("=$")[0]
                assert _var_name in _all_keys
                _entry_keys.append(_var_name)
                _arg_id = int(line.split("=$")[-1])
                _idx = _all_keys.index(_var_name)
                _arg_ids[_idx] = _arg_id

        #now get the ordered keys based on the
        _ordered_keys = [key for _,key in sorted(zip(_arg_ids, _entry_keys))]
        #generate the final string:
        out_str = ""
        for key in _ordered_keys:
            out_str += f"{_all_dict[key]}"
        return None

    def read_entrypoint(self):
        """
        Method to read the entrypoint file
        """
        with open(self.entry_point) as f:
            lines = f.readlines()

        return lines




#if __name__ == "__main__":

