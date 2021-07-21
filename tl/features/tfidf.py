import pandas as pd
from tl.features.utility import Utility
from tl.exceptions import RequiredInputParameterMissingException


class TFIDF(object):
    def __init__(self, output_column_name, feature_file, feature_name, total_docs, singleton_column, input_file=None,
                 df=None):
        """
        initialize the qnodes_dict as original tfidf required input, it is a dict with
            key: Q node id
            value: list of edges in format "property#node2"
        :param kwargs:
        """
        if df is None and input_file is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("input_file", "df"))

        if input_file is not None:
            self.input_df = pd.read_csv(input_file, dtype=object)
        elif df is not None:
            self.input_df = df
        self.input_df = self.input_df.sort_values(['column', 'row'])
        self.output_col_name = output_column_name
        self.N = float(total_docs)
        self.utils = Utility()

        self.feature_dict, self.feature_count_dict = self.utils.build_qnode_feature_dict(feature_file, feature_name)
        self.feature_idf_dict = self.utils.calculate_idf_features(self.feature_count_dict, self.N)
        self.singleton_column = singleton_column
        self.feature_name = feature_name

    def compute_tfidf(self):
        """
        Compute TF/IDF for all candidates.

        """
        hc_classes_idf = self.utils.normalize_idf_high_confidence_classes(self.input_df, self.singleton_column,
                                                                          self.feature_dict, self.feature_idf_dict)

        scores = []
        top_5_features = []
        top_5_col_name = f"top5_{self.feature_name}"
        for kg_id, column in zip(self.input_df['kg_id'], self.input_df['column']):
            _score = 0.0
            top_5_features_candidate = {}

            _feature_classes = self.feature_dict.get(kg_id, None)
            if _feature_classes:
                for _class in _feature_classes:
                    _score += hc_classes_idf[column].get(_class, 0.0)
                    top_5_features_candidate[_class] = hc_classes_idf[column].get(_class, 0.0)
            scores.append(_score)

            top_5_features.append("|".join([f"{k}:{'{:.3f}'.format(v)}" for k, v in
                                            sorted(top_5_features_candidate.items(),
                                                   key=lambda x: x[1], reverse=True)[:5]]))

        self.input_df[self.output_col_name] = scores
        self.input_df[top_5_col_name] = top_5_features

        return self.input_df
