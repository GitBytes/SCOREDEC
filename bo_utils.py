"""
Created on Sat Jun 27 16:44:18 2020
@author: Arnab Bhattacharya

This script contains the functions used during the BO runs. This includes
functions to import and preprocess data, interface with the emulator, 
initialize and run BO models, and save results and plots. 
"""

# import Python libraries
import json
import pandas as pd
import numpy as np
import shutil
import os
from multiprocessing import Process, Manager
from slurm import SlurmManager


def import_params(file):
    """
    Return the user-defined parameters related to Bayesopt algorithm, 
    optimization model, chiller candidates, and design days from a json file.
    
    :param file: name and location of the json file, default is './data/params.json'
    :return: A tuple of the following variables
             (i) boP => dictionary containing Bayesopt algorithm params
             (ii) chP => dictionary containg chiller candidate information
             (iii) optP => dictionary containing params related to optimization model
             (iv) designDays => list of design dates for the simulation           
    """
    
    # import data from json params file
    with open(file) as f:
        data = json.load(f)
        
    # use seperate dictionaries to store the params 
    boP = data["bo"]              # bayes-opt params
    chP = data["chiller"]         # chiller params
    optP = data["opt"]            # optimization model params 
    
    # store params related to design days
    temp = data["designDays"]          
    
    # check flag value to see if all or a subset of the design days are used
    if temp["flag"] == 1:              
        # if flag = 1, import all the design days from a csv file
        file = temp["filename"]       
        designDays = pd.read_csv(file)['day'].to_list()  # list of days
    else:
        # else use the smaller list of design days 
        designDays = temp["testDays"]                    # list of days
    
    return boP, chP, optP, designDays


def get_chillers(capacities):
    df = pd.read_csv('./trane_chillers.csv')
    chillers = []
    caps = []
    for cap in capacities:
        # Pick the chiller with the first largest capacity
        chiller_row = df.iloc[np.argmax(df['Capacity_kwh'] > cap)]
        chillers.append(chiller_row['Name'])
        caps.append(chiller_row['Capacity_kwh'])
    
    return chillers, caps


#def prepare_inputs(x):



def save_results(df):

    result_file = "results/bo_results.csv"
    eval_idx = df['eval_idx'].unique().item()

    sim_output_dir = f"results/ts_{eval_idx}"

    if eval_idx > 1:
        res_df = pd.read_csv(result_file)
        df = pd.concat([res_df, df], ignore_index=True)

    df.to_csv(result_file, index=False)

    shutil.copytree("output_dir", sim_output_dir)


def get_capacities(chP):
    """
    Return the list of candidate chiller capacities (and associated names and 
    other chiller characteristics such as COP) for given chiller type.
    
    :param chP: parameters related to chiller type/class (dictionary)
    :return df: table of unique chiller names, caps, and COPs (dataframe)
    """
    
    # import chiller data
    df = pd.read_csv(chP["filename"], index_col=False)
    
    # rename a few relevant columns for programming ease
    df.rename(columns={df.columns[0]:'name',
                       df.columns[2]:'cap',
                       df.columns[4]:'cop'}, inplace=True)
    
    # condition 1: select all rows (case-insenstive) containing specified chiller company name (e.g. Trane or Carrier) 
    # c1 = df['name'].str.lower().str.contains(chP['class']['name'].lower()) 
    
    # condition 2: select all rows (case-insenstive) containing specified chiller version (e.g. "23XL" for Carrier chillers) 
    # c2 = df['name'].str.lower().str.contains(chP['class']['version'].lower())
    
    # condition 3: select all rows (case-insenstive) containing specified chiller type (e.g. centrifugal or screw) 
    # c3 = df['type'].str.lower().str.contains(chP['class']['type'].lower())
    
    # select all rows that satisifies condition 1, 2 and 3 together
    # df = df[c1 & c2 & c3]

    # df = df[c1]

    # remove duplicate capacities using the following two steps:
    # step 1: sort by COP values in ascending order
    df.sort_values(by='cop', ascending=True, inplace=True)
    # step 2: drop duplicate capacities and retain one with highest COP 
    df.drop_duplicates(subset='cap', keep='last',inplace=True)
    
    # remove duplicate occurence of chiller names, if any
    if df['name'].duplicated().any():
        df.drop_duplicates(subset='name', keep='last',inplace=True)
        
    # select specific combination of chiller sizes
    # first check if there is less than 3 chiller candidates or if all capacities are selected as candidates
    if (df.shape[0] <= 2) | (chP["select_ch"]["num"] == "all"):
        # do nothing
        pass
    elif df.shape[0] > 2:                   # if 3 or more chiller candidates exist
        temp = chP["select_ch"]    
        if temp["num"] == "2":              # if 2 chillers are to be selected
            if temp["size2ch"] == "01":     # "01" refers to max and min size chillers in the group
                df = df[(df['cap'] == df['cap'].min()) | (df['cap'] == df['cap'].max())]
            elif temp["size2ch"] == "00":   # "00" refers to 2 smallest sized chillers in the group
                df = df.nsmallest(2, 'cap')
            else:                           # case "11" that refers to 2 largest sized chillers in the group 
                df = df.nlargest(2, 'cap')
        elif temp["num"] == "3":            # if 3 chillers are to be selected  
            # will add additional code her (if required) for 3 candidate chillers
            pass 
        else:
            pass
    else:
        pass
    
    return df 
    

