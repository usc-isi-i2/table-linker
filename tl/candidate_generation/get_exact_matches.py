import requests
import pandas as pd
from requests.auth import HTTPBasicAuth
from tl.exceptions import RequiredInputParameterMissingException


class ExactMatches(object):
    def __init__(self, es_url, es_index, es_user=None, es_pass=None):
        self.es_url = es_url
        self.es_index = es_index
        self.es_user = es_user
        self.es_pass = es_pass

    def search_es(self, query):

        es_search_url = '{}/{}/_search'.format(self.es_url, self.es_index)

        # return the top matched QNode using ES
        if self.es_user and self.es_pass:
            response = requests.post(es_search_url, json=query, auth=HTTPBasicAuth(self.es_user, self.es_pass))
        else:
            response = requests.post(es_search_url, json=query)

        if response.status_code == 200:
            return response.json()['hits']['hits']
        return None

    def create_exact_match_query(self, search_term, lower_case, size, properties):
        should = list()
        for property in properties:
            query_part = {
                "term": {
                    "{}.keyword_lower".format(property): {
                        "value": search_term
                    }
                }
            } if lower_case else \
                {
                    "term": {
                        "{}.keyword".format(property): {
                            "value": search_term
                        }
                    }
                }
            should.append(query_part)
        return {
            "query": {
                "bool": {
                    "should": should
                }
            },
            "size": size
        }

    def search_term_candidates(self, search_term_str, lower_case, size, properties):
        candidate_dict = {}
        search_terms = search_term_str.split('|')

        for search_term in search_terms:
            hits = self.search_es(self.create_exact_match_query(search_term, lower_case, size, properties))
            if hits is not None:
                for hit in hits:
                    all_labels = hit['_source'].get('labels', [])
                    all_labels.extend(hit['_source'].get('aliases', []))
                    candidate_dict[hit['_id']] = {'score': hit['_score'], 'label_str': '|'.join(all_labels)}
        return candidate_dict

    def get_exact_matches(self, column, properties="labels,aliases", lower_case=False, size=50, file_path=None,
                          df=None):
        """
        retrieves the identifiers of KG entities whose label or aliases match the input values exactly.

        Args:
            column: the column used for retrieving candidates.
            properties: a comma separated names of properties in the KG to search for exact match query: default is labels,aliases
            lower_case: case insensitive retrieval, default is case sensitive.
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
            candidate_dict = self.search_term_candidates(row[column], lower_case, size, properties)

            if not candidate_dict:
                cf_dict = {}
                for df_column in df_columns:
                    cf_dict[df_column] = row[df_column]
                cf_dict['kg_id'] = ""
                cf_dict['kg_labels'] = ""
                cf_dict['method'] = 'exact-match'
                cf_dict['retrieval_score'] = 0.0
                candidates_format.append(cf_dict)
            else:
                for kg_id in candidate_dict:
                    cf_dict = {}
                    for df_column in df_columns:
                        cf_dict[df_column] = row[df_column]
                    cf_dict['kg_id'] = kg_id
                    cf_dict['kg_labels'] = candidate_dict[kg_id]['label_str']
                    cf_dict['method'] = 'exact-match'
                    cf_dict['retrieval_score'] = candidate_dict[kg_id]['score']
                    candidates_format.append(cf_dict)

        return pd.DataFrame(candidates_format)
