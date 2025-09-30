import json
import os, glob
from joblib import Parallel, delayed

#This module will hendle generation of .sbatch files from a template file specified in sbatch.json

class Sbatch:

    def __init__(self, sim_json, out_json, key):

        """
        Class to read the template file and populate them
        :param template_file: (str) - full path to the template (.txt file)
        :param json_file: (str) - full path to the json file
        :param out_json: (str) - base output parameters json.
        :param key: (str) - name of key that will be used to access the parameters specific to the simulatir
        """
        self.json_file = sim_json
        self.out_json = out_json
        self.key = key

        self.vars = self.read_json()[self.key]

        self.template_file = self.vars["template_file"]
        self.output_dir = self.vars["output_dir"]
        self.instance_name = self.vars["instance_name"] if "instance_name" in self.vars.keys() else key

        #Get the simulation and the host output directory
        self.sim_output_dir = self.vars["sim_output_directory"]
        self.host_output_dir = self.vars["host_output_directory"]

        self._str_to_wite = self.read_template()
        self._setup_dir()

    def read_template(self):
        """
        Method to read data as a string
        """
        with open(self.template_file, 'r') as f:
            data = f.read()
        return data

    def read_json(self):
        with open(self.json_file, 'r') as f:
            var_dict = json.load(f)
        return var_dict

    def _setup_dir(self):
        """
        Set up the directory structure for sbatch output
        :return:
        """
        #set up the directory where the sbatch files will be hosted
        for dir in [self.output_dir, self.host_output_dir]:
            if not os.path.exists(dir):
                os.makedirs(dir)
        return None

    def generate(self, N=1):
        """
        Method to generate .sh or .sbatch files to run in parallel
        :param N: (int) - number of parallel ids to run
        """
        #First change all the bind directories to a list
        _out = f"{self._str_to_wite}"
        print(self.vars)
        for key, val in self.vars.items():
            if key != "bind_directories":
                _out = _out.replace(f"${key}", val)

        #The only one that needs to be changed is the instance name
        #Parallelly change the instance name
        _bind_dirs = self.vars["bind_directories"]
        Parallel(n_jobs=os.cpu_count())(
            delayed(write_sh)(
                n, self.instance_name, _out, self.output_dir, self.out_json, _bind_dirs, self.sim_output_dir, self.host_output_dir
            ) for n in range(N)
        )
        return None




def write_sh(n, instance_str, str_to_write, out_dir, base_out_json, bind_dirs, sim_out_dir=None, host_out_dir=None):
    """
    Function to write to .sh script. Will be parallelized across multiple threads
    :param n: (int) - Id of instance being parallelized
    :param instance_str: (str) - name of instance. (e.g "chiller" for chiller_plant example)
    :param str_to_write: (str) - text from template that will be replaced with entries from JSON
    :param out_dir: (str) - base name of the output directory. will be appended by "_{scen_id}" (e,g. out_1, out_2...)
    :param bind_dirs: (str/list) - all the directories that will need to bound EXCEPT out_dir.
    :param base_out_json: (str) - full path to the json file. will be appended with _{scen_id} in container
    :param sim_out_dir: (str) - full_path to the simulation output directory.
    :param host_out_dir: (str) - full path to the output directory in the local container where the outputs will be stored
    """

    #NOTE: AOWABIN -- CONOLIDATE ALL THE OUTPUT_DIR PARAMS INTO A SINGLE VARIABLE/DICT or an entry in the template
    #NOTE: REPLACE THE NOMENCLATURE: BIND_DIRECTORIES WITH JSON_INPUT DIRECTORIES

    instance_name = f"{instance_str}_{n+1}"
    #parse the out_json file
    _out_str = base_out_json.rstrip(".json")
    out_json = f"{_out_str}_{n+1}.json"

    #This block of code will handle the bund_dirs only
    bind_directories = bind_dirs

    #This creates sub-directories on the hold machine "outputs_{id}, where {id} is sccenario id"
    if sim_out_dir is not None and host_out_dir is not None:
        _host_out_dir = os.path.join(host_out_dir, f"output_{n+1}")
        _delimiter = "" if not bind_directories else ","
        bind_directories += _delimiter + f"{_host_out_dir}:{sim_out_dir}"

        #Create the output directory if already not created
        if not os.path.exists(_host_out_dir):
            os.makedirs(_host_out_dir)

    #Replacing the variables (starting with a $) with their actual values in .sbatch
    str_to_write = str_to_write.replace("$bind_directories", bind_directories)
    str_to_write = str_to_write.replace("$instance_name", instance_name)

    #NOTE: for now assume that bind_directories will contain out_json
    if bind_dirs == "":
        #Default: use the host output directory if no bind_dirs is provided
        str_to_write = str_to_write.replace("$out_json", out_json)
    else:
        # Get the basename of the json file from the full host path
        _json_file = os.path.basename(out_json)
        _out_json_with_binds  = os.path.join(bind_dirs.split(":")[-1], _json_file)  #Note, this will be changed to a json_dir local to the container
        str_to_write = str_to_write.replace("$out_json", _out_json_with_binds)

    #Writing outputs to file
    output_file = os.path.join(out_dir, f"{instance_name}.sh")
    with open(output_file, "w") as f:
        f.write(str_to_write)
    return None


if __name__=="__main__":
    #template_file = "/qfs/projects/scoredec/scoredec_sim/sbatch/template.txt"
    sim_json = "/qfs/projects/scoredec/scoredec_sim/data/sbatch.json"
    out_json = "/qfs/projects/scoredec/scoredec_sim/json_natig/input.json"
    key = "natig"

    TestSbatch = Sbatch(
        sim_json=sim_json,
        out_json=out_json,
        key=key
    )

    TestSbatch.generate(N=1)
