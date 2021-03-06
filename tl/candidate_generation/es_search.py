import copy
import requests
import typing
from typing import List
import hashlib
import logging

from tl.candidate_generation.phrase_query_json import query
from tl.utility.singleton import singleton
from requests.auth import HTTPBasicAuth


@singleton
class Search(object):
    def __init__(self, es_url: str, es_index: str, es_user: str = None, es_pass: str = None):
        self.es_url = es_url
        self.es_index = es_index
        self.es_user = es_user
        self.es_pass = es_pass
        self.query = copy.deepcopy(query)
        self.query_cache = dict()
        self.logger = logging.getLogger(__name__)

    def search_es(self, query: dict):
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
                self.logger.error("Query ES error with response {}!".format(response.status_code))
                self.logger.error(response.json())
            self.query_cache[cache_key] = response_output

        return self.query_cache[cache_key]

    def create_exact_match_query(self, search_term: str, lower_case: bool, size: int, properties: List[str]):
        must = list()
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
            must.append(query_part)

        return {
            "query": {
                "bool": {
                    "must": must
                }
            },
            "size": size
        }

    def create_phrase_query(self, search_term: str, size: int, properties):

        search_term_tokens = search_term.split(' ')
        slop = 0

        if len(search_term_tokens) <= 3:
            query_type = 'best_fields'
        else:
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

    def create_fuzzy_query(self, search_term: str, size: int, properties):
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

    def search_term_candidates(self, search_term_str: str, size: int, properties, query_type: str,
                               lower_case: bool = False, auxiliary_fields: List[str] = None):
        candidate_dict = {}
        candidate_aux_dict = {}

        search_terms = search_term_str.split('|')
        parameter = self.get_query_hash((search_term_str, size, properties, query_type, lower_case))

        if parameter not in self.query_cache:
            for search_term in search_terms:
                hits = None
                if query_type == 'exact-match':
                    hits = self.search_es(self.create_exact_match_query(search_term, lower_case, size, properties))
                elif query_type == 'phrase-match':
                    hits = self.search_es(self.create_phrase_query(search_term, size, properties))
                elif query_type == 'fuzzy-match':
                    hits = self.search_es(self.create_fuzzy_query(search_term, size, properties))
                if hits is not None:
                    hits_copy = hits.copy()  # prevent change on query cache
                    for hit in hits_copy:
                        _source = hit['_source']
                        _id = hit['_id']
                        all_labels = []
                        description = ""
                        if 'en' in _source['labels']:
                            all_labels.extend(_source['labels']['en'])
                        if 'en' in _source['aliases']:
                            all_labels.extend(_source['aliases']['en'])
                        if 'en' in _source['descriptions'] and len(_source['descriptions']['en']) > 0:
                            description = "|".join(_source['descriptions']['en'])

                        candidate_dict[_id] = {'score': hit['_score'],
                                               'label_str': '|'.join(all_labels),
                                               'description_str': description}
                        if _id not in candidate_aux_dict:
                            candidate_aux_dict[_id] = {}

                        if auxiliary_fields is not None:
                            for auxiliary_field in auxiliary_fields:
                                if auxiliary_field in _source:
                                    candidate_aux_dict[_id][auxiliary_field] = _source[auxiliary_field]

            self.query_cache[parameter] = candidate_dict

        return self.query_cache[parameter], candidate_aux_dict

    def get_node_info(self, search_nodes: typing.List[str]) -> dict:
        query = {
            "query": {
                "ids": {
                    "values": search_nodes
                }
            },
            "size": len(search_nodes)
        }
        response = self.search_es(query)
        return response

    def search_node_labels(self, search_nodes: typing.List[str]) -> dict:
        label_dict = {}
        for each in self.get_node_info(search_nodes):
            node_id = each["_source"]["id"]
            node_labels = each["_source"]["labels"] + each["_source"]["aliases"]
            label_dict[node_id] = node_labels
        return label_dict

    def search_node_pagerank(self, search_nodes: typing.List[str]) -> dict:
        label_dict = {}
        for each in self.get_node_info(search_nodes):
            node_id = each["_source"]["id"]
            node_pagerank = each["_source"]["pagerank"]
            label_dict[node_id] = node_pagerank
        return label_dict

    def get_query_hash(self, query: typing.Union[tuple, dict, list]):
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
