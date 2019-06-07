#!/usr/bin/env/python
from py4j.java_gateway import JavaGateway, launch_gateway, GatewayParameters
import time
import json
import numpy as np
import sys
import os

import multiprocessing
import matplotlib.pyplot as plt

common_gateway = JavaGateway(gateway_parameters=GatewayParameters(
        port=launch_gateway(
            classpath=os.path.join(
                os.path.dirname(__file__),
                'data/otm-python-api-1.0-SNAPSHOT-jar-with-dependencies.jar'),
            die_on_exit=True, redirect_stdout=sys.stdout
        ), auto_field=True, auto_convert=True
    ))

class OTMRunner(object):
    def __init__(self, otm_xml, **kwargs):

        # self.java = common_gateway.jvm.java  # allow calling JDK
        self.entry_point = common_gateway.jvm.EntryPointOTM()
        self.api = self.entry_point.api

        self.simulation_time = float(kwargs.get('simulation_time', 2*7200.0))
        self.sample_dt = float(kwargs.get('sample_dt', 15.0))
        self.entry_point.api.load(otm_xml, True)
        # self.entry_point.api.set_stochastic_process("deterministic")
        # self.subnet_set = self.beats_api.get_subnetworks()

    def insert_schedule(self, actuator_id, schedule_list):
        self.api.insertActuatorSchedule(actuator_id, schedule_list)

    def run(self):
        self.entry_point.initRequests(self.sample_dt)
        # Perform simulation
        timer = time.time()
        self.api.run(0.0, self.simulation_time)
        print("Running the model took: {:.3f}".format(time.time() - timer))
        output_dict = {
            'link_veh': json.loads(self.entry_point.generateLinkVeh()),
            'link_flw': json.loads(self.entry_point.generateLinkFlow())
        }
        common_gateway.jvm.System.gc()
        return output_dict

sched_dual = [60.0, 60.0]
sched_trio = [30.0, 30.0, 30.0]
# sched = [2000.0,2000.0,10.0,1000.0]


def multisim(input_xml, sched_dual, sched_trio):
    beats = OTMRunner(input_xml)
    # for targ in [7]:
        # emu: 5,5,5,5
        # longemu: 120,120,120,120
        # assy,: 20,20,80,80
        # beats.insert_schedule(targ, [200.0,10.0,10.0,10.0])
    beats.insert_schedule(4, sched_trio)
    beats.insert_schedule(5, sched_dual)
    output = beats.run()
    return output


def work(args):
    return multisim(*args)


if __name__ == "__main__":
    # Multi-threaded version
    inputfile_xml = sys.argv[1]
    multiprocessing.set_start_method('spawn')

    with multiprocessing.Pool(10) as workpool, \
         open("simulations_multiple.json", "wt") as output_file:

        runs = 64
        factors = np.arange(0.1, 0.9, 0.01)

        for factor in factors:
            # sched_dual = [factor * 120, (1 - factor) * 120.0 ]
            sched_trio = [600 * ((1-factor)/2), 600 * factor, 600 * ((1-factor)/2)]
            param_set = zip([inputfile_xml] * runs, [sched_dual] * runs, [sched_trio] * runs)
            output_set = workpool.map(work,param_set)

            links_list = output_set[0]['link_flw'].keys()
            
            param_val = {"paramval": factor}
            for i in links_list:
                # output['link_flw'][i] = np.mean([k['link_flw'][i] for k in output_set], axis=0)
                param_val[i] = np.mean([k['link_flw'][i] for k in output_set], axis=0).tolist()

            output_file.write(json.dumps(param_val) + "\n")
