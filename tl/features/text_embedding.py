import os
import sys
import math
import shutil
import typing
import random
import tempfile
import numpy as np
import pandas as pd
import tl.exceptions
from io import StringIO
from collections import defaultdict
from tl.utility.utility import Utility
from scipy.spatial.distance import cosine, euclidean
from kgtk.cli.text_embedding import main as main_embedding_function


class EmbeddingVector:
    """
        a class support embedding vectors ranking operations
    """

    def __init__(self, parameters):
        self.vectors_map = {}
        self.kwargs = parameters
        self.loaded_file = None
        self.kgtk_format_input = None
        self.centroid = {}
        self.only_one_candidates = set()
        self.groups = defaultdict(set)

    def load_input_file(self, input_file):
        """
            read the input file and then wrap it to kgtk format input
        """

        self.loaded_file = pd.read_csv(input_file, dtype=object)
        # remove evaluation label equals to 0 (which means no ground truth)
        self.loaded_file = self.loaded_file[self.loaded_file['evaluation_label'] != '0']
        all_info = {}
        count = 0
        correspond_key = {"label_clean": "label", "kg_id": "candidates", "GT_kg_id": "kg_id"}
        for i, each_part in self.loaded_file.groupby(["column", "row"]):
            info = {}
            for each_choice in correspond_key.keys():
                temp = list(set(each_part[each_choice].unique()))
                temp_filtered = []
                for each in temp:
                    if each != "" and not isinstance(each, float):
                        temp_filtered.append(each)
                info[correspond_key[each_choice]] = temp_filtered
            # if len(info['kg_id']) == 0:
            #     Utility.eprint("Skip pair {} with no ground truth nodes.".format(i))
            #     continue
            if len(info['kg_id']) > 1 or len(info['label']) > 1:
                Utility.eprint("WARNING: pair {} has multiple ground truths?".format(i))
            self.groups[i[0]].update(info["candidates"])
            self.groups[i[0]].update(info["kg_id"])
            info["label"] = info["label"][0]
            info["kg_id"] = info["kg_id"][0]
            info["candidates"] = "|".join(info["candidates"])

            all_info[count] = info
            count += 1

        self.kgtk_format_input = pd.DataFrame.from_dict(all_info, orient='index')

    def get_centroid(self):
        """
            function used to calculate the column-vector(centroid) value
        """
        n_value = int(self.kwargs.pop("n_value"))
        vector_strategy = self.kwargs.get("column_vector_strategy", "exact-matches")
        if vector_strategy == "ground-truth":
            if "GT_kg_id" not in self.loaded_file:
                raise tl.exceptions.TLException(
                    "The input file does not have `GT_kg_id` column! Can't run with ground-truth "
                    "strategy")
            candidate_nodes = list(set(self.loaded_file["GT_kg_id"].tolist()))
        elif vector_strategy == "exact-matches":
            candidate_nodes = list(set(self.loaded_file["kg_id"].tolist()))
        else:
            raise tl.exceptions.TLException("Unknown vector vector strategy {}".format(vector_strategy))
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
            val = cosine(v1, v2)

        elif self.kwargs["distance_function"] == "euclidean":
            val = euclidean(v1, v2)
            # because we need score higher to be better, here we use the reciprocal value
            if val == 0:
                val = float("inf")
            else:
                val = 1 / val
        else:
            raise tl.exceptions.TLException("Unknown distance function {}".format(self.kwargs["distance_function"]))
        return val

    def add_score_column(self):
        score_column_name = self.kwargs["output_column_name"]
        if score_column_name is None:
            score_column_name = "score_{}".format(self.kwargs["models_names"])

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

    def get_vectors(self):
        """
            send the table linker format data to kgtk vector embedding
            the load the output and get the vector map
        """
        # transform format to kgtk format input
        destination = tempfile.mkdtemp(prefix='table_linker_temp_file')
        temp_file_path = os.path.join(destination, "test_input_to_kgtk")
        self.kgtk_format_input.to_csv(temp_file_path, index=False)
        self.kwargs["input_uris"] = temp_file_path
        self.kwargs["input_format"] = "test_format"
        self.kwargs["logging_level"] = "none"
        self.kwargs["output_uri"] = "none"
        self.kwargs["use_cache"] = True
        # catch the stdout to string
        old_stdout = sys.stdout
        sys.stdout = output_vectors = StringIO()
        main_embedding_function(**self.kwargs)
        sys.stdout = old_stdout
        shutil.rmtree(destination)
        # read the output vectors
        output_vectors.seek(0)
        _ = output_vectors.readline()
        for each_line in output_vectors.readlines():
            each_line = each_line.replace("\n", "").split("\t")
            each_q = each_line[0]
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
