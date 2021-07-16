import pandas as pd
from typing import List
from tl.candidate_generation.es_search import Search
from tl.candidate_generation.utility import Utility
from tl.exceptions import RequiredInputParameterMissingException


class NgramMatches(object):
    def __init__(self, es_url, es_index, es_user=None, es_pass=None, output_column_name: str = "retrieval_score"):
        self.es = Search(es_url, es_index, es_user=es_user, es_pass=es_pass)
        self.utility = Utility(self.es, output_column_name)

    def get_ngram_matches(self, column, size=20, file_path=None,
                          df=None, auxiliary_fields: List[str] = None, auxiliary_folder: str = None, isa: str = None):
        """
        retrieves the identifiers of KG entities whose label or aliases ngrams match the search term

        Args:
            column: the column used for retrieving candidates.
            size: maximum number of candidates to retrieve, default is 50.
            file_path: input file in canonical format
            df: input dataframe in canonical format
            auxiliary_fields: auxiliary fields to fetch from ES
            auxiliary_folder: path where the auxiliary files will be stored
        Returns: a dataframe in candidates format

        """
        if file_path is None and df is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("file_path", "df"))

        if file_path:
            df = pd.read_csv(file_path, dtype=object)

        df.fillna(value="", inplace=True)

        extra_musts = None
        if isa:
            extra_musts = {
                "term": {
                    "instance_ofs.keyword_lower": {
                        "value": isa.lower()
                    }
                }
            }

        properties = "all_labels.en"

        return self.utility.create_candidates_df(df,
                                                 column,
                                                 size,
                                                 properties,
                                                 'ngram-match',
                                                 lower_case=False,
                                                 auxiliary_fields=auxiliary_fields,
                                                 auxiliary_folder=auxiliary_folder,
                                                 auxiliary_file_prefix='ngram_matches_',
                                                 extra_musts=extra_musts)
