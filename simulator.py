from singularity import Singularity
from utils import SystemSetup
from sbatch import Sbatch
from slurm import SlurmManager


class Simulator:

    def __init__(
            self,
            num_instances=1,
            key="natig",
            build_from_recipe=False,
            copy_simdir=False,
            sim_input="./json_out/sim_in.json",
            sim_params="./data/sbatch.json"
    ):
        """
        Class to handle singularity runs.
        :param num_instances: (int) - number of parallel scenarios to rin
        :param build_from_recipe: (bool) - whether to build directly from recipe or not
        :param copy_simdir: (bool) - whether to clone the simulation directory
        :param sim_input: (str) - sim input whether or not 
        :param sim_params:
        """
        self.num_instances = num_instances
        self.key = key
        self.sim_input = sim_input
        self.sim_json = sim_params
        self.copy_simdir = copy_simdir

        # Step [1] - call the Sbatch class to load all the simulation parameters
        self.sbatch_generator = Sbatch(
            key=self.key,
            out_json=self.sim_input,
            sim_json=self.sim_json,
        )

        # Step [2] - Build the singularity .sif file from Recipe if not available
        if build_from_recipe:
            self.ApptProcess = Singularity(
                recipe_file=self.sbatch_generator.vars["recipe_file"],
                image_to_build=self.sbatch_generator.vars["sif_file"]
            )
            self.ApptProcess.build()

        # Step [3] - Call the System setup to set up all the sim directories
        if self.copy_simdir:
            self.ContainerSetup = SystemSetup(
                sim_dir=self.sbatch_generator.sim_dir,
                num_instances=self.num_instances,
                json_out=self.sim_input
            )

            # Step [4] - Clone all the relevant directories
            self.ContainerSetup.clone()

        # Step [5] - Generate .sh files specific to each instance
        self.sbatch_generator.generate(N=self.num_instances)

        # Step [6] - Instantiate simulation manager
        self.sim_manager = SlurmManager(
            instance_name=self.sbatch_generator.instance_name,
            number_of_scenarios=self.num_instances,
            max_active_nodes=None,
            sim_dir=self.sbatch_generator.output_dir,
            account_id=self.sbatch_generator.vars["account_name"],
            user_id=self.sbatch_generator.vars["user_id"],
            logger=None,
            timeout_thresh=self.sbatch_generator.vars["sbatch_time"],
        )

    def run(self):
        # Run Sbatch
        self.sim_manager.start()
        # Monitor + error handling
        self.sim_manager.monitor()



def _test_natig():
    """
    Function to test out the simulator object for natig
    :return:
    """
    params = {
        "num_instances": 1,
        "key": "natig",
        "build_from_recipe": False,
        "sim_input": "/qfs/projects/scoredec/scoredec_sim/natig/json/input.json",
        "sim_params": "./data/sbatch.json"
    }

    NatigSim = Simulator(**params)
    NatigSim.run()

    return None

if __name__ == "__main__":
    params = {
        "num_instances": 2,
        "sim_input": "./json_out/sim_input.json",
        "sim_params": "./data/sbatch.json"
    }

    _test_natig()
    #sim = Simulator(**params)
    #sim.run()
