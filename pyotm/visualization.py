#!/usr/bin/env/python
import numpy as np
import matplotlib.animation as animation
from mpl_toolkits.axes_grid1 import make_axes_locatable
from osmnx.save_load import graph_to_gdfs
from osmnx import settings
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.collections import LineCollection
import matplotlib as mpl
# mpl.use('Agg')


def parallel_point_shift(p1, p2,  h):
    (x1,y1) = p1
    (x2,y2) = p2

    theta = np.arctan((x1-x2)/(y1-y2))
    if y1 < y2:
        x1 -= h*np.cos(theta)
        y1 += h*np.sin(theta)
        x2 -= h*np.cos(theta)
        y2 += h*np.sin(theta)
    else:
        x1 += h*np.cos(theta)
        y1 -= h*np.sin(theta)
        x2 += h*np.cos(theta)
        y2 -= h*np.sin(theta)

    return ((x1,y1), (x2,y2))


def plot_graph(G, bbox=None, fig_height=10, fig_width=None, margin=0.02,
               axis_off=True, equal_aspect=False, bgcolor='w', show=True,
               save=False, close=True, file_format='png', filename='temp',
               dpi=300, annotate=False, node_color='#66ccff', node_size=0,
               node_alpha=1, node_edgecolor='none', node_zorder=1,
               edge_color='#999999', edge_linewidth=1, edge_alpha=1,
               use_geom=True, offset=False):

    node_Xs = [float(x) for _, x in G.nodes(data='x')]
    node_Ys = [float(y) for _, y in G.nodes(data='y')]

    # get north, south, east, west values either from bbox parameter or from the
    # spatial extent of the edges' geometries
    if bbox is None:
        # edges = graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)
        west, south, east, north = np.min(node_Xs), np.min(
            node_Ys), np.max(node_Xs), np.max(node_Ys)
    else:
        north, south, east, west = bbox

    # if caller did not pass in a fig_width, calculate it proportionately from
    # the fig_height and bounding box aspect ratio
    bbox_aspect_ratio = (north-south)/(east-west) or 9/16
    if fig_width is None:
        fig_width = fig_height / bbox_aspect_ratio

    # create the figure and axis
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor=bgcolor)
    ax.set_facecolor(bgcolor)

    # draw the edges as lines from node to node
    lines = []
    for u, v, data in G.edges(keys=False, data=True):
        if 'geometry' in data and use_geom:
            # if it has a geometry attribute (a list of line segments), add them
            # to the list of lines to plot
            xs, ys = data['geometry'].xy
            points = zip(xs, ys)

            #parallel shift distance
            h = 1
            if (not data.get('oneway', False)) and offset:
                # for each point excluding the start point and end point, shift point based on line to next point
                transformed_points = [points[0]]
                # get pairs of points on the line segment
                for p1,p2 in zip(points[1:], points[2:]):
                    (x1,y1) = parallel_point_shift(p1,p2,h)[0]
                    transformed_points.append((x1,y1))

                transformed_points.append(points[-1])
                points = transformed_points

            lines.append(list(points))
        else:
            # if it doesn't have a geometry attribute, the edge is a straight
            # line from node to node
            x1 = G.nodes[u]['x']
            y1 = G.nodes[u]['y']
            x2 = G.nodes[v]['x']
            y2 = G.nodes[v]['y']

            if not data.get('oneway', False) and offset:
                ((x1,y1), (x2,y2)) = parallel_point_shift((x1,y1),(x2,y2), h)

            line = [(x1, y1), (x2, y2)]
            lines.append(line)

    # add the lines to the axis as a linecollection
    lc = LineCollection(lines, colors=edge_color,
                        linewidths=edge_linewidth, alpha=edge_alpha, zorder=2)
    ax.add_collection(lc)

    # scatter plot the nodes
    ax.scatter(node_Xs, node_Ys, s=node_size, c=node_color,
               alpha=node_alpha, edgecolor=node_edgecolor, zorder=node_zorder)

    # set the extent of the figure
    margin_ns = (north - south) * margin
    margin_ew = (east - west) * margin
    ax.set_ylim((south - margin_ns, north + margin_ns))
    ax.set_xlim((west - margin_ew, east + margin_ew))

    # configure axis appearance
    ax.get_xaxis().get_major_formatter().set_useOffset(False)
    ax.get_yaxis().get_major_formatter().set_useOffset(False)

    # if axis_off, turn off the axis display set the margins to zero and point
    # the ticks in so there's no space around the plot
    if axis_off:
        ax.axis('off')
        ax.margins(0)
        ax.tick_params(which='both', direction='in')
        fig.canvas.draw()

    if equal_aspect:
        # make everything square
        ax.set_aspect('equal')
        fig.canvas.draw()
    else:
        # if the graph is not projected, conform the aspect ratio to not stretch the plot
        if G.graph['crs'] == settings.default_crs:
            coslat = np.cos((min(node_Ys) + max(node_Ys)) / 2. / 180. * np.pi)
            ax.set_aspect(1. / coslat)
            fig.canvas.draw()
    return fig, ax


