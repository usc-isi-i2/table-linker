import pandas as pd
from tl.candidate_generation.es_search import Search
from tl.candidate_generation.utility import Utility
from tl.exceptions import RequiredInputParameterMissingException
from tl.utility.filter import Filter


class PhraseQueryMatches(object):
    def __init__(self, es_url, es_index, es_user=None, es_pass=None, score_column_name: str = "retrieval_score",
                 previous_match_column_name: str = "retrieval_score"):
        self.es = Search(es_url, es_index, es_user=es_user, es_pass=es_pass)
        self.utility = Utility(self.es, score_column_name, previous_match_column_name)

    def get_phrase_matches(self, column, properties="labels^2,aliases", size=50, file_path=None, df=None, filter_condition=None):
        """
        retrieves the identifiers of KG entities base on phrase match queries.

        Args:
            column: the column used for retrieving candidates.
            properties: a comma separated names of properties in the KG to search for exact match query: default is labels^2,aliases
            size: maximum number of candidates to retrieve, default is 50.
            file_path: input file in canonical format
            df: input dataframe in canonical format
            filter_condition: a string indicate the filter requirement
        Returns: a dataframe in candidates format

        """
        need_filter = False
        if filter_condition is not None:
            need_filter = True

        if file_path is None and df is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("file_path", "df"))

        if file_path:
            df = pd.read_csv(file_path, dtype=object)

        df.fillna(value="", inplace=True)

        if need_filter:
            query_input_df = Filter.remove_previous_match_res(df)
        else:
            query_input_df = df

        from tl.utility.utility import Utility

        output_df = self.utility.create_candidates_df(query_input_df, column, size, properties, 'phrase-match')
        Utility.eprint(output_df)
        if need_filter:
            output_df = Filter.combine_result(df, output_df, filter_condition)

        return output_df
