import pandas as pd
import os
import typing
import re
import wikipediaapi

from tl.exceptions import TLException
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED  # type: ignore
from collections import defaultdict
from datetime import datetime
from datetime import timezone
from tl.utility.utility import Utility
from date_extractor import extract_dates

WIKI_BASE = wikipediaapi.Wikipedia('en')
RE_BRACKET = re.compile(r"\s?\(.*\)")


class ExtraInformationProcessing:
    @staticmethod
    def check_extra_information(df: pd.DataFrame, extra_information_file: str,
                                query_address: str,
                                score_column: str = None) -> pd.DataFrame:
        """
        function used to add an extra column that do check the extra information
        It will give score 1 if we find those information exist, otherwise 0
        :param query_address:
        :param score_column: the output score column name
        :param df: input dataframe
        :param extra_information_file: path to the extra information file
        :return: the input dataframe with the extra column
        """
        if not score_column:
            score_column = "extra_information_score"

        if not os.path.exists(extra_information_file):
            raise TLException("The extra information file {} not exist!".format(extra_information_file))

        extra_info_df = pd.read_csv(extra_information_file)
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
                continue

            value_memo = ExtraInformationProcessing.get_all_property_values(candidate_nodes, query_address)
            wiki_memo = ExtraInformationProcessing.get_all_wikipedia_info(candidate_nodes, query_address)

            remained_info_cols = list(set(range(extra_info_df.shape[1])) - {int(key[0])})
            each_extra_info = extra_info_df.iloc[int(key[1]) - 1, remained_info_cols]

            nodes_found = set()
            for each_part_info in each_extra_info:
                if each_part_info in value_memo:
                    nodes_found.update(value_memo[each_part_info])
                if each_part_info in wiki_memo:
                    nodes_found.update(wiki_memo[each_part_info])

            each_group[score_column] = 0
            score_column_pos = each_group.columns.tolist().index(score_column)
            nodes_list = each_group["kg_id"].tolist()
            if len(nodes_found) > 0:
                for each in nodes_found:
                    each_group.iloc[nodes_list.index(each), score_column_pos] = 1
            out_df = out_df.append(each_group)
        return out_df

    @staticmethod
    def get_all_wikipedia_info(qnodes: typing.Union[typing.List[str], set], query_address: str):
        qnodes_str = " ".join(["wd:{}".format(each) for each in qnodes])
        query = """
            SELECT DISTINCT ?item ?article ?name
            WHERE {{
            values ?item {{{q_nodes}}}
              ?article schema:about ?item ;
                          schema:inLanguage ?lang ;
                          schema:name ?name ;
                          schema:isPartOf [ wikibase:wikiGroup "wikipedia" ] .
              FILTER(?lang in ('en')) .
              FILTER (!CONTAINS(?name, ':')) .
            }}
        """.format(q_nodes=qnodes_str)
        results = ExtraInformationProcessing.send_sparql_query(query, query_address)
        memo = defaultdict(set)
        for each in results:
            wiki_page = each['article']['value'][each['article']['value'].find("/wiki")+6:]
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
                    for each_key in Utility.add_acronym([key_no_bracket]):
                        memo[each_key].add(node)
                for each_key in Utility.add_acronym([each_page_key]):
                    memo[each_key].add(node)

            # search for time and parse them
            dates = extract_dates(wiki_page_unit.text)
            for each_date in dates:
                if each_date:
                    memo[datetime.fromtimestamp(each_date.timestamp(), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")].add(node)
        return memo

    @staticmethod
    def get_all_property_values(qnodes: typing.Union[typing.List[str], set], query_address: str):
        """
        send the sparql query and get all property values
        :param qnodes: list or set of q nodes in string format
        :param query_address: sparql query endpoint
        :return: a dict, key is the values, value is the qnodes
        """
        qnodes_str = " ".join(["wd:{}".format(each) for each in qnodes])
        query = """select
        DISTINCT ?item ?p_entityLabel ?oValueLabel
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
        memo = defaultdict(set)
        for each in results:
            node = each["item"]["value"].split("/")[-1]
            # property_label = each["p_entityLabel"]["value"]
            value = each["oValueLabel"]["value"]
            if value != "":
                for each_v in Utility.add_acronym([value]):
                    memo[each_v].add(node)
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
