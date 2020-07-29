import math
import pandas as pd

from collections import defaultdict
from tl.candidate_generation.es_search import Search
from tl.exceptions import RequiredColumnMissingException


class TFIDF(object):
    def __init__(self, **kwargs):
        """
        initialize the qnodes_dict as original tfidf required input, it is a dict with
            key: Q node id
            value: list of edges in format "property#node2"
        :param kwargs:
        """
        self.input_df = pd.read_csv(kwargs['input_file'], dtype=object)
        self.output_col_name = kwargs["output_column_name"]
        self.similarity_column = kwargs["similarity_column"]
        if self.similarity_column not in self.input_df.columns:
            raise RequiredColumnMissingException("Similarity column {} does not exist in input.".format(self.similarity_column))

        self.es = Search(kwargs["url"], kwargs["index"], es_user=kwargs.get("user"), es_pass=kwargs.get("password"))
        self.qnodes_dict = {}
        nodes_candidates = self.input_df["kg_id"].dropna().unique().tolist()
        for each in self.es.get_node_info(nodes_candidates):
            node_id = each["_source"]["id"]
            node_edges_info = each["_source"]["edges"]
            self.qnodes_dict[node_id] = node_edges_info
        # properties_classes_map is a dict mapping the P nodes or Q nodes to unique integer id (starting from 0)
        self.properties_classes_map = self.create_all_properties_classes_map()

    @staticmethod
    def get_properties_classes_for_qnode(edges):
        properties_classes_set = set()
        for wd_prop_val in edges:
            edge, value = wd_prop_val.split('#', 1)
            if len(value) > 6 and value[:3] == '"""' and value[-3:] == '"""':
                value = value[3:-3]
            elif len(value) > 2:
                if value[0] == "'" and value[-1] == "'":
                    value = value[1:-1]
                elif value[0] == '"' and value[-1] == '"':
                    value = value[1:-1]

            # add edges
            properties_classes_set.add(edge)
            # if "isinstance"
            if edge == 'P31':
                properties_classes_set.add(value)
        return properties_classes_set

    def create_all_properties_classes_map(self):
        # map each properties to a corresponding unique number id
        properties_classes_set = set()
        for qnode in self.qnodes_dict:
            v = self.qnodes_dict[qnode]
            properties_classes_set.update(self.get_properties_classes_for_qnode(v))
        return {p: idx for idx, p in enumerate(properties_classes_set)}

    def create_feature_vector_dict(self, label_candidates_dict):
        # creates input for tfidf computation
        feature_vector_dict = {}
        _p_c_len = len(self.properties_classes_map)

        for label, candidates in label_candidates_dict.items():
            feature_vector_dict[label] = {}
            for candidate in candidates:
                feature_vector = [0] * _p_c_len
                if candidate in self.qnodes_dict:
                    prop_class_list = self.get_properties_classes_for_qnode(self.qnodes_dict[candidate])
                    for _p_c in prop_class_list:
                        if _p_c in self.properties_classes_map:
                            feature_vector[self.properties_classes_map[_p_c]] = 1
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

        for _, each in self.input_df.iterrows():
            if isinstance(each["kg_id"], str) and each["kg_id"] != "":
                label_candidates_dict[each["label"]].append(each["kg_id"])
                if each["method"] == "exact-match":
                    high_precision_candidates[each["label"]].add(each["kg_id"])

        candidates = self.create_feature_vector_dict(label_candidates_dict)
        feature_count = len(self.properties_classes_map)
        tfidf_values = [{'tf': 0, 'df': 0, 'idf': 0} for _ in range(feature_count)]
        corpus_num = sum(len(qs) for _, qs in candidates.items())

        # get normalized similarity score
        similarity_score_col = self.input_df[self.similarity_column].astype(float)
        max_score = max(similarity_score_col)
        min_score = min(similarity_score_col)
        temp = self.input_df.copy()
        if max_score != 1.0 or min_score < 0:
            score_range = max_score - min_score
            temp["||similarity_score_col_normalized||"] = similarity_score_col.apply(lambda x: (x-min_score)/score_range)
        else:
            temp["||similarity_score_col_normalized||"] = similarity_score_col

        similarity_score_dict = {}
        for _, each_row in temp.iterrows():
            similarity_score_dict[(each_row["label"], each_row["kg_id"])] = each_row["||similarity_score_col_normalized||"]

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
                tfidf_values[f_idx]['idf'] = math.log(float(corpus_num) / tfidf_values[f_idx]['df'], 10)

        # compute final score
        ret = {}
        for e in candidates:
            for q, v in candidates[e].items():
                ret[q] = 0
                for f_idx in range(feature_count):
                    ret[q] += tfidf_values[f_idx]['tf'] * tfidf_values[f_idx]['idf'] * v[f_idx] \
                              * similarity_score_dict.get((e, q), 1)

        output_df = self.input_df.copy()
        output_df[self.output_col_name] = output_df['kg_id'].map(ret)
        return output_df
