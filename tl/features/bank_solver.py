# From: https://github.com/usc-isi-i2/GRAMS/blob/main/grams/algorithm/bank_solver.py 
import copy
from dataclasses import dataclass
from operator import attrgetter, itemgetter

import networkx as nx
import matplotlib.pyplot as plt
from typing import Set, List, Dict, Tuple, Callable, FrozenSet, Optional, Any

"""
Find a top-k approximate minimum steiner arborescence using the BANK algorithm
"""


@dataclass
class Edge:
    __slots__ = ("id", "source_id", "target_id", "edge_key", "weight", "n_edges")
    id: str
    source_id: str
    target_id: str
    edge_key: str
    weight: float
    n_edges: int


@dataclass
class Solution:
    id: FrozenSet[str]
    graph: nx.MultiDiGraph
    weight: float

    def get_n_edges(self):
        if not hasattr(self, "n_edges"):
            self.n_edges = sum(e.n_edges for _, _, e in self.graph.edges(data='data'))
        return self.n_edges


class NoSingleRootException(Exception):
    pass


# noinspection PyMethodMayBeStatic
class SteinerTreeBankSolver:

    def __init__(self,
                 original_graph: nx.MultiDiGraph,
                 terminal_nodes: Set[str],
                 weight_fn: Callable[[dict], float],
                 solution_cmp_fn: Optional[Callable[[Solution], Any]]=None,
                 top_k_st: int = 10,
                 top_k_path: int = 10,
                 allow_shorten_graph: bool = True):
        # original graph
        self.original_graph = original_graph
        # function that extract weights
        self.weight_fn = weight_fn
        # function to compare & sort solutions
        self.solution_cmp_fn = solution_cmp_fn or attrgetter('weight')
        # graph that the bank algorithm will work with
        self.graph: nx.MultiDiGraph = None
        # output graphs
        self.solutions: List[Solution] = []
        self.terminal_nodes = terminal_nodes
        self.top_k_st = top_k_st
        self.top_k_path = top_k_path
        self.allow_shorten_graph = allow_shorten_graph

    def run(self):
        self.graph = self._preprocessing(self.original_graph, self.weight_fn)

        if nx.is_weakly_connected(self.graph):
            print("Is weakly connected")
            self.solutions = self._solve(self.graph, self.terminal_nodes, self.top_k_st, self.top_k_path)
        else:
            graphs = self._split_connected_components(self.graph)
            final_solutions = None
            for g in graphs:
                terminal_nodes = self.terminal_nodes.intersection(list(g.nodes))
                # print("Starting the Solutions")
                solutions = self._solve(g, terminal_nodes, self.top_k_st, self.top_k_path)
                if final_solutions is None:
                    final_solutions = solutions
                else:
                    next_solutions = []
                    for current_sol in final_solutions:
                        for sol in solutions:
                            next_solutions.append(self._merge_graph(current_sol.graph, sol.graph))
                    final_solutions = self._sort_solutions(next_solutions, return_solution=True)[:self.top_k_st]

            self.solutions = final_solutions

        # [self._get_roots(sol.graph) for sol in self.solutions]
        # [sol.weight for sol in self.solutions]
        for sol in self.solutions:
            # print(self._postprocessing(self.original_graph, self.graph, sol.graph))
            nx.draw(sol.graph, with_labels = True)
            plt.show()
        return [self._postprocessing(self.original_graph, self.graph, sol.graph) for sol in self.solutions], self.solutions

    def _preprocessing(self, g: nx.MultiDiGraph, weight_fn: Callable[[dict], float]):
        ng = nx.MultiDiGraph()

        # convert edges
        edge_id_count = 0
        for uid, vid, eid, edata in g.edges(data=True, keys=True):
            # print("--------------")
            # print(uid, vid, eid, edata, weight_fn)
            # print(weight_fn.get((uid, vid, eid)))
            ng.add_edge(uid, vid, key=eid, data=Edge(id=str(edge_id_count), source_id=uid, target_id=vid, edge_key=eid,
                                                     weight=weight_fn.get((uid, vid, eid)), n_edges=1))
            edge_id_count += 1

        if self.allow_shorten_graph:
            # shorten path using the following heuristic
            # for a node that only connect two nodes (indegree & outdegree = 1) and not terminal nodes, we replace the node by one edge
            # map from the replaced edge to the removed nodes
            removed_nodes = {}
            for uid in list(ng.nodes):
                if uid not in self.terminal_nodes and g.in_degree(uid) == 1 and g.out_degree(uid) == 1:
                    inedge: Edge = next(iter(ng.in_edges(uid, data='data')))[-1]
                    outedge: Edge = next(iter(ng.out_edges(uid, data='data')))[-1]
                    if inedge.edge_key == outedge.edge_key:
                        new_edge_key = inedge.edge_key
                    else:
                        new_edge_key = f"{inedge.edge_key}-{outedge.edge_key}"
                    if not ng.has_edge(inedge.source_id, outedge.target_id, key=new_edge_key):
                        # replace it only if we don't have that link before
                        ng.remove_node(uid)
                        ng.add_edge(inedge.source_id, outedge.target_id, key=new_edge_key, data=Edge(id=str(edge_id_count),
                                                                                                    source_id=inedge.source_id,
                                                                                                    target_id=outedge.target_id,
                                                                                                    edge_key=new_edge_key,
                                                                                                    weight=inedge.weight + outedge.weight,
                                                                                                    n_edges=2))
                        removed_nodes[str(edge_id_count)] = (uid, inedge, outedge)
                        edge_id_count += 1

            # store the removed nodes to restore it later
            ng.graph['removed_nodes'] = removed_nodes
        return ng

    def _postprocessing(self, origin_graph: nx.MultiDiGraph, prep_graph: nx.MultiDiGraph, out_graph: nx.MultiDiGraph):
        if self.allow_shorten_graph:
            removed_nodes = prep_graph.graph['removed_nodes']
        else:
            removed_nodes = set()

        g = origin_graph.copy()
        selected_edges = set()
        for uid, vid, edge in out_graph.edges(data='data'):
            if edge.id in removed_nodes:
                removed_node, inedge, outedge = removed_nodes[edge.id]
                selected_edges.add((inedge.source_id, inedge.target_id, inedge.edge_key))
                selected_edges.add((outedge.source_id, outedge.target_id, outedge.edge_key))
            else:
                
                selected_edges.add((uid, vid, edge.edge_key))

        for uid, vid, eid in list(g.edges(keys=True)):
            #print("Selected Edges", selected_edges)
            if (uid, vid, eid) not in selected_edges:
                g.remove_edge(uid, vid, eid)
        for uid in list(g.nodes):
            # print(list(g.nodes), uid)
            if g.in_degree(uid) == 0 and g.out_degree(uid) == 0:
                g.remove_node(uid)
        return g

    def _merge_graph(self, g1: nx.MultiDiGraph, g2: nx.MultiDiGraph) -> nx.MultiDiGraph:
        g = g1.copy()
        for uid, vid, eid, edata in g2.edges(keys=True, data=True):
            g.add_edge(uid, vid, key=eid, **edata)
        return g

    def _split_connected_components(self, g: nx.MultiDiGraph):
        connected_comps = [
            comp
            for comp in nx.weakly_connected_components(g)
            # must have at least two terminal nodes (to form a graph)
            if len(self.terminal_nodes.intersection(comp)) > 1
        ]

        node2comp = {}
        for i, comp in enumerate(connected_comps):
            for uid in comp:
                node2comp[uid] = i

        subgs = [nx.MultiDiGraph() for _ in range(len(connected_comps))]
        for uid, vid, eid, edata in g.edges(keys=True, data=True):
            if uid not in node2comp:
                continue
            subgs[node2comp[uid]].add_edge(uid, vid, key=eid, **edata)
        return subgs

    def _solve(self, g: nx.MultiDiGraph, terminal_nodes: Set[str], top_k_st: int, top_k_path: int):
        """Despite the name, this is finding steiner tree. Assuming their is a root node that connects all
        terminal nodes together.
        """
        roots = set(g.nodes.keys())
        # print("These are the roots", roots)
        # print("These are the terminal nodes", terminal_nodes)
        attr_visit_hists = []
        # to ensure the order
        for uid in list(sorted(terminal_nodes)):
            visit_hist = UpwardTraversal.top_k_beamsearch(g, uid, top_k_path)
            roots = roots.intersection(visit_hist.paths.keys())
            attr_visit_hists.append((uid, visit_hist))

        if len(roots) == 0:
            # there is no nodes that can connect to all terminal nodes either this are disconnected
            # components or you pass a directed graph with weakly connected components (a -> b <- c)
            if nx.is_weakly_connected(g):
                # perhaps, we can break the weakly connected components by breaking one of the link (a -> b <- c)
                raise NoSingleRootException(
                    "You pass a weakly connected component and there are parts of the graph like this (a -> b <- c). Fix it before running this algorithm")
            raise Exception("Your graph is disconnected. Consider splitting them before calling bank solver")

        # to ensure the order again & remove randomness
        roots = sorted(roots)

        # merge the paths using beam search
        results = []
        for root in roots:
            current_states = []
            uid, visit_hist = attr_visit_hists[0]
            for path in visit_hist.paths[root]:
                pg = nx.MultiDiGraph()
                if len(path.path) > 0:
                    assert uid == path.path[0].target_id
                pg.add_node(uid)
                for e in path.path:
                    pg.add_node(e.source_id)
                    pg.add_edge(e.source_id, e.target_id, e.edge_key, weight=e.weight, data=e)
                current_states.append(pg)

            if len(current_states) > top_k_st:
                current_states = self._sort_solutions(current_states)[:top_k_st]

            for uid, visit_hist in attr_visit_hists[1:]:
                next_states = []
                for state in current_states:
                    for path in visit_hist.paths[root]:
                        pg = state.copy()
                        if len(path.path) > 0:
                            assert uid == path.path[0].target_id
                        pg.add_node(uid)
                        for e in path.path:
                            if e.source_id not in pg.nodes:
                                pg.add_node(e.source_id)
                            # TODO: here we don't check by edge_key because we may create another edge of different key
                            # hope this new path has been exploited before.
                            if not pg.has_edge(e.source_id, e.target_id):
                                pg.add_edge(e.source_id, e.target_id, key=e.edge_key, weight=e.weight, data=e)

                        # after add a path to the graph, it can create new cycle, detect and fix it
                        try:
                            # note that the function I'm using doesn't return parallel edges
                            cycles_iter = nx.find_cycle(pg, uid, orientation='reverse')
                            # we can show that if the graph contain cycle, there is a better path
                            #
                            # cycles_iter = [(uid, vid) for uid, vid, eid, orien in cycles_iter]
                            # for _g in self._break_cycles(root, pg, cycles_iter):
                            #     next_states.append(_g)
                        except nx.NetworkXNoCycle:
                            next_states.append(pg)
                        if len(list(pg.edges)) != len({(uid, vid) for uid, vid, eid in pg.edges(keys=True)}):
                            assert False
                if len(next_states) > top_k_st:
                    next_states = self._sort_solutions(next_states)[:top_k_st]
                current_states = next_states
                # cgs = [g for g in next_states if len(list(nx.simple_cycles(g))) > 0]
                # nx.draw_networkx(cgs[0]); plt.show()
                # nx.draw(cgs[0]); plt.show()
            results += current_states
        return self._sort_solutions(results, return_solution=True)

    def _break_cycles(self, root: str, g: nx.MultiDiGraph, cycles_iter: List[Tuple[str, str]]):
        # g = current_states[0]; g = self.output_graphs[0]
        # pos = nx.kamada_kawai_layout(g); nx.draw_networkx(g, pos); nx.draw_networkx_edge_labels(g, pos, edge_labels={(u, v): d for u, v, d in g.edges(keys=True)}); plt.show()
        # nx.draw(g); plt.show()
        return self._break_cycles_brute_force(root, g, cycles_iter)

    def _break_cycles_brute_force(self, root: str, g: nx.MultiDiGraph, cycles_iter: List[Tuple[str, str]]):
        # one side effect of this approach is that it may separate the graph
        # currently we say it only happen when the target node of the remove edge only has one incoming edge
        # if it has two edges, then the other source (not of the remove edge) must have a path from root -> itself
        # now, since we have cascade removing, if the path doesn't go through the removed node, then it's okay,
        # if the path goes through the remove node, it's impossible since we only remove node that indegree == 0 or
        # outdegree == 0
        parallel_edges = []
        for uid, vid in cycles_iter:
            if g.in_degree(vid) == 1:
                # we can't remove this edge, as removing it will make it's unreachable from the root
                # so just skip edge
                continue
            edges = [edata['data'] for eid, edata in g[uid][vid].items()]
            edge_weight = min(edges, key=attrgetter('weight')).weight
            parallel_edges.append((uid, vid, edges, edge_weight))

        # not comparing based on weight anymore since psl can be quite difficult to select correct edge
        # min_edge_weight = min(parallel_edges, key=itemgetter(3))[3]
        # unbreakable = {i for i, x in enumerate(parallel_edges) if x[3] == min_edge_weight}
        # new_graphs = []
        # if len(unbreakable) < len(parallel_edges):
        #     # it's great! we have some edge to break!
        #     # for each breakable edge, we will have a new graph
        #     for i, item in enumerate(parallel_edges):
        #         if i in unbreakable:
        #             continue
        #         ng: nx.MultiDiGraph = g.copy()
        #         ng.remove_edge(item[0], item[1])
        #         ng = self._remove_redundant_nodes(root, ng)
        #         new_graphs.append(ng)
        # else:
            # so bad, we have to try one by one
        new_graphs = []
        for uid, vid, edges, edge_weight in parallel_edges:
            ng: nx.MultiDiGraph = g.copy()
            ng.remove_edge(uid, vid)
            # self._draw(ng); self._draw(g)
            ng = self._remove_redundant_nodes(root, ng)
            new_graphs.append(ng)

        # just assert if it works as expected
        for ng in new_graphs:
            assert len(list(nx.simple_cycles(ng))) == 0
        return new_graphs

    def _sort_solutions(self, graphs: List[nx.MultiDiGraph], return_solution: bool = False):
        """Sort the solution by th"""
        solutions = {}
        for g in graphs:
            id = frozenset((e.id for _, _, e in g.edges(data='data')))
            if id in solutions:
                continue

            weight = sum(e.weight for _, _, e in g.edges(data='data'))
            # print("the Weights")
            # print(weight, g.edges(data='data'))
            solutions[id] = Solution(id, g, weight)

        solutions = sorted(solutions.values(), key=self.solution_cmp_fn)
        if return_solution:
            return solutions
        return [sol.graph for sol in solutions]

    def _remove_redundant_nodes(self, root: str, g: nx.MultiDiGraph):
        # remove nodes in the graph that shouldn't be in a steiner tree
        while True:
            removed_nodes = []
            for uid in g.nodes:
                if uid == root or uid in self.terminal_nodes:
                    continue
                if g.in_degree(uid) == 0 or g.out_degree(uid) == 0:
                    removed_nodes.append(uid)
            if len(removed_nodes) == 0:
                break
            for uid in removed_nodes:
                g.remove_node(uid)
        return g

    def _get_roots(self, g: nx.MultiDiGraph):
        """This function is mainly used for debugging"""
        return [uid for uid in g if g.in_degree(uid) == 0]

    @staticmethod
    def _draw(g: nx.MultiDiGraph):
        """This function is mainly used for debugging"""
        pos = nx.kamada_kawai_layout(g)
        nx.draw_networkx(g, pos)
        nx.draw_networkx_edge_labels(g, pos, edge_labels={(u, v): d for u, v, d in g.edges(keys=True)})
        plt.show()


