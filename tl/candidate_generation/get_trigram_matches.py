import sys

import pandas as pd
from typing import List
from tl.candidate_generation.es_search import Search
from tl.candidate_generation.utility import Utility
from tl.exceptions import RequiredInputParameterMissingException
from tl.exceptions import TLException
from operator import itemgetter

top5_class_column = 'top5_smc_class_score'
top5_property_column = 'top5_smc_property_score'
essential_columns = {'column', 'row', 'label', 'context', 'filename', 'column-id', 'label_clean'}


class TriGramMatches(object):
    def __init__(self,
                 es_url,
                 es_index,
                 es_user=None,
                 es_pass=None,
                 output_column_name: str = "retrieval_score",
                 pgt_column: str = None):
        self.es = Search(es_url, es_index, es_user=es_user, es_pass=es_pass)
        self.utility = Utility(self.es, output_column_name)
        self.pgt_column = pgt_column

    def get_trigram_matches(self,
                            column: str,
                            size: int = 50,
                            file_path: str = None,
                            df: pd.DataFrame = None,
                            auxiliary_fields: List[str] = None,
                            auxiliary_folder: str = None,
                            property: str = None,
                            isa: str = None):
        """

        Args:
            column: column in the file with search labels
            size: number of candidates to be returned
            file_path: input file path
            df: input dataframe
            auxiliary_fields: auxiliary fields to fetch from the ES index
            auxiliary_folder: folder where auxiliary data will be stored
            property: if specified, property:identifier pairs will be searched

        Returns: candidates DataFrame

        """
        if file_path is None and df is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("file_path", "df"))

        if self.pgt_column:
            if self.pgt_column not in df.columns:
                raise TLException(f'pgt column: {self.pgt_column} is not present in the file')

            if top5_property_column not in df.columns or top5_class_column not in df.columns:
                raise TLException(f'Required columns: {top5_class_column} and {top5_property_column}')

        if file_path:
            df = pd.read_csv(file_path, dtype=object)

        df.fillna(value="", inplace=True)

        pgt_dict = {}

        is_pgt_cell = []

        extra_musts = list()

        df_non_pgt = None

        if self.pgt_column:
            df_pgt_cells = df[df[self.pgt_column].astype(float) == 1]
            sorted_classes, sorted_properties = self.get_hc_properties_classes(df_pgt_cells)
            if len(sorted_classes) > 0:
                extra_musts.append({
                    "term": {
                        "instance_ofs.keyword_lower": {
                            "value": sorted_classes[0][0].lower()
                        }
                    }
                })

            if len(sorted_properties) > 0:
                extra_musts.append({
                    "term": {
                        "properties.keyword_lower": {
                            "value": sorted_properties[0][0].lower()
                        }
                    }
                })

            for c, r in zip(df_pgt_cells.column, df_pgt_cells.row):
                pgt_dict[f'{c}_{r}'] = 1

            for c, r in zip(df.column, df.row):
                is_pgt_cell.append(1) if f'{c}_{r}' in pgt_dict else is_pgt_cell.append(0)

            df['is_pgt_cell'] = is_pgt_cell

            df_non_pgt = df[df['is_pgt_cell'] == 0]

            non_essential_columns = [x for x in df.columns if x not in essential_columns]

            df_non_pgt.drop(columns=non_essential_columns, inplace=True)

            df_non_pgt.drop_duplicates(subset=['column', 'row'], inplace=True)

        if isa:
            extra_musts.append({
                "term": {
                    "instance_ofs.keyword_lower": {
                        "value": isa.lower()
                    }
                }
            })
        if property:
            extra_musts.append({
                "term": {
                    "properties.keyword_lower": {
                        "value": property.lower()
                    }
                }
            })

        properties = "all_labels.*.trigram"
        result_df = self.utility.create_candidates_df(df_non_pgt,
                                                      column,
                                                      size,
                                                      properties,
                                                      'trigram-match',
                                                      auxiliary_fields=auxiliary_fields,
                                                      auxiliary_folder=auxiliary_folder,
                                                      auxiliary_file_prefix='trigram_matches_',
                                                      extra_musts=extra_musts) \
            if df_non_pgt is not None \
            else \
            self.utility.create_candidates_df(
                df,
                column,
                size,
                properties,
                'trigram-match',
                auxiliary_fields=auxiliary_fields,
                auxiliary_folder=auxiliary_folder,
                auxiliary_file_prefix='trigram_matches_',
                extra_musts=extra_musts)

        if self.pgt_column:
            result_df = result_df[result_df['method'] == 'trigram-match']
        return result_df

    def get_hc_properties_classes(self, df_pgt):
        class_counts = {}
        property_counts = {}
        for qnode_vals in df_pgt[top5_class_column].values:
            for qnode_val in qnode_vals.split('|'):
                q, v = qnode_val.split(':')
                class_counts[q] = float(v)

        for qnode_vals in df_pgt[top5_property_column].values:
            for qnode_val in qnode_vals.split('|'):
                q, v = qnode_val.split(':')
                property_counts[q] = float(v)

        sorted_class_counts = [(k, v) for k, v in sorted(class_counts.items(), key=lambda item: item[1], reverse=True)]
        sorted_property_counts = [(k, v) for k, v in
                                  sorted(property_counts.items(), key=lambda item: item[1], reverse=True)]
        return sorted_class_counts, sorted_property_counts
