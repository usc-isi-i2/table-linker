import pandas as pd
from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError


class Utility(object):
    def __init__(self, es, output_column_name: str = 'retrieval_score',
                 previous_match_column_name: str = 'retrieval_score'):
        self.es = es
        self.previous_match_column_name = previous_match_column_name
        self.ffv = FFV(previous_match_column_name)
        self.score_column_name = output_column_name

    def create_candidates_df(self, df, column, size, properties, method, lower_case=False, auxiliary_fields=None,
                             auxiliary_folder=None):
        properties = properties.split(',')
        candidates_format = list()
        df_columns = df.columns
        all_candidates_aux_dict = {}

        if self.ffv.is_canonical_file(df):
            candidates_format, all_candidates_aux_dict = self.create_cfd_canonical(df, df_columns, column, size,
                                                                                   properties, method, lower_case,
                                                                                   auxiliary_fields=auxiliary_fields)

            self.write_auxiliary_files(auxiliary_folder, all_candidates_aux_dict, auxiliary_fields)
            return pd.DataFrame(candidates_format)

        elif self.ffv.is_candidates_file(df):
            grouped = df.groupby(by=['column', 'row', column])
            relevant_columns = [c for c in df_columns if
                                c not in ['kg_id', 'kg_labels', 'method', 'kg_descriptions',
                                          self.previous_match_column_name]]
            for key_tuple, gdf in grouped:
                gdf.reset_index(inplace=True)
                tuple = ((c, gdf.at[0, c]) for c in relevant_columns)

                _candidates_format, candidates_aux_dict = self.create_cfd_candidates(tuple, column, size,
                                                                                     properties, method, lower_case,
                                                                                     auxiliary_fields=auxiliary_fields)
                all_candidates_aux_dict = {**all_candidates_aux_dict, **candidates_aux_dict}

                candidates_format.extend(_candidates_format)
            self.write_auxiliary_files(auxiliary_folder, all_candidates_aux_dict, auxiliary_fields)
            return pd.concat([df, pd.DataFrame(candidates_format)])

        else:
            raise UnsupportTypeError("The input df is neither a canonical format or a candidate format!")

    def create_cfd_canonical(self, df, relevant_columns, column, size, properties, method, lower_case,
                             auxiliary_fields=None):
        candidates_format = list()
        all_candidates_aux_dict = {}

        for i, row in df.iterrows():
            candidate_dict, candidate_aux_dict = self.es.search_term_candidates(row[column],
                                                                                size,
                                                                                properties,
                                                                                method,
                                                                                lower_case=lower_case,
                                                                                auxiliary_fields=auxiliary_fields)

            all_candidates_aux_dict = {**all_candidates_aux_dict, **candidate_aux_dict}

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
        return candidates_format, all_candidates_aux_dict

    def create_cfd_candidates(self, key_tuple, column, size, properties, method, lower_case, auxiliary_fields=None):
        candidates_format = list()

        _ = {}
        for k in key_tuple:
            _[k[0]] = k[1]

        candidate_dict, candidate_aux_dict = self.es.search_term_candidates(_[column],
                                                                            size,
                                                                            properties,
                                                                            method,
                                                                            lower_case=lower_case,
                                                                            auxiliary_fields=auxiliary_fields)

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
        return candidates_format, candidate_aux_dict

    def write_auxiliary_files(self, auxiliary_folder, all_candidates_aux_dict, auxiliary_fields):
        _ = {}
        if auxiliary_fields is not None:
            for aux_field in auxiliary_fields:
                _[aux_field] = list()

            for qnode in all_candidates_aux_dict:
                qnode_dict = all_candidates_aux_dict[qnode]
                for aux_field in auxiliary_fields:
                    if aux_field in qnode_dict:
                        _[aux_field].append({
                            'qnode': qnode,
                            aux_field: qnode_dict[aux_field]
                        })

            for key in _:
                df = pd.DataFrame(_[key])
                df.to_csv(f"{auxiliary_folder}/{key}.tsv", sep='\t', index=False)
