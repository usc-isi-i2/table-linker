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
        human_nodes_set = {"Q15632617", "Q95074", "Q5"}
        o = open(output_path, 'w')

        if kgtk_file_path.endswith(".gz"):
            kgtk_file = gzip.open(kgtk_file_path)
        else:
            kgtk_file = open(kgtk_file_path, "r")

        _labels = list()
        _aliases = list()
        prev_node = None
        i = 0
        is_human_name = False
        try:
            for line in kgtk_file:
                i += 1
                if i % 100000 == 0:
                    print('Processed {} lines...'.format(i))
                if isinstance(line, bytes):
                    line = line.decode('utf-8')
                line = line.replace('\n', '')
                if line.startswith('Q'):
                    vals = line.split('\t')
                    id = vals[0]
                    if prev_node is None:
                        prev_node = id

                    if id != prev_node:
                        # we need to add acronym for human names
                        if is_human_name:
                            _labels = Utility.add_acronym(_labels)
                            _aliases = Utility.add_acronym(_aliases)
                        o.write(json.dumps({'id': prev_node, 'labels': _labels, 'aliases': _aliases}))
                        o.write('\n')
                        _labels = list()
                        _aliases = list()
                        prev_node = id
                        is_human_name = False

                    if vals[1] in labels:
                        tmp_val = Utility.remove_language_tag(vals[2])
                        if tmp_val.strip() != '':
                            _labels.append(tmp_val)
                    elif vals[1] in aliases:
                        tmp_val = Utility.remove_language_tag(vals[2])
                        if tmp_val.strip() != '':
                            _aliases.append(tmp_val)

                    # if it is human
                    if vals[2] in human_nodes_set:
                        is_human_name = True

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
        i = 0
        for line in f:
            i += 1
            counter += 1
            if i > 1918500:
                json_x = json.loads(line.replace('\n', ''))
                load_batch.append(json.dumps({"index": {"_id": json_x['id']}}))
                load_batch.append(line.replace('\n', ''))
                if len(load_batch) % batch_size == 0:
                    counter += len(load_batch)
                    print('done {} rows'.format(counter))
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
    def add_acronym(labels):
        """
        base on the given list of labels, add the acronym of each label
        For example: ["Barack Obama"] -> ["Barack Obama", "B. Obama"]
        :param labels: a list of str
        :return: a list of str with acronym format data
        """
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
                all_candidates.add(each_label[comma_pos+1:].lstrip() + " " + each_label[:comma_pos])

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
