import math
import pandas as pd
from collections import defaultdict


class TFIDF(object):
    def __init__(self, input_file, output_column_name, feature_file, feature_name, total_docs):
        """
        initialize the qnodes_dict as original tfidf required input, it is a dict with
            key: Q node id
            value: list of edges in format "property#node2"
        :param kwargs:
        """
        self.input_df = pd.read_csv(input_file, dtype=object)
        self.output_col_name = output_column_name
        self.N = float(total_docs)

        self.feature_dict, self.feature_count_dict = self.build_qnode_feature_dict(feature_file, feature_name)
        self.feature_idf_dict = self.calculate_idf_features()

        # properties_classes_map is a dict mapping the P nodes or Q nodes to unique integer id (starting from 0)
        self.features_classes_map = self.create_all_features_classes_map()
        self.features_classes_map_reverse = {v: k for k, v in self.features_classes_map.items()}

        self.create_singleton_feature()

    def calculate_idf_features(self):
        _ = {}
        for c in self.feature_count_dict:
            _[c] = math.log(self.N / self.feature_count_dict[c])
        return _

    @staticmethod
    def build_qnode_feature_dict(features_file: str, feature_name: str) -> (dict, dict):
        feature_dict = {}
        feature_count_dict = {}
        _df = pd.read_csv(features_file, sep='\t')
        for _, row in _df.iterrows():
            _features = row[feature_name].split("|")  # [Q103838820:3247, Q103940464:9346440, Q10800557:73492,...]
            feature_val = []
            for x in _features:
                vals = x.split(":")
                feature_val.append(vals[0])
                feature_count_dict[vals[0]] = float(vals[1])
            feature_dict[row['qnode']] = feature_val
        return feature_dict, feature_count_dict

    def create_singleton_feature(self):
        d = self.input_df[self.input_df['method'] == 'exact-match'].groupby(['column', 'row'])[['kg_id']].count()
        l = list(d[d['kg_id'] == 1].index)
        singleton_feat = []
        for i, row in self.input_df.iterrows():
            col_num, row_num = row['column'], row['row']
            if (col_num, row_num) in l and row['method'] == 'exact-match':
                singleton_feat.append(1)
            else:
                singleton_feat.append(0)
        self.input_df['singleton'] = singleton_feat

    def normalize_idf_high_confidence_classes(self):
        # hc = high confidence
        hc_candidates = self.input_df[self.input_df['singleton'] == 1]['kg_id'].unique().tolist()
        hc_classes_count = {}
        hc_classes_idf = {}
        for candidate in hc_candidates:
            if candidate in self.feature_dict:
                classes = self.feature_dict[candidate]
                for c in classes:
                    if c not in hc_classes_count:
                        hc_classes_count[c] = 0
                    hc_classes_count[c] += 1

        # multiply hc class count with idf
        for c in hc_classes_count:
            hc_classes_idf[c] = hc_classes_count[c] * self.feature_idf_dict[c]

        # normalize the high confidence idf scores so that they sum to 1
        hc_classes_idf_sum = sum([hc_classes_idf[x] for x in hc_classes_idf])
        for c in hc_classes_idf:
            hc_classes_idf[c] = hc_classes_idf[c] / hc_classes_idf_sum
        return hc_classes_idf

    def create_all_features_classes_map(self):
        # map each feature to a corresponding unique number id
        features_classes_set = set()
        for qnode in self.feature_dict:
            v = self.feature_dict[qnode]
            features_classes_set.update(set(v))
        return {p: idx for idx, p in enumerate(features_classes_set)}

    def create_feature_vector_dict(self, label_candidates_dict):
        # creates input for tfidf computation
        feature_vector_dict = {}
        _p_c_len = len(self.features_classes_map)

        for label, candidates in label_candidates_dict.items():
            feature_vector_dict[label] = {}
            for candidate in candidates:
                feature_vector = [0] * _p_c_len
                if candidate in self.feature_dict:
                    _features_class_list = self.feature_dict[candidate]
                    for _fc in _features_class_list:
                        if _fc in self.features_classes_map:
                            feature_vector[self.features_classes_map[_fc]] = 1
                feature_vector_dict[label][candidate] = feature_vector
        return feature_vector_dict

    def compute_tfidf(self):
        """
        Compute TF/IDF for all candidates.

        Args:
            candidates:
                ```
                {
                    e1: {
                        q1: [f1, f2, f3],
                        q2: [f1, f2, f3]
                    },
                    'e2': ...
                }
                ```
                `[f1, f2, f3]` is feature vector. All vectors should have same length.
            feature_count: Length of feature vector.
            high_preision_candidates: `{e1: q1, e2: q2}`.
                If None, all qnodes will be used to compute tf.

        Returns:
            ```
            {
                e1: {q1: 1.0, q2: 0.9},
                e2: {q3: 0.1}
            }
        """

        label_candidates_dict = defaultdict(list)
        high_precision_candidates = defaultdict(set)
        hc_classes_idf = self.normalize_idf_high_confidence_classes()
        for _, each in self.input_df.iterrows():
            if isinstance(each["kg_id"], str) and each["kg_id"] != "":
                label_candidates_dict[each["label"]].append(each["kg_id"])
                if each["singleton"] == 1:
                    high_precision_candidates[each["label"]].add(each["kg_id"])

        candidates = self.create_feature_vector_dict(label_candidates_dict)
        feature_count = len(self.features_classes_map)
        tfidf_values = [{'tf': 0, 'df': 0, 'idf': 0} for _ in range(feature_count)]
        corpus_num = sum(len(qs) for _, qs in candidates.items())

        # compute tf
        for f_idx in range(feature_count):
            for e in candidates:
                for q, v in candidates[e].items():
                    if high_precision_candidates.get(e) and q in high_precision_candidates[e]:
                        if v[f_idx] == 1:
                            tfidf_values[f_idx]['tf'] += 1
                    else:
                        tfidf_values[f_idx]['tf'] += 1

        # compute df
        for f_idx in range(feature_count):
            for e in candidates:
                for q, v in candidates[e].items():
                    if v[f_idx] == 1:
                        tfidf_values[f_idx]['df'] += 1

        # compute idf
        for f_idx in range(len(tfidf_values)):
            if tfidf_values[f_idx]['df'] == 0:
                tfidf_values[f_idx]['idf'] = 0
            else:
                tfidf_values[f_idx]['idf'] = math.log(float(corpus_num) / tfidf_values[f_idx]['df'])

        # compute final score
        ret = {}
        for e in candidates:
            for q, v in candidates[e].items():
                ret[q] = 0
                for f_idx in range(feature_count):
                    ret[q] += tfidf_values[f_idx]['tf'] * tfidf_values[f_idx]['idf'] * v[f_idx] * hc_classes_idf.get(
                        self.features_classes_map_reverse[f_idx], 0)

        output_df = self.input_df.copy()
        output_df[self.output_col_name] = output_df['kg_id'].map(ret)
        return output_df
