import unittest
import pandas as pd
from pathlib import Path
from tl.features.create_pseudo_gt import create_pseudo_gt


parent_path = Path(__file__).parent


class TestCreatePseudoGT(unittest.TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super(TestCreatePseudoGT, self).__init__(*args, **kwargs)
        self.feat_path = '{}/data/feature_file.csv'.format(parent_path)
        self.feat_path_no_singleton = ('{}/data/feature_file_no'
                                       '_singleton.csv').format(parent_path)
        self.bad_cd_path = '{}/data/bad_candidates.csv'.format(parent_path)
        self.threshold_median = "gt_score:median"
        self.threshold_mean = "gt_score:mean"
        self.threshold_max = "gt_score:max"
        self.threshold_median_top20 = "gt_score:mediantop20"
        self.threshold_median_top10 = "gt_score:mediantop10"
        self.threshold_mean_top20 = "gt_score:meantop20"
        self.threshold_fixed = "gt_score:0.8"
        self.bad_column_thresholds = "singleton:1,con:0.1"
        self.output_column = 'pseudo_gt'
        self.filter = "smc_class_score:0"
        self.bad_filter = "class_score:0.5"
        self.means = {0: 0.9998247592072738, 2: 0.9714986070990562,
                      3: 0.9999999880790711}
        self.medians = {0: 1.0, 2: 1.0, 3: 1.0}
        self.mediantop20_kgids = {
            0: ["Q2264773", "Q1583685"],
            2: ["Q1397597", "Q1747787", "Q5469569"],
            3: ["Q5785", "Q781", "Q414"]
        }
        self.meantop20_kgids = {
            0: ["Q2264773", "Q1583685", "Q2647508"],
            2: ["Q1397597", "Q1747787", "Q5469569"],
            3: ["Q5785", "Q781", "Q414"]
        }

    def test_bad_input_file(self):
        in_df = pd.read_csv(self.bad_cd_path)
        self.assertRaises(Exception,
                          lambda: create_pseudo_gt(in_df,
                                                   self.threshold_median,
                                                   self.output_column,
                                                   self.filter),
                          msg="The input file is not a candidates file!")

    def test_filter_missing_column(self):
        in_df = pd.read_csv(self.feat_path)
        self.assertRaises(Exception,
                          lambda: create_pseudo_gt(in_df,
                                                   self.threshold_median,
                                                   self.output_column,
                                                   self.bad_filter),
                          msg="The input column class_score does not exist in"
                              " given data")

    def test_filter_mising_column(self):
        in_df = pd.read_csv(self.feat_path)
        self.assertRaises(Exception,
                          lambda: create_pseudo_gt(in_df,
                                                   self.threshold_median,
                                                   self.output_column,
                                                   self.bad_filter),
                          msg="The input column class_score does not exist"
                              " in given data")
    
    def test_missing_columns(self):
        in_df = pd.read_csv(self.feat_path)
        self.assertRaises(Exception,
                          lambda: create_pseudo_gt(in_df,
                                                   self.bad_column_thresholds,
                                                   self.output_column,
                                                   self.filter),
                          msg="The input column con does not exist"
                          " in given data.")

    def test_feature_generation(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.threshold_median,
                                  self.output_column, self.filter)
        self.assertTrue(out_df[self.output_column].isin([1, -1]).all())

    def test_output_row_numbers(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.threshold_median,
                                  self.output_column, self.filter)
        self.assertTrue(in_df.shape[0] == out_df.shape[0])

    def test_median(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.threshold_median,
                                  self.output_column, self.filter)
        pgt = out_df[out_df[self.output_column] == 1]
        for col, score in zip(pgt["column"], pgt["gt_score"]):
            check = self.medians[col]
            self.assertTrue(score >= check)

    def test_mean(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.threshold_mean,
                                  self.output_column, self.filter)
        pgt = out_df[out_df[self.output_column] == 1]
        for col, score in zip(pgt["column"], pgt["gt_score"]):
            check = self.means[col]
            self.assertTrue(score >= check)

    def test_max(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.threshold_max,
                                  self.output_column, self.filter)
        pgt = out_df[out_df[self.output_column] == 1]
        top_cd_df = pd.concat([
            gdf.sort_values(by=["gt_score"], ascending=False).head(1)
            for _, gdf in in_df.groupby(by=["column", "row"])
        ])
        top_cd_df = top_cd_df[top_cd_df["smc_class_score"] > 0]
        for col, row, score in zip(pgt["column"], pgt["row"], pgt["gt_score"]):
            check = top_cd_df[((top_cd_df["column"] == col) &
                               (top_cd_df["row"] == row))]["gt_score"].max()
            self.assertTrue(score == check)

    def test_fixed(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.threshold_fixed,
                                  self.output_column, self.filter)
        pgt = out_df[out_df[self.output_column] == 1]
        for score in pgt["gt_score"].tolist():
            self.assertTrue(score >= 0.8)

    def test_median_top20(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.threshold_median_top20,
                                  self.output_column, self.filter)
        pgt = out_df[out_df[self.output_column] == 1]
        for col, kg_id in zip(pgt["column"], pgt["kg_id"]):
            self.assertTrue(kg_id in self.mediantop20_kgids[col])

    def test_mean_top20(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.threshold_mean_top20,
                                  self.output_column, self.filter)
        pgt = out_df[out_df[self.output_column] == 1]
        for col, kg_id in zip(pgt["column"], pgt["kg_id"]):
            self.assertTrue(kg_id in self.meantop20_kgids[col])

    def test_singleton(self):
        in_df = pd.read_csv(self.feat_path)
        out_df = create_pseudo_gt(in_df, self.threshold_median_top10,
                                  self.output_column, self.filter)
        pgt = out_df[out_df[self.output_column] == 1]
        self.assertTrue((pgt["singleton"] == 1).all())

    def test_pgr_rts(self):
        in_df = pd.read_csv(self.feat_path_no_singleton)
        out_df = create_pseudo_gt(in_df, self.threshold_median,
                                  self.output_column, self.filter)
        pgt = out_df[out_df[self.output_column] == 1]
        for col, row, pgrrts, gt in zip(pgt["column"], pgt["row"], 
                                       pgt["pgr_rts"], pgt["gt_score"]):
            check = out_df[((out_df["column"] == col) & (out_df["row"] == row))
                          ]["pgr_rts"].astype(float).max()
            check_gt = self.medians[col]
            self.assertTrue((check == pgrrts) or (gt >= check_gt))

if __name__ == '__main__':
    unittest.main()
