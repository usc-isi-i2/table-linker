import requests
import pandas as pd
import json
import re
from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError
from tl.exceptions import RequiredInputParameterMissingException

class FuzzyAugmented(object):
    def __init__(self, es_url, es_index, properties):
        self.es_url = es_url
        self.es_index = es_index
        self.properties = [prop.strip() for prop in properties.split(',')]
        self.keyword_lower_prop = [prop + '.keyword_lower' for prop in self.properties]
        self.ffv = FFV()


    def query_es(self,query):
        es_search_url = '{}/{}/_search'.format(self.es_url,self.es_index)
        #print(query)
        response = requests.post(es_search_url, json=query)
        # print(response.status_code)
        if response.status_code == 200:
            response_output = response.json()['hits']['hits']
        else:
            response_output = None
        return response_output


    def create_query1(self,search_term, size):
        query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": search_term,
                                "fields": self.properties,
                                "fuzziness": "AUTO",
                                "prefix_length": 1,
                                "max_expansions": 3
                            }
                        }
                    ]
                }
            },
            "size": size
        }
        return query


    def create_query2(self,search_term, size):
        query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": search_term,
                                "fields": self.keyword_lower_prop,
                                "fuzziness": "AUTO",
                                "prefix_length": 1,
                                "max_expansions": 3
                            }
                        }
                    ]
                }
            },
            "size": size
        }
        return query


    def get_query1_matches(self,search_term,key,size=100):
        fuzzy_matches = []
        label = []
        retrieval_score = []
        pagerank = []
        description = []
        search_term = search_term.replace('/',' ')
        search_term = re.sub(' +',' ',search_term)
        query1 = self.create_query1(search_term=search_term.strip(), size=size)
        query1_matches = self.query_es(query1)
        query1_dict = {}

        if query1_matches is not None and len(query1_matches) != 0:
            for item in query1_matches:
                fuzzy_matches.append(item['_id'])
                if 'en' in item['_source']['labels']:
                    label.append(item['_source']['labels']['en'][0])
                else:
                    label.append('')
                if 'en' in item['_source']['descriptions']:
                    description.append(item['_source']['descriptions']['en'][0])
                else:
                    description.append('')
                retrieval_score.append(item['_score'])
                pagerank.append(item['_source']['pagerank'])
                zipped_items = list(zip(fuzzy_matches, label, retrieval_score, pagerank, description))
                query1_dict[key] = zipped_items

        else:
            query1_dict[key] = []

        return query1_dict


    def get_query2_matches(self, search_term, key, size=100):
        fuzzy_matches = []
        label = []
        retrieval_score = []
        pagerank = []
        description = []
        search_term = search_term.replace('/', ' ')
        search_term = re.sub(' +', ' ', search_term)
        query2 = self.create_query2(search_term=search_term.strip(), size=size)
        query2_matches = self.query_es(query=query2)
        query2_dict = {}

        if query2_matches is not None and len(query2_matches) != 0:
            for item in query2_matches:
                fuzzy_matches.append(item['_id'])
                if 'en' in item['_source']['labels']:
                    label.append(item['_source']['labels']['en'][0])
                else:
                    label.append('')
                if 'en' in item['_source']['descriptions']:
                    description.append(item['_source']['descriptions']['en'][0])
                else:
                    description.append('')
                retrieval_score.append(item['_score'])
                pagerank.append(item['_source']['pagerank'])
                zipped_items = list(zip(fuzzy_matches, label, retrieval_score,pagerank,description))
                query2_dict[key] = zipped_items

        else:
            query2_dict[key] = []

        return query2_dict


    def create_union_result(self,query1_dict,query2_dict,key):
        final_dict = {}
        query1_res = query1_dict[key]
        query2_res = query2_dict[key]
        cand_dict = {}
        for item in query1_res:
            if item not in cand_dict:
                cand_dict[item[0]] = [item[1], item[2],item[3],item[4]]
            else:
                if cand_dict[item[0]][1] < item[2]:
                    cand_dict[item[0]][1] = item[2]
                else:
                    continue
        for item in query2_res:
            if item not in cand_dict:
                cand_dict[item[0]] = [item[1], item[2],item[3],item[4]]
            else:
                if cand_dict[item[0]][1] < item[2]:
                    cand_dict[item[0]][1] = item[2]
                else:
                    continue
        item_list = list(cand_dict.items())
        final_dict[key] = item_list
        return final_dict


    def get_matches(self, column, size=100, file_path=None, df=None, output_column_name="retrieval_score"):
        """
        Used the ElasticSearch which has the labels, aliases, wikipedia/wikitable anchor text, redirect text
        :param column: the column used to retrieve the candidates
        :param size: the size of the candidates that need to retrieved by the two queries
        :param file_path: input file in canonical format
        :param df: input dataframe in canonical format
        :param output_column_name: the output column name where the retrieval scores are stored
        :return: a dataframe in candidates format
        """

        if file_path is None and df is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("file_path","df")
            )

        if file_path:
            df = pd.read_csv(file_path, dtype=object)

        df.fillna(value="",inplace=True)
        columns = df.columns

        new_df_list = list()
        seen_dict = {}
        for i, row in df.iterrows():
            row_key = f"{row['column']}_{row['row']}_{row[column]}"
            if row_key not in seen_dict:
                query1_dict = self.get_query1_matches(search_term=row[column],key=row_key,size=size)
                query2_dict = self.get_query2_matches(search_term=row[column],key=row_key,size=size)
                search_result_dict = self.create_union_result(query1_dict=query1_dict,query2_dict=query2_dict,key=row_key)
                search_result = search_result_dict[row_key]
                if len(search_result) > 0:
                    for sr in search_result:
                        _ = {}

                        for c in columns:
                            _[c] = row[c]

                        _['kg_id'] = sr[0]
                        _['kg_labels'] = sr[1][0]
                        _['method'] = 'fuzzy-augmented'
                        _[output_column_name] = sr[1][1]
                        _['pagerank'] = sr[1][2]
                        _['description'] = sr[1][3]
                        new_df_list.append(_)
                else:
                    _ = {}
                    for c in columns:
                        _[c] = row[c]

                    _['kg_id'] = ''
                    _['kg_labels'] = ''
                    _['method'] = 'fuzzy-augmented'
                    _[output_column_name] = ''
                    _['pagerank'] = sr[1][2]
                    _['description'] = ''
                    new_df_list.append(_)
                seen_dict[row_key] = 1

        if self.ffv.is_canonical_file(df):
            return pd.DataFrame(new_df_list)

        if self.ffv.is_candidates_file(df):
            return pd.concat([df,pd.DataFrame(new_df_list)]).sort_values(by=['column','row',column])

        raise UnsupportedTypeError("The input file is neither canonical file or a candidate file")