class CycleBreaker:
    def spanning_arborescence(self, g: nx.MultiDiGraph, root: str, terminal_nodes: Set[str]):
        resp = nx.algorithms.tree.branchings.minimum_spanning_arborescence(g, attr='weight', default=None,
                                                                           preserve_attrs=True)
        ng = nx.MultiDiGraph()
        for uid, vid, edge in resp.edges(data='data'):
            ng.add_edge(uid, vid, key=edge.edge_key, weight=edge.weight, data=edge)
        # after breaking we may have multiple root nodes or leaf so we just need to clean them
        return [self._truncate_redundant_nodes(ng, root, terminal_nodes)]

    def one_edge_at_a_time(self, og: nx.MultiDiGraph, root: str, terminal_nodes: Set[str]):
        """This approach doesn't allow us to select the graph that has shorter length due to multiple cycles in the graph"""
        current_graphs = [og]
        has_cycle = True
        while has_cycle:
            # loop until we don't have any cycle left
            new_graphs = []
            for g in current_graphs:
                for cycle in nx.simple_cycles(g):
                    cycle.append(cycle[0])
                    edge_groups = []
                    for i in range(len(cycle) - 1):
                        uid = cycle[i]
                        vid = cycle[i+1]
                        # we may have more than one edge between two nodes
                        edges = [edata['data'] for eid, edata in g[uid][vid].items()]
                        edge_weight = min(edges, key=attrgetter('weight'))
                        edge_groups.append((uid, vid, edges, edge_weight))

                    min_edge_weight = min(edge_groups, itemgetter(3))
                    unbreakable = {i for i, x in enumerate(edge_groups) if x[3] == min_edge_weight}
                    if len(unbreakable) < len(edge_groups):
                        # it's great! we have some edge to break!
                        # for each breakable edge, we will have a new graph
                        for i, item in enumerate(edge_groups):
                            if i in unbreakable:
                                continue
                            ng: nx.MultiDiGraph = g.copy()
                            # we remove all instead of just one
                            ng.remove_edge(item[0], item[1])
                            ng = self._truncate_redundant_nodes(ng, root, terminal_nodes)
                            new_graphs.append(ng)
                    else:
                        # so bad, we have to try one by one
                        tmp = []
                        for uid, vid, edges, edge_weight in edge_groups:
                            ng: nx.MultiDiGraph = g.copy()
                            ng.remove_edge(uid, vid)
                            ng = self._truncate_redundant_nodes(ng, root, terminal_nodes)
                            # given a score for each split, we prefer the one that is smaller?
                            # however, we can't calculate the depth since the graph may contain multiple cycles
                            # this make this approach not good.
                            tmp.append(ng)

                        # find which one is better

                    pass

    def _truncate_redundant_nodes(self, g: nx.MultiDiGraph, root: str, terminal_nodes: Set[str]):
        while True:
            removed_nodes = []
            for uid in g.nodes:
                if uid == root or uid in terminal_nodes:
                    continue
                if g.in_degree(uid) == 0 or g.out_degree(uid) == 0:
                    removed_nodes.append(uid)
            if len(removed_nodes) == 0:
                break
            for uid in removed_nodes:
                g.remove_node(uid)
        return g


