import typing
import argparse
import sys
import traceback
import tl.exceptions

def parser():
    return {
        'help': 'use ktgk text embedding function to add vectors for candidates for further steps.'
    }

def add_arguments(parser):
    # input file
    from kgtk.cli.text_embedding import ALL_EMBEDDING_MODELS_NAMES
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    # query endpoint, default use official wikidata?
    parser.add_argument('-q', '--sparql-query-endpoint', action='store', dest='query_endpoint',
            help="sparql_query_endpoint", default="https://query.wikidata.org/sparql")
    # embedding model choice
    parser.add_argument('-c', '--column-vector-strategy', action='store', dest='column_vector_strategy',
            default="exact-matches", choices=("ground-truth", "exact-matches"),
            help="the name of the strategy to use to create the vector for the column:")
    parser.add_argument('-m', '--embedding-model', action='store', nargs='+', dest='models_names',
            default="bert-base-wikipedia-sections-mean-tokens", choices=ALL_EMBEDDING_MODELS_NAMES,
            help="the model to used for embedding")
    # distance function
    parser.add_argument('-d', '--distance-function', action='store', dest='distance_function',
            default="cosine", choices=("cosine", "euclidean"), 
            help="the function to compute similarity between column vectors and candidate vectors, default is cosine.")
    # n_value
    parser.add_argument('-n', action='store', dest='n_value',
            default=0, type=int,
            help="the number of cells used to estimate the vector for a column (K in the column-vector-strategy). The default is 0, which causes all eligible cells to be used to compute the column vector.")
    # output column name
    parser.add_argument('-o', '--output-column-name', action='store', dest='output_column_name',
            default=None, 
            help="the name of the column where the value of the distance function will be stored. If not provided, the name of the embedding model will be used.")
    # projector file
    parser.add_argument('-g', '--generate-projector-file', action='store', dest='projector_file_name',
            default=None, 
            help="generate the files needed to run the Google Project visualization, using the given name to compose the names of the output files. If given, an additional tsv file will be saved. If only a file name given, it will save on user's home directory.")
    # properties to use for embedding
    parser.add_argument('--label-properties', action='store', nargs='+', 
            dest='label_properties',default= ["label"],
            help="""The names of the eges for label properties, Default is ["label"]. \n This argument is only valid for input in kgtk format.""")
    parser.add_argument('--description-properties', action='store', nargs='+', 
            dest='description_properties', default= ["description"],
            help="""The names of the eges for description properties, Default is ["description"].\n This argument is only valid for input in kgtk format.""")
    parser.add_argument('--isa-properties', action='store', nargs='+', 
            dest='isa_properties', default= ["P31"],
            help="""The names of the eges for `isa` properties, Default is ["P31"] (the `instance of` node in wikidata).\n This argument is only valid for input in kgtk format.""")
    parser.add_argument('--has-properties', action='store', nargs='+', 
            dest='has_properties', default= ["all"],
            help="""The names of the eges for `has` properties, Default is ["all"] (will automatically append all properties found for each node).\n This argument is only valid for input in kgtk format.""")

def parse_evaluation_format(dataset_path):
    for source in os.listdir(dataset_path):
        if source.endswith(".csv") and not source.startswith("wrapped"):
            file_path = os.path.join(dataset_path, source)
            loaded_file = pd.read_csv(file_path)
            last_row = None
            all_info = {}
            count = 0
            info = defaultdict(set)
            for i, each_row in loaded_file.iterrows():
                if each_row["row"] != last_row and last_row != None:
                    if len(list(info["candidates"])) == 1 and isinstance(list(info['candidates'])[0], float):
                        info["candidates"] = []
                    info_list_format = {
                        "label": list(info["label"])[0],
                        "kg_id": list(info["kg_id"])[0] if len(info["kg_id"]) > 0 else "",
                        "candidates": "|".join(list(info["candidates"]))
                    }
                    all_info[count] = info_list_format
                    count += 1
                    info = defaultdict(set)
                last_row = each_row["row"]
                info["label"].add(each_row["label_clean"])
                info["kg_id"].add(each_row["GT_kg_id"])
                if each_row["kg_id"] is not np.nan:
                    info["candidates"].add(each_row["kg_id"])
            # add last row
            info_list_format = {
                        "label": list(info["label"])[0],
                        "kg_id": list(info["kg_id"])[0] if len(info["kg_id"]) > 0 else "",
                        "candidates": "|".join(list(info["candidates"]))
                    }
            all_info[count] = info_list_format
            output_res = pd.DataFrame.from_dict(all_info, orient='index')
            output_res.to_csv(os.path.join(dataset_path, "wrapped_{}".format(source)), index=False)


