import json
import pandas as pd
import sys

from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat


class Utility(object):
    def __init__(self, es, output_column_name: str = 'retrieval_score',
                 previous_match_column_name: str = 'retrieval_score'):
        self.es = es
        self.previous_match_column_name = previous_match_column_name
        self.ffv = FFV(previous_match_column_name)
        self.score_column_name = output_column_name

    def create_candidates_df(self, df, column, size, properties, method,
                             lower_case=False, auxiliary_fields=None,
                             auxiliary_folder=None, auxiliary_file_prefix='',
                             extra_musts=None, max_threads=50, identifier_property=None):
        properties = [_.strip() for _ in properties.split(',')]
        candidates_format = list()
        df_columns = df.columns
        all_candidates_aux_dict = {}
        max_threads = min(df.shape[0], max_threads)

        if self.ffv.is_canonical_file(df):
            rows = df.to_dict("records")
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                for _candidates_format, candidates_aux_dict in executor.map(
                        self.create_candidates, rows, repeat(df_columns),
                        repeat(column), repeat(size), repeat(properties),
                        repeat(method), repeat(lower_case),
                        repeat(auxiliary_fields), repeat(extra_musts), repeat(identifier_property)):
                    all_candidates_aux_dict = {**all_candidates_aux_dict,
                                               **candidates_aux_dict}
                    candidates_format.extend(_candidates_format)
            self.write_auxiliary_files(auxiliary_folder,
                                       all_candidates_aux_dict,
                                       auxiliary_fields,
                                       prefix=auxiliary_file_prefix)
            return pd.DataFrame(candidates_format)
        elif self.ffv.is_candidates_file(df):
            grouped = df.groupby(by=['column', 'row', column])
            relevant_columns = [c for c in df_columns if
                                c not in ['kg_id', 'kg_labels', 'method',
                                          'kg_descriptions',
                                          self.previous_match_column_name]]
            rows = list()
            for key_tuple, gdf in grouped:
                gdf.reset_index(inplace=True)
                rows.append({c: gdf.at[0, c] for c in relevant_columns})
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                for _candidates_format, candidates_aux_dict in executor.map(
                        self.create_candidates, rows,
                        repeat(relevant_columns), repeat(column),
                        repeat(size), repeat(properties), repeat(method),
                        repeat(lower_case), repeat(auxiliary_fields),
                        repeat(extra_musts)):
                    all_candidates_aux_dict = {**all_candidates_aux_dict,
                                               **candidates_aux_dict}
                    candidates_format.extend(_candidates_format)
            self.write_auxiliary_files(auxiliary_folder,
                                       all_candidates_aux_dict,
                                       auxiliary_fields,
                                       prefix=auxiliary_file_prefix)
            return pd.concat([df, pd.DataFrame(candidates_format)])
        else:
            raise UnsupportTypeError(
                "The input df is neither a canonical format"
                " or a candidate format!"
            )

    def create_candidates(self, row, relevant_columns, column, size,
                          properties, method, lower_case,
                          auxiliary_fields=None, extra_musts=None, identifier_property=None):
        candidates_format = list()

        _ = {}
        for k in row:
            _[k] = row[k]

        search_term_original = None
        if 'label' in relevant_columns and 'label' != column:
            # run the exact match query with cleaned and original label
            search_term_original = row['label']

        candidate_dict, candidate_aux_dict = self.es.search_term_candidates(
            _[column], size, properties,
            method, lower_case=lower_case,
            auxiliary_fields=auxiliary_fields,
            extra_musts=extra_musts,
            search_term_original=search_term_original,
            identifier_property=identifier_property)

        if not candidate_dict:
            cf_dict = {}

            for k in relevant_columns:
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
                for k in relevant_columns:
                    cf_dict[k] = _[k]

                cf_dict['kg_id'] = kg_id
                cf_dict['kg_labels'] = candidate_dict[kg_id]['label_str']
                cf_dict['kg_aliases'] = candidate_dict[kg_id]['alias_str']
                cf_dict['method'] = method
                cf_dict['kg_descriptions'] = (candidate_dict[kg_id]
                ['description_str'])
                cf_dict['pagerank'] = candidate_dict[kg_id]['pagerank_float']
                cf_dict[self.score_column_name] = (candidate_dict[kg_id]
                ['score'])
                candidates_format.append(cf_dict)
        return candidates_format, candidate_aux_dict

    def write_auxiliary_files(self, auxiliary_folder, all_candidates_aux_dict,
                              auxiliary_fields, prefix=''):
        _ = {}
        if auxiliary_fields is not None:
            for aux_field in auxiliary_fields:
                _[aux_field] = list()

            for qnode in all_candidates_aux_dict:
                qnode_dict = all_candidates_aux_dict[qnode]
                for aux_field in auxiliary_fields:
                    if aux_field in qnode_dict:
                        _val = qnode_dict[aux_field]
                        if aux_field == 'context':
                            _[aux_field].append({
                                qnode: _val
                            })
                        else:
                            if isinstance(_val, list):
                                _val = ','.join([str(x) for x in _val])
                            _[aux_field].append({
                                'qnode': qnode,
                                aux_field: _val
                            })

            for key in _:
                if key == 'context':
                    json_lines = _[key]
                    output_f = open(f"{auxiliary_folder}/{prefix}{key}.jl", 'w')
                    for jl in json_lines:
                        output_f.write(json.dumps(jl))
                        output_f.write('\n')
                else:
                    df = pd.DataFrame(_[key])
                    if len(df) > 0:
                        df.to_csv(f"{auxiliary_folder}/{prefix}{key}.tsv", sep='\t', index=False)
