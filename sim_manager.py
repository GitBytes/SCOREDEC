from turtle import update
import numpy as np
import pandas as pd
import json
import subprocess

import shutil
import os
import time
import glob

from runsim import run_sbatch, terminate, short_sbatch
from active_resiliency import ActiveResiliency

class SlurmManager:
    def __init__(
            self,
            user_id="rahm312",
            logger=None,
            timeout_thresh=4.00
    ):
        """
        Class for managing active jobs and scanceling if needed
        :param user_id (str) - user id used in constance
        :param logger (str) - txt filename with full path for generating log file
        :param timeout_thresh (float) - maximum allowable time in hours before job is cancelled
        """

        #Check slurm simulation status
        #check the job status using the job ids and see if it has been terminated early or not
        #finish.txt -> more universal
        #check the process status

        self.logger = logger
        self.user_id = user_id
        self.timeout_thresh = timeout_thresh

        #define variables
        self.sim_start = False #w
        self.sim_done = False

        #Initialize job ids that may contain issues
        self.jobid_corrupt = []
        self.scenid_corrupt = []

    def start(self, number_of_scenarios, time_to_sleep, sim_duration, sim_dir):
        """
        Method to start the simualtion
        """
        #launch the simulations based of the number of scenarios
        #TO DO: take in the arguments and the run file as input as well
        for n in range(number_of_scenarios):
            short_sbatch(scen_id=n + 1, sim_duration=sim_duration, sim_dir=sim_dir)
            time.sleep(time_to_sleep)

        _df_job = self.get_job_list()
        _start_checker = False
        #while _df is None or _df.shape[0] < number_of_scenarios:
        while not _start_checker:
            _df_job = self.get_job_list()
            if _df_job is not None:
                duration_vals = _df_job["duration"].values
                _start_checker = np.all(duration_vals > 0) and _df_job.shape[0] == number_of_scenarios
                #time.sleep(10) #Adding 5 seconds to monitor
            #print(f"start_checker: {_start_checker}, df shape: {_df_job.shape}")
        #Get the initial set of jobs
        self.df = self.get_job_list()
        self.df.sort_values(by=["JOBID"], ascending=True, inplace=True)
        self.df_init = self.df.copy() if self.df is not None else None #keep a copy of the initial jobs
        print(f"All simulations have started now...")
        #set start sim to be true
        self.sim_start = True
        return None

    def get_job_list(self):
        output = subprocess.check_output(f"squeue -u {self.user_id}", shell=True)
        header = None
        data_list = []
        for row in output.decode("utf8").split('\n'):
            if header is None:
                header = row.strip().split()
            elif row:
                data_list.append(row.strip().split())
        df = pd.DataFrame(data_list, columns=header) if data_list else None
        if df is not None:
            df["duration"] = df["TIME"].map(convert_str_to_duration)
            df["JOBID"] = df["JOBID"].astype(int)
        return df

    def timeout(self):
        try:
            assert self.df is not None
        except:
            raise Exception("No jobs currently in queue")

        job_ids  = self.df["JOBID"].values #get all the job ids
        print(f"Checking for timeout...")
        while np.any(job_ids) and self.df is not None:
            df_timeout = self.df.loc[self.df["duration"] > self.timeout_thresh]
            #get the selected job ids
            job_ids_timeout = df_timeout["JOBID"].values
            if np.any(job_ids_timeout):
                for n, id in enumerate(job_ids_timeout): #Cancel and append to list
                    subprocess.call(f"scancel {id}", shell=True)
                    print(f"scancel {id}")
                    self.jobid_corrupt.append(id)
                    self.scenid_corrupt.append(n+1)
                    time.sleep(5)
            #update df and job_ids
            self.df = self.get_job_list()
            job_ids = self.df["JOBID"].values if self.df is not None else np.asarray([])  # empty array if all jobs compeleted
        self.sim_done = True
        return None

    def check_early_terminate(
            self,
            list_of_scenario_dir,
            csv_name,
            dim_to_check="col",
            metrics=None
    ):

        """
        This method is used to identify the cases where the optimizer terminated early
        :param list_of_scenario_dir (str) - list of directories corresponding to scenarios (must be in order)
        :param csv_name (str) - csv used to validate the shape
        :param dim_to_check (str) - indicates whether the validating dimension is column or row. If
        """
        assert self.sim_done is True
        assert dim_to_check in ["row", "col"]
        idx = {
            "row": 0,
            "col": 1
        }[dim_to_check]

        _max_shape = None
        _list_of_shapes = []
        #_list_of_scen_issues = [] #list of scenarios with issues
        #Loop over all directories and read the csv
        for i, dir in enumerate(list_of_scenario_dir):
            path_to_csv = os.path.join(dir, csv_name)
            _df = pd.read_csv(path_to_csv)
            _list_of_shapes.append(_df.shape[idx])
            _max_shape = _df.shape[idx] if (_max_shape is None or _df.shape[idx] >= _max_shape) else _max_shape

        for i in range(len(list_of_scenario_dir)):
            if _max_shape is not None and _list_of_shapes[i] < _max_shape:
                self.scenid_corrupt.append(i+1)
                #_list_of_scen_issues.append(i+1)

        #Format scenid_corrupt to remove duplicate entries
        self.scenid_corrupt = np.unique(np.array(self.scenid_corrupt)).tolist()

        print(f"Max shape: {_max_shape}")
        #Adjust the metrics arrays if provided in arguments
        out_metrics = dict()
        if metrics is not None:
            for key, vals in metrics.items():
                max_cost = np.max(np.asarray(vals))
                print(f"key: {key}, max score{max_cost}")
                print(f"scenid: {self.scenid_corrupt}")
                out_vals = vals.copy()
                if any(self.scenid_corrupt):
                    for id in self.scenid_corrupt:
                        out_vals[id-1] = max_cost
                out_metrics[key] = out_vals
        return out_metrics




