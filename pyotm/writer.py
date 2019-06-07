import inspect  # SHOULD BE REMOVED
from igraph import read, OUT, IN
from lxml.etree import Element, SubElement, tostring, ElementTree
from shapely.wkt import loads
import itertools
import os
import numpy as np

# x0 = 290800
# y0 = 1621000
# x0 = 0
# y0 = 0
# LEFT = np.pi
# RIGHT = 0
# FORWARD = np.pi/2
# DOWN = 3/2*np.pi
DOWN = np.pi
FORWARD = 0
LEFT = np.pi/2
RIGHT = 3/2*np.pi
WEST = np.pi; EAST = 0; NORTH = np.pi/2; SOUTH = 3/2*np.pi


DIRECTIONS = {("NORTH", FORWARD): 0,
              ("SOUTH", FORWARD): 1,
              ("EAST", FORWARD): 2,
              ("WEST", FORWARD): 3,
              ("NORTH", LEFT): 4,
              ("NORTH", RIGHT): 5,
              ("SOUTH", LEFT): 6,
              ("SOUTH", RIGHT): 7,
              ("EAST", LEFT): 8,
              ("EAST", RIGHT): 9,
              ("WEST", LEFT): 10,
              ("WEST", RIGHT): 11
              }

phase_combos = {
    "ns": [0,1,5,7],
    "ew": [2,3,9,11],
    "left_ns": [4,6],
    "left_ew": [8,10] 
}


def what_turn(angle):
    dirs = np.array([LEFT, FORWARD, RIGHT])
    choices = np.abs(angle % (2*np.pi)-dirs)
    return dirs[np.argmin(choices)]


def num_in_link_lanes(num_lanes, num_left_lanes=1, num_right_lanes=1):
    if num_lanes == 1:
        num_left_lanes = 0
        num_right_lanes = 0
    # return {
    #     RIGHT: "%d#%d" % (num_lanes-num_right_lanes, num_lanes),
    #     LEFT: "%d#%d" % (1, 1+num_left_lanes),
    #     FORWARD: "%d#%d" % (1, num_lanes)
    # }
    return {
        RIGHT: "%d#%d" % (1, num_lanes),
        LEFT: "%d#%d" % (1, num_lanes),
        FORWARD: "%d#%d" % (1, num_lanes)
    }

def num_out_link_lanes(num_lanes, num_left_lanes=1, num_right_lanes=1):
    if num_lanes == 1:
        num_left_lanes = 0
        num_right_lanes = 0
    # return {
    #     RIGHT: "%d#%d" % (num_lanes-num_right_lanes, num_lanes),
    #     LEFT: "%d#%d" % (1, 1+num_left_lanes),
    #     FORWARD: "%d#%d" % (1, num_lanes)
    # }
    return {
        RIGHT: "%d#%d" % (1, num_lanes),
        LEFT: "%d#%d" % (1, num_lanes),
        FORWARD: "%d#%d" % (1, num_lanes)
    }

def csv2string(data):
    return ','.join(map(str, data))


