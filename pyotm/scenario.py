from shapely.geometry import LineString, Point
from lxml import etree
import networkx as nx


def _point_getter(point):
    point_att = point.attrib
    keys = ['x', 'y', 'z']
    return tuple(float(point_att.get(key, 0)) for key in keys)


def nodeparser(node):
    attrib = {key: val for key, val in node.attrib.items()}
    attrib['x'] = float(attrib['x'])
    attrib['y'] = float(attrib['y'])
    attrib['geometry'] = Point(attrib['x'], attrib['y'])
    attrib['osmid'] = -1
    return attrib


def egdeparser(link):
    attrib = {key: val for key, val in link.attrib.items()}
    attrib['length'] = float(attrib['length'])
    attrib['full_lanes'] = int(attrib['full_lanes'])
    points = link.xpath('.//point')
    if points:
        attrib['geometry'] = LineString(
            [_point_getter(point) for point in points])
    return attrib


def load(filepath, crs=None):
    doc = etree.parse(filepath)
    nodes = doc.xpath("//node")
    edges = doc.xpath("//link")
    G = nx.MultiDiGraph()
    G.add_nodes_from([(node.attrib["id"], nodeparser(node)) for node in nodes])
    G.add_edges_from([(edge.attrib["start_node_id"], edge.attrib["end_node_id"],
                       egdeparser(edge)) for edge in edges])
    G.graph['crs'] = crs
    G.graph['name'] = filepath
    return G


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        configfile = sys.argv[1]
    else:
        configfile = "../../OTM/otm-base/src/main/resources/test_configs/line.xml"

    G = load(configfile)
