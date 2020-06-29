import copy
import requests
import typing
import hashlib

from tl.candidate_generation.phrase_query_json import query
from tl.utility.singleton import singleton
from requests.auth import HTTPBasicAuth


@singleton
class Search(object):
    def __init__(self, es_url, es_index, es_user=None, es_pass=None):
        self.es_url = es_url
        self.es_index = es_index
        self.es_user = es_user
        self.es_pass = es_pass
        self.query = copy.deepcopy(query)
        self.query_cache = dict()

    def search_es(self, query):
        es_search_url = '{}/{}/_search'.format(self.es_url, self.es_index)
        cache_key = self.get_query_hash(query)

        if cache_key not in self.query_cache:
            # return the top matched QNode using ES
            if self.es_user and self.es_pass:
                response = requests.post(es_search_url, json=query, auth=HTTPBasicAuth(self.es_user, self.es_pass))
            else:
                response = requests.post(es_search_url, json=query)

            if response.status_code == 200:
                response_output = response.json()['hits']['hits']
            else:
                response_output = None
            self.query_cache[cache_key] = response_output

        return self.query_cache[cache_key]

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
        # query_type = "phrase"
        slop = 0

        if len(search_term_tokens) <= 3:
            query_type = 'best_fields'

        # if len(search_term_tokens) <= 3:
        #     slop = 2
        #     query_type = "phrase"
        # if len(search_term_tokens) > 3:
        else:
            query_type = "phrase"
            slop = 10
            # slop = len(search_term_tokens) - 1

        query = self.query
        query['query']['bool']['must'][0]['multi_match']['query'] = search_term
        query['query']['bool']['must'][0]['multi_match']['type'] = query_type
        query['query']['bool']['must'][0]['multi_match']['slop'] = slop

        query['size'] = size

        if properties:
            query['query']['bool']['must'][0]['multi_match']['fields'] = properties

        return query

    def create_fuzzy_query(self, search_term, size, properties):
        query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": search_term,
                                "fields": properties,
                                "fuzziness": "AUTO"
                            }
                        }
                    ]
                }
            },
            "size": size
        }

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
            elif query_type == 'fuzzy-match':
                hits = self.search_es(self.create_fuzzy_query(search_term, size, properties))
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

    def search_node_pagerank(self, search_nodes: typing.List[str]) -> dict:
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
            node_pagerank = each["_source"]["pagerank"]
            label_dict[node_id] = node_pagerank
        return label_dict

    def get_query_hash(self, query: dict):
        """
        get the hash key for the query for cache
        :param query: input query dict
        :return: a str represent the hash key
        """
        hash_generator = hashlib.md5()
        hash_generator.update(str(query).encode('utf-8'))
        hash_search_result = hash_generator.hexdigest()
        hash_key = str(hash_search_result)
        return hash_key
