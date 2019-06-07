#!/usr/bin/env/python
import matplotlib.pyplot as plt
import multiprocessing
import numpy as np
import sys

from pyotm.runner import OTMRunner

def runner_instance(arg):
    beats = OTMRunner(arg)
    output = beats.run()
    return output

def run_multiprocess(ntrials, procs=multiprocessing.cpu_count()):
    ## TODO: using multiprocessing is currently not friendly with
    ## the Java garbage collector (steadily increases with the
    ## number of runs done with the process).
    multiprocessing.set_start_method('spawn')
    with multiprocessing.Pool(10) as workpool:
        output_set = workpool.map(runner_instance, [sys.argv[1]] * 1024)
    return output_set


if __name__ == "__main__":
    # Single process
    beats = OTMRunner(sys.argv[1])
    output = beats.run()

    # Multiprocess
    # output_set = run_multiprocess(300)

    # for i in output['link_flw'].keys():
    #     output['link_flw'][i] = np.mean([k['link_flw'][i] for k in output_set], axis=0)

    # sum_list = []
    # for out in output_set:
    #     total_sum = np.sum(out['link_flw'][k][-1] for k in out['link_flw'])
    #     sum_list.append(total_sum)
    # plt.hist(sum_list, bins=25)

    for index,values in output['link_veh'].items():
        if 500 < np.sum(values) and (int(index) not in [24, 25]):# < 200:
            xvals = np.linspace(0, beats.simulation_time/60.0, len(values))
            plt.plot(xvals, values, label=f"Link {index}", linewidth=0.9, alpha=0.7)

    plt.legend()
    plt.title(f"OTM Simulation :: {sys.argv[1]}")
    plt.ylabel("Vehicles (Link)")
    plt.xlabel("Time (minutes)")
    # plt.ylim(0, 100)
    plt.savefig("output-dual.png", dpi=150)