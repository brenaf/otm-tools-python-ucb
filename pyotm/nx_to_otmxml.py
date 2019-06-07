from itertools import product
import networkx as nx
import numpy as np
from collections import OrderedDict

from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom

def pretty_tostring(xml_data):
    xml_data = xml.dom.minidom.parseString(tostring(xml_data))
    xml_pretty_str = xml_data.toprettyxml(indent="  ")
    return xml_pretty_str


graph = nx.DiGraph()

link_list = [
    # South-east flow
    [0, 1], [1, 2], [2, 3], [4, 5], [5, 6], [6, 7], [8, 9], [9, 10], [10, 11], [0, 4], [1, 5], [2, 6], [3, 7], [4, 8], [5, 9], [6, 10], [7, 11],
    # North-west flow
    [2, 1], [5, 4], [6, 5], [7, 6], [10, 9], [4, 0], [5, 1], [6, 2], [7, 3], [8, 4], [9, 5], [10, 6], [11, 7],
    # Ingress links
    [12, 13], [13, 0], [14, 15], [15, 8],
    # Egress links
    [3, 16], [16, 17], [11, 18], [18, 19],
]

link_id_list = [[*link_pair, {"link_id": link_id, "subnetwork_id": 1}] for link_id, link_pair in enumerate(link_list)]
graph.add_edges_from(link_id_list)

## Inject road connection data
rc_id = 0
for node in graph.nodes:
    in_set = graph.in_edges(node)
    out_set = graph.out_edges(node)
    rc_set = []
    if (len(in_set) > 0) and (len(out_set) > 0):
        # Perform link product across nodes but remove u-turns,
        # i.e. links that map to the reverse direction
        node_rcs = [lkpair for lkpair in list(product(in_set, out_set)) if lkpair[0] != lkpair[1][::-1]]
        for i in node_rcs:
            rc_set += [{
                'rc_id': rc_id,
                'link_id_pair': [graph.get_edge_data(*i[0])['link_id'],
                                 graph.get_edge_data(*i[1])['link_id']]
            }]
            rc_id += 1
    graph.nodes[node]['node_rcs'] = rc_set



## Inject split data
for node in graph.nodes:
    in_set = graph.in_edges(node)
    out_set = graph.out_edges(node)
    splits_set = []
    if (len(in_set) > 0) and (len(out_set) > 0):
        for enter_pair in in_set:
            enter_link_id = graph.get_edge_data(*enter_pair)['link_id'] 
            exit_link_ids = [graph.get_edge_data(*i)['link_id'] for i in out_set if enter_pair != i[::-1]]
            
            # Exclude guaranteed flow RCs
            if len(exit_link_ids) >= 1:
                splits_set.append({
                    "link_in": enter_link_id,
                    "link_out": exit_link_ids,
                    # Default: uniform probability per exit link.
                    # Adjust manually on XML if necessary.
                    "split_ratio": (np.ones(len(exit_link_ids))/np.ones(len(exit_link_ids)).sum()).tolist()
                })

    graph.nodes[node]['splits_set'] = splits_set


# Base XML data
scenario = Element("scenario")
network = SubElement(scenario, "network")

# Generate node list
node_set = SubElement(network, "nodes")
for node in graph.nodes:
    node_id = SubElement(node_set, "node", {"id": str(node)})

# Generate edge list
link_set = SubElement(network, "links")
sorted_links = sorted([[graph.edges[i]['link_id'], i, graph.edges[i]] for i in graph.edges], key=lambda x: x[0])
for link_id, node_pair, link_attr in sorted_links:
    edge_id = SubElement(link_set, "link", {
        "id": str(link_id), "length": str(100.0),
        "full_lanes": str(4), "start_node_id": str(node_pair[0]),
        "end_node_id": str(node_pair[1]), "roadparam": "0"
    })

