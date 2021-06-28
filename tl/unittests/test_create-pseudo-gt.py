import unittest
import pandas as pd
from pathlib import Path
from tl.features.create_pseudo_gt import create_pseudo_gt


parent_path = Path(__file__).parent


class TestCreatePseudoGT(unittest.TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super(TestCreatePseudoGT, self).__init__(*args, **kwargs)
        self.feat_path = '{}/data/feature_file.csv'.format(parent_path)
        self.singleton_column = 'singleton'
        self.context_column = 'context_score'
        self.context_threshold = 0.7
        self.output_column = 'pseudo_gt'

    def test_feature_generation(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.singleton_column,
                                  self.context_column, self.context_threshold,
                                  self.output_column)
        self.assertTrue(out_df[self.output_column].isin([1, 0]).all())

    def test_missing_singleton(self):
        in_df = pd.read_csv(self.feat_path)
        in_df.drop(columns=[self.singleton_column], axis=1, inplace=True)
        self.assertRaises(Exception,
                          lambda: create_pseudo_gt(in_df,
                                                   self.singleton_column,
                                                   self.context_column,
                                                   self.context_threshold,
                                                   self.output_column),
                          msg="The input column {} does not exist"
                          " in given data.".format(self.singleton_column))

    def test_missing_context(self):
        in_df = pd.read_csv(self.feat_path)
        in_df.drop(columns=[self.context_column], axis=1, inplace=True)
        self.assertRaises(Exception,
                          lambda: create_pseudo_gt(in_df,
                                                   self.singleton_column,
                                                   self.context_column,
                                                   self.context_threshold,
                                                   self.output_column),
                          msg="The input column {} does not exist"
                          " in given data.".format(self.context_column))

    def test_output_row_numbers(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.singleton_column,
                                  self.context_column, self.context_threshold,
                                  self.output_column)
        self.assertTrue(in_df.shape[0] == out_df.shape[0])


if __name__ == '__main__':
    unittest.main()
