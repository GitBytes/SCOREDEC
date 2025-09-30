import os
import json


class InputJSON:
    """
    Class to set up multiple scenarios using JSON
    :param inputs:                      list of parameters (including optimization parameters) needed to run multiple scenarios
    :type inputs:                       list_of_dict (see example)

    :param json_dir:                    full path to the directory that will contain the inputs needed for multiple scenarios
    :type json_dir:                     str

    :param base_json:                   template json string containing the parameters including the BO parameters.
    :type base_json:                    str

    :param json_str:                    base string to set json name. (e.g. sim_input will result in sim_input_{n}.json)
    :type json_str:                     str
    """
    def __init__(
            self,
            inputs: list,
            base_json: str = "./bldg_data/input.json",
            json_dir: str = "./json_out/",
            opt_json: str = "./bldg_data/opt_params.json",
            opt_key: str = "opt_domain"
    ):

        self.input_list = inputs
        self.json_dir = json_dir
        self.base_json = base_json

        self.n_scenarios = len(inputs)
        self.base_params = self._read_json(base_json)
        self.opt_params = self._read_json(opt_json)[opt_key]


    @staticmethod
    def _read_json(json_file):
        """
        Function to read the template json file
        """
        with open(json_file) as jf:
            data = json.loads(jf.read())
        return data

    def update_opt_params(self, x):
        """Method to set up o
        :param x:                   list of values passed by optimization
        """
        x = x[0]

        #opt_params is a list of dicts
        _running_idx = 0  #
        for param in self.opt_params:
            assert param["name"] in self.base_params.keys()
            if param["dimensionality"] == 1:
                self.base_params[param["name"]] = x[_running_idx]
            else:
                self.base_params[param["name"]] = x[_running_idx:_running_idx + param["dimensionality"]]

            _running_idx += param["dimensionality"]
        return None

    def scenarios(self):
        for n in range(self.n_scenarios):
            _base_str = os.path.basename(self.base_json).split(".")[0]
            _filename = os.path.join(self.json_dir, f"{_base_str}_{n+1}.json")

            #copy out_dict as the base params
            _out_dict = self.base_params.copy()
            sim_dict = self.input_list[n] #extract the relevant scenario

            print(f"writing to: {_filename}")
            #everwrite params from _out_dict with new scenario info from sim_dict
            for key in sim_dict.keys():
                _out_dict[key] = sim_dict[key]

            print(f"_out_dict: {_out_dict}")
            #Write to the output directory
            with open(_filename, "w") as f:
                f.write(json.dumps(_out_dict))
        return None



def _test_input_natig():
    """
    Function to test out the input oarser
    :return:
    """
    # Step 1: Define the scenarios
    base_json = "./natig/json/input.json"
    json_dir = "./natig/json/"
    opt_json = "./natig/data/opt_params.json"


    scenarios = [
        {
            "scenario_id": 1
        }
    ]

    TestInput = InputJSON(
        inputs=scenarios,
        base_json=base_json,
        json_dir=json_dir,
        opt_json=opt_json
    )

    x = [[0.5, 0.1]]
    TestInput.update_opt_params(x)
    TestInput.scenarios()

    return None

def _test_inputjson():
    """
    Function to test out input_json using the bldg_thermal example
    """
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
    TestInput = InputJSON(
        inputs=scenarios,
        base_json=base_json,
        json_dir=json_dir
    )

    #Define the optimization parameters
    x = [[0.5, 0.1]]
    TestInput.update_opt_params(x)
    TestInput.scenarios()
    return None

if __name__ == "__main__":
    _test_input_natig()