class EmbeddingVector:
    def __init__(self, parameters):
        from collections import defaultdict
        self.vectors_map = {}
        self.kwargs = parameters
        self.loaded_file = None
        self.kgtk_format_input = None
        self.centroid = {}
        self.only_one_candidates = set()
        self.groups = defaultdict(set)

    def load_input_file(self, input_file):
        """
            read the input file and then transform it to kgtk format input
        """
        import pandas as pd
        import os
        from collections import defaultdict
        import numpy as np
        self.loaded_file = pd.read_csv(input_file, dtype=object)
        last_location = None
        all_info = {}
        count = 0
        info = defaultdict(set)
        for i, each_row in self.loaded_file.iterrows():
            column_row_pair = (each_row["column"], each_row["row"])
            if column_row_pair != last_location and last_location != None:
                # in this condition, it means there is no proper candidates
                if len(list(info["candidates"])) == 1 and isinstance(list(info['candidates'])[0], float):
                    info["candidates"] = []
                info_list_format = {
                    "label": list(info["label"])[0],
                    "kg_id": list(info["kg_id"])[0] if len(info["kg_id"]) > 0 else "",
                    "candidates": "|".join(list(info["candidates"]))
                }
                if len(info["candidates"]) == 1 and info_list_format['kg_id'] != "":
                    self.only_one_candidates.update(info["candidates"])
                all_info[count] = info_list_format
                count += 1
                info = defaultdict(set)
            last_location = column_row_pair
            info["label"].add(each_row["label_clean"])
            # GT_kg_id can also sometime be empty?
            if each_row["GT_kg_id"] is not np.nan:
                info["kg_id"].add(each_row["GT_kg_id"])
                self.groups[each_row["column"]].add(each_row["GT_kg_id"])
            if each_row["kg_id"] is not np.nan:
                info["candidates"].add(each_row["kg_id"])
                self.groups[each_row["column"]].add(each_row["kg_id"])

        # add last row
        if len(list(info["candidates"])) == 1 and isinstance(list(info['candidates'])[0], float):
            info["candidates"] = []
        info_list_format = {
                    "label": list(info["label"])[0],
                    "kg_id": list(info["kg_id"])[0] if len(info["kg_id"]) > 0 else "",
                    "candidates": "|".join(list(info["candidates"]))
                }

        all_info[count] = info_list_format
        self.kgtk_format_input = pd.DataFrame.from_dict(all_info, orient='index')

    def get_centroid(self):
        """
            function used to calculate the column-vector(centroid) value
        """
        import numpy as np
        import random
        from collections import defaultdict
        n_value = int(self.kwargs.pop("n_value"))
        vector_strategy = self.kwargs.get("column_vector_strategy", "exact-matches")
        if vector_strategy == "ground-truth":
            if "GT_kg_id" not in self.loaded_file:
                raise ValueError("The input file does not have `GT_kg_id` column! Can't run with ground-truth strategy")
            candidate_nodes = list(set(self.loaded_file["GT_kg_id"].tolist()))
        elif vector_strategy == "exact-matches":
            candidate_nodes = list(set(self.loaded_file["kg_id"].tolist()))
        else:
            raise ValueError("Unknown vector vector strategy {}".format(vector_strategy))
        candidate_nodes = [each for each in candidate_nodes if each != "" and each is not np.nan]
        # get corresponding column of each candidate nodes
        nodes_map = defaultdict(set)
        for each_node in candidate_nodes:
            for group, nodes in self.groups.items():
                if each_node in nodes:
                    nodes_map[group].add(each_node)
        # random sample nodes if nedded
        nodes_map_updated = {}
        for group, nodes in nodes_map.items():
            if n_value != 0 and n_value < len(nodes):
                nodes_map_updated[group] = random.sample(nodes, n_value)
            else:
                nodes_map_updated[group] = nodes
        # get centroid
        for group, nodes in nodes_map_updated.items():
            nodes = list(nodes)
            each_centroid = self.vectors_map[nodes[0]]
            for each_node in nodes[1:]:
                each_centroid += self.vectors_map[each_node]
            each_centroid = each_centroid / len(nodes)
            self.centroid[group] = each_centroid

    def compute_distance(self, v1: typing.List[float], v2: typing.List[float]):
        if self.kwargs["distance_function"] == "cosine":
            from scipy.spatial.distance import cosine
            val = cosine(v1, v2)

        elif self.kwargs["distance_function"] == "euclidean":
            from scipy.spatial.distance import euclidean
            val = euclidean(v1, v2)
            # because we need score higher to be better, here we use the reciprocal value
            if val == 0:
                val = float("inf")
            else:
                val = 1 / val
        return val

    def add_score_column(self):
        import numpy as np
        import math
        score_column_name = self.kwargs["output_column_name"]
        if score_column_name is None:
            score_column_name = "score_{}".format(self.kwargs["models_names"])

        scores = []
        for i, each_row in self.loaded_file.iterrows():
            # the nan value can also be float
            if (isinstance(each_row["kg_id"], float) and math.isnan(each_row["kg_id"])) or each_row["kg_id"] is np.nan:
                each_score = ""
            else:
                each_score = self.compute_distance(self.centroid[each_row["column"]], self.vectors_map[each_row["kg_id"]])
                
            scores.append(each_score)
        self.loaded_file[score_column_name] = scores

    def get_vectors(self):
        """
            send the table linker format data to kgtk vector embedding
            the load the output and get the vector map
        """
        import tempfile
        import shutil
        import sys
        import os
        from io import StringIO
        import numpy as np
        from kgtk.cli.text_embedding import main as main_embedding_function
        # transform format to kgtk format input
        destination = tempfile.mkdtemp(prefix='table_linker_temp_file')
        temp_file_path = os.path.join(destination, "test_input_to_kgtk")
        self.kgtk_format_input.to_csv(temp_file_path, index=False)
        self.kwargs["input_uris"] = temp_file_path
        self.kwargs["input_format"] = "test_format"
        self.kwargs["logging_level"] = "none"
        self.kwargs["output_uri"] = "none"
        self.kwargs["run_TSNE"] = False
        # catch the stdout to string
        old_stdout = sys.stdout
        sys.stdout = output_vectors = StringIO()
        main_embedding_function(**self.kwargs)
        sys.stdout = old_stdout
        shutil.rmtree(destination)
        # read the output vectors
        output_vectors.seek(0)
        header = output_vectors.readline()
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
        import os
        output_path = self.kwargs["projector_file_name"]
        if "/" not in output_path:
            output_path = os.path.join(os.getcwd(), output_path)
        vector_io.seek(0)
        with open(output_path, "w") as f:
            f.writelines(vector_io.readlines())

    def print_output(self):
        self.loaded_file.to_csv(sys.stdout, index=False)

def run(**kwargs):
    try:
        input_file_path = kwargs.pop("input_file")
        vector_transformer = EmbeddingVector(kwargs)
        vector_transformer.load_input_file(input_file_path)
        vector_transformer.get_vectors()
        vector_transformer.get_centroid()
        vector_transformer.add_score_column()
        vector_transformer.print_output()
    except:
        message = 'Command: clean\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)