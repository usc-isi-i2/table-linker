import copy
import requests
import typing
from tl.candidate_generation.phrase_query_json import query
from requests.auth import HTTPBasicAuth


class Search(object):
    def __init__(self, es_url, es_index, es_user=None, es_pass=None):
        self.es_url = es_url
        self.es_index = es_index
        self.es_user = es_user
        self.es_pass = es_pass
        self.query = copy.deepcopy(query)

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

    def create_phrase_query(self, search_term, size, properties):

        search_term_tokens = search_term.split(' ')
        query_type = "phrase"
        slop = 0

        if len(search_term_tokens) == 1:
            query_type = 'best_fields'

        if len(search_term_tokens) <= 3:
            slop = 2
            query_type = "most_fields"

        if len(search_term_tokens) > 3:
            query_type = "phrase"
            slop = 10

        query = self.query
        query['query']['bool']['must'][0]['multi_match']['query'] = search_term
        query['query']['bool']['must'][0]['multi_match']['type'] = query_type
        query['query']['bool']['must'][0]['multi_match']['slop'] = slop

        query['size'] = size

        if properties:
            query['query']['bool']['must'][0]['multi_match']['fields'] = properties

        return query

        # elif len(search_term_tokens) > 3:
        #     for i in range(0, -4, -1):
        #         t_search_term = ' '.join(search_term_tokens[:i])
        #         query['query']['function_score']['query']['bool']['must'][0]['multi_match']['query'] = t_search_term
        #         response = self.search_es(query)
        #         if response is not None:
        #             return response
        #         else:
        #             continue

    def search_term_candidates(self, search_term_str, size, properties, query_type, lower_case=False):
        candidate_dict = {}
        search_terms = search_term_str.split('|')

        for search_term in search_terms:
            hits = None
            if query_type == 'exact-match':
                hits = self.search_es(self.create_exact_match_query(search_term, lower_case, size, properties))
            elif query_type == 'phrase-match':
                hits = self.search_es(self.create_phrase_query(search_term, size, properties))

            if hits is not None:
                for hit in hits:
                    all_labels = hit['_source'].get('labels', [])
                    all_labels.extend(hit['_source'].get('aliases', []))
                    candidate_dict[hit['_id']] = {'score': hit['_score'], 'label_str': '|'.join(all_labels)}
        return candidate_dict

    def search_node_labels(self, search_nodes: typing.List[str]) -> dict:
        query = {
            "query": {
                "ids": {
                    "values": search_nodes
                }
            },
            "size": len(search_nodes)
        }
        response = self.search_es(query)
        label_dict = {}
        for each in response:
            node_id = each["_source"]["id"]
            node_labels = each["_source"]["labels"] + each["_source"]["aliases"]
            label_dict[node_id] = node_labels
        return label_dict
