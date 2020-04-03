import pandas as pd
from tl.candidate_generation.es_search import Search
from tl.exceptions import RequiredInputParameterMissingException


class PhraseQueryMatches(object):
    def __init__(self, es_url, es_index, es_user=None, es_pass=None):
        self.es = Search(es_url, es_index, es_user=es_user, es_pass=es_pass)

    def get_phrase_matches(self, column, properties="labels^2,aliases", size=50, file_path=None, df=None):
        """
        retrieves the identifiers of KG entities base on phrase match queries.

        Args:
            column: the column used for retrieving candidates.
            properties: a comma separated names of properties in the KG to search for exact match query: default is labels^2,aliases
            size: maximum number of candidates to retrieve, default is 50.
            file_path: input file in canonical format
            df: input dataframe in canonical format

        Returns: a dataframe in candidates format

        """
        if file_path is None and df is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("file_path", "df"))

        if file_path:
            df = pd.read_csv(file_path, dtype=object)

        df.fillna(value="", inplace=True)

        properties = properties.split(',')
        candidates_format = list()
        df_columns = df.columns

        for i, row in df.iterrows():
            candidate_dict = self.es.search_term_candidates(row[column], size, properties, 'phrase_matches')

            if not candidate_dict:
                cf_dict = {}
                for df_column in df_columns:
                    if df_column not in ['kg_id', 'kg_labels', 'method', 'retrieval_score']:
                        cf_dict[df_column] = row[df_column]
                cf_dict['kg_id'] = ""
                cf_dict['kg_labels'] = ""
                cf_dict['method'] = 'phrase-match'
                cf_dict['retrieval_score'] = 0.0
                candidates_format.append(cf_dict)
            else:
                for kg_id in candidate_dict:
                    cf_dict = {}
                    for df_column in df_columns:
                        if df_column not in ['kg_id', 'kg_labels', 'method', 'retrieval_score']:
                            cf_dict[df_column] = row[df_column]
                    cf_dict['kg_id'] = kg_id
                    cf_dict['kg_labels'] = candidate_dict[kg_id]['label_str']
                    cf_dict['method'] = 'phrase-match'
                    cf_dict['retrieval_score'] = candidate_dict[kg_id]['score']
                    candidates_format.append(cf_dict)

        return pd.DataFrame(candidates_format)
