import math
import pandas as pd


class TFIDF(object):
    def __init__(self, input_file, output_column_name, feature_file, feature_name, total_docs, singleton_column):
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
        self.singleton_column = singleton_column

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

    def normalize_idf_high_confidence_classes(self):
        # hc = high confidence
        hc_candidates = self.input_df[self.input_df[self.singleton_column] == "1"]['kg_id'].unique().tolist()
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

    def compute_tfidf(self):
        """
        Compute TF/IDF for all candidates.

        """

        hc_classes_idf = self.normalize_idf_high_confidence_classes()
        output = []
        for i, row in self.input_df.iterrows():
            _score = 0.0
            _feature_classes = self.feature_dict.get(row['kg_id'], None)
            if _feature_classes:
                for _class in _feature_classes:
                    _score += hc_classes_idf.get(_class, 0.0)
            row[self.output_col_name] = _score
            output.append(row)

        return pd.DataFrame(output)