def get_domain_general(n, optP, caps):
    """
    Return the domain of decision parameters for the most general case when
    capacities are heterogenous.
    
    :param n: number of chillers (integer)
    :param optP: params related to optimization model (dictionary)
    :param caps: list of candidate capacities (1D numpy array)
    :return domain: dictionary containing domain of all decision variables
    """ 

    # mixed-type domain for discrete capacities and continuous thresholds                                
    domain = [{
                'name': 'capacities',
                'type': 'discrete',
                'domain': caps, 
                'dimensionality':n
               },
                {
                'name': 'thresholds',
                'type': 'continuous', 
                'domain': (optP["minThreshold"],optP["maxThreshold"]), 
                'dimensionality': n}
              ]   
    return domain


# def get_domain(optP):
#
#     domain = [{
#                 'name': 'numChiller',
#                 'type': 'discrete',
#                 'domain': np.arange(optP["minChillers"],optP["maxChillers"]+1),
#                 'dimensionality':1
#                },
#                 {
#                 'name': 'threshold',
#                 'type': 'continuous',
#                 'domain': (optP["minThreshold"],optP["maxThreshold"]),
#                 'dimensionality': 1}
#               ]
#
#     return domain


def get_occupancy(day):
    occ = np.ones(1440)
    occ[:360] = 0
    occ[-360:] = 0

    return occ


def get_objective_weights(chP, days):
    """
    Return the objective weights for different days for each cost term in the 
    Bayes-Opt objective.
    
    :param chP: params related to chiller (dictionary)
    :param days: list of candidate design days:
    :return df: dataframe containing objective weights, with the following columns:
                'd': index column containing all design days
                'energy': column with weights for energy 
                'capcost': column with weights for capital cost
                'opcost': column with weights for operational costs
                'peak': column with weights for peak demand
    """
    # decide the keyword used to search file containing ground truth results
    if chP['class']['name'].lower() == 'carrier':
        keyword = 'Carrier_830'                    # default for Carrier chillers
    elif chP['class']['name'].lower() == 'trane':
        keyword = 'Trane_1442'                     # default for Trane chillers 
    else:
        keyword = 'Trane_1442'                     # default for other chillers
    
    
    # search for a csv file in the data folder that contains the keyword 
    for fname in os.listdir('./data'):
        if keyword.lower() in fname.lower():
            # print message that such a file has been found
            print("File \"{}\" has the keyword {}".format(fname, keyword))
            break
    
    # import grid-simulation data from the file as a dataframe
    df = pd.read_csv(os.path.join('./data/',fname))
    
    # change column names for ease of programming
    df.rename(columns= {
                        df.columns[0]:'d',           # day (index column by default)
                        df.columns[1]:'n',           # num of chillers  
                        df.columns[2]:'t',           # threshold    
                        df.columns[3]:'energy',      # energy 
                        df.columns[4]:'capcost',     # capital+operational cost
                        df.columns[5]:'peak',        # peak demand
                        }, inplace=True)
        
    # extract max values for each cost type (in each design day) and drop columns which are not needed
    df = df.groupby('d').max().drop(['n','t'], axis=1)
    
    # scale using corresponding cost magnitudes and invert them (this will be used as weights)
    df['energy'] = 1./(1e10*df['energy'])
    df['capcost'] = 1./(1e6*df['capcost'])
    df['opcost'] = df['capcost']                # assumption for now
    df['peak']   = 1./(1e5*df['peak'])
    
    # drop rows (days) with negative cost values (indicates errors or timeouts in emulator)
    df=df[df['energy']>0]
    
    # assign mean values to cost types for days that werent simulated 
    means = [df[col].mean() for col in df.columns]   # list of mean values
    for d in days:                                   # iterate over given design days
        if d not in df.index:                        # if day has not been previously simulated  
            df.loc[d] = means                        # add to dataframe with mean values 
                   
    return df


