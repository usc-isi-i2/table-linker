import copy

import hashlib
import logging
import re

import json
import requests
import sys
import typing
from requests.auth import HTTPBasicAuth
from typing import List

from tl.candidate_generation.phrase_query_json import query
from tl.candidate_generation.ngram_query import ngram_query
from tl.utility.singleton import singleton

romance_languages = {'en', 'de', 'es', 'fr', 'it', 'pt'}


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

    def create_exact_match_query(self,
                                 search_term: str,
                                 lower_case: bool,
                                 size: int,
                                 properties: List[str],
                                 extra_musts: dict = None,
                                 search_term_original: str = None):
        must = list()
        search_terms = list()
        search_terms.append(search_term.strip())
        if search_term_original != search_term:
            search_terms.append(search_term_original)

        highlight_fields = {
            "fields": {}
        }

        for property in properties:

            if lower_case:
                _field = "{}.keyword_lower".format(property)
                query_part = {
                    "terms": {
                        _field: [x.lower() for x in search_terms]
                    }
                }
                highlight_fields['fields'][_field] = {}
            else:
                _field = "{}.keyword".format(property)
                query_part = {
                    "term": {
                        _field: search_terms
                    }
                }
                highlight_fields['fields'][_field] = {}
            must.append(query_part)

        if extra_musts:
            must.append(extra_musts)

        must_not = [
            {
                "terms": {
                    "descriptions.en.keyword_lower": [
                        "wikimedia disambiguation page",
                        "wikimedia category",
                        "wikimedia kml file",
                        "wikimedia list article",
                        "wikimedia template",
                        "wikimedia module",
                        "wikinews article",
                        "wikimedia template page"
                    ]
                }
            }
        ]

        return {
            "query": {
                "bool": {
                    "must": must,
                    "must_not": must_not
                }
            },
            "highlight": highlight_fields,
            "size": size
        }

    def create_trigram_query(self, search_term,
                             size,
                             properties,
                             extra_musts=None):
        must = list()
        search_term = search_term.lower()

        highlight = {
            'fields': {}
        }
        for p in properties:
            highlight['fields'][p] = {}

        query_part = {
            "query_string": {
                "fields": properties,
                "query": search_term
            }
        }
        must.append(query_part)

        if extra_musts:
            must.extend(extra_musts) if isinstance(extra_musts, list) else must.append(extra_musts)

        must_not = [
            {
                "terms": {
                    "descriptions.en.keyword_lower": [
                        "wikimedia disambiguation page",
                        "wikimedia category",
                        "wikimedia kml file",
                        "wikimedia list article",
                        "wikimedia template",
                        "wikimedia module",
                        "wikinews article",
                        "wikimedia template page"
                    ]
                }
            }
        ]

        return {
            "query": {
                "bool": {
                    "must": must,
                    "must_not": must_not
                }
            },
            "size": size,
            "highlight": highlight
        }

    def create_external_identifier_query(self, search_term,
                                         size,
                                         properties,
                                         identifier_property):
        must = list()
        search_value = f"{identifier_property.upper()}:{search_term}" \
            if identifier_property is not None \
            else search_term
        for property in properties:
            query_part = {
                "term": {
                    "{}.keyword".format(property.lower()): {
                        "value": search_value
                    }
                }
            }
            must.append(query_part)

        must_not = [
            {
                "terms": {
                    "descriptions.en.keyword_lower": [
                        "wikimedia disambiguation page",
                        "wikimedia category",
                        "wikimedia kml file",
                        "wikimedia list article",
                        "wikimedia template",
                        "wikimedia module",
                        "wikinews article",
                        "wikimedia template page"
                    ]
                }
            }
        ]

        return {
            "query": {
                "bool": {
                    "must": must,
                    "must_not": must_not
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

    def create_fuzzy_augmented_query(self, search_term: str, size: int, lower_case: bool, properties: List[str],
                                     extra_musts: dict = None):
        if lower_case:
            properties = [prop + '.keyword_lower' for prop in properties]

        highlight = {
            'fields': {}
        }
        for prop in properties:
            _f = prop + '.keyword_lower' if lower_case else prop
            highlight['fields'][_f] = {}
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": search_term,
                                "fields": properties,
                                "fuzziness": "AUTO",
                                "prefix_length": 1,
                                "max_expansions": 3
                            }
                        }
                    ],
                    "must_not": [
                        {
                            "terms": {
                                "descriptions.en.keyword_lower": [
                                    "wikimedia disambiguation page",
                                    "wikimedia category",
                                    "wikimedia kml file",
                                    "wikimedia list article",
                                    "wikimedia template",
                                    "wikimedia module",
                                    "wikinews article"
                                ]
                            }
                        }
                    ]
                }
            },
            "size": size
        }
        if extra_musts:
            query['query']['bool']['must'].append(extra_musts)
        query['highlight'] = highlight
        return query

    def create_fuzzy_augmented_union(self, fuzzy_augmented_hits, fuzzy_augmented_keyword_lower_hits):
        seen_ids = set()
        hits = []
        for item in fuzzy_augmented_hits:
            if item['_id'] not in seen_ids:
                hits.append(item)
                seen_ids.add(item['_id'])

        for item in fuzzy_augmented_keyword_lower_hits:
            if item['_id'] not in seen_ids:
                hits.append(item)
                seen_ids.add(item['_id'])

        return hits

    def search_term_candidates(self,
                               search_term_str: str,
                               size: int,
                               properties,
                               query_type: str,
                               lower_case: bool = True,
                               auxiliary_fields: List[str] = None,
                               ignore_cache=False,
                               extra_musts: dict = None,
                               search_term_original: str = None,
                               identifier_property: str = None):
        candidate_dict = {}
        candidate_aux_dict = {}

        search_terms = search_term_str.split('|')
        parameter = self.get_query_hash((search_term_str, size, properties, query_type, lower_case))

        if parameter not in self.query_cache or ignore_cache:
            for search_term in search_terms:
                hits = None
                if query_type == 'exact-match':
                    hits = self.search_es(self.create_exact_match_query(search_term, lower_case, size, properties,
                                                                        extra_musts=extra_musts,
                                                                        search_term_original=search_term_original))
                    if not hits:
                        hits = self.search_es(self.create_exact_match_query(search_term, lower_case, size,
                                                                            ['all_labels_aliases'],
                                                                            extra_musts=extra_musts,
                                                                            search_term_original=search_term_original))
                elif query_type == 'ex-id-match':
                    hits = self.search_es(self.create_external_identifier_query(search_term,
                                                                                size,
                                                                                properties,
                                                                                identifier_property))
                elif query_type == 'trigram-match':
                    hits = self.search_es(self.create_trigram_query(search_term,
                                                                    size,
                                                                    properties,
                                                                    extra_musts=extra_musts))

                elif query_type == 'phrase-match':
                    hits = self.search_es(self.create_phrase_query(search_term, size, properties))
                elif query_type == 'ngram-match':
                    hits = self.search_es(self.create_ngram_query(search_term, size=size, extra_musts=extra_musts))
                elif query_type == 'fuzzy-match':
                    hits = self.search_es(self.create_fuzzy_query(search_term, size, properties))
                elif query_type == 'fuzzy-augmented':
                    fuzzy_augmented_hits = self.search_es(
                        self.create_fuzzy_augmented_query(search_term, size, lower_case, properties,
                                                          extra_musts=extra_musts))
                    fuzzy_augmented_keyword_lower_hits = self.search_es(
                        self.create_fuzzy_augmented_query(search_term, size, not (lower_case), properties,
                                                          extra_musts=extra_musts))
                    hits = self.create_fuzzy_augmented_union(fuzzy_augmented_hits, fuzzy_augmented_keyword_lower_hits)
                if hits is not None:
                    hits_copy = hits.copy()  # prevent change on query cache
                    for hit in hits_copy:
                        if re.match(r'Q\d+', hit['_id']):
                            _source = hit['_source']
                            _id = hit['_id']
                            highlight = hit.get('highlight', None)
                            description = ""
                            pagerank = 0.0
                            all_labels, all_aliases = self.get_all_labels_aliases(_source.get('labels', {}),
                                                                                  _source.get('aliases', {}),
                                                                                  _source.get('ascii_labels', []),
                                                                                  _source.get('abbreviated_name', {}),
                                                                                  _source.get('extra_aliases', []),
                                                                                  _source.get('external_identifiers',
                                                                                              []),
                                                                                  _source.get('redirect_text',
                                                                                              {}),
                                                                                  _source.get('wikipedia_anchor_text',
                                                                                              {}),
                                                                                  _source.get('wikitable_anchor_text',
                                                                                              {}),
                                                                                  highlight=highlight
                                                                                  )

                            if 'en' in _source['descriptions'] and len(_source['descriptions']['en']) > 0:
                                description = "|".join(_source['descriptions']['en'])
                            if 'pagerank' in _source:
                                pagerank = _source['pagerank']

                            candidate_dict[_id] = {'score': hit['_score'],
                                                   'label_str': '|'.join(all_labels),
                                                   'alias_str': '|'.join(all_aliases),
                                                   'description_str': description,
                                                   'pagerank_float': pagerank}

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

    @staticmethod
    def get_all_labels_aliases(labels: dict,
                               aliases: dict,
                               ascii_labels: List[str],
                               abbreviated_name: dict,
                               extra_aliases: List[str],
                               external_identifiers: List[str],
                               redirect_text: dict,
                               wikipedia_anchor_text: dict,
                               wikitable_anchor_text: dict,
                               highlight: dict = None) -> (List[str], List[str]):
        all_labels = set()
        all_aliases = set()

        relevant_languages = set()
        if highlight is not None:
            for k in highlight:
                relevant_languages.add(k.split(".")[1])
        if len(relevant_languages) == 0:
            relevant_languages = romance_languages

        if labels:
            for lang in labels:
                if lang in relevant_languages:
                    all_labels.update(x for x in labels[lang] if x.strip())

        if aliases:
            for lang in aliases:
                if lang in relevant_languages:
                    all_aliases.update(x for x in aliases[lang] if x.strip())

        if ascii_labels:
            all_aliases.update(x for x in ascii_labels if x.strip())

        if extra_aliases:
            all_aliases.update(x for x in extra_aliases if x.strip())

        if external_identifiers:
            all_aliases.update(x for x in external_identifiers if x.strip())

        if abbreviated_name:
            for lang in abbreviated_name:
                if lang in relevant_languages:
                    all_aliases.update(x for x in abbreviated_name[lang] if x.strip())

        if redirect_text:
            for lang in redirect_text:
                if lang in relevant_languages:
                    all_aliases.update(x for x in redirect_text[lang] if x.strip())

        if wikipedia_anchor_text:
            for lang in wikipedia_anchor_text:
                if lang in relevant_languages:
                    all_aliases.update(x for x in wikipedia_anchor_text[lang] if x.strip())

        if wikitable_anchor_text:
            for lang in wikitable_anchor_text:
                if lang in relevant_languages:
                    all_aliases.update(x for x in wikitable_anchor_text[lang] if x.strip())

        return list(all_labels), list(all_aliases)

    @staticmethod
    def create_ngram_query(search_term: str, language: str = 'en', size: int = 20, extra_musts: dict = None) -> dict:
        _search_terms = search_term.split(' ')
        _search_terms = [x[:20] for x in _search_terms]

        search_term_truncated = ' '.join(_search_terms)

        search_field = f'all_labels.{language}.ngram'

        exact_match_field = f'all_labels.{language}.keyword_lower'

        query_part = {
            "query_string": {
                "fields": [
                    f"{search_field}^1.0",
                    f"{exact_match_field}^100"
                ],
                "query": search_term_truncated,
                "default_operator": "AND"
            }
        }

        ngrams_query = copy.deepcopy(ngram_query)
        ngrams_query['query']['function_score']['query']['bool']['must'].append(query_part)

        if extra_musts:
            ngrams_query['query']['function_score']['query']['bool']['must'].append(extra_musts)

        ngrams_query['size'] = size
        ngrams_query['highlight'] = {
            'fields': {
                search_field: {},
                exact_match_field: {}
            }
        }

        return ngrams_query
