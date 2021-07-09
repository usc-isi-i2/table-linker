import math


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