def initialize_bo_data():
    # initialize an empty dataframe to store data of interest
    df = pd.DataFrame(columns=['n', 't', 'cost', 'sim_time', 'num_days'])
    return df


def initialize_bo_data_general():
    """
    Return an empty dataframe that will store relevant data from each Bayes-opt
    evaluation.
    
    :return df: empty dataframe with relevant columns 
    """
    
    # relevant data points to record ('column name': description (data type))
    # local script variables: 
    #                        'n'            : current number of chillers (integer) 
    #                        'sim_time'     : total simulation time (float)
    #                        'sim_time_day' : simulation time per day (vector)  
    #                        'days'         : candidate design days (vector)
    #                        'wE_day'       : weight for energy term per day (vector)    
    #                        'wC_day'       : weight for capital cost term per day (vector)
    #                        'wO_day'       : weight for operational cost term per day (vector) 
    #                        'wP_day'       : weight for peak demand term per day (vector)  
    
    # Bayes-opt data points:
    #                       'c'   : candidate capacities (vector)
    #                       't'   : candidate thresholds (vector)
        
    # emulator cost points:
    #                       'energy_day'  : energy cost per day (vector)
    #                       'capcost_day' : chiller capital cost (vector)
    #                       'opcost_day'  : operational/running cost per day (vector)  
    #                       'peak_day'    : peak-demand per day (vector)
    

    # post-processed points:
    #                     'bayes_cost'       : weighted objective cost for BO (float)   
    #                     'energy'           : total energy over simulation (float)
    #                     'capcost'          : total capital cost incurred over the simulation (float) 
    #                     'opcost'           : total op cost over simulation (float)
    #                     'peak'             : peak-demand over simulation (float) 
    #                     'success_days'     : actual days where simulation was successful without issues (vector)
    #                     'num_success_days' : number of days where simulation was successful (integer)

    
    # define list of column names
    columns = ['n', 'sim_time', 'sim_time_day', 'days',
               'wE_day', 'wC_day', 'wO_day', 'wP_day',
               'c', 't',
               'energy_day', 'capcost_day', 'opcost_day', 'peak_day', 'tempDiff_day',
               'bayes_cost', 'energy', 'capcost', 'opcost', 'peak', 'tdcost',
               'success_days', 'num_success_days']
    
    # initialize empty dataframe with relevant columns
    df = pd.DataFrame(columns=columns)
    return df


def get_names_from_capacities(capacities, df):
    """
    Return the list of chiller names corresponding to a list capacities of 
    same chiller class.
    
    :param capacities : chiller capacities (list)
    :param df         : candidate info of chillers of a given class (dataframe)
    :return names     : chiller names (list)
    """
    # initialize list for storing chiller names
    names = ['_'] * len(capacities)
    
    # initialize index counter 
    idx = 0
    
    # iterate over given capacities 
    for c in capacities:
        #  store chiller name by checking for corresponding capacity
        names[idx] = df[df['cap'] == c]['name'].iloc[0]
        idx += 1

    return names


