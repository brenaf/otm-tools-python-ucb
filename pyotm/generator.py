from shapely.geometry import LineString
import pandas as pd
import osmnx as ox
import numpy as np
from igraph import OUT


def nearest_neighbor(points, coord, nodes, latlon=True):
    if latlon:
        distances = haversine(coord, points)
    else:
        distances = np.sqrt((coord['Latitude']-points['Latitude'])**2 + (coord['Longitude']-points['Longitude'])**2)
    location = np.where(distances==np.min(distances))[0][0]
    return np.min(distances), nodes.iloc[location].osmid


def extract_streets(bounding_box, crs=None, **kwargs):
    streets = ox.graph_from_bbox(north=bounding_box['north'], 
                                south=bounding_box['south'], 
                                east=bounding_box['east'], 
                                west=bounding_box['west'], network_type='drive', clean_periphery=True, 
                                **kwargs
                                )
    if crs:
        streets = ox.project_graph(streets, crs)
    return streets


def get_buildings(bounding_box, N_buildings=None, crs=None):
    buildings = ox.buildings.create_buildings_gdf(north=bounding_box['north'], 
                                                  south=bounding_box['south'], 
                                                  east=bounding_box['east'], 
                                                  west=bounding_box['west'])
    if crs:
        buildings = buildings.to_crs(crs)
    buildings['area'] = buildings.geometry.area
    buildings['x'] = buildings.geometry.centroid.x
    buildings['y'] = buildings.geometry.centroid.y
    buildings['osmid'] = buildings.index.format()
    buildings['osmid'] = buildings['osmid'].str.strip()
    buildings['highway'] = np.nan
    # buildings = buildings[buildings.area>(buildings.area.mean()*1.5)]
    buildings.sort_values('area', ascending=False, inplace=True)
    return buildings.head(N_buildings)



def draw_edges(u,v, length, nodes, buildings):
    new_edges = pd.DataFrame([], columns=['u', 'v'])
    new_edges['u'] = u
    new_edges['v'] = v
    new_edges['osmid'] = new_edges[['u', 'v']].apply(lambda x: ''.join([str(i) for i in x]), axis=1)
    new_edges['length'] = length
    new_edges['geometry'] = buildings.apply(lambda x: 
                                            LineString([x.geometry.centroid, nodes[nodes.osmid==x.nearest_id].geometry.values[0]]),
                                            axis=1)
    new_edges['oneway'] = True
    new_edges["speed"] = 30
    new_edges["capacity_lane_hour"] = 900
    new_edges['lanes'] = 1
    return new_edges


def merge_od_streets(origins, destinations, streets, filepath=None, latlon=False):
    nodes, edges = ox.save_load.graph_to_gdfs(streets)
    n = []
    for i, buildings in enumerate([origins, destinations]):
        buildings['Longitude'], buildings['Latitude'] = zip(*buildings.geometry.centroid.apply(lambda x: (x.x, x.y)))
        nodes['Longitude'], nodes['Latitude'] = nodes['x'].astype(float), nodes['y'].astype(float)
        buildings['nearest_length'], buildings['nearest_id'] = zip(*buildings[['Latitude', 'Longitude']].apply(
                                                            lambda x: nearest_neighbor(nodes[['Latitude', 'Longitude']], x, nodes, latlon=latlon), axis=1
                                                            ))
        node_cols = ['highway', 'osmid', 'x', 'y', 'geometry']
        n.append(buildings[node_cols])

        ## need the ids as integers since NetworkX tracks nodes by integers
        if i==0:
            edges = edges.append(draw_edges(buildings['osmid'].astype(int), buildings['nearest_id'].astype(int), buildings['nearest_length'], nodes, buildings))
        else:
            edges = edges.append(draw_edges(buildings['nearest_id'].astype(int), buildings['osmid'].astype(int), buildings['nearest_length'], nodes, buildings))
    nodes2 = pd.concat([nodes, *n])
    nodes2.gdf_name = nodes.gdf_name
    edges.reset_index(drop=True)
    edges['id'] = range(edges.shape[0])
    edges = edges.set_index(edges.id.values)

    mdf = ox.save_load.gdfs_to_graph(nodes2, edges)
    ox.save_graphml(mdf, filepath)
    return mdf


def generate_paths(graph, ods, paths_per_od):
    graph.vs["Coordinates"] = list(zip(graph.vs['x'], graph.vs['y']))

    # Generate the paths between the od pairs
    all_paths = {}
    for o in ods:
        #Find all paths between origin and destination that have at most max_length edges
        #start_time1 = timeit.default_timer()
        # Each iteration the weight of the shortest path is multiplied by power to allow to
        # find a new shortest path
        # Add edge weights to graph, we start will all edges with weight 1
        # graph.es["weight"] = np.ones(graph.ecount())
        graph.es['weight'] = list(map(float, graph.es['length']))

        factor = 10
        paths = []
        for i in range(paths_per_od):
            path = graph.get_shortest_paths(o[0], o[1], weights="weight", mode=OUT, output="epath")
            if path[0] not in paths:
                paths.append(path[0])

            #change weight of edges in path in order to find new shortest path
            size_of_path = len(path[0])
            new_weights = np.multiply(factor**(i+1),np.ones(size_of_path))
            graph.es[path[0]]["weight"] = np.multiply(factor**(i+1), graph.es[path[0]]["weight"])
        #elapsed1 = timeit.default_timer() - start_time1

        #If we could not get paths_per_od paths between the od, double the max_length value
        #if len(paths) < paths_per_od:
            #paths = find_all_paths_len(graph,o[0],o[1],maxlen=max_length*2)

        #Sort paths by length so that the shortest are first
        #paths.sort(key=len)
        # print("Finding paths for od ", o[0], " and dest ", o[1])
        #new_paths = translate_paths(graph, paths[0:paths_per_od])
        if len(paths) > 0:
            all_paths[o] = {"paths": paths, "demand": ods[o]}

    return all_paths

if __name__=="__main__":
    import json
    from preprocessing import add_speed_capacity
    import osmnx as ox

    # Prepare buildings and road network
    N_buildings = 50
    num_ods = int(N_buildings**2*0.01)
    # num_ods = 10
    np.random.seed(1234567809)

    with open('bounding_boxes.json', 'r') as f:
        areas = json.load(f)
    
    custom_filter = None
    crs = {"init":"epsg:32651"}
    area_name = "MetroManila"
    filename = "data/"+area_name

    area_name = "UPDiliman_small"
    # suffix = "_small_splits_mn"
    filename = "data/"+area_name#+suffix
    bbox = areas[area_name]['bbox']
    custom_filter = areas[area_name]['custom_filter']
    # custom_filter = None
    # filename = "UP-Katipunan"
    # bbox = {'north':14.6746, 'south':14.5958, 'east':121.0939, 'west': 121.0182}
    streets = extract_streets(bbox, crs=crs, custom_filter=custom_filter)
    streets = add_speed_capacity(streets)
    ox.save_load.save_graphml(streets, filename=area_name+".base.graphml")