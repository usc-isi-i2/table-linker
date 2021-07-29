import unittest
import pandas as pd
from pathlib import Path
from tl.preprocess import preprocess
from tl.file_formats_validator import FFV

parent_path = Path(__file__).parent


class TestCanonicalize(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestCanonicalize, self).__init__(*args, **kwargs)
        self.input_csv = pd.read_csv('{}/data/input.csv'.format(parent_path), dtype=object)
        self.input_tsv_path = '{}/data/input.tsv'.format(parent_path)
        self.ffv = FFV()

    def test_canonicalize_columns_1(self):
        odf = preprocess.canonicalize('col0,col1,col2,col3,col4', df=self.input_csv)
        odf.to_csv('{}/data/canonical.csv'.format(parent_path), index=False)
        self.assertTrue(self.ffv.is_canonical_file(odf))
        self.assertEqual(len(odf), 685)
        columns = odf.columns
        self.assertTrue('label' in columns)

    def test_canonicalize_columns_2(self):
        odf = preprocess.canonicalize('col0', df=self.input_csv, output_column='alias')
        self.assertTrue(self.ffv.is_canonical_file(odf))
        columns = odf.columns
        self.assertTrue('alias' in columns)

    def test_canonicalize_tsv(self):
        odf = preprocess.canonicalize('col0,col3', file_path=self.input_tsv_path, file_type='tsv')
        self.assertEqual(len(odf), 274)
        self.assertTrue(self.ffv.is_canonical_file(odf))

    def test_canonicalize_with_context(self):
        odf = preprocess.canonicalize('col0,col3', df=self.input_csv, add_context=True)
        self.assertEqual(len(odf), 274)
        self.assertTrue(self.ffv.is_canonical_file(odf))
        self.assertTrue('context' in odf.columns)
        self.assertEqual(odf.iloc[116, 3], "B. Robison|George Strait|George Strait|How 'bout Them Cowgirls")
        self.assertEqual(odf.iloc[91, 3], "B. Nowell|Paul Leary|Sublime|Doin' Time")

    def test_canonicalize_with_additional_columns(self):
        odf = preprocess.canonicalize('col0,col3', df=self.input_csv, add_context=True, file_name='input.csv')
        self.assertTrue(self.ffv.is_canonical_file(odf))
        self.assertTrue('context' in odf.columns)
        self.assertTrue('filename' in odf.columns)
        self.assertTrue('column-id' in odf.columns)
        self.assertEqual(odf.iloc[116, 3], "B. Robison|George Strait|George Strait|How 'bout Them Cowgirls")
        self.assertEqual(odf.iloc[91, 3], "B. Nowell|Paul Leary|Sublime|Doin' Time")
        self.assertEqual(odf.iloc[34, 4], "input.csv")
        self.assertEqual(odf.iloc[34, 5], "input.csv-0")
        self.assertEqual(odf.iloc[200, 5], "input.csv-3")
        grouped = odf.groupby(['column'])
        for key, gdf in grouped:
            self.assertEqual(len(gdf), 137)
