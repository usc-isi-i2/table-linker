import pandas as pd
from tl.file_formats_validator import FFV


class Utility(object):
    def __init__(self, es):
        self.es = es
        self.ffv = FFV()

    def create_candidates_df(self, df, column, size, properties, method, lower_case=False):
        properties = properties.split(',')
        candidates_format = list()
        df_columns = df.columns

        if self.ffv.is_canonical_file(df):
            candidates_format = self.create_cfd(df, df_columns, column, size, properties, method, lower_case)

            return pd.DataFrame(candidates_format)

        elif self.ffv.is_candidates_file(df):
            grouped = df.groupby(by=['column', 'row', column])
            for key_tuple, gdf in grouped:
                candidates_format.extend(self.create_cfd(gdf, key_tuple, column, size, properties, method, lower_case))
            return pd.concat(df, pd.DataFrame(candidates_format))

    def create_cfd(self, df, relevant_columns, column, size, properties, method, lower_case):
        candidates_format = list()
        for i, row in df.iterrows():
            candidate_dict = self.es.search_term_candidates(row[column], size, properties, method,
                                                            lower_case=lower_case)

            if not candidate_dict:
                cf_dict = {}
                for key in relevant_columns:
                    cf_dict[key] = row[key]

                cf_dict['kg_id'] = ""
                cf_dict['kg_labels'] = ""
                cf_dict['method'] = method
                cf_dict['retrieval_score'] = 0.0
                candidates_format.append(cf_dict)
            else:
                for kg_id in candidate_dict:
                    cf_dict = {}
                    for key in relevant_columns:
                        cf_dict[key] = row[key]
                    cf_dict['kg_id'] = kg_id
                    cf_dict['kg_labels'] = candidate_dict[kg_id]['label_str']
                    cf_dict['method'] = method
                    cf_dict['retrieval_score'] = candidate_dict[kg_id]['score']
                    candidates_format.append(cf_dict)
        return candidates_format