# Generate RC list 
roadconnections = SubElement(network, "roadconnections")
for node in graph.nodes:
    for rc_data in graph.nodes[node]['node_rcs']:
        rc = SubElement(roadconnections, "roadconnection", {
            "id": str(rc_data['rc_id']),
            "in_link": str(rc_data['link_id_pair'][0]),
            "out_link": str(rc_data['link_id_pair'][1]),
            "in_link_lanes": "1#1",
            "out_link_lanes": "1#1"
        })
        
roadparams = SubElement(network, "roadparams")
roadparam = SubElement(roadparams, "roadparam", {
    "id": "0", "name": "link type 0", "speed": str(20.0), "capacity": str(2500), "jam_density": str(608.3333)
})


## SPLITS DATA

splits = SubElement(scenario, "splits")
for node in graph.nodes:
    for split_data in graph.nodes[node]['splits_set']:
        split_node = SubElement(splits, "split_node", {
            "node_id": str(node), "commodity_id": str(0), "link_in": str(split_data['link_in'])
        })
#         print(list(zip(split_data['link_out'], split_data['split_ratio'])))
        for link_out, ratio in zip(split_data['link_out'], split_data['split_ratio']):
            split = SubElement(split_node, "split", {"link_out": str(link_out) })
            split.text = str(ratio)

            
# SUBNETWORK DATA
subnetworks = SubElement(scenario, "subnetworks")
# zip all edge ids to their respective subnetwork ids
subnet_pairs = [(graph.edges[edge]['link_id'],graph.edges[edge]['subnetwork_id']) for edge in graph.edges]
distinct_subnets = set(list(zip(*subnet_pairs))[1])

for subnet_id in distinct_subnets:
    subnet_links = sorted([i[0] for i in subnet_pairs if i[1] == subnet_id])
    subnetwork = SubElement(subnetworks, "subnetwork", {"id": str(subnet_id)})
    subnetwork.text = ",".join([str(i) for i in subnet_links])

    
# SENSOR DATA
sensors = SubElement(scenario, "sensors")
for edge in graph.edges:
    edge_attr = graph.edges[edge]
    sensor = SubElement(sensors, "sensor", {
        "id": str(edge_attr['link_id']), "type": "fixed", "dt": "2", "link_id": str(edge_attr['link_id'])
    })


# AUXILLIARY DATA

plugins = SubElement(scenario, "plugins")
plugin = SubElement(plugins, "plugin", {
    "name": "linkpressure", "folder": "", "class": "ControllerSignalPretimedInternal"
})

models = SubElement(scenario, "models")
model = SubElement(models, "model", {
    "type": "point_queue", "name": "my_model", "is_default": "true"
})
model_params = SubElement(model, "model_params", {
    "max_cell_length": "20", "sim_dt": "2"
})

commodities = SubElement(scenario, "commodities")
commodity = SubElement(commodities, "commodity", {"id": "0", "name": "car", "subnetworks": "1"})

demands = SubElement(scenario, "demands")
for source_link_id in [30, 32]:
    demand = SubElement(demands, "demand", {
        "commodity_id": "0", "subnetwork": "1", "start_time": "0", "link_id": str(source_link_id), "dt": "28000"
    })
    demand.text = ",".join([str(i) for i in [600]])


controllers = SubElement(scenario, "controllers")
controller = SubElement(controllers, "controller", {"id": "0", "type": "linkpressure", "dt": "2.0"})

feedback_sensors = SubElement(controller, "feedback_sensors")
for edge in graph.edges:
    edge_id = graph.edges[edge]['link_id']
    SubElement(feedback_sensors, "feedback_sensor", {"id": str(edge_id), "usage": str(edge_id)})

target_actuators = SubElement(controller, "target_actuators")
for actuator_id in [0, 1]:
    target_actuator = SubElement(target_actuators, "target_actuator", {
        "id": str(actuator_id), "usage": str(actuator_id)
    })

with open("otm_netgen.xml", "wt") as xml_file:
    xml_file.write(pretty_tostring(scenario))
