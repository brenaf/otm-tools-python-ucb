#!/usr/bin/env/python
from py4j.java_gateway import JavaGateway, launch_gateway, GatewayParameters
import matplotlib.pyplot as plt
import multiprocessing
import numpy as np
import time
import json
import sys
import os


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
        return {
            'link_veh': json.loads(self.entry_point.generateLinkVeh()),
            'link_flw': json.loads(self.entry_point.generateLinkFlow())
        }