def simulator(
        csv_file="/qfs/projects/scoredec/codesign_metrics_par/sim_params/sim_params.csv",
        sim_dir="/qfs/projects/scoredec/codesign_metrics_par",
        sim_duration=1440,
        bat_wt=100.0,
        bat_multiplier=1.0,
        pred_horizon=15,
        sample_intv=15,
        k_inv=1.0,
        k_Q=1.0,
        k_P=1.0,
        k_VB=1.0,
        k_gen=1.0,
        pic_username="vasi412"
     
):
    """
    wrapper to run the bash.sh file for BO Optimizer
    :param attack_mag_vector: (np.array or list) - list of attack magnitudes. Length of list corresponds to the number of adversarial scenarios
    :param start_time_vector: (np.array or list) - list of start times (in hours).  Length of list corresponds to the number of adversarial scenarios
    :param duration_vector: (np.array or list) - list of attack duration (in hours). Length of duration must amtch number of adversarial scenarios
    :param sim_dir: (str) - simulation directory (that contains run.sh)
    :param sim_duration: (int) - the total time period for simulation (in minutes).
    :param bat_wt: (float) - Battery weight, one of the design variables to be optimzied by BO
    :param bat_multiplier: (float) - Multiplier for vb_SOC. One of the design variables for BO
    :param pic_username: (str) - Username for Constance. Used to stop sbatch script
    :param k_inv: (float) - multiplier for inverter limit used as constraint. k_inv \in [0, 2]
    :param k_Q: (float) - multiplier for Q_limit used in optimization. k_Q \in [0, 1]
    :param k_P: (float) - multiplier for P_limit used in optimization. k_P \in [0, 1]
    :param k_VB: (float) - multiplier for VB_KW k_VB \in [0, 1]
    :param k_gen: (float) - multiiplier for k_gen in [0, 1]
    :return:
    """

    #we should not have these many arguments
    #run.sh -> runner
    #design_params ->
    #scenarios -> functionality to add scenarios if needed
    #message passing to run.sh instead of writing to files

    #move "sbatch command" to SlurmManager
    #option to select environment --> right now only slurm is supported
    #factor out simulator function to a simulator class in a separate file

    econ_performance = []
    load_curtail = []
    
    bo_params = {
        "bat_wt": bat_wt,
        "bat_factor": bat_multiplier,
        "pred_horizon": pred_horizon,
        "sample_intv": sample_intv,
        "k_intv": k_inv,
        "k_Q": k_Q,
        "k_P": k_P,
        "k_VB": k_VB,
        "k_gen": k_gen
    }
    

    df = update_csv(
        csv_file=csv_file,
        bo_params=bo_params
    )
    #save to csv
    number_of_scenarios = df.shape[0] #change this back
    #number_of_scenarios = 3
    for n in range(number_of_scenarios):
        out_dir=os.path.join("/qfs/projects/scoredec/codesign_metrics_par/gridlabd/", "scen_{}".format(n+1))
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

    #Instantiate SlurmManager
    sim_duration = df.sim_duration.values[0]
    TestSimManager = SlurmManager(timeout_thresh=2.00)
    TestSimManager.start(
        number_of_scenarios=number_of_scenarios,
        sim_duration=sim_duration,
        time_to_sleep=5,
        sim_dir=sim_dir
    )
    TestSimManager.timeout()


    # check_sim = []
    # for n in range(number_of_scenarios):
    #     print("Waiting for scenario {}...".format(n+1))
    #     _, sim_bool = terminate(
    #         sim_dir=sim_dir,
    #         finish_str="Simulation Complete",
    #         scen_id=n+1,
    #         username=pic_username
    #     )
    #     check_sim.append(sim_bool)

    ##gather data from output files
    #print(f"check sim: {check_sim}")
    #if np.all(np.asarray(check_sim)):
    for n in range(number_of_scenarios):
        out_dir = os.path.join(sim_dir, "python/output_{}".format(n+1))
        ActiveResObj = ActiveResiliency(out_dir)
        metrics = ActiveResObj.active_metrics
        econ_performance.append(metrics["econ_performance"])
        load_curtail.append(metrics["load_curtailment"])

    metrics_dict = {
        "econ_performance": econ_performance,
        "load_curtail": load_curtail
    }

    #Finalize check
    scenario_dirs = sorted(glob.glob("/qfs/projects/scoredec/codesign_metrics_par/python/output_*"),
                            key=lambda x: int(x.split("_")[-1])) #[:3]#
    # scenario_dirs = sorted(glob.glob("/qfs/projects/scoredec/bo_implementation/results/bo_ts_0/output_*"),
    #                        key=lambda x: int(x.split("_")[-1])) [:3]#
    out_dict = TestSimManager.check_early_terminate(
        list_of_scenario_dir=scenario_dirs,
        csv_name="battP_record.csv",
        metrics=metrics_dict
    )
    print(f"metrics: {metrics_dict}\n")
    print(f"output dict: {out_dict}")

    return out_dict["econ_performance"], out_dict["load_curtail"]