class OTM_Model():
    def __init__(self, graph):
        self.scenario = Element("scenario")
        self.road_connection_map = {}
        self.graph = graph
        self.add_network(self.graph)

    def nodes2xml(self, nodes):
        xnodes = Element('nodes')
        for v in nodes:
            # if v.index in node_list:
            xnode = SubElement(xnodes, 'node', {
                'id': str(v.index),
                'x': str(float(v["x"])),
                'y': str(float(v["y"]))
            })
        return xnodes

    def links2xml(self, links, link_types):
        """Assumes `links` is a list of graphml edges"""
        xlinks = Element('links')
        for e in links:
            linkid = e.index
            xlink = Element('link')
            xlinks.append(xlink)
            xlink.set('id', str(linkid))
            # length in meters --- FIX THIS
            xlink.set('length', str(float(e['length'])))
            xlink.set('full_lanes', str(e['lanes']))  # number of lanes
            xlink.set('start_node_id', str(e.source))
            xlink.set('end_node_id', str(e.target))
            xlink.set('roadparam', str(
                link_types[(e["capacity_lane_hour"], e["speed"])]["id"]))
            geom_x, geom_y = loads(e['geometry']).xy
            if len(geom_x) > 2:
                points = Element('points')
                xlink.append(points)
                for x, y in zip(geom_x, geom_y):
                    point = Element('point')
                    point.set('x', str(x))
                    point.set('y', str(y))
                    points.append(point)
        return xlinks

    def add_network(self, graph):
        # network ---------------------
        xnetwork = Element('network')

        # nodes ........................
        xnetwork.append(self.nodes2xml(graph.vs))

        link_types = {(capacity, speed): {"capacity": capacity,
                                          "speed": speed,
                                          "name": "link type %d" % i,
                                          "id": i} for i, (capacity, speed) in
                      enumerate(list(set(zip(graph.es['capacity_lane_hour'], graph.es['speed']))))}
        # links .........................
        xnetwork.append(self.links2xml(links=graph.es, link_types=link_types))

        # road params .......................
        xnetwork.append(self.roadparams2xml(link_types))

        # road connections .......................

        # add only the road connections needed for the paths
        # create a map from node id to road connections in that node
        for edge_id, edge in enumerate(graph.es):
            target_node = edge.target
            source_node = edge.source
            edge_direction = float(edge['direction'])
            edge_lanes = int(edge["lanes"])
            # up_links = graph.incident(node_id, mode=IN)
            down_links = graph.incident(target_node, mode=OUT)
            in_link_lanes = num_in_link_lanes(edge_lanes)
            for link_id in down_links:
                link = graph.es[link_id]
                link_lanes = int(link["lanes"])
                if link.target == source_node:
                    continue
                link_direction = float(link['direction'])
                turn = what_turn(link_direction-edge_direction)
                out_link_lanes = num_out_link_lanes(link_lanes)
                connection_info = {"in_link": {"id": edge_id},
                                   "out_link":  {"id": link_id},
                                   "in_link_lanes": in_link_lanes[turn],
                                   "out_link_lanes": out_link_lanes[turn],
                                   "direction": edge_direction,
                                   "dir_txt": edge['dir_txt'],
                                   "turn": turn
                                   }

                self.road_connection_map[target_node] = self.road_connection_map.get(
                    target_node, {})
                node_map = self.road_connection_map[target_node]
                node_map[edge_id] = node_map.get(
                    edge_id, []) + [connection_info]

        # road connections to xml
        xnetwork.append(self.roadconnections2xml(self.road_connection_map))
        self.scenario.append(xnetwork)

    def roadconnections2xml(self, road_connection_map):
        c = -1
        self.phases = {}
        xroadconnections = Element('roadconnections')
        for node_id, in_links in road_connection_map.items():
            self.phases[node_id] = {}
            for in_link_id, tuple_list in in_links.items():
                for in_out_link in tuple_list:
                    c += 1
                    xroad_con = Element('roadconnection')
                    xroadconnections.append(xroad_con)
                    xroad_con.set('id', str(c))
                    xroad_con.set('in_link', str(in_out_link["in_link"]["id"]))
                    xroad_con.set('out_link', str(
                        in_out_link["out_link"]["id"]))
                    xroad_con.set('in_link_lanes',
                                  (in_out_link["in_link_lanes"]))
                    xroad_con.set('out_link_lanes',
                                  (in_out_link["out_link_lanes"]))
                    turn_direction = DIRECTIONS.get((in_out_link["dir_txt"], in_out_link["turn"]), None)
                    if turn_direction is not None:
                        self.phases[node_id][turn_direction] = c
        return xroadconnections

    def roadparams2xml(self, link_types):
        xroadparams = Element('roadparams')
        for info in link_types.values():
            xroadparam = Element('roadparam')
            xroadparams.append(xroadparam)
            xroadparam.set('id', str(info["id"]))
            xroadparam.set('name', info["name"])
            road_capacity = float(info["capacity"])
            road_speed = float(info["speed"])
            xroadparam.set('speed', str(road_speed))          # km/hr
            xroadparam.set('capacity', str(road_capacity))     # veh/hr/lane
            xroadparam.set('jam_density', str(
                road_capacity/road_speed*5))   # veh/km/lane
        return xroadparams

    def add_splits(self):
        xsplits = Element("splits")
        self.scenario.append(xsplits)
        for node_id, node in enumerate(graph.vs):
            up_links = graph.incident(node_id, mode=IN)
            down_links = graph.incident(node_id, mode=OUT)
            for up_link in up_links:
                if len(down_links) > 1:
                    xsplit_node = Element('split_node')
                    xsplit_node.set('node_id', str(node_id))
                    xsplit_node.set('commodity_id', '0')
                    xsplit_node.set('link_in', str(up_link))
                    for down_link in down_links:
                        xsplit = Element('split')
                        xsplit.set('link_out', str(down_link))
                        xsplit.text = str(1/len(down_links))
                        xsplit_node.append(xsplit)
                    xsplits.append(xsplit_node)

    def add_demands(self, source_node, demand_ts, demand_dt):
        links = self.graph.es
        nodes = self.graph.vs
        xsubnetworks = Element('subnetworks')
        xdemands = Element('demands')
        self.scenario.append(xsubnetworks)
        self.scenario.append(xdemands)
        xsubnetwork = Element('subnetwork')
        xsubnetworks.append(xsubnetwork)
        xsubnetwork.set('id', str(1))
        xsubnetwork.text = csv2string([e.index for e in links])

        xdemand = Element('demand')
        xdemands.append(xdemand)
        xdemand.set('commodity_id', "0")
        xdemand.set('subnetwork', str(1))
        xdemand.set('start_time', "0")
        xdemand.set('link_id', str(graph.incident(source_node, mode=OUT)[0]))
        xdemand.set('dt', str(demand_dt))
        xdemand.text = csv2string(demand_ts)

    def add_controllers(self):
        xactuators =  Element('actuators')
        self.scenario.append(xactuators)
        xsensors =  Element('sensors')
        self.scenario.append(xsensors)
        xcontrollers =  Element('controllers')
        self.scenario.append(xcontrollers)
        xcontroller = Element('controller')
        xcontrollers.append(xcontroller)

        xtarget_actuators = Element('target_actuators')
        xcontroller.append(xtarget_actuators)
        xfeedback_sensors = Element('feedback_sensors')
        xcontroller.append(xfeedback_sensors)
        xcontroller.set('id', str(0))
        xcontroller.set('type', 'linkpressure')
        xcontroller.set('dt', '10')
        #Acutators
        for actuator_id, (nodeid, _) in enumerate(self.phases.items()):
            # nodeid = node.index

            xactuator = Element('actuator')
            xactuators.append(xactuator)
            xactuator.set('id', str(actuator_id))
            xactuator.set('type', 'signal')
            # xactuator.set('dt', '30')
            xactuator_target = Element('actuator_target')
            xactuator.append(xactuator_target)
            xactuator_target.set('type','node')
            xactuator_target.set('id', str(nodeid))

            xsignal = Element('signal')
            xactuator.append(xsignal)
            for phase_id, (phase_name, rcs) in enumerate(phase_combos.items()):
                roadconns = [self.phases[nodeid].get(i, None) for i in rcs if self.phases[nodeid].get(i, None) is not None]
                if roadconns:
                    xphase = Element("phase")
                    xsignal.append(xphase)
                    xphase.set('id', str(phase_id))
                    xphase.set("yellow_time", "3")
                    xphase.set("red_clear_time", "2")
                    xphase.set("min_green_time", "5")
                    xphase.set("roadconnection_ids", csv2string(roadconns))
            xtarget_actuator = Element('target_actuator')
            xtarget_actuators.append(xtarget_actuator)
            xtarget_actuator.set('id', str(actuator_id))
            xtarget_actuator.set('usage', str(nodeid))

        #sensors
        for sensor_id, link in enumerate(graph.es):
            linkid = link.index
            xsensor = Element('sensor')
            xsensors.append(xsensor)
            xsensor.set('id', str(sensor_id))
            xsensor.set('type', 'fixed')
            xsensor.set('dt', '10')
            xsensor.set('link_id', str(linkid))
            xfeedback_sensor = Element('feedback_sensor')
            xfeedback_sensors.append(xfeedback_sensor)
            xfeedback_sensor.set('id', str(sensor_id))
            xfeedback_sensor.set('usage', str(sensor_id))

    def add_plugins(self):
        xplugins = Element('plugins')
        self.scenario.append(xplugins)
        xplugin = Element('plugin')
        xplugins.append(xplugin)
        xplugin.set('name', 'linkpressure')
        xplugin.set('folder', "/Users/acbalingit/Projects/otm/otm-plugin/target/otm-plugin-1.0-SNAPSHOT.jar")
        xplugin.set('class', 'controller.ControllerSignalPretimedTest')

    # def add_phases(self):
        
    def write(self, filename, pretty_print=True):
        # # MN model --------------------
        xmodels = Element('models')
        self.scenario.append(xmodels)
        xmodel = Element('model')
        xmodels.append(xmodel)
        xmodel.set("type", "ctm")
        xmodel.set("name", "myctm")
        xmodel.set("is_default", "true")
        xmn = Element('model_params')
        xmodel.append(xmn)
        xmn.set('max_cell_length', '100')  # m
        xmn.set('sim_dt', '2')  # m
        # xmn.text = csv2string([e.index for e in self.graph.es])

        # commodities ---------------------
        xcommodities = Element('commodities')
        self.scenario.append(xcommodities)
        xcommodity = Element('commodity')
        xcommodities.append(xcommodity)
        xcommodity.set('id', '0')
        xcommodity.set('name', 'car')
        xcommodity.set('subnetworks', '1')
        ElementTree(self.scenario).write(filename, pretty_print=pretty_print)


