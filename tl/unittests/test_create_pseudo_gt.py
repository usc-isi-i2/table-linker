import unittest
import pandas as pd
from pathlib import Path
from tl.features.create_pseudo_gt import create_pseudo_gt


parent_path = Path(__file__).parent


class TestCreatePseudoGT(unittest.TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super(TestCreatePseudoGT, self).__init__(*args, **kwargs)
        self.feat_path = '{}/data/feature_file.csv'.format(parent_path)
        self.column_thresholds = "singleton:1,context_score:0.7"
        self.bad_column_thresholds = "singleton:1,con:0.1"
        self.output_column = 'pseudo_gt'

    def test_feature_generation(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.column_thresholds,
                                  self.output_column)
        self.assertTrue(out_df[self.output_column].isin([1, -1]).all())

    def test_missing_columns(self):
        in_df = pd.read_csv(self.feat_path)
        self.assertRaises(Exception,
                          lambda: create_pseudo_gt(in_df,
                                                   self.bad_column_thresholds,
                                                   self.output_column),
                          msg="The input column {} does not exist"
                          " in given data.".format(self.column_thresholds[1]
                                                   [0]))

    def test_output_row_numbers(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.column_thresholds,
                                  self.output_column)
        self.assertTrue(in_df.shape[0] == out_df.shape[0])


if __name__ == '__main__':
    unittest.main()
