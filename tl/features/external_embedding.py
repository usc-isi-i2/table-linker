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
        self.centroid = dict()
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
        self.loaded_file = self.loaded_file.sort_values(['column', 'row'])

    def get_result_df(self):
        return self.loaded_file

    def _load_vectors_from_file(self, embedding_file, qnodes):
        with open(embedding_file, 'rt') as fd:
            for line in fd:
                if 'qnode' not in line:
                    fields = line.strip().split('\t')
                    qnode = fields[0]
                    embeddings = [float(x) for x in fields[1].split(",")]
                    if qnode in qnodes:
                        # self.vectors_map[qnode] = np.asarray(list(map(float, fields[1:])))
                        self.vectors_map[qnode] = np.asarray(embeddings)

    def _save_new_to_file(self, embedding_file, new_qnodes):
        with open(embedding_file, 'at') as fd:
            for qnode in new_qnodes:
                vector = self.vectors_map[qnode]
                line = f'{qnode}\t'
                line += ','.join([str(x) for x in vector])
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
            # query response example: see http://ckg07:9200/wikidatadwd-augmented/_doc/Q2
            query = {
                "_source": ["id", "graph_embedding_complex"],
                "size": batch_size,
                "query": {
                    "ids": {
                        "values": part
                    }
                }
            }
            response = requests.get(search_url, json=query)
            result = response.json()

            # print(result, file=sys.stderr)

            if result['hits']['total'] == 0:
                missing += part
            else:
                hit_qnodes = []
                for hit in result['hits']['hits']:
                    if 'graph_embedding_complex' in hit['_source']:
                        qnode = hit['_source']['id']
                        if isinstance(hit['_source']['graph_embedding_complex'], str):
                            vector = np.asarray(list(map(float, hit['_source']['graph_embedding_complex'].split(','))))
                        else:
                            vector = np.asarray(list(map(float, hit['_source']['graph_embedding_complex'])))
                        hit_qnodes.append(qnode)
                        self.vectors_map[qnode] = vector
                found += hit_qnodes
                missing += [q for q in part if q not in hit_qnodes]
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
        elif vector_strategy == "centroid-of-lof":
            if not self._centroid_of_lof():
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

        self.loaded_file[score_column_name] = self.loaded_file.apply(
            lambda x: self.compute_cosine_distance(x[self.input_column_name], x.column), axis=1)

    def compute_cosine_distance(self, qnode: str, column_num: str) -> float:
        if ((isinstance(qnode, float) and math.isnan(qnode))
                or qnode is np.nan
                or qnode not in self.vectors_map):
            _score = 0.0
        else:
            _score = self.compute_distance(self.centroid[column_num],
                                           self.vectors_map[qnode])
        return _score

    def print_output(self):
        self.loaded_file.to_csv(sys.stdout, index=False)

    def _centroid_of_singletons(self) -> bool:
        grouped_obj = self.loaded_file.groupby('column')
        for column, col_candidates_df in grouped_obj:
            # Use only results from exact-match
            data = col_candidates_df[col_candidates_df['method'] == 'exact-match']
            # Find singleton ids, i.e. ids from candidate generation sets of size one
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
            self.centroid[column] = np.mean(np.array(vectors), axis=0)

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

    def _centroid_of_lof(self) -> bool:
        from sklearn.neighbors import LocalOutlierFactor

        results = []
        grouped_obj = self.loaded_file.groupby('column')
        for column, col_candidates_df in grouped_obj:
            data = col_candidates_df.copy()

            # label exact-match-singleton candidates
            if 'singleton' not in data:
                tmp_df = pd.DataFrame()
                for ((col, row), group) in data.groupby(['column', 'row']):
                    group['singleton'] = 0
                    if len(group[group['method'] == 'exact-match']) == 1 and pd.notna(
                            group[group['method'] == 'exact-match'].iloc[0]['kg_id']):
                        # exact match is singleton, non-nan candidate set
                        group.loc[group['method'] == 'exact-match', 'singleton'] = 1
                    tmp_df = tmp_df.append(group)
                data = tmp_df
            # assert 1 in pd.unique(data['is_ems']), 'there is no exact-match-singleton in this dataset!'

            # check lof strategy
            lof_strategy = self.kwargs.get("lof_strategy", 'ems-mv')
            data['is_lof'] = -1
            if lof_strategy == 'ems-mv':
                # check input data: should contain column 'vote_by_classifier'
                assert 'vote_by_classifier' in data, f"Missing column 'vote_by_classifier' to use lof-strategy: ems-mv"
                assert 'singleton' in data, f"Missing column 'singleton' to use lof-strategy: ems-mv"
                data.loc[data['vote_by_classifier'].astype(int) == 1, 'is_lof'] = 1
                data.loc[data['singleton'].astype(int) == 1, 'is_lof'] = 1
            elif lof_strategy == 'ems-only':
                assert 'singleton' in data, f"Missing column 'singleton' to use lof-strategy: ems-only"
                data.loc[data['singleton'].astype(int) == 1, 'is_lof'] = 1
            elif lof_strategy == 'pseudo-gt':
                assert 'pseudo_gt' in data, f"Missing column 'pseudo_gt' to use lof-strategy: pseudo-gt"
                data.loc[data['pseudo_gt'].astype(float) == 1.0, 'is_lof'] = 1
            else:
                raise ValueError(f"No such lof strategy available! {lof_strategy}")
            lof_candidate_ids = list(data[data['is_lof'] == 1]['kg_id'])

            if not lof_candidate_ids:
                print("No pseudo GT available, using all exact matches as high precision", file=sys.stderr)
                # return False
                data.loc[(data['method'] == 'exact-match') & (data['kg_id'] != ""), 'is_lof'] = 1
                lof_candidate_ids = list(data[data['is_lof'] == 1]['kg_id'])

            # obtain graph embedding
            missing_embedding_ids = []
            data['retrieved_embedding_vector'] = -1
            vectors = []
            for kg_id in lof_candidate_ids:
                if kg_id not in self.vectors_map:
                    missing_embedding_ids.append(kg_id)
                    vectors.append([np.nan])
                else:
                    vectors.append(self.vectors_map[kg_id])
            if len(missing_embedding_ids):
                print(f'_centroid_of_lof: Missing {len(missing_embedding_ids)} of {len(lof_candidate_ids)}',
                      file=sys.stderr)

            data.loc[data['is_lof'] == 1, 'retrieved_embedding_vector'] = [-1 if len(v) == 1 else 1 for v in vectors]
            data.loc[data['retrieved_embedding_vector'] == -1, 'is_lof'] = -1

            vectors = np.array([v for v in vectors if len(v) > 1])

            assert data['is_lof'].equals(
                data['retrieved_embedding_vector']), "Not all lof candidates have retrieved embedding!"
            data.drop(['retrieved_embedding_vector'], axis=1, inplace=True)

            # run outlier removal algorithm
            n_neigh = min(10, len(vectors) // 3)

            lof_failed = False
            try:
                clf = LocalOutlierFactor(n_neighbors=n_neigh, contamination=0.4, metric='cosine')
                lof_pred = clf.fit_predict(vectors)
                assert len(lof_pred) == len(vectors)

                lof_vectors = vectors[lof_pred == 1]
                print(f"Outlier removal generates {len(lof_vectors)} lof-voted candidates", file=sys.stderr)
                data.loc[data['is_lof'] == 1, 'is_lof'] = lof_pred

                # centroid of lof-voted candidates
                self.centroid[column] = np.mean(lof_vectors, axis=0)
            except Exception:
                print('Column_vector_stragtegy centroid_of_lof failed', file=sys.stderr)
                lof_failed = True

            if lof_failed:
                self.centroid[column] = np.mean(vectors, axis=0)
            assert "is_lof" in data, "is_lof column doesn't exist!"
            results.append(data)

        self.loaded_file = pd.concat(results)
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
