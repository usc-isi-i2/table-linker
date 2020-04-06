import unittest
import pandas as pd
from pathlib import Path
from tl.preprocess import preprocess
from tl.file_formats_validator import FFV

parent_path = Path(__file__).parent


class TestClean(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestClean, self).__init__(*args, **kwargs)
        self.input_csv = pd.read_csv('{}/data/canonical.csv'.format(parent_path), dtype=object)
        self.ffv = FFV()

    def test_clean_default(self):
        odf = preprocess.clean('label', df=self.input_csv)
        gdf = pd.read_csv('{}/data/canonical_default_gt.csv'.format(parent_path), dtype=object)
        self.assertTrue(self.ffv.is_canonical_file(odf))
        for i in range(len(odf)):
            self.assertEqual(odf.at[i, 'label_clean'], gdf.at[i, 'label_clean'])

    def test_clean_replace_by_space_false(self):
        odf = preprocess.clean('label', df=self.input_csv, output_column='clean_labels', replace_by_space=False)
        gdf = pd.read_csv('{}/data/canonical_replace_by_space_false_gt.csv'.format(parent_path), dtype=object)
        self.assertTrue(self.ffv.is_canonical_file(odf))
        self.assertTrue('clean_labels' in odf.columns.values)

        for i in range(len(odf)):
            self.assertEqual(odf.at[i, 'clean_labels'], gdf.at[i, 'clean_labels'])

    def test_clean_keep_original_true(self):
        odf = preprocess.clean('label', df=self.input_csv, keep_original=True)
        gdf = pd.read_csv('{}/data/canonical_keep_original_gt.csv'.format(parent_path), dtype=object)
        self.assertTrue(self.ffv.is_canonical_file(odf))
        for i in range(len(odf)):
            self.assertEqual(odf.at[i, 'label_clean'], gdf.at[i, 'label_clean'])

    def test_clean_symbols(self):
        odf = preprocess.clean('label', df=self.input_csv, symbols=".'")
        gdf = pd.read_csv('{}/data/canonical_symbols_gt.csv'.format(parent_path), dtype=object)
        self.assertTrue(self.ffv.is_canonical_file(odf))
        for i in range(len(odf)):
            self.assertEqual(odf.at[i, 'label_clean'], gdf.at[i, 'label_clean'])
