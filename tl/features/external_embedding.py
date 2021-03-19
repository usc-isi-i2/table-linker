import json
import math
import sys
import typing

import numpy as np
import requests
import pandas as pd

from collections import defaultdict
from pathlib import Path

from scipy.spatial.distance import cosine, euclidean

from tl.utility.utility import Utility
from tl.exceptions import TLException


# column,row,label,||other_information||,label_clean,kg_id,kg_labels,method,retrieval_score,retrieval_score_normalized,GT_kg_id,GT_kg_label,evaluation_label,gt_embed_score,sentence,vector,gt_embed_score_normalized,pagerank-precomputed,pagerank-precomputed_normalized,pagerank,pagerank_normalized,extra_information_score

# /lfs1/ktyao/Shared/table-linker-datasets/2019-iswc_challenge_data/t2dv2/evaluation_files/28086084_0_3127660530989916727.csv
# column,row,label_x,kg_id,kg_labels,method,retrieval_score,pagerank,label_y,GT_kg_id,GT_kg_label,evaluation_label
class EmbeddingVector:
    def __init__(self, kwargs):
        self.kwargs = kwargs
        self.load_input_file(self.kwargs)
        self.vectors_map = {}
        self.centroid = None
        self.groups = defaultdict(set)
        self.input_column_name = kwargs['input_column_name']
        self.debug = True
        self.min_vote = int(kwargs.get('min_vote', 0))

    def load_input_file(self, kwargs):
        """
            read the input file
        """
        if 'input_file' in kwargs:
            self.loaded_file = pd.read_csv(kwargs['input_file'], dtype=object)

        if 'df' in kwargs:
            self.loaded_file = kwargs['df']

        # Drop duplicate rows for uniqueness
        self.loaded_file.drop_duplicates(inplace=True, ignore_index=True)

    def get_result_df(self):
        return self.loaded_file

    def _load_vectors_from_file(self, embedding_file, qnodes):
        with open(embedding_file, 'rt') as fd:
            for line in fd:
                fields = line.strip().split('\t')
                qnode = fields[0]
                if qnode in qnodes:
                    self.vectors_map[qnode] = np.asarray(list(map(float, fields[1:])))

    def _save_new_to_file(self, embedding_file, new_qnodes):
        with open(embedding_file, 'at') as fd:
            for qnode in new_qnodes:
                vector = self.vectors_map[qnode]
                line = f'{qnode}\t'
                line += '\t'.join([str(x) for x in vector])
                line += '\n'
                fd.write(line)

    # def _load_vectors_server(self, url, qnodes):
    #     found_one = False
    #     for i, qnode in enumerate(qnodes):
    #         # Use str, becauses of missing values (nan)
    #         response = requests.get(url + 'doc/' + str(qnode))
    #         if response.status_code == 200:
    #             result = response.json()
    #             if result['found']:
    #                 found_one = True
    #                 self.vectors_map[qnode] = np.asarray(list(map(float, result['_source']['embedding'].split())))
    #         if i > 100 and not found_one:
    #             raise TLException(f'Failing to find vectors: {url} {qnode}')
    #     if not found_one:
    #         raise TLException(f'Failed to find any vectors: {url} {qnode}')

    def _load_vectors_from_server(self, url, qnodes) -> typing.List[str]:
        search_url = url + '_search'
        batch_size = 1000
        found = []
        missing = []
        for i in range(0, len(qnodes), batch_size):
            part = qnodes[i:i + batch_size]
            query = {
                "_source": ["id", "embedding"],
                "size": batch_size,
                "query": {
                    "ids": {
                        "values": part
                    }
                }
            }
            response = requests.get(search_url, json=query)
            result = response.json()
            if result['hits']['total'] == 0:
                missing += part
            else:
                hit_qnodes = []
                for hit in result['hits']['hits']:
                    qnode = hit['_source']['id']
                    if isinstance(hit['_source']['embedding'], str):
                        vector = np.asarray(list(map(float, hit['_source']['embedding'].split())))
                    else:
                        vector = np.asarray(list(map(float, hit['_source']['embedding'])))
                    hit_qnodes.append(qnode)
                    self.vectors_map[qnode] = vector
                found += hit_qnodes
                missing += [q for q in part if q not in hit_qnodes]
                # print(f'found:{len(found)} missing:{len(missing)}', file=sys.stderr)
        return found

    def get_vectors(self):
        '''Get embedding vectors.'''
        wanted_nodes = set(self.loaded_file.loc[:, self.input_column_name].fillna('')) - {''}
        if self.debug:
            print(f'Qnodes to lookup: {len(wanted_nodes)}', file=sys.stderr)
        embedding_file = self.kwargs['embedding_file']
        url = self.kwargs['embedding_url']
        if embedding_file and Path(embedding_file).exists():
            self._load_vectors_from_file(embedding_file, wanted_nodes)
            wanted_nodes = wanted_nodes - set(self.vectors_map.keys())
            if self.debug:
                print(f'Qnodes from file: {len(self.vectors_map)}', file=sys.stderr)

        if url and len(wanted_nodes) > 0:
            newly_found = self._load_vectors_from_server(url, list(wanted_nodes))
            if self.debug:
                print(f'Qnodes from server: {len(newly_found)}', file=sys.stderr)
            if embedding_file:
                self._save_new_to_file(embedding_file, newly_found)

    def process_vectors(self):
        """
        apply corresponding vector strategy to process the calculated vectors
        :return:
        """
        vector_strategy = self.kwargs.get("column_vector_strategy", "centroid-of-singletons")
        if vector_strategy == "centroid-of-singletons":
            if not self._centroid_of_singletons():
                raise TLException(f'Column_vector_stragtegy {vector_strategy} failed')
        elif vector_strategy == "centroid-of-voting":
            if not self._centroid_of_voting():
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
                each_score = 0.0
            else:
                each_score = self.compute_distance(self.centroid,
                                                   self.vectors_map[each_row[self.input_column_name]])

            scores.append(each_score)
        self.loaded_file[score_column_name] = scores

    def print_output(self):
        self.loaded_file.to_csv(sys.stdout, index=False)

    def _centroid_of_singletons(self) -> bool:

        # Use only results from exact-match
        data = self.loaded_file[self.loaded_file['method'] == 'exact-match']

        # Find singleton ids, i.e. ids from candidation generation sets of size one
        singleton_ids = []
        for ((col, row), group) in data.groupby(['column', 'row']):
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

    def _centroid_of_voting(self) -> bool:
        # Use only results from exact-match
        data = self.loaded_file

        if 'votes' not in data:
            return False

        # Find high confidence candidate ids by feature voting
        # Note that 'votes' column is by default str
        singleton_ids = []
        for ((col, row), group) in data.groupby(['column', 'row']):
            # employ voting on cheap features for non-singleton candidate set
            max_vote = group['votes'].astype(int).max()
            if self.min_vote > max_vote:
                continue
            if max_vote > 0:
                voted_candidate = group[group['votes'].astype(int) == max_vote].iloc[0]['kg_id']
                singleton_ids.append(voted_candidate)

        if not singleton_ids:
            return False

        missing_embedding_ids = []
        vectors = []
        for kg_id in singleton_ids:
            if kg_id not in self.vectors_map:
                missing_embedding_ids.append(kg_id)
            else:
                vectors.append(self.vectors_map[kg_id])

        # print(*missing_embedding_ids, file=sys.stderr)
        if len(missing_embedding_ids):
            print(f'_centroid_of_voting: Missing {len(missing_embedding_ids)} of {len(singleton_ids)}',
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