def update_csv(
    csv_file,
    bo_params
):
    """
    Function to update 
    """
    df = pd.read_csv(csv_file)
    ones_vector = np.ones(df.shape[0], )

    for key, val in bo_params.items():
        #assert key in df.columns
        df[key] = val*ones_vector
    df.to_csv(csv_file, index=False)
    return df

#add helper function to allow conversion to durations
def convert_str_to_duration(date_str):
    if date_str.count(":") == 1:
        mins, secs = date_str.split(":")[0], date_str.split(":")[-1]
        duration = float(mins)/60.0 + float(secs)/3600.0
    elif date_str.count(":") == 2:
        hrs, mins, secs = date_str.split(":")[0], date_str.split(":")[1], date_str.split(":")[2]
        duration = float(hrs) + float(mins)/60.0 + float(secs)/3600.0
    else:
        duration = None
    return duration
###function to parallelize
def parallel_run(
    sim_dir,
    attack_magnitude,
    sim_duration,
    start_time,
    attack_duration,
    dur_time,
    bat_wt,
    bat_multiplier,
    pred_horizon,
    sample_intv,
    k_inv,
    k_Q,
    k_P,
    k_VB,
    k_gen,
    scen_id,
    username="rahm312"

):

    start_time = start_time
    attack_duration = duration_vector[n]
    out_dir=os.path.join("/qfs/projects/scoredec/codesign_metrics_par/gridlabd/", "scen_{}".format(scen_id))

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)


    print("Starting run .. ")
    run_sbatch(
        sim_dir=sim_dir,
        attack_magnitude=attack_magnitude,
        sim_duration=sim_duration,
        start_time=start_time,
        dur_time=dur_time,
        bat_wt=bat_wt,
        bat_multiplier=bat_multiplier,
        pred_horzion=pred_horizon,
        sample_intv=sample_intv,
        k_inv=k_inv,
        k_Q=k_Q,
        k_P=k_P,
        k_VB=k_VB,
        k_gen=k_gen,
        scen_id=scen_id,
        username=username
    )

    ActiveResObj = ActiveResiliency(sim_dir)
    metrics = ActiveResObj.active_metrics
    print("Metrics: {}".format(metrics))
    econ_performance.append(metrics["econ_performance"])
    load_curtail.append(metrics["load_curtailment"])



    return None


if __name__ == "__main__":
    # attack_mag_vector = [0.8, 0.1, 0.3, 0.5, 0.8] #two extreme scenarios
    # start_time_vector = [7, 2, 5, 3, 8]

    # duration_vector = [12, 24, 10, 11, 12]
    #scenario 4 tryout
    sim_dir = "/qfs/projects/scoredec/codesign_metrics_par"
    sim_duration = 24*60
    bat_wt = 100.0
    bat_multiplier = 1.75
    
    #adding new variables
    pred_horizon= 5
    sample_intv = 5

    #design variables
    k_inv = 0.6778
    k_Q = 1.0
    k_P = 1.0
    k_VB = 0.40
    k_gen = 0.60

    username = "rahm312"

    simulator(
        sim_dir=sim_dir,
        bat_wt=bat_wt,
        bat_multiplier=bat_multiplier,
        pred_horizon=pred_horizon,
        sample_intv=sample_intv,
        k_inv=k_inv,
        k_Q=k_Q,
        k_P=k_P,
        k_VB=k_VB,
        k_gen=k_gen,
        pic_username=username
    )

    #get all the scenarios sorted
    # scenario_dirs = sorted(glob.glob("/qfs/projects/scoredec/bo_implementation/results/bo_ts_0/output_*"), key=lambda x: int(x.split("_")[-1]))
    # TestSimManager = SlurmManager(timeout_thresh=10.00)
    # bad_ids = TestSimManager.check_early_terminate(
    #     list_of_scenario_dir=scenario_dirs,
    #     csv_name="battP_record.csv"
    # )
    #print(f"bad ids: {bad_ids}")