def get_true_name(chP):
    # split chiller type parameter into chiller company name and capacity (stored as list of strings)
    keywords= chP["type"].split('_')
    
    # import list of all actual chiller names from chiller data
    names = pd.read_csv(chP["filename"], index_col=False)['variable name'].to_list()   
    
    # iterate over chiller names
    for name in names:
        # check if each termstring in keywords appears in chiller name 
        if all(word in name for word in keywords):
            break       # if true, break and return this name            
       
    return name


def run_chiller(n, rs, caps, thr, st, et, timeout=200.0):
    """
    Return the output of a process encapsulating chiller simulation.
    
    :param n        : number of chillers (integer)
    :param rs       : runtime sort (boolean)
    :param caps     : chiller capacities (list of ints)
    :param thr      : chiller thresholds (list of floats)
    :param st       : starting time of simulation in seconds (float)
    :param et       : ending time of simulation in seconds (float)
    :param timeout  : timeout parameter of a process in seconds (integer)
    :return out     : output of process (a dictionary of results)
    :return out['error'] is either None, -1 (emulator errors) or -2 (Timing out)
    """
    mgr = Manager()
    out = mgr.dict() 
    
    # set error to -1 which will be reset to None if emulator succeeds
    out['error'] = -1

    p = Process(target=run_chiller_helper, args=(n, rs, caps, thr, st, et, out))
    p.start()
    p.join(timeout)
    
    if p.is_alive():
        print("Timing out ...")
        p.terminate()
        p.join()
        # set error to -2 to indicate timeout
        out['error'] = -2
    
    return out


# def run_chiller_helper(n, rs, caps, thr, st, et, out):
#     """
#     Return output from emulator.
#
#     :param n     : number of chillers (integer)
#     :param names : chiller types (list of strings)
#     :param t     : chiller thresholds (list of floats)
#     :param s     : starting time of simulation in seconds (float)
#     :param e     : ending time of simulation in seconds (float)
#     :param out   : output of process (dictionary)
#     """
#     res = {}
#     res = emulator.chiller(num_chiller=n, run_time_sort=rs, chillers=caps, thrhol=thr, statim=st, endtim=et)
#
#     # set error to None only if emulator returns correctly
#     if res:
#       out['error'] = None
#       out.update(res)
#
#
# def run_chiller_old(n, c, t, s, e, timeout=200.0):
#     """
#     Return the output of a process encapsulating chiller simulation.
#
#     :param n        : number of chillers (integer)
#     :param c        : chiller types (list of strings)
#     :param t        : chiller thresholds (list of floats)
#     :param s        : starting time of simulation in seconds (float)
#     :param e        : ending time of simulation in seconds (float)
#     :param timeout  : timeout parameter of a process in seconds (integer)
#     :return out[0]  : output of process (list of floats)
#     """
#     mgr = Manager()
#     out = mgr.dict()
#     out[0] = [-1, -1, -1]
#
#     p = Process(target=run_chiller_helper_old, args=(n, c, t, s, e, out))
#     p.start()
#     p.join(timeout)
#
#     if p.is_alive():
#         print("Timing out ...")
#         p.terminate()
#         p.join()
#         out[0] = [-2, -2, -2]
#
#     return out[0]
#
#
# def run_chiller_helper_old(n, c, t, s, e, out):
#     """
#     Return output from emulator.
#
#     :param n   : number of chillers (integer)
#     :param c   : chiller types (list of strings)
#     :param t   : chiller thresholds (list of floats)
#     :param s   : starting time of simulation in seconds (float)
#     :param e   : ending time of simulation in seconds (float)
#     :param out : output of process (list)
#     :return out[0]: emulator output (list)
#     """
#     res = emulator.chiller(num_chiller=n,chiller_type=c,thrhol=t,statim=s,endtim=e)
#     out[0] = res


