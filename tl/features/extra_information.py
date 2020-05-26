import math
import os
import pandas as pd
import re
import typing
import wikipediaapi

from ast import literal_eval
from collections import defaultdict
from datetime import datetime
from datetime import timezone
from date_extractor import extract_dates
from kgtk.gt.embedding_utils import connect_to_redis
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED  # type: ignore
from tl.exceptions import TLException
from tl.candidate_generation.es_search import Search
from tl.exceptions import RequiredColumnMissingException
from tl.utility.utility import Utility


WIKI_BASE = wikipediaapi.Wikipedia('en')
RE_BRACKET = re.compile(r"\s?\(.*\)")


class ExtraInformationProcessing:
    def __init__(self, **kwargs):
        self.es = Search(kwargs["url"], kwargs["index"], es_user=kwargs.get("user"), es_pass=kwargs.get("password"))
        self.extra_information_file = kwargs["extra_information_file"]
        self.score_column = kwargs["score_column"]
        self.query_address = kwargs["query_address"]
        self.redis_server = connect_to_redis(kwargs.get("redis_host", "dsbox01.isi.edu"), kwargs.get("redis_port", 6379))
        if not self.score_column:
            self.score_column = "extra_information_score"

    def check_extra_information(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        function used to add an extra column that do check the extra information
        It will give score 1 if we find those information exist, otherwise 0
        :return: the input dataframe with the extra column
        """

        if self.extra_information_file and not os.path.exists(self.extra_information_file):
            raise TLException("The extra information file {} not exist!".format(self.extra_information_file))

        if not self.extra_information_file and "||other_information||" not in df.columns:
            raise RequiredColumnMissingException("extra_information column does not exist in input file and extra_information "
                                                 "file was not given! Can't continue!")

        # load extra info df file based on input method
        if not self.extra_information_file:
            extra_info_df = df["||other_information||"].apply(lambda x: pd.Series(str(x).split("|")))
            extra_info_df["column"] = df["column"]
            extra_info_df["row"] = df["row"]
            extra_info_df = extra_info_df.drop_duplicates()
        else:
            extra_info_df = pd.read_csv(self.extra_information_file)

        # try to transform the time column to uct standard format for further comparision
        for each_col in extra_info_df.columns:
            try:
                temp = pd.to_datetime(extra_info_df[each_col])
                has_time_format_or_not = (pd.isnull(temp) == True).value_counts()
                if False in has_time_format_or_not.keys() and \
                        has_time_format_or_not[False] >= extra_info_df.shape[0] * 0.7:
                    formatted_res = []
                    for each in temp:
                        formatted_res.append(
                            datetime.fromtimestamp(each.timestamp(), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                    extra_info_df[each_col] = formatted_res
            except:
                pass

        out_df = pd.DataFrame()

        for key, each_group in df.groupby(["column", "row"]):
            candidate_nodes = set(each_group['kg_id'].dropna())

            if len(candidate_nodes) == 0:
                # for those nodes with 0 candidates, just append them and continue
                each_group[self.score_column] = 0
                each_group["kg_id"] = ""
                # each_group.fillna(0)
                out_df = out_df.append(each_group)
                continue

            cache_memo = {}
            # get cached part if exists
            if self.redis_server:
                candidate_nodes_need_query = []
                for each_node in candidate_nodes:
                    query_cache_key = each_node + "_extra_information"
                    cache_res = self.redis_server.get(query_cache_key)
                    if cache_res is not None:
                        cache_memo[each_node] = literal_eval(cache_res.decode("utf-8"))
                    else:
                        candidate_nodes_need_query.append(each_node)
            else:
                candidate_nodes_need_query = candidate_nodes

            # query to get all possible reference strings which not exist in cache
            if len(candidate_nodes_need_query) > 0:
                value_memo = self.get_all_property_values(candidate_nodes_need_query, self.query_address)
                wiki_memo = self.get_all_wikipedia_info(candidate_nodes_need_query, self.query_address)
                for k, v in wiki_memo.items():
                    if k in value_memo:
                        value_memo[k].update(v)
                    else:
                        value_memo[k] = v
            else:
                value_memo = {}

            # combine the cached result and queried results
            if len(cache_memo) > 0:
                for values, nodes in self.reverse_key_value(cache_memo, "set").items():
                    if values in value_memo:
                        value_memo[values].update(nodes)
                    else:
                        value_memo[values] = nodes

            # push new query results to cache server
            if len(candidate_nodes_need_query) > 0 and self.redis_server:
                nodes_to_push = set(candidate_nodes_need_query)
                for each_node, values in self.reverse_key_value(value_memo, "set").items():
                    if each_node in nodes_to_push:
                        query_cache_key = each_node + "_extra_information"
                        self.redis_server.set(query_cache_key, str(values))

            if self.extra_information_file:
                remained_info_cols = list(set(range(extra_info_df.shape[1])) - {int(key[0])})
            else:
                remained_info_cols = list(range(extra_info_df.shape[1]))
            if self.extra_information_file:
                each_extra_info = extra_info_df.iloc[int(key[1]) - 1, remained_info_cols]
            else:
                each_extra_info = extra_info_df.loc[(extra_info_df['column'] == key[0]) & (extra_info_df['row'] == key[1])]
                each_extra_info = each_extra_info.drop(columns=["column", "row"])

            # count the same string amount if found in those values
            found_count = defaultdict(int)
            information_count = len(each_extra_info.values[0])
            for each_part_info in each_extra_info.values[0]:
                each_part_info = each_part_info.lower()
                if each_part_info in value_memo:
                    for each_match_node in value_memo[each_part_info]:
                        found_count[each_match_node] += 1

            each_group[self.score_column] = 0
            score_column_pos = each_group.columns.tolist().index(self.score_column)
            nodes_list = each_group["kg_id"].tolist()
            # give the score as same value count / all extra information count given
            for node, each_count in found_count.items():
                each_group.iloc[nodes_list.index(node), score_column_pos] = each_count / information_count
            out_df = out_df.append(each_group)

        # sort results by column / row
        out_df = Utility.sort_by_col_and_row(out_df)

        return out_df

    @staticmethod
    def get_all_wikipedia_info(qnodes: typing.Union[typing.List[str], set], query_address: str):
        memo = defaultdict(set)
        cache_memo = defaultdict(set)  # used to store node: information which will be pushed to cache server later
        qnodes_str = ["wd:{}".format(each) for each in qnodes]
        parallel_count = 5
        split_part = math.ceil(len(qnodes_str) / parallel_count)
        for i in range(split_part):
            if i == split_part - 1:
                each_part = qnodes_str[i * parallel_count:]
            else:
                each_part = qnodes_str[i * parallel_count:(i + 1) * parallel_count]
            each_part_str = " ".join(each_part)
            query = """
            SELECT DISTINCT ?item ?article WHERE {{
              values ?item {{{q_nodes}}} 
              ?article schema:about ?item ;  
              FILTER (SUBSTR(str(?article), 1, 25) = "https://en.wikipedia.org/")
            }}
            """.format(q_nodes=each_part_str)
            results = ExtraInformationProcessing.send_sparql_query(query, query_address)

            for each in results:
                wiki_page = each['article']['value'][each['article']['value'].find("/wiki") + 6:]
                node = each['item']['value'].split("/")[-1]
                wiki_page_unit = WIKI_BASE.page(wiki_page)
                if not wiki_page_unit.exists():
                    continue
                # add wikipedia links
                page_links = wiki_page_unit.links
                for each_page_key in page_links.keys():
                    if RE_BRACKET.search(each_page_key):
                        re_res = RE_BRACKET.search(each_page_key)
                        key_no_bracket = each_page_key[:re_res.start()] + " " + each_page_key[re_res.end():]
                        key_inside_bracket = each_page_key[re_res.start()+1: re_res.end()-1]
                        for each_key in Utility.add_acronym([key_no_bracket, key_inside_bracket]):
                            cache_memo[node].add(each_key)
                            memo[each_key.lower()].add(node)
                    for each_key in Utility.add_acronym([each_page_key]):
                        memo[each_key.lower()].add(node)
                        cache_memo[node].add(each_key)

                # search for time and parse them
                dates = extract_dates(wiki_page_unit.text)
                for each_date in dates:
                    if each_date:
                        uct_time_str = datetime.fromtimestamp(each_date.timestamp(), tz=timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%SZ")
                        memo[uct_time_str.lower()].add(node)
                        cache_memo[node].add(uct_time_str)
        return memo

    def get_all_property_values(self, qnodes: typing.Union[typing.List[str], set], query_address: str):
        """
        send the sparql query and get all property values
        :param qnodes: list or set of q nodes in string format
        :param query_address: sparql query endpoint
        :return: a dict, key is the values, value is the qnodes
        """
        cache_memo = defaultdict(set)  # used to store node: information which will be pushed to cache server later
        value_to_node_memo = defaultdict(set)
        memo = defaultdict(set)  # the main memo store the {value: node} pairs where value are from all of those property values
        need_check_labels_nodes = set()  # the nodes referred from main node which need to be send for get labels
        qnodes_str = " ".join(["wd:{}".format(each) for each in qnodes])
        query = """select
        DISTINCT ?item ?p_entityLabel ?oValue ?oValueLabel
        where
        {{
            values ?item
        {{{q_nodes}}}
        ?item ?p ?o.
            FILTER
        regex(str(?p), "^http://www.wikidata.org/prop/P", "i")
        BIND(IRI(REPLACE(STR(?p), "http://www.wikidata.org/prop", "http://www.wikidata.org/entity")) AS ?p_entity).
        BIND(IRI(REPLACE(STR(?p), "http://www.wikidata.org/prop", "http://www.wikidata.org/prop/direct")) AS ?p_wdt).
    
        ?item ?p_wdt ?oValue.
            SERVICE wikibase:label {{bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".}}
        }}""".format(q_nodes=qnodes_str)

        results = ExtraInformationProcessing.send_sparql_query(query, query_address)

        for each in results:
            node = each["item"]["value"].split("/")[-1]
            # property_label = each["p_entityLabel"]["value"]
            value_label = each["oValueLabel"]["value"]
            value_node = each["oValue"]["value"].split("/")[-1]
            if value_node.startswith("Q") and value_node[1:].isnumeric():
                need_check_labels_nodes.add(value_node)
            value_to_node_memo[value_node].add(node)
            if value_label != "":
                for each_v in Utility.add_acronym([value_label]):
                    memo[each_v.lower()].add(node)

        nodes_labels = self.es.search_node_labels(list(need_check_labels_nodes))
        for value_node_id, labels in nodes_labels.items():
            for each_label in labels:
                for each_target_node in value_to_node_memo[value_node_id]:
                    memo[each_label.lower()].add(each_target_node)

        return memo

    @staticmethod
    def send_sparql_query(query_body: str, query_address: str):
        """
            a simple wrap to send the query and return the returned results
        """
        qm = SPARQLWrapper(query_address)
        qm.setReturnFormat(JSON)
        qm.setMethod(POST)
        qm.setRequestMethod(URLENCODED)
        qm.setQuery(query_body)
        try:
            results = qm.query().convert()['results']['bindings']
            return results
        except Exception as e:
            error_message = ("Sending Sparql query to {} failed!".format(query_address))
            raise TLException(error_message)

    @staticmethod
    def reverse_key_value(input_dict, value_type="list"):
        if value_type == "list":
            output_dict = defaultdict(list)
        elif value_type == "set":
            output_dict = defaultdict(set)
        else:
            raise TLException("Unsupport dict type: {}".format(value_type))
        for k, v in input_dict.items():
            for each_v in v:
                if value_type == "list":
                    output_dict[each_v].append(k)
                elif value_type == "set":
                    output_dict[each_v].add(k)
        return output_dict
