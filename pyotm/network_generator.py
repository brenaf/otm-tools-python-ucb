import numpy as np
import networkx as nx
from shapely.geometry import LineString, Point
import osmnx as ox


def add_node(node_id, xpos, ypos):
    return (node_id, dict(id=str(node_id), x=xpos, y=ypos, geometry=Point(xpos, ypos)))


def add_source(G, node_id):
    anchor_node = G.nodes[node_id]
    x_anchor = anchor_node['x']-length/2
    y_anchor = anchor_node['y']-length/2
    new_id = len(G.nodes)
    G.add_node(new_id, **dict(id=str(new_id), x=x_anchor,
                              y=y_anchor, geometry=Point(x_anchor, y_anchor)))
    G.add_edge(new_id, node_id, **{'length': length*np.sqrt(2),
                                   'lanes': 1,
                                   'capacity_lane_hour': capacity,
                                   'speed': speed,
                                   'direction': np.pi/4,
                                   'geometry': LineString([(x_anchor, y_anchor), (anchor_node['x'], anchor_node['y'])])
                                   })


def add_sink(G, node_id):
    anchor_node = G.nodes[node_id]
    x_anchor = anchor_node['x']+length/2
    y_anchor = anchor_node['y']+length/2
    new_id = len(G.nodes)
    G.add_node(new_id, **dict(id=str(new_id), x=x_anchor,
                              y=y_anchor, geometry=Point(x_anchor, y_anchor)))
    G.add_edge(node_id, new_id, **{'length': length*np.sqrt(2),
                                   'lanes': 1,
                                   'capacity_lane_hour': capacity,
                                   'speed': speed,
                                   'direction': np.pi/4,
                                   'geometry': LineString([(anchor_node['x'], anchor_node['y']), (x_anchor, y_anchor)])
                                   })

if __name__=="__main__":
    WEST = np.pi
    EAST = 0
    NORTH = np.pi/2
    SOUTH = 3/2*np.pi
    G = nx.MultiDiGraph()
    G.graph['crs'] = {"init": "epsg:32651"}
    G.graph['name'] = "grid"

    # constants
    length = 100  # m
    lanes = 4
    speed = 60
    capacity = 2500

    edge_attributes = {
        'length': length,
        'lanes': lanes,
        'direction': 0,
        'capacity_lane_hour': capacity,
        'speed': speed
    }

    # parameters
    N = 2
    x = np.arange(N)*length
    X, Y = np.meshgrid(x, x)
    ids = np.arange(N**2)
    pos = list(zip(X.flatten(), Y.flatten()))

    G.add_nodes_from([add_node(i, x, y) for i, (x, y) in enumerate(pos)])
    for i, row in enumerate(ids.reshape(N, N)):
        for j, node in enumerate(row):
            if j < N-1:
                start_node = node
                end_node = i*N+j+1
                edge_attributes["direction"] = EAST
                edge_attributes["dir_txt"] = "EAST"
                G.add_edge(start_node, end_node, geometry=LineString(
                    [pos[start_node], pos[end_node]]), **edge_attributes)

                end_node = node
                start_node = i*N+j+1
                edge_attributes["direction"] = WEST
                edge_attributes["dir_txt"] = "WEST"
                G.add_edge(start_node, end_node, geometry=LineString(
                    [pos[start_node], pos[end_node]]), **edge_attributes)
            if i < N-1:
                start_node = node
                end_node = (i+1)*N+j
                edge_attributes["direction"] = NORTH
                edge_attributes["dir_txt"] = "NORTH"
                G.add_edge(start_node, end_node, geometry=LineString(
                    [pos[start_node], pos[end_node]]), **edge_attributes)

                end_node = node
                start_node = (i+1)*N+j
                edge_attributes["direction"] = SOUTH
                edge_attributes["dir_txt"] = "SOUTH"
                G.add_edge(start_node, end_node, geometry=LineString(
                    [pos[start_node], pos[end_node]]), **edge_attributes)
    add_source(G, 0)
    add_sink(G, N**2-1)
    ox.save_graphml(G, "test%dby%d.graphml" % (N, N), folder='./')
    

