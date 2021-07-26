import unittest
import pandas as pd
from pathlib import Path
from tl.utility.utility import Utility

parent_path = Path(__file__).parent


class TestCreateGRoundTruth(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestCreateGRoundTruth, self).__init__(*args, **kwargs)
        self.input = pd.read_excel('{}/data/create_gt_input.xlsx'.format(parent_path), dtype=object)
        self.utils = Utility()

    def test_create_gt(self):
        odf = self.utils.create_gt_file_from_candidates(self.input, 'evaluation_label')
        gdf = pd.read_csv('{}/data/create_gt_gt.csv'.format(parent_path), dtype=object)
        self.assertEqual(len(odf), len(gdf))
        for kg_id, kg_label, gt_kg_id, gt_kg_label in zip(odf.GT_kg_id, odf.GT_kg_label, gdf.GT_kg_id,
                                                          gdf.GT_kg_label):
            self.assertEqual(kg_id, gt_kg_id)
            self.assertEqual(kg_label, gt_kg_label)
