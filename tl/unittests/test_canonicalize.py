import unittest
import pandas as pd
from tl.preprocess import preprocess
from pathlib import Path

parent_path = Path(__file__).parent


class TestCanonicalize(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestCanonicalize, self).__init__(*args, **kwargs)
        self.input_csv = pd.read_csv('{}/data/v16_431.csv'.format(parent_path), dtype=object)
        self.input_tsv_path = '{}/data/v16_431.tsv'.format(parent_path)

    def test_canonicalize_columns_1(self):
        odf = preprocess.canonicalize('col0,col1,col2,col3,col4', df=self.input_csv)
        self.assertEqual(len(odf), 685)
        columns = odf.columns
        self.assertTrue('column' in columns)
        self.assertTrue('row' in columns)
        self.assertTrue('label' in columns)

    def test_canonicalize_columns_2(self):
        odf = preprocess.canonicalize('col0', df=self.input_csv, output_column='alias')

        columns = odf.columns
        self.assertTrue('column' in columns)
        self.assertTrue('row' in columns)
        self.assertTrue('alias' in columns)

    def test_canonicalize_tsv(self):
        odf = preprocess.canonicalize('col0,col3', file_path=self.input_tsv_path, file_type='tsv')
        self.assertEqual(len(odf), 274)
        columns = odf.columns
        self.assertTrue('column' in columns)
        self.assertTrue('row' in columns)
        self.assertTrue('label' in columns)

