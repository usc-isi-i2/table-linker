import pandas as pd
import sys
from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError
import concurrent


class Utility(object):
    def __init__(self, es, output_column_name: str = 'retrieval_score',
                 previous_match_column_name: str = 'retrieval_score'):
        self.es = es
        self.previous_match_column_name = previous_match_column_name
        self.ffv = FFV(previous_match_column_name)
        self.score_column_name = output_column_name

    def create_candidates_df(self, df, column, size, properties, method, lower_case=True, auxiliary_fields=None,
                             auxiliary_folder=None, auxiliary_file_prefix='', extra_musts: dict = None):
        properties = [_.strip() for _ in properties.split(',')]
        candidates_format = list()
        df_columns = df.columns
        all_candidates_aux_dict = {}

        if self.ffv.is_canonical_file(df):
            candidates_format, all_candidates_aux_dict = self.create_cfd_canonical(df, df_columns, column, size,
                                                                                   properties, method, lower_case,
                                                                                   auxiliary_fields=auxiliary_fields,
                                                                                   extra_musts=extra_musts)

            self.write_auxiliary_files(auxiliary_folder,
                                       all_candidates_aux_dict,
                                       auxiliary_fields,
                                       prefix=auxiliary_file_prefix)
            return pd.DataFrame(candidates_format)

        elif self.ffv.is_candidates_file(df):
            grouped = df.groupby(by=['column', 'row', column])
            relevant_columns = [c for c in df_columns if
                                c not in ['kg_id', 'kg_labels', 'method', 'kg_descriptions',
                                          self.previous_match_column_name]]
            tuples = list()
            for key_tuple, gdf in grouped:
                gdf.reset_index(inplace=True)
                tuples.append(((c, gdf.at[0, c]) for c in relevant_columns))
            
            def create_cf_candidates_threaded(tuple):
                nonlocal all_candidates_aux_dict
                nonlocal candidates_format
                _candidates_format, candidates_aux_dict = self.create_cfd_candidates(tuple, column, size,
                                                                                     properties, method, lower_case,
                                                                                     auxiliary_fields=auxiliary_fields,
                                                                                     extra_musts=extra_musts)
                all_candidates_aux_dict = {**all_candidates_aux_dict, **candidates_aux_dict}

                candidates_format.extend(_candidates_format)
            
            max_threads = 50
            # print(f'Max thread used: {max_threads}', file=sys.stderr)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                executor.map(create_cf_candidates_threaded, tuples)
            self.write_auxiliary_files(auxiliary_folder,
                                       all_candidates_aux_dict,
                                       auxiliary_fields, prefix=auxiliary_file_prefix)
            return pd.concat([df, pd.DataFrame(candidates_format)])

        else:
            raise UnsupportTypeError("The input df is neither a canonical format or a candidate format!")

    def create_cfd_canonical(self, df, relevant_columns, column, size, properties, method, lower_case,
                             auxiliary_fields=None, extra_musts=None):
        candidates_format = list()
        all_candidates_aux_dict = {}

        def call_es(row):
            nonlocal all_candidates_aux_dict
            nonlocal candidates_format
            candidate_dict, candidate_aux_dict = self.es.search_term_candidates(row[column],
                                                                                size,
                                                                                properties,
                                                                                method,
                                                                                lower_case=lower_case,
                                                                                auxiliary_fields=auxiliary_fields,
                                                                                extra_musts=extra_musts)
            all_candidates_aux_dict = {**all_candidates_aux_dict, **candidate_aux_dict}

            if not candidate_dict:
                cf_dict = {}
                for key in relevant_columns:
                    if key not in ['kg_id', 'kg_labels', 'method', self.score_column_name]:
                        cf_dict[key] = row[key]

                cf_dict['kg_id'] = ""
                cf_dict['kg_labels'] = ""
                cf_dict['kg_aliases'] = ""
                cf_dict['method'] = method
                cf_dict['kg_descriptions'] = ""
                cf_dict['pagerank'] = 0.0
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
                    cf_dict['kg_aliases'] = candidate_dict[kg_id]['alias_str']
                    cf_dict['method'] = method
                    cf_dict['kg_descriptions'] = candidate_dict[kg_id]['description_str']
                    cf_dict['pagerank'] = candidate_dict[kg_id]['pagerank_float']
                    cf_dict[self.score_column_name] = candidate_dict[kg_id]['score']
                    candidates_format.append(cf_dict)
        
        max_threads = 50
        # print(f'Max thread used: {max_threads}', file=sys.stderr)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            executor.map(call_es, df.to_dict("records"))
            
        return candidates_format, all_candidates_aux_dict

    def create_cfd_candidates(self, key_tuple, column, size, properties, method, lower_case, auxiliary_fields=None,
                              extra_musts=None):
        candidates_format = list()

        _ = {}
        for k in key_tuple:
            _[k[0]] = k[1]

        candidate_dict, candidate_aux_dict = self.es.search_term_candidates(_[column],
                                                                            size,
                                                                            properties,
                                                                            method,
                                                                            lower_case=lower_case,
                                                                            auxiliary_fields=auxiliary_fields,
                                                                            extra_musts=extra_musts)

        if not candidate_dict:
            cf_dict = {}

            for k in _:
                cf_dict[k] = _[k]

            cf_dict['kg_id'] = ""
            cf_dict['kg_labels'] = ""
            cf_dict['kg_aliases'] = ""
            cf_dict['method'] = method
            cf_dict['kg_descriptions'] = ""
            cf_dict['pagerank'] = 0.0
            cf_dict[self.score_column_name] = 0.0
            candidates_format.append(cf_dict)
        else:
            for kg_id in candidate_dict:
                cf_dict = {}
                for k in _:
                    cf_dict[k] = _[k]

                cf_dict['kg_id'] = kg_id
                cf_dict['kg_labels'] = candidate_dict[kg_id]['label_str']
                cf_dict['kg_aliases'] = candidate_dict[kg_id]['alias_str']
                cf_dict['method'] = method
                cf_dict['kg_descriptions'] = candidate_dict[kg_id]['description_str']
                cf_dict['pagerank'] = candidate_dict[kg_id]['pagerank_float']
                cf_dict[self.score_column_name] = candidate_dict[kg_id]['score']
                candidates_format.append(cf_dict)
        return candidates_format, candidate_aux_dict

    def write_auxiliary_files(self, auxiliary_folder, all_candidates_aux_dict, auxiliary_fields, prefix=''):
        _ = {}
        if auxiliary_fields is not None:
            for aux_field in auxiliary_fields:
                _[aux_field] = list()

            for qnode in all_candidates_aux_dict:
                qnode_dict = all_candidates_aux_dict[qnode]
                for aux_field in auxiliary_fields:
                    if aux_field in qnode_dict:
                        _val = qnode_dict[aux_field]
                        if isinstance(_val, list):
                            _val = ','.join([str(x) for x in _val])
                        _[aux_field].append({
                            'qnode': qnode,
                            aux_field: _val
                        })

            for key in _:
                df = pd.DataFrame(_[key])
                if len(df) > 0:
                    df.to_csv(f"{auxiliary_folder}/{prefix}{key}.tsv", sep='\t', index=False)
