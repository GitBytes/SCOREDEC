from turtle import update
import numpy as np
import pandas as pd
import json
import subprocess
import re
import os
import time
import glob

class SlurmManager:
    def __init__(
            self,
            instance_name,
            number_of_scenarios,
            max_active_nodes=None,
            sim_dir="/qfs/projects/scoredec/scoredec_sim/sbatch/out",
            account_id="rd2c",
            user_id="rahm312",
            logger=None,
            timeout_thresh=4.00,
            time_to_sleep=15
    ):
        """
        Class for managing active jobs and scanceling if needed
        :param instance_name: (str) - Name of container.
        :param number_of_scenarios: (int) - Number of scenarios for which
        :param user_id (str) - user id used in constance
        :param logger (str) - txt filename with full path for generating log file
        :param timeout_thresh (float) - maximum allowable time in hours before job is cancelled
        """
        #TO DO
        # [1] need to parse out the userids
        self.instance_name = instance_name
        self.number_of_scenarios = number_of_scenarios
        self.max_nodes = max_active_nodes if max_active_nodes is not None else number_of_scenarios
        self.sim_dir = sim_dir
        self.logger = logger
        self.account_id = account_id
        self.user_id = user_id
        self.timeout_thresh = timeout_thresh
        self.time_to_sleep = time_to_sleep

        #assign number of variables
        #define variables
        #initialize arrays
        self.job_scens = np.arange(1, self.number_of_scenarios + 1)
        self.job_ids = np.zeros_like(self.job_scens)
        self.sim_start = False #w
        self.sim_done = False

        #Initialize job ids that may contain issues
        self.jobid_corrupt = []
        self.scenid_corrupt = []
        self.jobid_et = [] #jobids for early terminate
        self.scenid_et = [] #scenids for early terminate


    def start(self):
        """
        Method to start the simualtion
        """
        _jobs_submitted = 0
        _last_idx = 0
        _available_nodes = self.max_nodes if self.max_nodes < self.number_of_scenarios else self.number_of_scenarios

        while _jobs_submitted < self.number_of_scenarios:
            if _available_nodes > 0:
                for n in range(_last_idx + 1, _last_idx + _available_nodes + 1):
                    _jobid = self.sbatch_command(n)
                    print(f"Submitted job for jobid {_jobid} for scenario {n}")
                    self.job_ids[n-1] = _jobid
                _jobs_submitted += _available_nodes
                _last_idx = _jobs_submitted
            #Update available nodes by checking the jobs in queue
            _df_job = self._get_job_list()
            _available_nodes = self.max_nodes - _df_job.shape[0]
        return None


    def sbatch_command(self, n):
        """
        Method to run sbatch correspodning to scenario n
        :param n: (int) - scenario id to run
        :returnn jobid: (int) - id of the job submitted
        """
        _filename = os.path.join(self.sim_dir, f"{self.instance_name}_{n}.sh")
        _cmd = f"sbatch {_filename}"
        print(_cmd)
        output = subprocess.run(_cmd, shell=True, stdout=subprocess.PIPE)
        assert len(output.stdout) > 0
        jobid = re.findall(r'\d+', str(output.stdout).split()[-1])[0]
        time.sleep(self.time_to_sleep)
        return jobid

    def _get_job_list(self):
        """
        Method to get all running and queued jobs
        """
        output = subprocess.check_output(f"squeue -A {self.account_id}", shell=True)
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

    def monitor(self):
        """
        Method to check status of job after all jobs have been submitted
        """
        #First check the status of all running jobs and if they're on timeout
        _df = self._get_job_list()
        if _df is not None:
            self.timeout(_df)

        #all the jobs should be completeed now. Check status of all the completed jobs
        self.check_status()
        #self.clean_up()
        return None

    def timeout(self, df):
        try:
            assert df is not None
        except:
            raise Exception("No jobs currently in queue")

        job_ids  = df["JOBID"].values  #get all the job ids
        print(f"Checking for timeout...")
        _t = self.timeout_thresh.split(":")
        _thresh_time = int(_t[0])*1+int(_t[1])*(1/60.0) +int(_t[2])/3600.0 #duration converted to hours
        while np.any(job_ids) and df is not None:
            df_timeout = df.loc[df["duration"] > _thresh_time]
            #get the selected job ids
            job_ids_timeout = df_timeout["JOBID"].values
            if np.any(job_ids_timeout):
                for n, id in enumerate(job_ids_timeout): #Cancel and append to list
                    subprocess.call(f"scancel {id}", shell=True)
                    print(f"scancel {id}")
                    self.jobid_corrupt.append(id)
                    self.scenid_corrupt.append(n+1)
                    time.sleep(self.time_to_sleep)
            #update df and job_ids
            df = self._get_job_list()
            job_ids = df["JOBID"].values if df is not None else np.asarray([])  # empty array if all jobs compeleted

            #Adding this to make sure we don't get the send/recv error
            time.sleep(10)
        self.sim_done = True
        return None

    def check_status(self):
        """
        Method to loop over all the job ids
        """
        for i, id in enumerate(self.job_ids):
            status, exit_code = self._get_sacct_innfo(id)
            print(f"status for scen {i+1} with jobid {id} is {status}. exit_code: {exit_code}")
            if exit_code != 0:
                self.jobid_et.append(id)
                self.scenid_et.append(i+1)
        if len(self.jobid_et) > 0:
            print(f"THe following scenarios failed: {self.scenid_et}")
        else:
            print(f"All scenarios have been completed!")
        return None

    def _get_sacct_innfo(self, job_id):
        """
        Method to check whether
        """
        _proc = subprocess.run(f"sacct -j {job_id}", shell=True, stdout=subprocess.PIPE)
        output = _proc.stdout
        header = None
        data_list = []
        completed_status = None
        exit_code = None
        for row in output.decode("utf8").split('\n'):
            if header is None:
                header = row.strip().split()
            elif row:
                data_list.append(row.strip().split())
        df = pd.DataFrame(data_list, columns=header) if data_list else None
        if df is not None:
            print(df.columns)
            df = df.loc[df["Account"]==self.account_id]
            df["JobID"] = df["JobID"].astype(int)
            df_job = df.loc[df["JobID"]==job_id]
            _completed_state = df_job["State"].values[0]
            _ec = df_job["ExitCode"].values[0]
            completed_status = True if _completed_state == "COMPLETED" else False
            exit_code = 0 if _ec == "0:0" else _ec
        return completed_status, exit_code

    def clean_up(self):
        """
        Method to remove all the slurm-*.out files
        """
        _slurm_outs = glob.glob(os.path.join(os.getcwd(), "slurm-*.out"))
        if len(_slurm_outs) > 0:
            for file in _slurm_outs:
                os.remove(file)
        return None



def convert_str_to_duration(date_str):
    """
    Function to change date_str to duration in hours
    :param date_str: (str) - datestamp in hours
    :param
    """
    if date_str.count(":") == 1:
        mins, secs = date_str.split(":")[0], date_str.split(":")[-1]
        duration = float(mins)/60.0 + float(secs)/3600.0
    elif date_str.count(":") == 2:
        hrs, mins, secs = date_str.split(":")[0], date_str.split(":")[1], date_str.split(":")[2]
        duration = float(hrs) + float(mins)/60.0 + float(secs)/3600.0
    else:
        duration = None
    return duration

if __name__ == "__main__":
    # sbatch_file = "/qfs/projects/scoredec/scoredec_sim/sbatch/out/sample_instance_1.sh"
    # output = subprocess.run(f"sbatch {sbatch_file}", shell=True, stdout=subprocess.PIPE)
    # jobid = re.findall(r'\d+', str(output.stdout).split()[-1])[0]
    # print(f"The jobid is {jobid}")

    args = {
        "instance_name": "chiller",
        "number_of_scenarios": 1,
        "max_active_nodes": 2,
        "timeout_thresh": 0.01
    }

    TestSlurm = SlurmManager(**args)
    TestSlurm.start()
    TestSlurm.monitor()
