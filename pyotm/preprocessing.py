## code from https://github.com/ual/create-network-bpr/blob/master/edges-add-speed-capacity.ipynb
import statistics
import pandas as pd
import osmnx as ox
import ast

# define speed defaults for each hwy type and number of lanes, so we can infer when lacking data
speed_defaults = {'residential' : {1 : 20, 2 : 20, 3 : 20, 4 : 20, -1 : 20},
                  'living_street' : {1 : 20, 2 : 20, 3 : 20, 4 : 20, -1 : 20},
                  'tertiary' : {1 : 20, 2 : 20, 3 : 20, 4 : 20, -1 : 20},
                  'tertiary_link' : {1 : 20, 2 : 20, 3 : 20, 4 : 20, -1 : 20},
                  'secondary' : {1 : 25, 2 : 25, 3 : 25, 4 : 25, -1 : 25},
                  'secondary_link' : {1 : 25, 2 : 25, 3 : 25, 4 : 25, -1 : 25},
                  'primary' : {1 : 30, 2 : 30, 3 : 30, 4 : 30, -1 : 30},
                  'primary_link' : {1 : 30, 2 : 30, 3 : 30, 4 : 30, -1 : 30},
                  'trunk' : {1 : 45, 2 : 45, 3 : 45, 4 : 45, -1 : 45},
                  'trunk_link' : {1 : 45, 2 : 45, 3 : 45, 4 : 45, -1 : 45},
                  'motorway' : {1 : 50, 2 : 50, 3 : 65, 4 : 65, -1 : 57.5},
                  'motorway_link' : {1 : 50, 2 : 50, 3 : 65, 4 : 65, -1 : 57.5},
                  'unclassified' : {1 : 20, 2 : 20, 3 : 20, 4 : 20, -1 : 20},
                  'road' : {1 : 30, 2 : 30, 3 : 30, 4 : 30, -1 : 30}}

# define per-lane capacity defaults for each hwy type and number of lanes, so we can infer when lacking data
capacity_defaults = {'residential' : {1 : 500, 2 : 500, 3 : 500, 4 : 500, -1 : 500},
                     'living_street' : {1 : 500, 2 : 500, 3 : 500, 4 : 500, -1 : 500},
                     'tertiary' : {1 : 900, 2 : 900, 3 : 900, 4 : 900, -1 : 900},
                     'tertiary_link' : {1 : 900, 2 : 900, 3 : 900, 4 : 900, -1 : 900},
                     'secondary' : {1 : 900, 2 : 900, 3 : 900, 4 : 900, -1 : 900},
                     'secondary_link' : {1 : 900, 2 : 900, 3 : 900, 4 : 900, -1 : 900},
                     'primary' : {1 : 1000, 2 : 1000, 3 : 1000, 4 : 1000, -1 : 1000},
                     'primary_link' : {1 : 1000, 2 : 1000, 3 : 1000, 4 : 1000, -1 : 1000},
                     'trunk' : {1 : 1900, 2 : 2000, 3 : 2000, 4 : 2000, -1 : 1975},
                     'trunk_link' : {1 : 1900, 2 : 2000, 3 : 2000, 4 : 2000, -1 : 1975},
                     'motorway' : {1 : 1900, 2 : 2000, 3 : 2000, 4 : 2200, -1 : 2025},
                     'motorway_link' : {1 : 1900, 2 : 2000, 3 : 2000, 4 : 2200, -1 : 2025},
                     'unclassified' : {1 : 800, 2 : 800, 3 : 800, 4 : 800, -1 : 800},
                     'road' : {1 : 900, 2 : 900, 3 : 900, 4 : 900, -1 : 900}}

# note: -1 is the key for the null value
# note: highway_links are given the same values as their highway types
# note: 'road' is effectively an OSM null highway type
# note: 'unclassified' is a highway type one step below tertiary in the OSM hierarchy


# convert string representations of lists to lists# conve 
def convert_lists(value):
    if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
        return ast.literal_eval(value) #parse str -> list
    else:
        return value
    

# collapse multiple highway type values into a single value# colla 
def collapse_multiple_hwy_values(hwy):
    if isinstance(hwy, list):
        # if we find an item in our defaults dict, use that value
        # otherwise, just use the zeroth item in the list
        for item in hwy:
            if item in speed_defaults.keys():
                return item
        return hwy[0]
    else:
        return hwy

# collapse multiple lane values into a single value# colla 
def collapse_multiple_lane_values(value):
    if isinstance(value, list):
        # return the mean of the values in the list
        numeric_values = [int(x) for x in value]
        return int(statistics.mean(numeric_values))
    else:
        return value