def initialize_timeSeries_table(numChillers=2):
    """
    return an empty dataframe with appropriate column names to store time-series
    data from emulator.
    
    :return df: empty dataframe with assigned column names
    """
    # list of data points to store
    # bo_iter : counter for BO evaluation calls
    # error: indicator of whether an error happened
    # n: number of chillers
    # c: current candidate chiller capacities
    # t: current candidate thresholds
    # chillers: name of the current candidate chillers
    # start_day: starting day of the simulation
    # plr: part load ratios
    # load : cooling load
    # cop_ch{i}: cop of chiller i (i is index of chiller in list of chillers)
    # on_ch{i}: on/off status of chiller i (i is index of chiller in list of chillers)
    
    
    # inital set of column names
    cols = ['bo_iter', 'error', 'n', 'c', 't', 'chillers', 'day', 'timestamp', 'plr', 'load',
            'ahu_setpoint', 'ahu_t1', 'ahu_t2', 'ahu_t3', 'ahu_t4']
    
    # columns corresponding to COP for each chiller 
    c1 = ['cop_ch{}'.format(i+1) for i in range(numChillers)]
    
    # columns corresponding to on/off status of each chiller 
    c2 = ['on_ch{}'.format(i+1) for i in range(numChillers)]

    c3 = ['zone_t{}'.format(i+1) for i in range(12)]

    c4 = ['zone_ht{}'.format(i+1) for i in range(12)]

    c5 = ['zone_ct{}'.format(i+1) for i in range(12)]
   
    c6 = ['PCooTow{}'.format(i+1) for i in range(numChillers)]

    c7 = ['PCh{}'.format(i+1) for i in range(numChillers)]
    
    # final list of all column names
    cols += c1 + c2 + c3 + c4 + c5 + c6 + c7
    
    # initialize an empty dataframe with given column names
    df = pd.DataFrame(columns=cols)
    
    return df

    
def current_timeSeries(output,bo_iter,n,c,chillers,t,day,columns):
    """
    Return the current time-series data from the emulator as a dataframe.
    """
    
    # initialize an empty dataframe 
    df = pd.DataFrame(columns=columns)
    
#    # print message
#    print("the keys in output are:{}".format(output.keys()))
#    
#    print("Length of PLR list={}".format(len(output['PLR'])))
#    print("Length of chiller runtime list={}".format(len(output['running_time'])))
#    print("Length of load list={}".format(len(output['Load'])))
#    print("Length of time list={}".format(len(output['time'])))
#    print("Number of elements in cop list={}".format(len(output['cop'])))
#    print("# of rows in each array of cop list ={}".format(len(output['cop'][0])))
#    print("Number of elements in chiller on-off list={}".format(len(output['on'])))
#    print("# of rows in each array of on-off list={}".format(len(output['on'][0])))   
#    print("Length of ahu list={}".format(len(output['ahu_t'])))

    if output['error'] == None:         # simulation has successfully completed without timing out
        # set number of rows of df equal to number of data points in time-series data
        nRows = len(output['PLR'])           # output['PLR'] is a list
        # store all the time-series data
        df['bo_iter'] = [bo_iter] * nRows    # multiplied by nRows to create a list equal to number of time-series datapoints
        df['error'] = ["None"] * nRows
        df['n'] = [n] * nRows
        df['c'] = [c] * nRows
        df['chillers'] = [chillers] * nRows
        df['t'] = [t] * nRows
        df['day'] = [day] * nRows
        df['timestamp'] = output['time']
        df['plr'] = output['PLR']
        df['load'] = output['Load']

        df.loc[:,'ahu_t1'] = pd.Series(np.array([row[0] for row in output['ahu_t']]))
        df.loc[:,'ahu_t2'] = pd.Series(np.array([row[1] for row in output['ahu_t']]))
        df.loc[:,'ahu_t3'] = pd.Series(np.array([row[2] for row in output['ahu_t']]))
        df.loc[:,'ahu_t4'] = pd.Series(np.array([row[3] for row in output['ahu_t']]))

        df.loc[:,'ahu_setpoint'] = pd.Series(output['ahu_setpoint'])

        # iterate over number of zone temps (12)
        for i in range(12):
            zt = 'zone_t{}'.format(i+1)
            zht = 'zone_ht{}'.format(i+1)
            zct = 'zone_ct()'.format(i+1)
            
            df.loc[:,zt] = pd.Series(np.array([row[i] for row in output['zone_temp'] if row]))
            df.loc[:,zht] = pd.Series(np.array([row[i] for row in output['zone_temp_ht'] if row]))
            df.loc[:,zct] = pd.Series(np.array([row[i] for row in output['zone_temp_ct'] if row]))

        # iterative over the number of chillers
        for i in range(n):
            # cop value of chiller i
            c = 'cop_ch{}'.format(i+1)
            df[c] = output['cop'][i]
            # on/off status of chiller i
            c = 'on_ch{}'.format(i+1)
            df[c] = output['on'][i]

            # cooling tower power
            pc = 'PCooTow{}'.format(i+1)
            df[pc] = output['PCooTow'][i]

            # cooling tower power
            pch = 'PCh{}'.format(i+1)
            df[pch] = output['PCh'][i]

    else: # simulation wasnt successful and timed out
        # store dataframe with single row where the time-series outputs are set to np.nan
        df['bo_iter'] = [bo_iter] 
        df['error'] = [output['error']]
        df['n'] = [n]
        df['c'] = [c] 
        df['chillers'] = [chillers] 
        df['t'] = [t] 
        df['day'] = [day] 
        df['plr'] =  [np.nan]
        df['load'] = [np.nan]
        df['ah_t1'] = [np.nan]
        df['ah_t2'] = [np.nan]
        df['ah_t3'] = [np.nan]
        df['ah_t4'] = [np.nan]
        df['ahu_setpoint'] = [np.nan]
        for i in range(n):
            # cop value of chiller i
            c = 'cop_ch{}'.format(i+1)
            df[c] = [np.nan]
            # on/off status of chiller i
            c = 'on_ch{}'.format(i+1)
            df[c] = [np.nan]  
    return df


