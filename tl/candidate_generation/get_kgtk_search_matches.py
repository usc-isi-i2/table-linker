import requests
import pandas as pd
from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError
from tl.exceptions import RequiredInputParameterMissingException


class KGTKSearchMatches(object):
    def __init__(self, api_url='https://kgtk.isi.edu/api'):
        self.api_url = api_url
        self.ffv = FFV()

    def get_matches(self, column, size=50, file_path=None, df=None, output_column_name: str = "retrieval_score"):
        """
        uses KGTK search API to retrieve identifiers of KG entities matching the input search term.

        Args:
            column: the column used for retrieving candidates.
            size: maximum number of candidates to retrieve, default is 50.
            file_path: input file in canonical format
            df: input dataframe in canonical format,
            output_column_name: the output column name where the normalized scores will be stored.Default is kgtk_retrieval_score
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

        results_dict = {}
        for uniq_label in uniq_labels:
            api_search_url = f"{self.api_url}/" \
                             f"{uniq_label}?extra_info=true&language=en&type=ngram&size={size}&lowercase=true"
            results_dict[uniq_label] = requests.get(api_search_url, verify=False).json()

        new_df_list = list()
        seen_dict = {}
        for i, row in df.iterrows():
            row_key = f"{row['column']}_{row['row']}_{row[column]}"
            if row_key not in seen_dict:
                search_results = results_dict.get(row[column], [])
                if len(search_results) > 0:
                    for sr in search_results:
                        _ = {}
                        for c in columns:
                            _[c] = row[c]

                        _['kg_id'] = sr['qnode']
                        _['pagerank'] = sr['pagerank']
                        kg_label = ''
                        if 'label' in sr and len(sr['label']) > 0:
                            kg_label = sr['label'][0]
                        _['kg_labels'] = kg_label
                        _['method'] = 'kgtk-search'
                        _[output_column_name] = sr['score']
                        new_df_list.append(_)
                else:
                    _ = {}
                    for c in columns:
                        _[c] = row[c]

                    _['kg_id'] = ''
                    _['pagerank'] = ''
                    _['kg_labels'] = ''
                    _['method'] = ''
                    _[output_column_name] = ''
                    new_df_list.append(_)
                seen_dict[row_key] = 1

        if self.ffv.is_canonical_file(df):
            return pd.DataFrame(new_df_list)

        if self.ffv.is_candidates_file(df):
            return pd.concat([df, pd.DataFrame(new_df_list)]).sort_values(by=['column', 'row', column])

        raise UnsupportTypeError("The input file is neither a canonical file or a candidate file!")