@dataclass
class UpwardPath:
    __slots__ = ("visited_nodes", "path", "weight")

    visited_nodes: Set[str]
    path: List[Edge]
    weight: float

    @staticmethod
    def empty(start_node_id: str):
        return UpwardPath({start_node_id}, [], 0.0)

    def push(self, edge: Edge) -> 'UpwardPath':
        c = self.clone()
        c.path.append(edge)
        c.visited_nodes.add(edge.source_id)
        c.weight += edge.weight
        return c

    def clone(self):
        return UpwardPath(copy.copy(self.visited_nodes), copy.copy(self.path), self.weight)


@dataclass
class UpwardTraversal:
    __slots__ = ("source_id", "paths")

    source_id: str

    # storing that we can reach this node through those list of paths
    paths: Dict[str, List[UpwardPath]]

    @staticmethod
    def top_k_beamsearch(g: nx.MultiDiGraph, start_node_id: str, top_k_path: int):
        travel_hist = UpwardTraversal(start_node_id, dict())
        travel_hist.paths[start_node_id] = [UpwardPath.empty(start_node_id)]
        for source_id, target_id, edge_id, orientation in nx.edge_bfs(g, start_node_id, orientation='reverse'):
            if source_id not in travel_hist.paths:
                travel_hist.paths[source_id] = []

            edge: Edge = g.edges[source_id, target_id, edge_id]['data']
            #
            # for edata in g[source_id][target_id].values():
            #     edge: Edge = edata['data']
            for path in travel_hist.paths[target_id]:
                if source_id in path.visited_nodes:
                    # path will become loopy, which we don't want to do
                    continue
                path = path.push(edge)
                travel_hist.paths[source_id].append(path)

            # we trim the number of paths in here
            if len(travel_hist.paths[source_id]) > top_k_path:
                # calculate the score of each path, and then select the best one
                travel_hist.sort_paths(source_id)
                travel_hist.paths[source_id] = travel_hist.paths[source_id][:top_k_path]
        return travel_hist

    def sort_paths(self, node_id: str):
        self.paths[node_id] = sorted(self.paths[node_id], key=attrgetter('weight'))