def get_color(G):
    colors = []
    for _, _, data in G.edges(keys=False, data='weight', default=0):
        colors.append(data)
    return colors


def aggregate_paths(G, demands, paths, i):
    n, e = ox.save_load.graph_to_gdfs(G)
    e['weight'] = 0
    for pathID in demands.keys():
        e.loc[e.index.astype(int).isin(paths[pathID]),
              'weight'] = demands[pathID][i]
    return n, e


def add_edge_weights(G, edge_weights, i):
    for (u, v, edge_id) in G.edges(data="link_id"):
        G[u][v][0]['weight'] = edge_weights[str(edge_id)][i]
    return G


def filter_edges(n, e, paths):
    active_edges = e.loc[sorted({x for v in paths.values() for x in v}), : ]
    active_nodes = n.loc[n.index.isin(
        set(active_edges.u.values).union(active_edges.v.values))]
    active_nodes.gdf_name = n.gdf_name
    return ox.save_load.gdfs_to_graph(active_nodes, active_edges)


def plot_anim(G, link_flow, paths, label, streets=None, sampling_dt=300, type="time", plot_kwargs=None):
    minima = 1e-5
    maxima = np.max([i for i in link_flow.values()])
    cmap = cm.RdYlGn_r
    cmap.set_under('#999999')
    norm = mpl.colors.Normalize(vmin=minima, vmax=maxima, clip=False)
    mapper = cm.ScalarMappable(norm=norm, cmap=cmap)

    # if paths:
    #     pass
    #     # n, e = aggregate_paths(G, link_flow, paths, 0)
    #     # G = filter_edges(n, e, paths)
    # else:
    G = add_edge_weights(G, link_flow, 0)

    # Initialize graph
    fig, ax = plot_graph(G, show=False,
                         node_size=0, **plot_kwargs)
    # workaround to be able to use OSMnx's future features
    lc = ax.collections[2 if streets else 0]
    divider = make_axes_locatable(ax)
    ax1 = divider.append_axes("right", size="5%", pad=0.05)
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap,
                                    norm=norm,
                                    orientation='vertical')
    cb1.set_label(label)

    def updatefig(i):
        # if paths:
        #     # not implemented yet
        #     # n, e = aggregate_paths(G, link_flow, paths, i)
        #     # G = filter_edges(n, e, paths)
        #     pass
        # else:
        Gprime = add_edge_weights(G, link_flow, i)

        colors = get_color(Gprime)
        lc.set_color(mapper.to_rgba(colors))
        ax.set_title("%d seconds" % (i*sampling_dt))
        return lc,
    anim = animation.FuncAnimation(fig, updatefig,
                                   frames=len(
                                       list(link_flow.values())[0]),
                                   interval=200,
                                   blit=True)

    return fig, ax, anim


if __name__ == "__main__":
    import sys
    import scenario
    from simulation import OTMRunner
    configfile = sys.argv[2]
    otm = OTMRunner(configfile, model=sys.argv[1])
    output = otm.run()
    G = scenario.load(configfile)

    # s = pd.read_csv("plugin_30_g_link_flw_global.txt")
    # link_flow = {}
    # for link, veh in enumerate(s.values.T):
    #     link_flow[link] = veh

    fig, ax, anim = plot_anim(G, output['link_flw'], paths=None, label="Vehicles/hr",
                              sampling_dt=90, plot_kwargs={"edge_linewidth": 3})
    print("saving animation...")
    anim.save(configfile[:-4]+".mp4", dpi=300, fps=3)
