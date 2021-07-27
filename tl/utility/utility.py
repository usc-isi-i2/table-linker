import sys

import requests
import json

import pandas as pd
import re
import typing

import pprint

from tl.exceptions import UploadError
from requests.auth import HTTPBasicAuth


class Utility(object):

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
        out_df = out_df.sort_values(by=['column', 'row']).reset_index(drop=True)
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
        except Exception:
            pass
        return False

    @staticmethod
    def create_gt_file_from_candidates(df: pd.DataFrame, evaluation_label_column: str) -> pd.DataFrame:
        df[evaluation_label_column] = df[evaluation_label_column].map(lambda x: Utility.return_int(x))
        df = df[df[evaluation_label_column] == 1]
        out = list()
        for (column, row), gdf in df.groupby(['column', 'row']):
            labels = "|".join(dict.fromkeys(gdf['GT_kg_label'].values))  # keeps the values in order
            kg_ids = "|".join(dict.fromkeys(gdf['GT_kg_id'].values))

            out.append({
                'column': int(column),
                'row': int(row),
                'GT_kg_id': kg_ids,
                'GT_kg_label': labels
            })
        return pd.DataFrame(out)

    @staticmethod
    def return_int(x):
        try:
            return int(x)
        except:
            return 0
