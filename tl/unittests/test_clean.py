import unittest
import pandas as pd
from tl.preprocess import preprocess
from pathlib import Path

parent_path = Path(__file__).parent


class TestClean(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestClean, self).__init__(*args, **kwargs)
        self.input_csv = pd.read_csv('{}/data/canonical.csv'.format(parent_path), dtype=object)

    def test_clean_default(self):
        odf = preprocess.clean('label', df=self.input_csv)

        self.assertTrue('label_clean' in odf.columns.values)
        self.assertEqual(odf.at[487, 'label_clean'], "L'Arc-en-Ciel")

        self.assertEqual(odf.at[680, 'label_clean'], "0 to 100   The Catch Up")
        print(odf.at[677, 'label_clean'])
        print(odf.at[430, 'label_clean'])

    def test_clean_replace_by_space_false(self):
        odf = preprocess.clean('label', df=self.input_csv, output_column='clean_labels', replace_by_space=False)

        self.assertTrue('clean_labels' in odf.columns.values)

        self.assertEqual(odf.at[680, 'clean_labels'], "0 to 100  The Catch Up")

    def test_clean_keep_original_true(self):
        odf = preprocess.clean('label', df=self.input_csv, keep_original=True)

        self.assertEqual(odf.at[680, 'label_clean'], "0 to 100 / The Catch Up|0 to 100   The Catch Up")
        self.assertEqual(odf.at[624, 'label_clean'], "Chase|Chase")
        self.assertEqual(odf.at[66, 'label_clean'], "Y.M.C.A.|Y.M.C.A.")

    def test_clean_symbols(self):
        odf = preprocess.clean('label', df=self.input_csv, symbols=".'")

        self.assertEqual(odf.at[350, 'label_clean'], "L Arc-en-Ciel")
        self.assertEqual(odf.at[434, 'label_clean'], "Guns N  Roses")
        self.assertEqual(odf.at[447, 'label_clean'], "The Go-Go s")
        self.assertEqual(odf.at[448, 'label_clean'], "Will i am")
        self.assertEqual(odf.at[66, 'label_clean'], "Y M C A ")
