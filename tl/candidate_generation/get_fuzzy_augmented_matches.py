import pandas as pd
from typing import List
from tl.candidate_generation.es_search import Search
from tl.candidate_generation.utility import Utility
from tl.exceptions import RequiredInputParameterMissingException


class FuzzyAugmented(object):
    def __init__(self, es_url, es_index, es_user, es_pass, properties, output_column_name):
        self.properties = properties
        self.es = Search(es_url, es_index, es_user=es_user, es_pass=es_pass)
        self.utility = Utility(self.es, output_column_name)

    def get_matches(self, column, size=50, file_path=None,
                    df=None, auxiliary_fields: List[str] = None, auxiliary_folder: str = None, isa: str = None):
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
                'One of the input parameters is required: {} or {}'.format("file_path", "df"))

        if file_path:
            df = pd.read_csv(file_path, dtype=object)

        df.fillna(value="", inplace=True)
        properties = self.properties

        extra_musts = None
        if isa:
            extra_musts = {
                "term": {
                    "instance_ofs.keyword_lower": {
                        "value": isa.lower()
                    }
                }
            }
        return self.utility.create_candidates_df(df,
                                                 column,
                                                 size,
                                                 properties,
                                                 'fuzzy-augmented',
                                                 lower_case=False,
                                                 auxiliary_fields=auxiliary_fields,
                                                 auxiliary_folder=auxiliary_folder,
                                                 auxiliary_file_prefix='fuzzy_augmented_',
                                                 extra_musts=extra_musts)
