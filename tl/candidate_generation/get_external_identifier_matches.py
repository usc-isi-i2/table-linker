import pandas as pd
from typing import List
from tl.candidate_generation.es_search import Search
from tl.candidate_generation.utility import Utility
from tl.exceptions import RequiredInputParameterMissingException


class ExIDMatches(object):
    def __init__(self, es_url, es_index, es_user=None, es_pass=None, output_column_name: str = "retrieval_score"):
        self.es = Search(es_url, es_index, es_user=es_user, es_pass=es_pass)
        self.utility = Utility(self.es, output_column_name)

    def get_ex_id_matches(self,
                          column: str,
                          size: int = 50,
                          file_path: str = None,
                          df: pd.DataFrame = None,
                          auxiliary_fields: List[str] = None,
                          auxiliary_folder: str = None,
                          property: str = None):
        """

        Args:
            column: column in the file with search labels
            size: number of candidates to be returned
            file_path: input file path
            df: input dataframe
            auxiliary_fields: auxiliary fields to fetch from the ES index
            auxiliary_folder: folder where auxiliary data will be stored
            property: if specified, property:identifier pairs will be searched

        Returns: candidates DataFrame

        """
        if file_path is None and df is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("file_path", "df"))

        if file_path:
            df = pd.read_csv(file_path, dtype=object)

        df.fillna(value="", inplace=True)

        properties = "external_identifiers_pairs" if property is not None else "external_identifiers"

        return self.utility.create_candidates_df(df,
                                                 column,
                                                 size,
                                                 properties,
                                                 'ex-id-match',
                                                 lower_case=False,
                                                 auxiliary_fields=auxiliary_fields,
                                                 auxiliary_folder=auxiliary_folder,
                                                 auxiliary_file_prefix='ex_id_matches_',
                                                 identifier_property=property)
