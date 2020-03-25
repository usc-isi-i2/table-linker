import requests
import json
import gzip
import re
import traceback
from requests.auth import HTTPBasicAuth


class Utility(object):
    @staticmethod
    def build_elasticsearch_file(kgtk_file_path, label_fields, mapping_file_path, output_path, alias_fields=None):
        """
        builds a json lines file and a mapping file to support retrieval of candidates
        It is assumed that the file is sorted by subject and predicate, in order to be able to process it in a streaming fashion

        Args:
            kgtk_file_path: a file in KGTK format
            label_fields: field in the kgtk file to be used as labels
            mapping_file_path: output mapping file path for elasticsearch
            output_path: output json lines path, converted from the input kgtk file
            alias_fields: field in the kgtk file to be used as aliases

        Returns: Nothing

        """
        labels = label_fields.split(',')
        aliases = alias_fields.split(',')

        o = open(output_path, 'w')

        kgtk_file = gzip.open(kgtk_file_path)

        _labels = list()
        _aliases = list()
        prev_node = None
        i = 0
        try:
            for line in kgtk_file:
                i += 1
                if i % 100000 == 0:
                    print('Processed {} lines...'.format(i))
                line = line.decode('utf-8').replace('\n', '')
                if line.startswith('Q'):
                    vals = line.split('\t')
                    id = vals[0]
                    if prev_node is None:
                        prev_node = id

                    if id != prev_node:
                        o.write(json.dumps({'id': prev_node, 'labels': _labels, 'aliases': _aliases}))
                        o.write('\n')
                        _labels = list()
                        _aliases = list()
                        prev_node = id

                    if vals[1] in labels:
                        tmp_val = Utility.remove_language_tag(vals[2])
                        if tmp_val.strip() != '':
                            _labels.append(tmp_val)
                    elif vals[1] in aliases:
                        tmp_val = Utility.remove_language_tag(vals[2])
                        if tmp_val.strip() != '':
                            _aliases.append(tmp_val)

        except:
            print(traceback.print_exc())

        mapping_dict = Utility.create_mapping_es(['id', 'labels', 'aliases'])
        open(mapping_file_path, 'w').write(json.dumps(mapping_dict))
        print('Done!')

    @staticmethod
    def remove_language_tag(label_str):
        return re.sub(r'@.*$', '', label_str).replace("'", "")

    @staticmethod
    def create_mapping_es(str_fields):
        properties_dict = {}
        for str_field in str_fields:
            properties_dict[str_field] = {}
            properties_dict[str_field]['type'] = "text"
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
        mapping_dict = {
            "mappings": {
                "doc": {
                    "properties": properties_dict
                }
            },
            "settings": {
                "index": {
                    "analysis": {
                        "normalizer": {
                            "lowercase_normalizer": {
                                "filter": [
                                    "lowercase"
                                ],
                                "type": "custom"
                            }
                        }
                    }
                }
            }
        }
        return mapping_dict

    @staticmethod
    def load_elasticsearch_index(kgtk_jl_path, es_url, es_index, mapping_file_path=None, es_user=None, es_pass=None,
                                 batch_size=1000):
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

        for line in f:
            json_x = json.loads(line.replace('\n', ''))
            load_batch.append(json.dumps({"index": {"_id": json_x['id']}}))
            load_batch.append(line.replace('\n', ''))
            if len(load_batch) % batch_size == 0:
                response = None
                try:
                    response = Utility.load_index(es_url, es_index, '{}\n\n'.format('\n'.join(load_batch)),
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

            response = Utility.load_index(es_url, es_index, '{}\n\n'.format('\n'.join(load_batch)), mapping_file_path,
                                          es_user=es_user, es_pass=es_pass)
            if response.status_code >= 400:
                print(response.text)
        print('Finished loading the elasticsearch index')

    @staticmethod
    def load_index(es_url, es_index, payload, mapping_file_path, es_user=None, es_pass=None):

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
        elif response.status_code == 404:
            if mapping_file_path is not None:
                # no need to create index if mapping file is not specified, it'll be created at load time
                mapping = json.load(open(mapping_file_path))
                if es_user and es_pass:
                    return requests.put(es_url_index, auth=HTTPBasicAuth(es_user, es_pass), json=mapping)
                else:
                    return requests.put(es_url_index, json=mapping)
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

# Utility.build_elasticsearch_file('5000.tsv', 'label', '', alias_fields='aliases')
# Utility.build_elasticsearch_file('/Users/amandeep/Downloads/edges_no_scholarly_articles_in_subject_sorted.tsv.gz',
#                                  'label', 'mapping_file.json', 'kgtk_labels.jl', alias_fields='aliases')


# response = Utility.create_index('http://kg2018a.isi.edu:9200', 'test_index_1', 'mapping_file.json')
# print(response.text)
# print(response.status_code)


# response = Utility.load_index('http://kg2018a.isi.edu:9200', 'test_index_1', 'mapping_file.json')
# Utility.load_elasticsearch_index('kgtk_labels_sample.jl', 'http://kg2018a.isi.edu:9200', 'test_index_1',
#                                  'mapping_file.json')
# print(response.text)
# print(response.status_code)
