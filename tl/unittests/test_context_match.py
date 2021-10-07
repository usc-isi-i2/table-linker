import unittest
import pandas as pd
from pathlib import Path
from tl.features.context_match import MatchContext

parent_path = Path(__file__).parent


class TestContextMatch(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestContextMatch, self).__init__(*args, **kwargs)
        self.output_column_name = "weighted_context_score"
        self.input_file_path = '{}/data/unit_test.csv'.format(parent_path)
        self.context_file_path = '{}/data/unit_test_context.tsv'.format(parent_path)
        self.custom_context_path = '{}/data/custom_context.tsv.gz'.format(parent_path)
        self.similarity_string_threshold = 0.90
        self.similarity_quantity_threshold = 0.80
        self.missing_property_replacement_factor = 0.5
        self.string_separator = ','
        self.ignore_column_name = 'ignore'
        self.pseudo_gt_column_name = None

    def test_combination_types_of_input(self):
        # the input file contains varied set of inputs ranging from
        # quantity as numbers, floats and badly formatted numbers, dates and strings with separators.
        obj_1 = MatchContext(self.input_file_path, self.similarity_string_threshold, self.similarity_quantity_threshold,
                             self.string_separator, self.missing_property_replacement_factor, self.ignore_column_name,
                             self.pseudo_gt_column_name, self.output_column_name, self.context_file_path,
                             custom_context_path=None)
        odf = obj_1.process_data_by_column()
        odf.to_csv('{}/data/result_test_1.csv'.format(parent_path), index=False)
        columns = odf.columns
        # The context-score's should not be all 0).
        distinct_context_score_values = odf[self.output_column_name].unique().tolist()
        self.assertTrue(len(distinct_context_score_values) > 1)
        self.assertTrue(self.output_column_name in columns)
        # Check for one row : Red Dead Redemption Q548203
        node_context_score = odf[odf['kg_id'] == 'Q548203'][self.output_column_name].values.tolist()[0]
        self.assertTrue(node_context_score == 1.0)

    def test_for_custom_context_file(self):
        # The custom file contains the property Pcoauthor and should therefore match for column 7's some of the qnodes.
        obj_2 = MatchContext(self.input_file_path, self.similarity_string_threshold, self.similarity_quantity_threshold,
                             self.string_separator, self.missing_property_replacement_factor,
                             self.ignore_column_name, self.pseudo_gt_column_name,
                             self.output_column_name,
                             custom_context_path=self.custom_context_path,
                             context_path=self.context_file_path)
        odf = obj_2.process_data_by_column()
        odf.to_csv('{}/data/result_test_2.csv'.format(parent_path), index=False)
        columns = odf.columns
        # Check if the score for a researcher is greater than 0.
        researcher_val = odf[odf['kg_id'] == 'Q91463330'][self.output_column_name].values.tolist()
        self.assertTrue(researcher_val[0] > 0)
        # researcher_prop_value contains the value for the properties matched.
        researcher_prop_value = odf[odf['kg_id'] == 'Q91463330']['context_property'].values.tolist()
        # The custom context file contains Pcoauthor as property.
        researcher_prop_value_list = researcher_prop_value[0]
        self.assertTrue('Pcoauthor' in researcher_prop_value_list)
        self.assertTrue('context_similarity' in columns)
        self.assertTrue('context_property' in columns)

    def test_for_string_separators(self):
        # We will check for results with string separator ;
        string_separator = ";"
        obj_3 = MatchContext(self.input_file_path, self.similarity_string_threshold, self.similarity_quantity_threshold,
                             string_separator, self.missing_property_replacement_factor, self.ignore_column_name,
                             self.pseudo_gt_column_name, self.output_column_name,
                             custom_context_path=self.custom_context_path, context_path=self.context_file_path)
        odf = obj_3.process_data_by_column()
        odf.to_csv('{}/data/result_test_3.csv'.format(parent_path), index=False)
        # Check for qnode researcher
        node_property = odf[odf['kg_id'] == 'Q50419679']['context_property'].values.tolist()[0]
        # The custom context file contains Pcoauthor as property.
        researcher_prop_value_list = node_property
        node_similarity = odf[odf['kg_id'] == 'Q50419679']['context_similarity'].values.tolist()[0]
        node_context_score = odf[odf['kg_id'] == 'Q50419679'][self.output_column_name].values.tolist()[0]
        self.assertTrue(node_similarity[2] == '1.0')
        self.assertTrue(researcher_prop_value_list[2] == 'Pcoauthor')
        self.assertTrue(node_context_score == 0.6375)

    def test_for_quantity_match(self):
        similarity_quantity_threshold = 1
        obj_4 = MatchContext(self.input_file_path, self.similarity_string_threshold, similarity_quantity_threshold,
                             self.string_separator, self.missing_property_replacement_factor, self.ignore_column_name,
                             self.pseudo_gt_column_name, self.output_column_name, context_path=self.context_file_path)
        odf = obj_4.process_data_by_column()
        odf.to_csv('{}/data/result_test_4.csv'.format(parent_path), index=False)
        # Check for the United States.
        # The property should match to P3259 with similariy 1.
        node_property = odf[odf['kg_id'] == 'Q30']['context_property'].values.tolist()[0]
        node_similarity = odf[odf['kg_id'] == 'Q30']['context_similarity'].values.tolist()[0]
        node_context_score = odf[odf['kg_id'] == 'Q30'][self.output_column_name].values.tolist()[0]
        self.assertTrue(node_property[0] == 'P3529')
        self.assertTrue(node_similarity[0] == "1.0")
        self.assertTrue(node_context_score == 1.0)

    def test_for_item_match(self):
        similarity_string_threshold = 0.85
        obj_5 = MatchContext(self.input_file_path, similarity_string_threshold, self.similarity_quantity_threshold,
                             self.string_separator, self.missing_property_replacement_factor, self.ignore_column_name,
                             self.pseudo_gt_column_name,
                             self.output_column_name, context_path=self.context_file_path)
        odf = obj_5.process_data_by_column()
        odf.to_csv('{}/data/result_test_5.csv'.format(parent_path), index=False)
        # Check for the Bioshock series.
        # The property P400 should match with similariy 0.87 for the context field Windows ..
        node_property = odf[odf['kg_id'] == 'Q4914658']['context_property'].values.tolist()[0]
        node_similarity = odf[odf['kg_id'] == 'Q4914658']['context_similarity'].values.tolist()[0]
        node_context_score = odf[odf['kg_id'] == 'Q4914658'][self.output_column_name].values.tolist()[0]
        self.assertTrue(node_property[2] == 'P400')
        self.assertTrue(node_similarity[2] == "0.875")
        self.assertTrue(node_context_score >= 0.87)

    def test_for_date_match(self):
        obj_6 = MatchContext(self.input_file_path, self.similarity_string_threshold, self.similarity_quantity_threshold,
                             self.string_separator, self.missing_property_replacement_factor, self.ignore_column_name,
                             self.output_column_name, context_path=self.context_file_path)
        odf = obj_6.process_data_by_column()
        odf.to_csv('{}/data/result_test_6.csv'.format(parent_path), index=False)
        # Check for the Bioshock series.
        # The property P400 should match with similariy 0.87 for the context field Windows ..
        node_property = odf[odf['kg_id'] == 'Q102395995']['context_property'].values.tolist()[0]
        node_similarity = odf[odf['kg_id'] == 'Q102395995']['context_similarity'].values.tolist()[0]
        node_context_score = odf[odf['kg_id'] == 'Q102395995'][self.output_column_name].values.tolist()[0]
        self.assertTrue(node_property[1] == 'P577')
        self.assertTrue(node_similarity[1] == "1.0")
        self.assertTrue(node_context_score == 1.0)

