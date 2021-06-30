import unittest
import pandas as pd
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout
import importlib


check_candidates = importlib.import_module("tl.cli.check-candidates")

parent_path = Path(__file__).parent


class TestCheckCandidates(unittest.TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super(TestCheckCandidates, self).__init__(*args, **kwargs)
        self.cd_path = '{}/data/candidates.csv'.format(parent_path)
        self.gt_path = '{}/data/gt.csv'.format(parent_path)
        self.gt_d_path = '{}/data/gt_with_descriptions.csv'.format(parent_path)
        self.bad_cd_path = '{}/data/bad_candidates.csv'.format(parent_path)
        self.bad_gt_path = '{}/data/bad_gt.csv'.format(parent_path)

    def test_candidates_input(self):
        out_csv = StringIO()
        with redirect_stdout(out_csv):
            check_candidates.run(**{
                "input_file": self.cd_path,
                "gt_file": self.gt_path,
                "logfile": None
            })
        out_df = pd.read_table(StringIO(out_csv.getvalue()), sep=",")
        columns = out_df.columns
        required_columns = ["column", "row", "label", "context", "GT_kg_id",
                            "GT_kg_label"]
        self.assertTrue(pd.Series(required_columns).isin(columns).all())

    def test_candidates_input_with_GT_description(self):
        out_csv = StringIO()
        with redirect_stdout(out_csv):
            check_candidates.run(**{
                "input_file": self.cd_path,
                "gt_file": self.gt_d_path,
                "logfile": None
            })
        out_df = pd.read_table(StringIO(out_csv.getvalue()), sep=",")
        columns = out_df.columns
        required_columns = ["column", "row", "label", "context", "GT_kg_id",
                            "GT_kg_label", "GT_kg_description"]
        self.assertTrue(pd.Series(required_columns).isin(columns).all())

    def test_candidate_file_check(self):
        self.assertRaises(Exception, lambda: check_candidates.run(**{
                "input_file": self.bad_cd_path,
                "gt_file": self.gt_path,
                "logfile": None
            }), msg="The input dataframe is not a candidates file")

    def test_gt_file_check(self):
        self.assertRaises(Exception, lambda: check_candidates.run(**{
                "input_file": self.cd_path,
                "gt_file": self.bad_gt_path,
                "logfile": None
            }), msg="GT file does not have required columns")

    def test_output_row_number(self):
        out_csv = StringIO()
        with redirect_stdout(out_csv):
            check_candidates.run(**{
                "input_file": self.cd_path,
                "gt_file": self.gt_path,
                "logfile": None
            })
        out_df = pd.read_table(StringIO(out_csv.getvalue()), sep=",")
        self.assertEqual(out_df.shape[0], 4)


if __name__ == '__main__':
    unittest.main()
