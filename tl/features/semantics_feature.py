import pandas as pd
from tl.features.utility import Utility
from tl.exceptions import RequiredInputParameterMissingException

HC_CANDIDATE = 'hc_candidate'


class SemanticsFeature(object):
    def __init__(self, output_column: str,
                 feature_file: str,
                 feature_name: str,
                 total_docs: float,
                 pagerank_column: str,
                 retrieval_score_column: str,
                 hc_column: str,
                 input_file: str = None,
                 df: pd.DataFrame = None):

        if df is None and input_file is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("input_file", "df"))

        if input_file is not None:
            i_df = pd.read_csv(input_file)
            i_df['kg_id'].fillna("", inplace=True)
            self.input_df = i_df[i_df['kg_id'] != ""]

        elif df is not None:
            self.input_df = df

        self.output_col_name = output_column
        self.pagerank_column = pagerank_column
        self.retrieval_score_column = retrieval_score_column
        self.N = total_docs
        self.hc_column = hc_column
        self.utils = Utility()

        self.multiply_pgr_rts()

        self.feature_dict, self.feature_count_dict = self.utils.build_qnode_feature_dict(feature_file, feature_name)

        self.feature_idf_dict = self.utils.calculate_idf_features(self.feature_count_dict, self.N)

        self.feature_name = feature_name

        self.hc_candidates = self.find_hc_candidates()

        self.hc_classes = self.create_hc_classes_set()

        grouped = self.input_df.groupby(['column', 'row'])
        table_lens = {}

        for key, gdf in grouped:
            if key[0] not in table_lens:
                table_lens[key[0]] = 0
            table_lens[key[0]] += 1

        self.table_lengths = table_lens

    def create_hc_classes_set(self):
        hc_classes = set()
        for candidate in self.hc_candidates:
            hc_classes.update(self.feature_dict.get(candidate, []))
        return hc_classes

    def find_hc_candidates(self):
        if self.hc_column is not None:
            data = self.input_df[self.input_df[self.hc_column].astype(int) == 1]
        else:
            self.label_high_confidence_candidates()
            data = self.input_df[self.input_df[HC_CANDIDATE] == 1]
        hc_candidates = set(data['kg_id'])
        return hc_candidates

    def label_high_confidence_candidates(self):
        data = self.input_df
        data[HC_CANDIDATE] = 0
        data.loc[data['method'] == 'exact-match', HC_CANDIDATE] = 1
        grouped = data.groupby(['column', 'row'])
        table_lens = {}

        for key, gdf in grouped:
            if key[0] not in table_lens:
                table_lens[key[0]] = 0
            table_lens[key[0]] += 1
            top_fuzzy_match = gdf[gdf['method'] == 'fuzzy-augmented']['pgr_rts'].max()

            data.loc[data['pgr_rts'] == top_fuzzy_match, HC_CANDIDATE] = 1

        self.input_df = data
        self.table_lengths = table_lens

    def multiply_pgr_rts(self):
        # create a new feature by multiplying the pagerank and the retrieval score
        scores = []

        data = self.input_df.copy()
        for pagerank, retrieval_score in zip(data[self.pagerank_column],
                                             data[self.retrieval_score_column]):
            scores.append(pagerank * retrieval_score)

        data['pgr_rts'] = scores
        self.input_df = data

    def compute_semantic_feature(self):

        top_5_features = []
        scores = []
        top_5_col_name = f"top5_{self.output_col_name}"

        candidate_x_i, alpha_j = self.compute_xi_alphaj()
        _hc_column = self.hc_column if self.hc_column is not None else HC_CANDIDATE
        hc_classes_idf = self.utils.normalize_idf_high_confidence_classes(self.input_df, _hc_column,
                                                                          self.feature_dict, self.feature_idf_dict)

        for _qnode, column, row, hc_candidate in zip(self.input_df['kg_id'], self.input_df['column'],
                                                     self.input_df['row'], self.input_df[_hc_column]):

            top_5_features_candidate = {}

            _candidate_classes = self.feature_dict.get(_qnode, [])
            if hc_candidate == 0:
                scores.append(0.0)
                top_5_features.append("")
            else:
                _score = hc_candidate * sum([
                    candidate_x_i[column][row].get(_qnode, dict()).get(cc, 0.0) *
                    alpha_j[column].get(cc, 0.0) *
                    hc_classes_idf[column].get(cc, 0.0)
                    for cc in self.feature_dict.get(_qnode, [])])

                for cc in self.feature_dict.get(_qnode, []):
                    top_5_features_candidate[cc] = hc_classes_idf[column].get(cc, 0.0)

                scores.append(_score)
                top_5_features.append("|".join([f"{k}:{'{:.3f}'.format(v)}" for k, v in
                                                sorted(top_5_features_candidate.items(),
                                                       key=lambda x: x[1], reverse=True)[:5]]))
        self.input_df[self.output_col_name] = scores
        self.input_df[top_5_col_name] = top_5_features
        return self.input_df

    def compute_xi_alphaj(self) -> (dict, dict):
        if self.hc_column is not None:
            data = self.input_df[self.input_df[self.hc_column] == 1]
        else:
            data = self.input_df[self.input_df[HC_CANDIDATE] == 1]

        classes_count = {}
        candidate_x_i = {}
        alpha_j = {}

        for column, row, kg_id in zip(data['column'], data['row'], data['kg_id']):
            if column not in classes_count:
                classes_count[column] = {}
            if row not in classes_count[column]:
                classes_count[column][row] = {}

            candidate_classes = self.feature_dict.get(kg_id, [])

            for cc in candidate_classes:
                if kg_id not in classes_count[column][row]:
                    classes_count[column][row][kg_id] = {}

                if cc not in classes_count[column][row][kg_id]:
                    classes_count[column][row][kg_id][cc] = 0
                classes_count[column][row][kg_id][cc] += 1

        cell_class_count = {}
        for c in classes_count:
            c_d = classes_count[c]
            candidate_x_i[c] = {}
            if c not in cell_class_count:
                cell_class_count[c] = {}
            for r in c_d:
                if r not in cell_class_count[c]:
                    cell_class_count[c][r] = {}
                candidate_x_i[c][r] = {}
                r_d = c_d[r]
                for candidate in r_d:
                    candidate_x_i[c][r][candidate] = {}
                    classes = r_d[candidate]
                    for classs in classes:
                        if classs not in cell_class_count[c][r]:
                            cell_class_count[c][r][classs] = 0
                        cell_class_count[c][r][classs] += 1

        for c in classes_count:
            c_d = classes_count[c]
            for r in c_d:
                r_d = c_d[r]
                for candidate in r_d:
                    classes = r_d[candidate]
                    for classs in classes:
                        candidate_x_i[c][r][candidate][classs] = 1 / cell_class_count[c][r][classs]

        for c in candidate_x_i:
            c_d = candidate_x_i[c]
            alpha_j[c] = {}
            for r in c_d:
                r_d = c_d[r]
                for candidate in r_d:
                    classes = r_d[candidate]
                    for cc in classes:
                        if cc not in alpha_j[c]:
                            alpha_j[c][cc] = classes[cc]
                        else:
                            alpha_j[c][cc] += classes[cc]
        for column in alpha_j:
            for cc in alpha_j[column]:
                alpha_j[column][cc] = alpha_j[column][cc] / self.table_lengths[column]
        return candidate_x_i, alpha_j