# if this is a two-way street, there will be two edges, one uv and one vu
# give each half the lanes
# probably not right... review https://wiki.openstreetmap.org/wiki/Key:lanes#Assumptions
def allocate_lanes(row):
    if row['oneway']:
        return row['lanes']
    else:
        return int(row['lanes'] / 2)

# collapse multiple maxspeed values into a single value
def collapse_multiple_maxspeed_values(value):
    if isinstance(value, list):
        try:
            # strip non-numeric " mph" from each value in the list then take the mean
            values = [int(x.replace(' mph', '')) for x in value]
            return statistics.mean(values)
        except:
            # if exception, return null (a few have multiple values like "35 mph;40 mph")
            return None
    else:
        return value

# infer speed from defaults based on highway type classifier and number of lanes  
def infer_speed(row):
    hwy = row['highway']
    lanes = row['lanes_capped']
    return speed_defaults[hwy][lanes]

def parse_speed_strings(value):
    if isinstance(value, str):
        # for all string maxspeed values, strip non-numeric " mph" from each value
        value = value.replace(' mph', '')
        # sometimes multiple speeds are semicolon-delimited -- collapse to a single value
        if ';' in value:
            # return the mean of the values if it has that semicolon
            values = [int(x) for x in value.split(';')]
            return statistics.mean(values)
        else:
            return int(value)
    else:
        return value

# infer capacity per lane per hour from defaults based on highway type classifier and number of lanes
def infer_capacity(row):
    hwy = row['highway']
    lanes = row['lanes_capped']
    return capacity_defaults[hwy][lanes]

def add_speed_capacity(streets):
    nodes, edges = ox.graph_to_gdfs(streets)
    edges['highway'] = edges['highway'].map(collapse_multiple_hwy_values)
    edges['highway'].fillna(value="unclassified", inplace=True)
    edges['highway'].value_counts(dropna=False).sort_index()
    edges['lanes'] = edges['lanes'].map(convert_lists)
    edges['lanes'] = edges['lanes'].map(lambda x: int(x) if type(x)==str else x) ## assure integer values

    edges['lanes'] = edges['lanes'].map(collapse_multiple_lane_values)
    edges['lanes'].value_counts().sort_index()

    # calculate "typical" number of lanes per hwy type
    edges['lanes'] = edges['lanes'].astype(float)
    lane_defaults = edges.groupby('highway')['lanes'].median()
    lane_defaults = lane_defaults.fillna(value=2).to_dict() #'road' type is null

    # impute number of lanes when data is missing# impute 
    def impute_lanes(row):
        if pd.notnull(row['lanes']):
            return row['lanes']
        else:
            return lane_defaults[row['highway']]
    edges['lanes'] = edges.apply(impute_lanes, axis=1).astype(int)
    edges['lanes'] = edges.apply(allocate_lanes, axis=1)

    # make 1 lanes the min (in case some edge says zero lanes)# make 1 
    edges.loc[edges['lanes'] < 1, 'lanes'] = 1
    # make 4 lanes the capped value (for 4+ lanes dict lookup), but retain true lanes value in lanes column# make 4 
    edges['lanes_capped'] = edges['lanes']
    edges.loc[edges['lanes_capped'] > 4, 'lanes_capped'] = 4
    edges['lanes_capped'].value_counts().sort_index()


    # convert string representation of multiple maxspeed values to a list# conver 
    edges['maxspeed'] = edges['maxspeed'].map(convert_lists)


    edges['maxspeed'] = edges['maxspeed'].map(collapse_multiple_maxspeed_values)
        
    edges['maxspeed'] = edges['maxspeed'].map(parse_speed_strings)
    edges['maxspeed'].value_counts(dropna=False).sort_index()


    # extract maxspeed from OSM data when it already exists
    known_speeds = edges[pd.notnull(edges['maxspeed'])]['maxspeed']
    known_speeds = known_speeds.astype(int)

    # infer speed on all other edges that lack maxspeed data# infer  
    inferred_speeds = edges[pd.isnull(edges['maxspeed'])].apply(infer_speed, axis=1)

    # merge known speeds with inferred speeds to get a free-flow speed for each edge
    edges['speed'] = known_speeds.append(inferred_speeds, ignore_index=False, verify_integrity=True)

    # infer per-lane capacity for each edge using capacity defaults# infer  
    edges['capacity_lane_hour'] = edges.apply(infer_capacity, axis=1)
    edges['jam_density'] = 5*edges['capacity_lane_hour']/edges['speed']
    return ox.gdfs_to_graph(nodes, edges)