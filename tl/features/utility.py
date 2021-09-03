import math
from collections import defaultdict


class Utility(object):

    @staticmethod
    def build_qnode_feature_dict(features_file: str, feature_name: str) -> (dict, dict):
        """
        Reads a features file and the feature name,returns two dictionaries:
        1. Qnode to all classes
        2. Qnode(class) to TFIDF score
        Args:
            features_file: A file created while candidate generation
            feature_name: name of the column in the file to read the features from

        Returns: 2 dictionaries

        """
        feature_dict = {}
        feature_count_dict = {}

        f = open(features_file)
        feature_idx = -1
        node_idx = -1

        for line in f:
            row = line.strip().split('\t')
            if feature_name in row:  # first line
                feature_idx = row.index(feature_name)
                node_idx = row.index('qnode')
            else:
                _features = row[feature_idx].split("|")  # [Q103838820:3247, Q103940464:9346440, Q10800557:73492,...]
                feature_val = []
                for x in _features:
                    vals = x.split(":")
                    feature_val.append(vals[0])
                    feature_count_dict[vals[0]] = float(vals[1])
                feature_dict[row[node_idx]] = feature_val
        return feature_dict, feature_count_dict

    @staticmethod
    def calculate_idf_features(feature_count_dict: dict, N: float) -> dict:
        _ = {}
        for c in feature_count_dict:
            _[c] = math.log(N / feature_count_dict[c])
        return _

    @staticmethod
    def normalize_idf_high_confidence_classes(input_df, hc_column, feature_dict, feature_idf_dict) -> defaultdict:
        grouped_obj = input_df.groupby('column')
        # hc = high confidence
        hc_classes_count = defaultdict(dict)
        hc_classes_idf = defaultdict(dict)
        for column, col_candidates_df in grouped_obj:
            hc_candidates = col_candidates_df[col_candidates_df[hc_column].astype(float) == 1.0]['kg_id'].unique().tolist()
            for candidate in hc_candidates:
                if candidate in feature_dict:
                    classes = feature_dict[candidate]
                    for c in classes:
                        if c not in hc_classes_count[column]:
                            hc_classes_count[column][c] = 0
                        hc_classes_count[column][c] += 1

        # multiply hc class count with idf
        for column, col_hc_classes in hc_classes_count.items():
            for c in col_hc_classes:
                hc_classes_idf[column][c] = col_hc_classes[c] * feature_idf_dict[c]

        # normalize the high confidence idf scores so that they sum to 1
        hc_classes_idf_sum = {}
        for column, col_idf in hc_classes_idf.items():
            hc_classes_idf_sum[column] = sum([col_idf[x] for x in col_idf])
        for column, col_idf in hc_classes_idf.items():
            for c in col_idf:
                hc_classes_idf[column][c] = hc_classes_idf[column][c] / hc_classes_idf_sum[column]
        return hc_classes_idf
