import numpy as np
import pandas as pd
from spython.main import Client
from joblib import Parallel, delayed

class Singularity:

    def __init__(
            self,
            recipe_file=None,
            dockerfile=None,
            image_to_build="chiller_plant.sif",
            bind_args="/qfs/projects/scoredec/chiller_plant:/home/developer/fmu",
            host_base_port=8080,
            container_base_port=80,
            writable=False,
            detach=True,
            fakeroot=True
    ):
        """
        Class to build and manage singularity containers
        :param recipe_file: (str) - full path to the Recipe file (e.g. def file) to build of. Analog to dokerfile
        :param dockerfile: (str) - full path to the dockerfile (that can be converted to a Singlarity Recipe)
        :param bind_args: (str) - all directories in the local directory to be mounted on container. Note you can separate multiple directories via ","
        :param detach: (bool) - whether to run the container in a detached mode (recommended = True)
        :param image_to_build: (str) - full path of filename for the built image
        """
        self.recipe_file = recipe_file
        self.dockerfile = dockerfile
        self.bind_args = bind_args
        self.detach = detach
        self.host_port = host_base_port
        self.writable = writable
        self.container_port = container_base_port
        self.fakeroot = fakeroot

        if recipe_file is None:
            assert self.dockerfile is not None
            self.convert_dockerfile_to_recipe()
        self.image_to_build = image_to_build

    def convert_dockerfile_to_recipe(self):
        """
        Method to convert dockerfile to Singularity Recipe
        """

        return None

    def build(self):
        """
        Method to build recipe file based on pwd (anolog to docker build ...)
        """
        #Runs only once at the beginning of expt
        Client.build(
            recipe=self.recipe_file,
            image=self.image_to_build,
            sudo=False
        )
        return None

    def start(
            self,
            base_name="chiller_plant", #remove that
            N=1
    ):
        """
        Method to start N instances of the container, each with a seaparate id
        :param base_name: (str) - base name of the instance
        """
        #This is the function that will need to be parallelized
        self._running_instances = [] #keep track of all the
        for n in range(N):
            id = n + 1
            options = self.set_args(id)
            instance_name = f"{base_name}_{str(id)}"
            instance = Client.instance(self.image_to_build, instance_name, quiet=self.detach, options=options)
            cmd = " ".join(instance.cmd)
            print(f"{cmd}")
            self._running_instances.append(instance.name)
        return None


    def set_args(self, id):
        """
        Method to set up arguments for running the container
        :param id: (int) -
        """
        options = []
        if self.bind_args is not None:
            options += ["--bind", self.bind_args]
        if self.fakeroot:
            options += ["--fakeroot"]
        if self.host_port is not None:
            port = self.host_port + id
            container_port = self.container_port + id
            options += ["--net", "--network", f"portmap={str(port)}:{str(container_port)}/tcp"]
        if self.writable:
            options += ["--writable-tmpfs"]
        return options


    def stop(self, id, all=False):

        if all:
            Client.instane_stopall()

        return None


class SbatchTemplate:

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





def create_dir():
    """
    Helper function to parallelize and
    """


    return None




if __name__ == "__main__":
    recipe_file = "/qfs/projects/scoredec/chiller_plant/ChillerPlant/Singularity.def"
    img_to_build = "/qfs/projects/scoredec/chiller_plant/ChillerPlant/chiller_plant.sif"
    TestImage = Singularity(
        recipe_file=recipe_file,
        image_to_build=img_to_build
    )
    TestImage.build()
    #TestImage.start(N=1)
    #TestImage.build()


