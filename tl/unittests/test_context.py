import unittest
import pandas as pd
from pathlib import Path
from tl.features.context_match import MatchContext

parent_path = Path(__file__).parent


class TestContextMatch(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestContextMatch, self).__init__(*args, **kwargs)
        self.output_column_name = "weighted_context_score"
        self.input_file_path = '{}/data/uni_test.csv'.format(parent_path)
        self.context_file_path = '{}/data/unit_test_context.tsv'.format(parent_path)
        self.custom_context_path = '{}/data/custom_context.tsv.gz'.format(parent_path)
        self.kwargs = {'similarity_string_threshold': 0.80, 'similarity_quantity_threshold': 0.80,
                       'string_separator': ",", 'output_column': self.output_column_name}

    def test_different_types_of_input(self):
        # the input file contains varied set of inputs ranging from
        # quantity as numbers, floats and badly formatted numbers, dates and strings with separators.
        obj_1 = MatchContext(self.input_file_path, self.kwargs, self.context_file_path, custom_context_path=None)
        odf = obj_1.process_data_by_column()
        odf.to_csv('{}/data/result_test_1.csv'.format(parent_path), index=False)
        columns = odf.columns
        # The context-score's should not be all 0).
        distinct_context_score_values = odf[self.output_column_name].unique().tolist()
        self.assertTrue(len(distinct_context_score_values) > 1)
        self.assertTrue(self.output_column_name in columns)

    def test_for_custom_context_file(self):
        # The custom file contains the property Pcoauthor and should therefore match for column 7's some of the qnodes.
        obj_2 = MatchContext(self.input_file_path, self.kwargs, custom_context_path=self.custom_context_path,
                             context_path=None)
        odf = obj_2.process_data_by_column()
        odf.to_csv('{}/data/result_test_2.csv'.format(parent_path), index=False)
        columns = odf.columns
        self.assertTrue('context_similarity' in columns)
        self.assertTrue('context_property' in columns)
        # Check if the score for a researcher is greater than 0. 
        researcher_val = odf[odf['kg_id'] == 'Q91463330'][self.output_column_name].values.tolist()
        self.assertTrue(researcher_val[0] > 0)
        self.assertTrue('context_similarity' in columns)
        self.assertTrue('context_property' in columns)
        # researcher_prop_value contains the value for the properties matched.
        researcher_prop_value = odf[odf['kg_id'] == 'Q91463330']['context_property'].values.tolist()
        # The custom context file contains Pcoauthor as property.
        researcher_prop_value_list = researcher_prop_value[0].split("|")
        self.assertTrue('Pcoauthor' in researcher_prop_value_list)

    def test_for_string_separators(self):
        # We will check for results with string separator ;
        kwargs = self.kwargs
        kwargs['string_separator'] = ";"
        obj_3 = MatchContext(self.input_file_path, kwargs, custom_context_path=self.custom_context_path,
                             context_path=None)
        odf = obj_3.process_data_by_column()
        odf.to_csv('{}/data/result_test_3.csv'.format(parent_path), index=False)
        distinct_context_score_values = odf[self.output_column_name].unique().tolist()
        self.assertTrue(len(distinct_context_score_values) > 1)