def save_bo_data(model, evals, chP, homedir, folder="results"):
    # path to the results folder
    path = os.path.join(homedir,folder)  
    
     # check if reults folder exists
    if not os.path.isdir(path):         
        os.mkdir(path)                   # if not, then create results folder   
        
    # rename index column as iteration
    evals.index.names = ['iter']   
    
    # store evaluations data
    evals.to_csv(os.path.join(path,"eval_"+chP["type"]+".csv"))   
    
    return


def save_bo_data_general(model, n, evals, chP, homedir, folder="results"):
    """
    Save recorded data of all evaluation calls in the BO loop as a csv file.
    
    :param model    : BO model (GPyOpt object)
    :param n        : number of chillers (integer)
    :param evals    : table containing all evaluations data (dataframe)
    :param chP      : chiller parameters (dictionary)
    :param homedir  : path to project's home directory (string)
    :param folder   : folder where evals file will be stored 
    :return None
    """
    # path to the results folder
    path = os.path.join(homedir,folder)
    
    # if results folder doesnt exist then create one 
    if not os.path.isdir(path):         
        os.mkdir(path)                  
        
    # rename index column in evals file as 'iteration'
    evals.index.names = ['iter']  
    
    # store evaluations data as a csv file
    evals.to_csv(os.path.join(path,'eval_'+'n='+str(n)\
                              +'_'+chP["class"]["name"]\
                              +'_'+chP["class"]["version"]\
                              +".csv"))
       
    return


def save_plots(model, chP, homedir, folder="results"):
    # path to the results folder
    path = os.path.join(homedir,folder) 
    
    #store acquisition and convergence plots
    model.plot_acquisition(filename=os.path.join(path,'acq_'+chP["type"]+'.png'),label_x = 'n',label_y = 't')
    model.plot_convergence(filename=os.path.join(path,'con_'+chP["type"]+'.png'))                     
    return


def save_plots_general(model, n, chP, homedir, folder="results"):
    """
    Save convergence plots for the BO loop.
    
    :param model   : BO model (GPyOpt object)
    :param n       : number of chillers (integer)
    :param chP     : chiller parameters (dictionary)
    :param homedir : path to project's home directory (string)
    :param folder  : folder where plots will be stored
    :return None
    """
    # path to the results folder
    path = os.path.join(homedir,folder) 
    
    # if results folder doesnt exist then create one 
    if not os.path.isdir(path):         
        os.mkdir(path) 
    
    #store convergence plot
    model.plot_convergence(filename=os.path.join(path,'con_'+'n='+str(n)\
                                                 +'_'+chP["class"]["name"]\
                                                 +'_'+chP["class"]["version"]\
                                                 +'.png'))
    return
       