# write the scenario to an xml file
def write_to_xml(graph, all_paths=None, filename='updiliman_scenario.xml', pretty_print=True):

    xscenario = Element('scenario')
    xnetwork = network2xml(graph)
    xscenario.append(xnetwork)

    # # MN model --------------------
    xmodel = Element('model')
    xscenario.append(xmodel)
    xmn = Element('mn')
    xmodel.append(xmn)
    xmn.set('max_cell_length', '100')  # m
    xmn.text = csv2string([e.index for e in graph.es])

    # split_ratios
    if not all_paths:
        xsplits = Element("splits")
        xscenario.append(xsplits)
        for node_id, node in enumerate(graph.vs):
            up_links = graph.incident(node_id, mode=IN)
            down_links = graph.incident(node_id, mode=OUT)
            for up_link in up_links:
                if len(down_links) > 1:
                    xsplit_node = Element('split_node')
                    xsplit_node.set('node_id', str(node_id))
                    xsplit_node.set('commodity_id', '0')
                    xsplit_node.set('link_in', str(up_link))
                    for down_link in down_links:
                        xsplit = Element('split')
                        xsplit.set('link_out', str(down_link))
                        xsplit.text = str(1/len(down_links))
                        xsplit_node.append(xsplit)
                    xsplits.append(xsplit_node)

    # paths ---------------------
    # # demands ---------------------
    xsubnetworks, xdemands = paths2xml(all_paths, graph.es)
    xscenario.append(xsubnetworks)
    xscenario.append(xdemands)

    # commodities ---------------------
    xcommodities = Element('commodities')
    xscenario.append(xcommodities)
    xcommodity = Element('commodity')
    xcommodities.append(xcommodity)
    xcommodity.set('id', '0')
    xcommodity.set('name', 'car')

    xcommodity.set('pathfull', 'true' if all_paths else 'false')
    if all_paths:
        xcommodity.set('subnetworks', csv2string(
            range(len(xsubnetworks.getchildren()))))
    else:
        xcommodity.set('subnetworks', '0')

    # write to file ---------------------
    # this_folder = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    # configfile = os.path.join(this_folder, os.path.pardir, 'configfiles', filename)
    ElementTree(xscenario).write(filename, pretty_print=True)
    # with open(filename, 'wb') as f:
    #     f.write(tostring(xscenario, pretty_print=pretty_print))
    return xscenario


if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    graph = read(filename)
    # paths_xml = write_to_xml(graph, all_paths=None, filename=filename+'.xml', pretty_print=True)
    OTM = OTM_Model(graph)
    OTM.add_splits()
    demand_ts = [100, 6000]*20
    demand_dt = 600
    OTM.add_demands(graph.vs.find(_degree=1).index, demand_ts, demand_dt)
    OTM.add_controllers()
    OTM.add_plugins()
    OTM.write(filename+".xml")
    