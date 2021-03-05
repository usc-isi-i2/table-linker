import pandas as pd
from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError


class Utility(object):
    def __init__(self, es, output_column_name: str = 'retrieval_score', previous_match_column_name: str = 'retrieval_score'):
        self.es = es
        self.previous_match_column_name = previous_match_column_name
        self.ffv = FFV(previous_match_column_name)
        self.score_column_name = output_column_name

    def create_candidates_df(self, df, column, size, properties, method, lower_case=False):
        properties = properties.split(',')
        candidates_format = list()
        df_columns = df.columns

        if self.ffv.is_canonical_file(df):
            candidates_format = self.create_cfd_canonical(df, df_columns, column, size, properties, method, lower_case)

            return pd.DataFrame(candidates_format)

        elif self.ffv.is_candidates_file(df):
            grouped = df.groupby(by=['column', 'row', column])
            relevant_columns = [c for c in df_columns if c not in ['kg_id', 'kg_labels', 'method', self.previous_match_column_name]]
            for key_tuple, gdf in grouped:
                gdf.reset_index(inplace=True)
                tuple = ((c, gdf.at[0, c]) for c in relevant_columns)

                candidates_format.extend(
                    self.create_cfd_candidates(tuple, column, size, properties, method, lower_case))
            return pd.concat([df, pd.DataFrame(candidates_format)])

        else:
            raise UnsupportTypeError("The input df is neither a canonical format or a candidate format!")

    def create_cfd_canonical(self, df, relevant_columns, column, size, properties, method, lower_case):
        candidates_format = list()

        for i, row in df.iterrows():
            candidate_dict = self.es.search_term_candidates(row[column], size, properties, method,
                                                            lower_case=lower_case)

            if not candidate_dict:
                cf_dict = {}
                for key in relevant_columns:
                    if key not in ['kg_id', 'kg_labels', 'method', self.score_column_name]:
                        cf_dict[key] = row[key]

                cf_dict['kg_id'] = ""
                cf_dict['kg_labels'] = ""
                cf_dict['method'] = method
                cf_dict['kg_descriptions'] = ""
                cf_dict[self.score_column_name] = 0.0
                candidates_format.append(cf_dict)
            else:
                for kg_id in candidate_dict:
                    cf_dict = {}
                    for key in relevant_columns:
                        if key not in ['kg_id', 'kg_labels', 'method', self.score_column_name]:
                            cf_dict[key] = row[key]

                    cf_dict['kg_id'] = kg_id
                    cf_dict['kg_labels'] = candidate_dict[kg_id]['label_str']
                    cf_dict['method'] = method
                    cf_dict['kg_descriptions'] = candidate_dict[kg_id]['description_str']
                    cf_dict[self.score_column_name] = candidate_dict[kg_id]['score']
                    candidates_format.append(cf_dict)
        return candidates_format

    def create_cfd_candidates(self, key_tuple, column, size, properties, method, lower_case):
        candidates_format = list()

        _ = {}
        for k in key_tuple:
            _[k[0]] = k[1]

        candidate_dict = self.es.search_term_candidates(_[column], size, properties, method,
                                                        lower_case=lower_case)

        if not candidate_dict:
            cf_dict = {}

            for k in _:
                cf_dict[k] = _[k]

            cf_dict['kg_id'] = ""
            cf_dict['kg_labels'] = ""
            cf_dict['method'] = method
            cf_dict['kg_descriptions'] = ""
            cf_dict[self.score_column_name] = 0.0
            candidates_format.append(cf_dict)
        else:
            for kg_id in candidate_dict:
                cf_dict = {}
                for k in _:
                    cf_dict[k] = _[k]

                cf_dict['kg_id'] = kg_id
                cf_dict['kg_labels'] = candidate_dict[kg_id]['label_str']
                cf_dict['method'] = method
                cf_dict['kg_descriptions'] = candidate_dict[kg_id]['description_str']
                cf_dict[self.score_column_name] = candidate_dict[kg_id]['score']
                candidates_format.append(cf_dict)
        return candidates_format
