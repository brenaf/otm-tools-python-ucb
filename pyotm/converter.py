from itertools import product
import networkx as nx
import numpy as np
import osmnx as ox

from pyotm.preprocessing import add_speed_capacity
from pyotm.generator import extract_streets

from lxml.etree import Element, SubElement, tostring, ElementTree
import sys

bbox = {"north":14.6689, "south":14.6406, "east":121.0989, "west": 121.0480}

def generate_graph_from_bbox(north, south, east, west, **kwargs):

    custom_filter = kwargs.get("custom_filter", "['highway'~'primary|trunk|motorway|secondary|tertiary']")
    crs = kwargs.get("crs", {"init":"epsg:32651"})

    streets = extract_streets(bbox, crs=crs, custom_filter=custom_filter)
    n, e = ox.save_load.graph_to_gdfs(streets)
    node_id_map = dict(zip(n.index, range(len(n.index))))
    n = n.reset_index()
    n.gdf_name = "whatever"
    e.u = e.u.apply(lambda x: node_id_map[x])
    e.v = e.v.apply(lambda x: node_id_map[x])
    e['subnetwork_id'] = 1 ## hardcode only one subnetwork
    e["link_id"] = list(range(e.shape[0]))
    graph = ox.gdfs_to_graph(n, e)
    graph = add_speed_capacity(graph)


    ## Inject road connection data
    rc_id = 0
    for node in graph.nodes:
        in_set = graph.in_edges(node)
        out_set = graph.out_edges(node)
        rc_set = []
        if (len(in_set) > 0) and (len(out_set) > 0):
            # Perform link product across nodes but remove u-turns,
            # i.e. links that map to the reverse direction
            node_rcs = [lkpair for lkpair in list(product(in_set, out_set)) if ((lkpair[0] != lkpair[1][::-1]) and (lkpair[0] != lkpair[1]))]
            for i in node_rcs:
                rc_set += [{
                    'rc_id': rc_id,
                    'link_id_pair': [graph.get_edge_data(*i[0],0)['link_id'],
                                    graph.get_edge_data(*i[1],0)['link_id']],
                    'in_lanes': graph.get_edge_data(*i[0],0)['lanes'],
                    'out_lanes': graph.get_edge_data(*i[1],0)['lanes']
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
                enter_link_id = graph.get_edge_data(*enter_pair)[0]['link_id'] 
                exit_link_ids = set([graph.get_edge_data(*i)[0]['link_id'] for i in out_set if ((enter_pair != i[::-1]) and (enter_pair != i))])
                
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

    return graph

def generate_otm_xml(graph, output_file, with_controller=True):

    ## build roadparams
    ## TODO: graph operation should be in generate_graph_from_bbox
    rdparams = {}
    rdparam_id = 0
    for edge in graph.edges:
        edge_data = graph.get_edge_data(*edge)
        if (edge_data["capacity_lane_hour"], edge_data["speed"]) not in rdparams:
            rdparams[(edge_data["capacity_lane_hour"], edge_data["speed"])] = rdparam_id
            rdparam_id += 1
        graph.edges[edge]['rdparam_id'] = rdparams[(edge_data["capacity_lane_hour"], edge_data["speed"])]

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
            "id": str(link_id), "length": str(link_attr['length']),
            "full_lanes": str(link_attr['lanes']), "start_node_id": str(node_pair[0]),
            "end_node_id": str(node_pair[1]), "roadparam": str(link_attr['rdparam_id'])
        })

    # Generate RC list 
    roadconnections = SubElement(network, "roadconnections")
    for node in graph.nodes:
        for rc_data in graph.nodes[node]['node_rcs']:
            rc = SubElement(roadconnections, "roadconnection", {
                "id": str(rc_data['rc_id']),
                "in_link": str(rc_data['link_id_pair'][0]),
                "out_link": str(rc_data['link_id_pair'][1]),
                "in_link_lanes": "{0}#{0}".format(rc_data['in_lanes']),
                "out_link_lanes": "{0}#{0}".format(rc_data['out_lanes'])
            })
            
    roadparams = SubElement(network, "roadparams")

    for (capacity, speed), rdparam_id in rdparams.items():
        SubElement(roadparams, "roadparam", {
            "id": str(rdparam_id), "name": "link type {}".format(rdparam_id), "speed": str(speed), "capacity": str(capacity), "jam_density": str(5*capacity/speed)
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
    ## TODO: output from the OSM has nodes with in-degree 0 but out-degree > 1.
    ## Implementation currently ignores such links as source links, but vehicle
    ## traffic is expected on the boundaries. Either add phantom links that
    ## will inject traffic on the node or, preferably, duplicate the node by
    ## the out degree.
    for src, dst, data in graph.edges(data=True):
        # Look for edges whose source node has in-degree 0 and
        # out-degree 1, then tag the node as a source link
        if ((graph.in_degree(src) == 0) and (graph.out_degree(src) == 1)):
            demand = SubElement(demands, "demand", {
                "commodity_id": "0", "subnetwork": "1", "start_time": "0", "link_id": str(data['link_id']), "dt": "28000"
            })
            ## TODO: Demand profile should either be an argument of the 
            ## network generator, or a function of the link capacity.
            demand.text = ",".join([str(i) for i in [600]])


    if with_controller:
        # SENSOR DATA
        sensors = SubElement(scenario, "sensors")
        for edge in graph.edges:
            edge_attr = graph.edges[edge]
            sensor = SubElement(sensors, "sensor", {
                "id": str(edge_attr['link_id']), "type": "fixed", "dt": "2", "link_id": str(edge_attr['link_id'])
            })

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

    document = ElementTree(scenario)
    document.write(output_file, pretty_print=True)


if __name__ == "__main__":
    fname = sys.argv[1]
    graph = generate_graph_from_bbox(14.6689, 14.6406, 121.0989, 121.0480)
    generate_otm_xml(graph, "otm_netgen.xml", with_controller=False)