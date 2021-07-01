import unittest
import pandas as pd
from pathlib import Path
from tl.evaluation.check_candidates import check_candidates


parent_path = Path(__file__).parent


class TestCheckCandidates(unittest.TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super(TestCheckCandidates, self).__init__(*args, **kwargs)
        self.cd_path = '{}/data/candidates.csv'.format(parent_path)
        self.cd_d_path = '{}/data/cd_with_descriptions.csv'.format(parent_path)
        self.bad_cd_path = '{}/data/bad_candidates.csv'.format(parent_path)
        self.cd_no_eval = '{}/data/cd_no_eval.csv'.format(parent_path)

    def test_candidates_input(self):
        df = pd.read_csv(self.cd_path)
        out_df = check_candidates(df)
        for c, r in zip(out_df["column"], out_df["row"]):
            temp_df = df.loc[((df["column"] == c) & (df["row"] == r))]
            self.assertTrue(1 not in temp_df["evaluation_label"].values)

    def test_check_columns_output(self):
        df = pd.read_csv(self.cd_path)
        out_df = check_candidates(df)
        required_columns = ["column", "row", "label", "context", "GT_kg_id",
                            "GT_kg_label"]
        columns = out_df.columns
        self.assertTrue(pd.Series(required_columns).isin(columns).all())

    def test_check_columns_output_with_description(self):
        df = pd.read_csv(self.cd_d_path)
        out_df = check_candidates(df)
        required_columns = ["column", "row", "label", "context", "GT_kg_id",
                            "GT_kg_label", "GT_kg_description"]
        columns = out_df.columns
        self.assertTrue(pd.Series(required_columns).isin(columns).all())

    def test_candidate_file_check(self):
        df = pd.read_csv(self.bad_cd_path)
        self.assertRaises(Exception, lambda: check_candidates(df),
                          msg="The input dataframe is not a candidates file")

    def test_evaluation_label_error(self):
        df_no_eval = pd.read_csv(self.cd_no_eval)
        self.assertRaises(Exception, lambda: check_candidates(df_no_eval),
                          msg="Input file does not have required columns. "
                              "Run ground-truth-labeler with ground truth.")


if __name__ == '__main__':
    unittest.main()
