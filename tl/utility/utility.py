import requests
import json
import gzip
import pandas as pd
import re
import typing
import os
import traceback
import pprint

from collections import defaultdict
from tl.exceptions import FileNotExistError, UploadError
from requests.auth import HTTPBasicAuth


class Utility(object):
    @staticmethod
    def build_elasticsearch_file(kgtk_file_path, label_fields,
                                 mapping_file_path, output_path,
                                 alias_fields=None, pagerank_fields=None,
                                 black_list_file_path=None,
                                 extra_info=False,
                                 add_text=False,
                                 description_properties=None,
                                 copy_to_properties=None,
                                 es_version=7,
                                 separate_languages=True
                                 ):
        """
        builds a json lines file and a mapping file to support retrieval of candidates
        It is assumed that the file is sorted by subject and predicate, in order to be able to process it in a streaming fashion

        Args:
            kgtk_file_path: a file in KGTK format
            label_fields: field in the kgtk file to be used as labels
            mapping_file_path: output mapping file path for elasticsearch
            output_path: output json lines path, converted from the input kgtk file
            alias_fields: field in the kgtk file to be used as aliases
            pagerank_fields: field in the kgtk file to be used as pagerank
            black_list_file_path: path to black list file
        Returns: Nothing

        """
        file_names = ["KGTK input file", "Black list file"]
        file_paths = [kgtk_file_path, black_list_file_path]
        mapping_parameter_dict = defaultdict(list)
        for each_file_name, each_file_path in zip(file_names, file_paths):
            if each_file_path and not os.path.exists(each_file_path):
                raise FileNotExistError("{} {} does not exist!".format(each_file_name, each_file_path))

        if black_list_file_path:
            with open(black_list_file_path, "r") as f:
                black_list_dict = json.load(f)
                black_list_dict = {k: set(v) for k, v in black_list_dict.items()}
        else:
            black_list_dict = {}

        skipped_node_count = 0
        labels = label_fields.split(',')
        aliases = alias_fields.split(',') if alias_fields else []
        pagerank = pagerank_fields.split(',') if pagerank_fields else []
        descriptions = description_properties.split(',') if description_properties else []
        mapping_parameter_dict['str_fields_need_index'] = ['id', 'labels', 'is_class']
        if len(aliases):
            mapping_parameter_dict['str_fields_need_index'].append('aliases')
        if len(pagerank):
            mapping_parameter_dict['float_fields_need_index'].append('pagerank')
        if len(descriptions):
            mapping_parameter_dict['str_fields_need_index'].append('descriptions')

        human_nodes_set = {"Q15632617", "Q95074", "Q5"}
        skip_edges = set(labels + aliases)

        if kgtk_file_path.endswith(".gz"):
            kgtk_file = gzip.open(kgtk_file_path)
        else:
            kgtk_file = open(kgtk_file_path, "r")

        if output_path.endswith(".gz"):
            output_file = gzip.open(output_path, mode='wt')
        else:
            output_file = open(output_path, 'w')

        _labels = dict()
        _aliases = dict()
        _descriptions = dict()
        _instance_ofs = set()
        data_type = None
        all_langs = set()
        lang = 'en'
        qnode_statement_count = 0
        is_class = False
        _wikitable_anchor_text = {}
        _wikipedia_anchor_text = {}
        _abbreviated_name = {}
        _redirect_text = {}
        _text_embedding = ''
        _graph_embeddings_complex = ''

        _pagerank = 0.0

        current_node_info = defaultdict(set)
        prev_node = None
        i = 0
        is_human_name = False

        column_header_dict = None
        try:
            for line in kgtk_file:
                i += 1
                if i % 1000000 == 0:
                    print('Processed {} lines...'.format(i))
                if isinstance(line, bytes):
                    line = line.decode('utf-8')
                line = line.replace('\n', '')
                if column_header_dict is None and 'node1' in line and 'id' in line and 'node2' in line:
                    # header line
                    cols = line.replace('\n', '').split('\t')
                    column_header_dict = {
                        # 'id': cols.index('id'),
                        'node1': cols.index('node1'),
                        'label': cols.index('label'),
                        'node2': cols.index('node2')
                    }

                # if line.startswith('Q'):
                else:
                    vals = line.split('\t')
                    node1_id = column_header_dict['node1']
                    label_id = column_header_dict['label']
                    node2_id = column_header_dict['node2']
                    node1 = vals[node1_id]
                    if '-' not in node1:  # ignore qualifiers
                        if prev_node is None:
                            prev_node = node1
                        if node1 != prev_node:
                            skipped_node_count = Utility._write_one_node(_labels=_labels, _aliases=_aliases,
                                                                         _pagerank=_pagerank,
                                                                         black_list_dict=black_list_dict,
                                                                         current_node_info=current_node_info,
                                                                         is_human_name=is_human_name,
                                                                         prev_node=prev_node,
                                                                         skipped_node_count=skipped_node_count,
                                                                         output_file=output_file, skip_edges=skip_edges,
                                                                         extra_info=extra_info,
                                                                         _descriptions=_descriptions,
                                                                         add_all_text=add_text,
                                                                         data_type=data_type,
                                                                         instance_ofs=_instance_ofs,
                                                                         qnode_statement_count=qnode_statement_count,
                                                                         is_class=is_class,
                                                                         wikitable_anchor_text=_wikitable_anchor_text,
                                                                         wikipedia_anchor_text=_wikipedia_anchor_text,
                                                                         abbreviated_name=_abbreviated_name,
                                                                         redirect_text=_redirect_text,
                                                                         text_embedding=_text_embedding,
                                                                         graph_embeddings_complex=_graph_embeddings_complex
                                                                         )
                            # initialize for next node
                            _labels = dict()
                            _aliases = dict()
                            _descriptions = dict()
                            _instance_ofs = set()
                            data_type = None
                            _pagerank = 0.0
                            current_node_info = defaultdict(set)
                            prev_node = node1
                            is_human_name = False
                            lang = 'en'
                            qnode_statement_count = 0
                            is_class = False
                            _wikitable_anchor_text = {}
                            _wikipedia_anchor_text = {}
                            _abbreviated_name = {}
                            _redirect_text = {}
                            _text_embedding = None
                            _graph_embeddings_complex = None

                        qnode_statement_count += 1
                        current_node_info[vals[label_id]].add(str(vals[node2_id]))
                        if vals[label_id] in labels:
                            if separate_languages:
                                tmp_val, lang = Utility.separate_language_text_tag(vals[node2_id])
                            else:
                                tmp_val = Utility.remove_language_tag(vals[node2_id])
                            if lang not in _labels:
                                _labels[lang] = set()
                                all_langs.add(lang)

                            if tmp_val.strip() != '':
                                _labels[lang].add(tmp_val)
                        elif vals[label_id] in aliases:
                            if separate_languages:
                                tmp_val, lang = Utility.separate_language_text_tag(vals[node2_id])
                            else:
                                tmp_val = Utility.remove_language_tag(vals[node2_id])
                            if lang not in _aliases:
                                _aliases[lang] = set()
                                all_langs.add(lang)

                            if tmp_val.strip() != '':
                                _aliases[lang].add(tmp_val)
                        elif vals[label_id] in pagerank:
                            tmp_val = Utility.to_float(vals[node2_id])
                            if tmp_val:
                                _pagerank = tmp_val
                        elif vals[label_id] in descriptions:
                            if separate_languages:
                                tmp_val, lang = Utility.separate_language_text_tag(vals[node2_id])
                            else:
                                tmp_val = Utility.remove_language_tag(vals[node2_id])
                            if lang not in _descriptions:
                                _descriptions[lang] = set()
                                all_langs.add(lang)
                            if tmp_val.strip() != '':
                                _descriptions[lang].add(tmp_val)
                        elif vals[label_id].strip() == 'isa_star':
                            _instance_ofs.add(vals[node2_id])
                        elif vals[label_id].strip() == 'datatype':
                            data_type = vals[node2_id]
                        elif vals[label_id] == 'P279' and vals[node2_id].startswith('Q'):
                            is_class = True
                        elif vals[label_id] == 'wikipedia_table_anchor':
                            tmp_val, lang = Utility.separate_language_text_tag(vals[node2_id])
                            if tmp_val.strip() != "":
                                if lang not in _wikitable_anchor_text:
                                    _wikitable_anchor_text[lang] = set()
                                _wikitable_anchor_text[lang].add(tmp_val)
                        elif vals[label_id] == 'wikipedia_anchor':
                            tmp_val, lang = Utility.separate_language_text_tag(vals[node2_id])
                            if tmp_val.strip() != "":
                                if lang not in _wikipedia_anchor_text:
                                    _wikipedia_anchor_text[lang] = set()
                                _wikipedia_anchor_text[lang].add(tmp_val)
                        elif vals[label_id] == 'redirect_from':
                            tmp_val, lang = Utility.separate_language_text_tag(vals[node2_id])
                            if tmp_val.strip() != "":
                                if lang not in _redirect_text:
                                    _redirect_text[lang] = set()
                                _redirect_text[lang].add(tmp_val)
                        elif vals[label_id] == 'abbreviated_name':
                            tmp_val, lang = Utility.separate_language_text_tag(vals[node2_id])
                            if tmp_val.strip() != "":
                                if lang not in _abbreviated_name:
                                    _abbreviated_name[lang] = set()
                                _abbreviated_name[lang].add(tmp_val)
                        elif vals[label_id] == 'graph_embeddings_complEx':
                            _graph_embeddings_complex = vals[node2_id]
                            if isinstance(_graph_embeddings_complex, str):
                                _graph_embeddings_complex = [float(x) for x in _graph_embeddings_complex.split(",")]
                        elif vals[label_id] == 'text_embedding':
                            _text_embedding = vals[node2_id]
                            if isinstance(_text_embedding, str):
                                _text_embedding = [float(x) for x in _text_embedding.split(",")]

                        # if it is human
                        if vals[node2_id] in human_nodes_set:
                            is_human_name = True

            # do one more write for last node
            skipped_node_count = Utility._write_one_node(_labels=_labels, _aliases=_aliases, _pagerank=_pagerank,
                                                         black_list_dict=black_list_dict,
                                                         current_node_info=current_node_info,
                                                         is_human_name=is_human_name, prev_node=prev_node,
                                                         skipped_node_count=skipped_node_count,
                                                         output_file=output_file, skip_edges=skip_edges,
                                                         extra_info=extra_info,
                                                         _descriptions=_descriptions,
                                                         add_all_text=add_text,
                                                         data_type=data_type,
                                                         instance_ofs=_instance_ofs,
                                                         qnode_statement_count=qnode_statement_count,
                                                         is_class=is_class,
                                                         wikitable_anchor_text=_wikitable_anchor_text,
                                                         wikipedia_anchor_text=_wikipedia_anchor_text,
                                                         abbreviated_name=_abbreviated_name,
                                                         redirect_text=_redirect_text,
                                                         text_embedding=_text_embedding,
                                                         graph_embeddings_complex=_graph_embeddings_complex
                                                         )
        except:
            print(traceback.print_exc())

        if copy_to_properties is not None:
            mapping_parameter_dict['copy_to_fields'] = copy_to_properties.split(',')
        else:
            mapping_parameter_dict['copy_to_fields'] = None

        mapping_dict = Utility.create_mapping_es(es_version, mapping_parameter_dict['str_fields_need_index'],
                                                 mapping_parameter_dict['float_fields_need_index'],
                                                 ["edges"], mapping_parameter_dict['copy_to_fields'],
                                                 all_langs=list(all_langs), int_fields=["statements"])
        open(mapping_file_path, 'w').write(json.dumps(mapping_dict))
        print("Totally skipped {} nodes in black list".format(skipped_node_count))
        print('Done!')

    @staticmethod
    def _write_one_node(**kwargs):
        """
        inner function called by build_elasticsearch_file only
        :param kwargs:
        :return:
        """
        labels = kwargs["_labels"]
        aliases = kwargs["_aliases"]
        descriptions = kwargs["_descriptions"]
        _pagerank = kwargs["_pagerank"]
        black_list_dict = kwargs["black_list_dict"]
        current_node_info = kwargs["current_node_info"]
        # is_human_name = kwargs["is_human_name"]
        prev_node = kwargs["prev_node"]
        skipped_node_count = kwargs["skipped_node_count"]
        output_file = kwargs["output_file"]
        skip_edges = kwargs["skip_edges"]
        extra_info = kwargs['extra_info']
        add_all_text = kwargs['add_all_text']
        instance_ofs = kwargs['instance_ofs']
        data_type = kwargs['data_type']
        qnode_statement_count = kwargs['qnode_statement_count']
        is_class = kwargs['is_class']
        wikitable_anchor_text = kwargs['wikitable_anchor_text']
        wikipedia_anchor_text = kwargs['wikipedia_anchor_text']
        abbreviated_name = kwargs['abbreviated_name']
        redirect_text = kwargs['redirect_text']
        text_embedding = kwargs['text_embedding']
        graph_embeddings_complex = kwargs['graph_embeddings_complex']

        _labels = {}
        _aliases = {}
        _descriptions = {}
        _wikitable_anchor_text = {}
        _wikipedia_anchor_text = {}
        _abbreviated_name = {}
        _redirect_text = {}

        for k in labels:
            _labels[k] = list(labels[k])

        for k in aliases:
            _aliases[k] = list(aliases[k])

        for k in descriptions:
            _descriptions[k] = list(descriptions[k])

        for k in wikitable_anchor_text:
            _wikitable_anchor_text[k] = list(wikitable_anchor_text[k])

        for k in wikipedia_anchor_text:
            _wikipedia_anchor_text[k] = list(wikipedia_anchor_text[k])

        for k in abbreviated_name:
            _abbreviated_name[k] = list(abbreviated_name[k])

        for k in redirect_text:
            _redirect_text[k] = list(redirect_text[k])

        if len(_labels) > 0 or len(_aliases) > 0 or len(_descriptions) > 0:
            if not Utility.check_in_black_list(black_list_dict, current_node_info):

                _edges = Utility.generate_edges_information(current_node_info, skip_edges)
                _ = {'id': prev_node,
                     'labels': _labels,
                     'aliases': _aliases,
                     'pagerank': _pagerank,
                     'descriptions': _descriptions,
                     'statements': qnode_statement_count,
                     'wikitable_anchor_text': _wikitable_anchor_text,
                     'wikipedia_anchor_text': _wikipedia_anchor_text,
                     'abbreviated_name': _abbreviated_name,
                     'redirect_text': _redirect_text
                     }
                if extra_info:
                    _['edges'] = _edges

                if add_all_text:
                    _['all_text'] = Utility.create_all_text(_labels, aliases=_aliases, descriptions=_descriptions)

                if len(instance_ofs) > 0:
                    _['instance_ofs'] = list(instance_ofs)
                if data_type is not None:
                    _['data_type'] = data_type
                if is_class:
                    _['is_class'] = 'true'
                if text_embedding:
                    _['text_embedding']: text_embedding
                if graph_embeddings_complex:
                    _['graph_embedding_complex'] = graph_embeddings_complex
                output_file.write(json.dumps(_))
            else:
                skipped_node_count += 1
            output_file.write('\n')
        return skipped_node_count

    @staticmethod
    def remove_language_tag(label_str):
        return re.sub(r'@.*$', '', label_str).replace("'", "")

    @staticmethod
    def separate_language_text_tag(label_str):
        if len(label_str) == 0:
            return "", "en"
        if "@" in label_str:
            res = label_str.split("@")
            text_string = "@".join(res[:-1]).replace('"', "").replace("'", "")
            lang = res[-1].replace('"', '').replace("'", "")
        else:
            text_string = label_str.replace('"', "").replace("'", "")
            lang = "en"
        return text_string, lang

    @staticmethod
    def create_all_text(labels, aliases, descriptions):
        text = ''
        if 'en' in labels and labels['en']:
            text = text + '\n'.join(labels['en']) + '\n'
        if 'en' in aliases and aliases['en']:
            text = text + '\n'.join(aliases['en']) + '\n'
        if 'en' in descriptions and descriptions['en']:
            text = text + '\n'.join(descriptions['en']) + '\n'
        return text

    @staticmethod
    def to_float(input_str):
        try:
            return float(input_str)
        except:
            return None

    @staticmethod
    def create_mapping_es(es_version: float, str_fields_need_index: typing.List[str],
                          float_fields: typing.List[str] = None,
                          str_fields_no_index: typing.List[str] = None, copy_to_fields: typing.List[str] = None,
                          all_langs=None, int_fields: typing.List[str] = None):
        if all_langs is None or len(all_langs) == 0:
            all_langs = ['en']
        properties_dict = {}
        # add property part
        for str_field in str_fields_need_index:
            if str_field == 'id':
                properties_dict[str_field] = {}
                properties_dict[str_field]["type"] = "text"
                properties_dict[str_field]['fields'] = {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    },
                    "keyword_lower": {
                        "type": "keyword",
                        "normalizer": "lowercase_normalizer"
                    }
                }
            else:
                properties_dict[str_field] = {"properties": {}}

                for lang in all_langs:
                    if lang not in properties_dict[str_field]["properties"]:
                        properties_dict[str_field]["properties"][lang] = {}

                    properties_dict[str_field]["properties"][lang]['type'] = "text"

                    if str_field == "aliases" or str_field == 'labels':
                        properties_dict[str_field]["properties"][lang]['fields'] = {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            },
                            "keyword_lower": {
                                "type": "keyword",
                                "normalizer": "lowercase_normalizer"
                            }
                        }
                    else:
                        properties_dict[str_field]["properties"][lang]['fields'] = {
                            "keyword_lower": {
                                "type": "keyword",
                                "normalizer": "lowercase_normalizer"
                            }
                        }

                    if copy_to_fields:
                        # one copy to field for different languages
                        # one  copy to field for all languages

                        if str_field in copy_to_fields:
                            properties_dict[str_field]["properties"][lang]["copy_to"] = [
                                f"all_labels.{lang}",
                                "all_labels_aliases"
                            ]
                            if "all_labels" not in properties_dict:
                                properties_dict["all_labels"] = {"properties": {}}
                            properties_dict["all_labels"]["properties"][lang] = {
                                "type": "text",
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                        "ignore_above": 256
                                    },
                                    "keyword_lower": {
                                        "type": "keyword",
                                        "normalizer": "lowercase_normalizer"
                                    },
                                    "ngram": {
                                        "type": "text",
                                        "analyzer": "edge_ngram_analyzer",
                                        "search_analyzer": "edge_ngram_search_analyzer"
                                    }
                                }
                            }
        if "all_labels_aliases" not in properties_dict:
            properties_dict["all_labels_aliases"] = {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    },
                    "keyword_lower": {
                        "type": "keyword",
                        "normalizer": "lowercase_normalizer"
                    }
                }
            }

        if float_fields:
            for float_field in float_fields:
                properties_dict[float_field] = {
                    "type": "float"
                }
        if int_fields:
            for int_field in int_fields:
                properties_dict[int_field] = {
                    "type": "integer"
                }

        if str_fields_no_index:
            for str_field in str_fields_no_index:
                if es_version >= 6:
                    properties_dict[str_field] = {
                        "type": "text",
                        "index": "false"
                    }
                else:
                    properties_dict[str_field] = {
                        "type": "text",
                        "index": "no"
                    }
        settings = {
            "index": {
                "analysis": {
                    "normalizer": {
                        "lowercase_normalizer": {
                            "filter": [
                                "lowercase"
                            ],
                            "type": "custom"
                        }
                    },
                    "analyzer": {
                        "edge_ngram_analyzer": {
                            "filter": [
                                "lowercase"
                            ],
                            "tokenizer": "edge_ngram_tokenizer"
                        },
                        "edge_ngram_search_analyzer": {
                            "tokenizer": "lowercase"
                        }
                    },
                    "tokenizer": {
                        "edge_ngram_tokenizer": {
                            "token_chars": [
                                "letter"
                            ],
                            "min_gram": "2",
                            "type": "edge_ngram",
                            "max_gram": "20"
                        }
                    }
                }
            }
        }

        # finish mapping dict
        if es_version >= 6:
            mapping_dict = {
                "mappings": {
                    "properties": properties_dict
                },
                "settings": settings
            }

        else:
            mapping_dict = {
                "mappings": {
                    "doc": {
                        "properties": properties_dict
                    }
                },
                "settings": settings
            }
        return mapping_dict

    @staticmethod
    def load_elasticsearch_index(kgtk_jl_path, es_url, es_index, es_version, mapping_file_path=None, es_user=None,
                                 es_pass=None,
                                 batch_size=10000):
        """
         loads a jsonlines file to Elasticsearch index.

        Args:
            kgtk_jl_path: input json lines file, could be output of build_elasticsearch_index
            es_url:  Elasticsearch server url
            es_index: Elasticsearch index to be created/loaded
            mapping_file_path: mapping file for the index
            es_user: Elasticsearch user
            es_pass: Elasticsearch password
            batch_size: batch size to be loaded at once

        Returns: Nothing

        """

        # first create the index
        create_response = Utility.create_index(es_url, es_index, mapping_file_path, es_user, es_pass)
        print('create response: {}'.format(create_response.status_code))

        f = open(kgtk_jl_path)
        load_batch = []
        counter = 0
        # i = 0
        for line in f:
            # i += 1
            counter += 1
            # if i > 1918500:
            each_res = line.replace('\n', '')
            if not each_res:
                continue
            json_x = json.loads(each_res)

            load_batch.append(json.dumps({"index": {"_id": json_x['id']}}))
            load_batch.append(line.replace('\n', ''))
            if len(load_batch) % batch_size == 0:
                counter += len(load_batch)
                print('done {} rows'.format(counter))
                response = None
                try:
                    response = Utility.load_index(es_version, es_url, es_index, '{}\n\n'.format('\n'.join(load_batch)),
                                                  mapping_file_path,
                                                  es_user=es_user, es_pass=es_pass)
                    if response.status_code >= 400:
                        print(response.text)
                except:
                    print('Exception while loading a batch to es')
                    print(response.text)
                    print(response.status_code)
                load_batch = []

        if len(load_batch) > 0:

            response = Utility.load_index(es_version, es_url, es_index, '{}\n\n'.format('\n'.join(load_batch)),
                                          mapping_file_path,
                                          es_user=es_user, es_pass=es_pass)
            if response.status_code >= 400:
                print(response.text)
        print('Finished loading the elasticsearch index')

    @staticmethod
    def load_index(es_version, es_url, es_index, payload, mapping_file_path, es_user=None, es_pass=None):

        if es_version >= 6:
            es_url_bulk = '{}/{}/_doc/_bulk'.format(es_url, es_index)
        else:
            es_url_bulk = '{}/{}/doc/_bulk'.format(es_url, es_index)

        headers = {
            'Content-Type': 'application/x-ndjson',
        }
        if es_user and es_pass:
            return requests.post(es_url_bulk, headers=headers, data=payload, auth=HTTPBasicAuth(es_user, es_pass))
        else:
            return requests.post(es_url_bulk, headers=headers, data=payload)

    @staticmethod
    def create_index(es_url, es_index, mapping_file_path, es_user=None, es_pass=None):
        es_url_index = '{}/{}'.format(es_url, es_index)
        # first check if index exists
        if es_user and es_pass:
            response = requests.get(es_url_index, auth=HTTPBasicAuth(es_user, es_pass))
        else:
            response = requests.get(es_url_index)

        if response.status_code == 200:
            print('Index: {} already exists...'.format(es_index))
        elif response.status_code // 100 == 4:
            if mapping_file_path is not None:
                # no need to create index if mapping file is not specified, it'll be created at load time
                mapping = json.load(open(mapping_file_path))
                if es_user and es_pass:
                    response = requests.put(es_url_index, auth=HTTPBasicAuth(es_user, es_pass), json=mapping)
                else:
                    response = requests.put(es_url_index, json=mapping)
                if response.text and "error" in json.loads(response.text):
                    pp = pprint.PrettyPrinter(indent=4)
                    pp.pprint(json.loads(response.text))
                    raise UploadError("Creating new index failed! Please check the error response above!")

        else:
            print('An exception has occurred: ')
            print(response.text)
        return response

    @staticmethod
    def format_error_details(module_name, error_details, error_code=-1):

        error = {
            "module_name": module_name,
            "error_details": error_details,
            "error_code": error_code
        }
        return error

    @staticmethod
    def str2bool(v: str):
        """
            a simple wrap function that can wrap any kind of input to bool type, used for argparsers 
        """
        import argparse
        if isinstance(v, bool):
            return v
        if v.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif v.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
        else:
            raise argparse.ArgumentTypeError('Boolean value expected.')

    @staticmethod
    def execute_shell_code(shell_command: str, debug=False):
        from subprocess import Popen, PIPE
        if debug:
            Utility.eprint("Executing...")
            Utility.eprint(shell_command)
            Utility.eprint("-" * 100)
        out = Popen(shell_command, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        # out.wait()
        """
        Popen.wait():
    
        Wait for child process to terminate. Set and return returncode attribute.
    
        Warning: This will deadlock when using stdout=PIPE and/or stderr=PIPE and the child process generates enough output to 
        a pipe such that it blocks waiting for the OS pipe buffer to accept more data. Use communicate() to avoid that. """
        stdout, stderr = out.communicate()
        if stderr:
            Utility.eprint("Error!!")
            Utility.eprint(stderr)
            Utility.eprint("-" * 50)
        if debug:
            Utility.eprint("Running fished!!!!!!")
        return stdout

    @staticmethod
    def eprint(*args, **kwargs):
        """
        print the things to stderr instead of stdout to prevent get included of bash `>`
        """
        import sys
        print(*args, file=sys.stderr, **kwargs)

    @staticmethod
    def add_acronym(labels: typing.Union[str, typing.List[str]]):
        """
        base on the given list of labels, add the acronym of each label
        For example: ["Barack Obama"] -> ["Barack Obama", "B. Obama"]
        :param labels: a list of str or a str
        :return: a list of str with acronym format data
        """
        if isinstance(labels, str):
            labels = [labels]

        useless_words = [
            'Mr', 'Ms', 'Miss', 'Mrs', 'Mx', 'Master', 'Sir', 'Madam', 'Dame', 'Lord', 'Lady',
            'Dr', 'Prof', 'Br', 'Sr', 'Fr', 'Rev', 'Pr', 'Elder'
        ]
        # ensure we can search both on capitalized case and normal case
        temp = []
        for each in useless_words:
            temp.append(each.lower())
        useless_words.extend(temp)

        useless_words_parser = re.compile(r"({})\s".format("|".join(useless_words)))
        all_candidates = set(labels)
        # check comma
        new_add_labels = set()
        for each_label in labels:
            if "," in each_label:
                comma_pos = each_label.find(",")
                # if have comma, it means last name maybe at first
                all_candidates.add(each_label[comma_pos + 1:].lstrip() + " " + each_label[:comma_pos])

        # check useless words and remove them (like honorifics)
        labels = list(all_candidates)
        for each_label in labels:
            # remove those until nothing remained, add the processed label after each removal
            while useless_words_parser.search(each_label):
                temp_search_res = useless_words_parser.search(each_label)
                each_label = each_label[:temp_search_res.start()] + " " + each_label[temp_search_res.end():]
                all_candidates.add(each_label)

        # generate acronyms
        labels = list(all_candidates)
        for each_label in labels:
            # ensure only 1 space between words
            label_preprocessed = " ".join(each_label.split())
            f_name1, f_name2 = "", ""
            names = label_preprocessed.split(' ')
            for n in names[:-1]:
                f_name1 = '{}{}. '.format(f_name1, n[0])
                f_name2 = '{}{} '.format(f_name2, n[0])
            f_name1 += names[-1]
            f_name2 += names[-1]
            all_candidates.add(f_name1)
            all_candidates.add(f_name2)

        return list(all_candidates)

    @staticmethod
    def jaccard_similarity(list1: typing.List[str], list2: typing.List[str]):
        s1 = set(list1)
        s2 = set(list2)
        return len(s1.intersection(s2)) / len(s1.union(s2))

    @staticmethod
    def sort_by_col_and_row(input_df: pd.DataFrame) -> pd.DataFrame:
        out_df = input_df.copy()
        # astype float first to prevent error of "invalid literal for int() with base 10: '0.0'"
        out_df["column"] = out_df["column"].astype(float).astype(int)
        out_df["row"] = out_df["row"].astype(float).astype(int)
        out_df = out_df.sort_values(by=['column', 'row'])
        return out_df

    @staticmethod
    def get_all_numeric_columns(input_df: pd.DataFrame,
                                skip_columns: typing.Optional[typing.Union[set, typing.List[str]]] = None
                                ) -> typing.List[str]:
        if skip_columns is None:
            skip_columns = {"row", "column", "evaluation_label"}
        elif isinstance(skip_columns, list):
            skip_columns = set(skip_columns)

        columns = []
        for each_column_name in input_df.columns:
            each_column_content = input_df[each_column_name]
            if each_column_name in skip_columns:
                continue
            if "float" in each_column_content.dtype.name or "int" in each_column_content.dtype.name:
                columns.append(each_column_name)
            else:
                try:
                    each_column_content.astype(float)
                    columns.append(each_column_name)
                except:
                    pass
        return columns

    @staticmethod
    def check_in_black_list(black_list: dict, current_node_info: dict):
        for key, val in black_list.items():
            if key in current_node_info and len(val.intersection(current_node_info[key])) > 0:
                return True
        return False

    @staticmethod
    def check_es_ready(es_url: str, es_port: str, es_user=None, es_pass=None) -> bool:
        """
        check if elastic search index initialize finished
        :return:
        """
        query = "http://{}:{}/_cluster/health?pretty=true".format(es_url, es_port)
        try:
            if es_user and es_pass:
                response = requests.get(query, auth=HTTPBasicAuth(es_user, es_pass))
            else:
                response = requests.get(query)

            if response.status_code == 200 and response.json()['status'] in {"yellow", "green"}:
                return True
        except:
            pass
        return False

    @staticmethod
    def generate_edges_information(current_node_info: dict, skip_edges: set):
        res = set()
        for edge, nodes in current_node_info.items():
            if edge not in skip_edges:
                for each_node in nodes:
                    # if len(edge) >= 6 and edge[:3] == '"""' and edge[-3:] == '"""':
                    # edge = edge[3:-3]
                    res.add("{}#{}".format(edge, each_node))
        return list(res)
