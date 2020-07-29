import io
import math
import numpy as np
import os
import pandas as pd
import random
import sys
import typing
import tempfile

from pathlib import Path
from collections import defaultdict
from io import StringIO
from kgtk.cli.text_embedding import main as main_embedding_function
from scipy.spatial.distance import cosine, euclidean
from tl.utility.utility import Utility
from tl.candidate_generation.es_search import Search
from tl.exceptions import TLException


class EmbeddingVector:
    """
        a class support embedding vectors ranking operations
    """

    def __init__(self, parameters):
        self.vectors_map = {}
        self.sentence_map = {}
        self.kwargs = parameters
        self.loaded_file = None
        self.kgtk_format_input = None
        self.centroid = {}
        self.groups = defaultdict(set)
        self.es = Search(self.kwargs["url"], self.kwargs["index"],
                         es_user=self.kwargs.get("user"), es_pass=self.kwargs.get("password"))

    def load_input_file(self, input_file):
        """
            read the input file
        """
        self.loaded_file = pd.read_csv(input_file, dtype=object)
        self._to_kgtk_test_format()

    def _to_kgtk_test_format(self):
        """
        wrap input file to kgtk format input
        :return:
        """
        # remove evaluation label equals to 0 (which means no ground truth)
        self.groups = defaultdict(set)
        if "evaluation_label" in self.loaded_file.columns:
            self.loaded_file = self.loaded_file[self.loaded_file['evaluation_label'] != '0']
        all_info = {}
        count = 0
        correspond_key = {"label_clean": "label", "kg_id": "candidates", "GT_kg_id": "kg_id"}
        for i, each_part in self.loaded_file.groupby(["column", "row"]):
            info = {}
            for each_choice in correspond_key.keys():
                if each_choice in each_part.columns:
                    temp = list(set(each_part[each_choice].unique()))
                    temp_filtered = []
                    for each in temp:
                        if each != "" and not isinstance(each, float):
                            temp_filtered.append(each)
                    info[correspond_key[each_choice]] = temp_filtered
                else:
                    info[correspond_key[each_choice]] = []

            if len(info['kg_id']) > 1 or len(info['label']) > 1:
                Utility.eprint("WARNING: pair {} has multiple ground truths?".format(i))
            self.groups[i[0]].update(info["candidates"])
            self.groups[i[0]].update(info["kg_id"])
            info["label"] = info["label"][0]
            if len(info["kg_id"]) > 0:
                info["kg_id"] = info["kg_id"][0]
            else:
                info["kg_id"] = " "
            info["candidates"] = "|".join(info["candidates"])

            all_info[count] = info
            count += 1

        self.kgtk_format_input = pd.DataFrame.from_dict(all_info, orient='index')

    def process_vectors(self):
        """
        apply corresponding vector strategy to process the calculated vectors
        :return:
        """
        vector_strategy = self.kwargs.get("column_vector_strategy", "exact-matches")
        if vector_strategy == "page-rank":
            self._calculate_page_rank()
        elif vector_strategy == "page-rank-precomputed":
            self._get_precomputed_page_rank()
        else:
            self._get_centroid(vector_strategy)

    def _generate_graph(self):
        """
        function used to calculate page rank
        :return:
        """
        Utility.eprint("start calculating page rank, it may take some time.")
        import networkx as nx
        # calculate probability to next stage
        # calculate probability base on columns
        col_memo = {}
        nodes_memo = {}
        graph_memo = {}
        similarity_memo = {}
        for col_number, each_part in self.loaded_file.groupby(["column"]):
            # first calculate all distance for memo
            all_nodes = set(each_part['kg_id']) - {"", np.nan}
            all_nodes_list = list(all_nodes)
            for i, each_node in enumerate(all_nodes):
                col_memo[each_node] = col_number
            for i in range(len(all_nodes_list)):
                for j in range(i + 1, len(all_nodes_list)):
                    similarity = self.compute_distance(self.vectors_map[all_nodes_list[i]], self.vectors_map[all_nodes_list[j]])
                    similarity_memo[(all_nodes_list[i], all_nodes_list[j])] = similarity
                    similarity_memo[(all_nodes_list[j], all_nodes_list[i])] = similarity
            similarity_graph = nx.DiGraph()
            similarity_graph.add_nodes_from(all_nodes)
            graph_memo[col_number] = similarity_graph
            nodes_memo[col_number] = all_nodes

        for i, each_row in self.kgtk_format_input.iterrows():
            each_surface = each_row["candidates"].split("|")
            if len(each_surface) > 0:
                for each_node_i in each_surface:
                    if each_node_i == "":
                        continue
                    col_number = col_memo[each_node_i]
                    all_nodes_set = nodes_memo[col_number]
                    remained_nodes = all_nodes_set - set(each_surface)
                    # calculate sum score first
                    sum_score = 0
                    for each_node_j in remained_nodes:
                        sum_score += similarity_memo[(each_node_i, each_node_j)]
                    for each_node_j in remained_nodes:
                        # pos = (pos_memo[each_node_i], pos_memo[each_node_j])
                        each_weight = similarity_memo[(each_node_i, each_node_j)] / sum_score
                        graph_memo[col_number].add_edge(each_node_i, each_node_j, weight=each_weight)
        return graph_memo

    def _calculate_page_rank(self):
        import networkx as nx
        # just get initial page rank to do filtering
        weights_original = {}
        graph_memo = self._generate_graph()
        for each_graph in graph_memo.values():
            weights_original.update(dict(each_graph.degree(weight='weight')))
        self.loaded_file['|pr|'] = self.loaded_file['kg_id'].map(weights_original)
        from tl.features.normalize_scores import drop_by_score
        self.loaded_file = drop_by_score(column="|pr|", df=self.loaded_file, k=20)
        # also we need to update kgtk format input
        self._to_kgtk_test_format()
        # create the graph again base on filtered result
        res = {}
        graph_memo = self._generate_graph()
        # it seems pagerank_numpy runs quickest
        for each_graph in graph_memo.values():
            res.update(nx.pagerank_numpy(each_graph, alpha=0.9))
        self.loaded_file['|pr|'] = self.loaded_file['kg_id'].map(res)

    def _get_precomputed_page_rank(self):
        """
        get the precomputed pagerank from whole wikidata graph
        :return:
        """
        pageranks = {k: v[0] if len(v) > 0 else 0
                     for k, v in self.es.search_node_pagerank(self.loaded_file['kg_id'].dropna().unique().tolist()).items()}
        self.loaded_file["|pr|"] = self.loaded_file['kg_id'].map(pageranks).fillna(0)

    def _get_centroid(self, vector_strategy: str):
        """
            function used to calculate the column-vector(centroid) value
        """
        n_value = int(self.kwargs.pop("n_value"))

        if vector_strategy == "ground-truth":
            if "GT_kg_id" not in self.loaded_file:
                raise TLException(
                    "The input file does not have `GT_kg_id` column! Can't run with ground-truth "
                    "strategy")
            candidate_nodes = list(set(self.loaded_file["GT_kg_id"].tolist()))
        elif vector_strategy == "exact-matches":
            candidate_nodes = list(set(self.loaded_file["kg_id"].tolist()))
        else:
            raise TLException("Unknown vector vector strategy {}".format(vector_strategy))
        candidate_nodes = [each for each in candidate_nodes if each != "" and each is not np.nan]

        # get corresponding column of each candidate nodes
        nodes_map = defaultdict(set)
        for each_node in candidate_nodes:
            for group, nodes in self.groups.items():
                if each_node in nodes:
                    nodes_map[group].add(each_node)

        # random sample nodes if needed
        nodes_map_updated = {}

        for group, nodes in nodes_map.items():
            if n_value != 0 and n_value < len(nodes):
                nodes_map_updated[group] = random.sample(nodes, n_value)
            else:
                nodes_map_updated[group] = nodes

        # get centroid for each column
        for group, nodes in nodes_map_updated.items():
            temp = []
            for each_node in sorted(list(nodes)):
                temp.append(self.vectors_map[each_node])
            each_centroid = np.mean(np.array(temp), axis=0)
            self.centroid[group] = each_centroid

    def compute_distance(self, v1: typing.List[float], v2: typing.List[float]):
        if self.kwargs["distance_function"] == "cosine":
            val = 1 - cosine(v1, v2)

        elif self.kwargs["distance_function"] == "euclidean":
            val = euclidean(v1, v2)
            # because we need score higher to be better, here we use the reciprocal value
            if val == 0:
                val = float("inf")
            else:
                val = 1 / val
        else:
            raise TLException("Unknown distance function {}".format(self.kwargs["distance_function"]))
        return val

    def add_score_column(self):
        score_column_name = self.kwargs["output_column_name"]
        if score_column_name is None:
            score_column_name = "score_{}".format(self.kwargs["column_vector_strategy"])
            i = 1
            while score_column_name in self.loaded_file:
                i += 1
                score_column_name = "score_{}_{}".format(self.kwargs["column_vector_strategy"], i)

        if self.kwargs["column_vector_strategy"] in {"page-rank", "page-rank-precomputed"}:
            self.loaded_file = self.loaded_file.rename(columns={'|pr|': score_column_name})
        else:
            scores = []
            for i, each_row in self.loaded_file.iterrows():
                # the nan value can also be float
                if (isinstance(each_row["kg_id"], float) and math.isnan(each_row["kg_id"])) or each_row["kg_id"] is np.nan:
                    each_score = ""
                else:
                    each_score = self.compute_distance(self.centroid[each_row["column"]],
                                                       self.vectors_map[each_row["kg_id"]])

                scores.append(each_score)
            self.loaded_file[score_column_name] = scores

        if self.kwargs["save_embedding_feature"]:
            self.loaded_file['sentence'] = self.loaded_file['kg_id'].map(self.sentence_map)
            self.loaded_file['vector'] = self.loaded_file['kg_id'].map(self.vectors_map)

        if self.kwargs["ignore_empty_sentences"]:
            # remove sentences which is same as kg ids
            self.loaded_file = self.loaded_file[
                self.loaded_file['kg_id'] != self.loaded_file['sentence'].apply(
                    lambda x: x[:-1] if isinstance(x, str) else x)
                ]

    def _create_detail_has_properties(self):
        """
        By loading the property file, remove unnecessary things and get something inside if needed
        :return: None
        """
        model_file_path = os.path.join(repr(__file__).replace("'", "").replace("/text_embedding.py", ""),
                                       "predicate_counts_and_labels.tsv")
        if os.path.exists(model_file_path):
            properties_df = pd.read_csv(model_file_path, sep='\t')
        else:
            return
        # process
        need_isa_properties = {"P31"}
        need_has_properties = set()
        for _, each_row in properties_df.iterrows():
            if not isinstance(each_row["label"], str) and np.isnan(each_row["label"]):
                continue
            if each_row["operation"] == "check_inside" or each_row["label"].endswith("of'@en"):
                need_isa_properties.add(each_row["predicate"])
                continue
            elif each_row["operation"] == "bl":
                continue
            else:
                if "ID" in each_row["label"] or \
                        "identifier" in each_row["label"].lower() or \
                        "common" in each_row["label"].lower():
                    continue
            need_has_properties.add(each_row["predicate"])

        self.kwargs["has_properties"] = list(need_has_properties)
        self.kwargs["isa_properties"] = list(need_isa_properties)

    def get_vectors(self):
        """
            send the table linker format data to kgtk vector embedding
            the load the output and get the vector map
        """
        # no vector calculation needed for precomputed pagerank
        if self.kwargs.get("column_vector_strategy") == "page-rank-precomputed":
            return

        # transform format to kgtk format input
        temp_file = tempfile.NamedTemporaryFile(mode='r+', suffix=".csv")
        self.kgtk_format_input.to_csv(temp_file, index=False)
        temp_file.seek(0)
        self.kwargs["input_file"] = Path(temp_file.name)
        self.kwargs["input_format"] = "test_format"
        self.kwargs["_debug"] = self.kwargs["debug"]
        self.kwargs["output_uri"] = "none"
        self.kwargs["use_cache"] = True
        # always send true to kgtk, so that we can get the sentences to check if they are empty or not
        self.kwargs["save_embedding_sentence"] = True
        if self.kwargs["has_properties"] == ["all"] and self.kwargs["isa_properties"] == ["P31"] \
                and self.kwargs["use_default_file"]:
            self._create_detail_has_properties()

        # catch the stdout to string
        old_stdout = sys.stdout
        sys.stdout = output_vectors = StringIO()

        main_embedding_function(**self.kwargs)
        sys.stdout = old_stdout
        # read the output vectors
        output_vectors.seek(0)
        _ = output_vectors.readline()
        for each_line in output_vectors.readlines():
            each_line = each_line.replace("\n", "").split("\t")
            each_q = each_line[0]
            each_edge = each_line[1]
            if each_edge == "embedding_sentence":
                each_sentence = each_line[2]
                self.sentence_map[each_q] = each_sentence
            else:
                each_vector = np.array([float(each_v) for each_v in each_line[2].split(",")])
                self.vectors_map[each_q] = each_vector

        # save kgtk output vector file if needed
        if self.kwargs["projector_file_name"] is not None:
            self.save_vector_file(output_vectors)
        output_vectors.close()

    def save_vector_file(self, vector_io):
        output_path = self.kwargs["projector_file_name"]
        if "/" not in output_path:
            output_path = os.path.join(os.getcwd(), output_path)
        vector_io.seek(0)
        with open(output_path, "w") as f:
            f.writelines(vector_io.readlines())

    def print_output(self):
        self.loaded_file.to_csv(sys.stdout, index=False)

