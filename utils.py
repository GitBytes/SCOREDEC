import os
import shutil
from joblib import Parallel, delayed

class SystemSetup:

    def __init__(
            self,
            sim_dir,
            num_instances,
            json_out="/qfs/projects/scoredec/json_out/out.json",
            output_dir=None

    ):
        """
        Method to set up working directory
        """
        self.base_dir = sim_dir
        self.num_instances = num_instances
        self.json_out = json_out
        self.output_dir = output_dir

        #Set up files
        self.copy_to_basedir()

    def copy_to_basedir(self):
        """
        Method to copy relevant files to base directory
        """
        shutil.copy(self.json_out, self.base_dir)
        return None

    def _setup_output_dir(self):
        """
        Method to create output directories for each of the parallel instances
        :return:
        """
        #get current working directory
        working_dir = os.path.join(os.getcwd(), "output_binds") if self.output_dir is None else self.output_dir
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
        for n in range(self.num_instances):
            if not os.path.exists(os.path.join(working_dir, f"output_{n}")):
                os.makedirs(os.path.join(working_dir, f"output_{n}"))
        return None

    def clone(self):
        """
        set up cloned directory
        """
        N = self.num_instances
        _n_jobs = N if N <= os.cpu_count() else os.cpu_count()
        Parallel(n_jobs=_n_jobs)(
            delayed(create_dir)(self.base_dir, n+1) for n in range(N)
        )
        return None

    def cleanup(self):
        N = self.num_instances
        _n_jobs = N if N <= os.cpu_count() else os.cpu_count()
        Parallel(n_jobs=_n_jobs)(
            delayed(remove_dir)(self.base_dir, n+1) for n in range(N)
        )
        return None

class ParallelSystem:

    def __init__(
            self,
            template_file,
            mount_dirs=None,
            num_parallel_instances=5,
            out_dir="/qfs/projects/scoredec/scoredec_sim/"
    ):
        """
        Class to generate multiple parallel
        :param template file: (str) - full path to the template file
        :param mount_dirs: (list) - list of full paths to the directors that need to be mounted
        :param num_parallel_instances: (int) - number of parallel instances
        :param out_dir: (str) - full path to the output directory
        """

        self.template_file = template_file
        self.num_parallel_instance = num_parallel_instances
        self.mount_dirs = mount_dirs
        self.out_dir = out_dir




def create_dir(dir_name, inst_id):
    """
    Helper function to parallelize directory cre
    """
    clone_dir_name = f"{dir_name}_{inst_id}"
    if not os.path.exists(clone_dir_name):
        shutil.copytree(dir_name, clone_dir_name)
    return None

def remove_dir(dir_name, inst_id):
    clone_dir_name = f"{dir_name}_{inst_id}"
    if os.path.exists(clone_dir_name):
        shutil.rmtree(clone_dir_name)
    return None