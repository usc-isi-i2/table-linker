import requests
import pandas as pd
from typing import List
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat

from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError
from tl.exceptions import RequiredInputParameterMissingException
from tl.candidate_generation.es_search import Search
from tl.candidate_generation.utility import Utility


class KGTKSearchMatches(object):
    def __init__(self, es_url, es_index, api_url='https://kgtk.isi.edu/api', es_user=None, es_pass=None):
        self.api_url = api_url
        self.ffv = FFV()
        self.es_search = Search(es_url, es_index, es_user, es_pass)
        self.utility = Utility(self.es_search)

    def get_matches(self, column, size=20, file_path=None, df=None, output_column_name: str = "retrieval_score",
                    auxiliary_fields: List[str] = None, auxiliary_folder: str = None,
                    auxiliary_file_prefix='kgtk_search_', max_threads=50):
        """
        uses KGTK search API to retrieve identifiers of KG entities matching the input search term.

        Args:
            column: the column used for retrieving candidates.
            size: maximum number of candidates to retrieve, default is 20.
            file_path: input file in canonical format
            df: input dataframe in canonical format,
            output_column_name: the output column name where the normalized scores will be stored.Default is
                                kgtk_retrieval_score
        Returns: a dataframe in candidates format

        """
        if file_path is None and df is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("file_path", "df"))

        if file_path:
            df = pd.read_csv(file_path, dtype=object)

        df.fillna(value="", inplace=True)

        columns = df.columns

        uniq_labels = list(df[column].unique())
        max_threads = min(len(uniq_labels), max_threads)

        results_dict = {}
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            for _results_dict in executor.map(
                    self.kgtk_api_search, uniq_labels, repeat(size)):
                results_dict.update(_results_dict)
        # for uniq_label in uniq_labels:
        #     results_dict.update(self.kgtk_api_search(size, uniq_label))

        new_df_list = list()
        seen_dict = {}
        all_candidates = []
        candidate_aux_dict = {}
        for i, row in df.iterrows():
            row_key = f"{row['column']}_{row['row']}_{row[column]}"
            row_candidates = set()
            if row_key not in seen_dict:
                search_results = results_dict.get(row[column], [])
                if len(search_results) > 0:
                    for sr in search_results:
                        _ = {}
                        for c in columns:
                            _[c] = row[c]

                        _['kg_id'] = sr['qnode']
                        row_candidates.add(sr['qnode'])
                        _['pagerank'] = sr['pagerank']
                        kg_label = []
                        kg_description = ''

                        if 'label' in sr and len(sr['label']) > 0:
                            kg_label.extend(sr['label'])
                        if 'alias' in sr and len(sr['alias']) > 0:
                            kg_label.extend(sr['alias'])
                        _['kg_labels'] = "|".join(kg_label)

                        _['method'] = 'kgtk-search'

                        if 'description' in sr and len(sr['description']) > 0:
                            kg_description = "|".join(sr['description'])
                        _['kg_descriptions'] = kg_description

                        _[output_column_name] = sr['score']
                        new_df_list.append(_)
                    all_candidates.extend(self.es_search.get_node_info(list(row_candidates)))
                else:
                    _ = {}
                    for c in columns:
                        _[c] = row[c]

                    _['kg_id'] = ''
                    _['pagerank'] = ''
                    _['kg_labels'] = ''
                    _['method'] = 'kgtk-search'
                    _['kg_descriptions'] = ''
                    _[output_column_name] = ''
                    new_df_list.append(_)
                seen_dict[row_key] = 1

        for candidate in all_candidates:
            _id = candidate['_id']
            _source = candidate['_source']
            if _id not in candidate_aux_dict:
                candidate_aux_dict[_id] = {}

            if auxiliary_fields is not None:
                for auxiliary_field in auxiliary_fields:
                    if auxiliary_field in _source:
                        candidate_aux_dict[_id][auxiliary_field] = _source[auxiliary_field]

        self.utility.write_auxiliary_files(auxiliary_folder, candidate_aux_dict, auxiliary_fields,
                                           prefix=auxiliary_file_prefix)

        if self.ffv.is_canonical_file(df):
            return pd.DataFrame(new_df_list)

        if self.ffv.is_candidates_file(df):
            return pd.concat([df, pd.DataFrame(new_df_list)]).sort_values(by=['column', 'row', column])

        raise UnsupportTypeError("The input file is neither a canonical file or a candidate file!")

    def kgtk_api_search(self, uniq_label: str, size: int) -> dict:
        results_dict = dict()
        api_search_url = f"{self.api_url}?q=" \
                         f"{uniq_label}&extra_info=true&language=en&type=ngram&size={size}&lowercase=true"
        results_dict[uniq_label] = requests.get(api_search_url).json()
        return results_dict
