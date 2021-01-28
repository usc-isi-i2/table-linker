import sys
import math

import numpy as np
import requests
import pandas as pd

from collections import defaultdict

from scipy.spatial.distance import cosine, euclidean

from tl.utility.utility import Utility
from tl.exceptions import TLException

# column,row,label,||other_information||,label_clean,kg_id,kg_labels,method,retrieval_score,retrieval_score_normalized,GT_kg_id,GT_kg_label,evaluation_label,gt_embed_score,sentence,vector,gt_embed_score_normalized,pagerank-precomputed,pagerank-precomputed_normalized,pagerank,pagerank_normalized,extra_information_score

# /lfs1/ktyao/Shared/table-linker-datasets/2019-iswc_challenge_data/t2dv2/evaluation_files/28086084_0_3127660530989916727.csv
# column,row,label_x,kg_id,kg_labels,method,retrieval_score,pagerank,label_y,GT_kg_id,GT_kg_label,evaluation_label
class EmbeddingVector:
    def __init__(self, kwargs):
        self.kwargs = kwargs
        self.loaded_file = None
        self.vectors_map = {}
        self.centroid = None
        self.groups = defaultdict(set)
        self.input_column_name = kwargs['input_column_name']
        pass

    def load_input_file(self, input_file):
        """
            read the input file
        """
        self.loaded_file = pd.read_csv(input_file, dtype=object)

        # Drop duplicate rows for uniqueness
        self.loaded_file.drop_duplicates(inplace=True, ignore_index=True)

    def get_vectors(self):
        qnodes = set(self.loaded_file.loc[:, self.input_column_name])
        embedding_file = self.kwargs['embedding_file']
        url = self.kwargs['embedding_url']
        if embedding_file:
            with open(embedding_file, 'rt') as fd:
                for line in fd:
                    fields = line.strip().split('\t')
                    qnode = fields[0]
                    if qnode in qnodes:
                        self.vectors_map[qnode] = np.asarray(list(map(float, fields[1:])))
        elif url:
            found_one = False
            for i, qnode in enumerate(qnodes):
                # Use str, becauses of missing values (nan)
                response = requests.get(url + str(qnode))
                if response.status_code == 200:
                    result = response.json()
                    if result['found']:
                        found_one = True
                        self.vectors_map[qnode] = np.asarray(list(map(float, result['_source']['embedding'].split())))
                if i > 100 and not found_one:
                    raise TLException('Failing to find vectors: ' + url + qnode)
            if not found_one:
                raise TLException('Failed to find any vectors: ' + url + qnode)

    def process_vectors(self):
        """
        apply corresponding vector strategy to process the calculated vectors
        :return:
        """
        vector_strategy = self.kwargs.get("column_vector_strategy", "centroid-of-singletons")
        if vector_strategy == "centroid-of-singletons":
            if not self._centroid_of_singletons():
                raise TLException(f'Column_vector_stragtegy {vector_strategy} failed')
        else:
            raise TLException(f'Unknown column_vector_stragtegy')

    def add_score_column(self):
        score_column_name = self.kwargs["output_column_name"]
        if score_column_name is None:
            score_column_name = "score_{}".format(self.kwargs["column_vector_strategy"])
            i = 1
            while score_column_name in self.loaded_file:
                i += 1
                score_column_name = "score_{}_{}".format(self.kwargs["column_vector_strategy"], i)

        scores = []
        for i, each_row in self.loaded_file.iterrows():
            # the nan value can also be float
            if ((isinstance(each_row[self.input_column_name], float) and math.isnan(each_row[self.input_column_name]))
                or each_row[self.input_column_name] is np.nan
                or each_row[self.input_column_name] not in self.vectors_map):
                each_score = ""
            else:
                each_score = self.compute_distance(self.centroid,
                                                   self.vectors_map[each_row[self.input_column_name]])

            scores.append(each_score)
        self.loaded_file[score_column_name] = scores

    def print_output(self):
        self.loaded_file.to_csv(sys.stdout, index=False)

    def _centroid_of_singletons(self) -> bool:

        # Find singleton ids, i.e. ids from candidation generation sets of size one
        singleton_ids = []
        for ((col, row), group) in self.loaded_file.groupby(['column', 'row']):
            ids = group[self.input_column_name].unique().tolist()
            if np.nan in ids:
                ids.remove(np.nan)
            if len(ids) == 1:
                singleton_ids.append(ids[0])

        if not singleton_ids:
            return False

        missing_embedding_ids = []
        vectors = []
        for kg_id in singleton_ids:
            if kg_id not in self.vectors_map:
                missing_embedding_ids.append(kg_id)
            else:
                vectors.append(self.vectors_map[kg_id])

        if len(missing_embedding_ids):
            print(f'_centroid_of_singletons: Missing {len(missing_embedding_ids)} of {len(singleton_ids)}',
                  file=sys.stderr)

        # centroid of singletons
        self.centroid = np.mean(np.array(vectors), axis=0)
        return True


    def compute_distance(self, v1: np.array, v2: np.array):
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
