import re
import json
import operator
import sys
import dateutil.parser as dp
import pandas as pd
from typing import List, Tuple, Set
from rltk import similarity
from tl.exceptions import TLException
import numpy as np

ccm_columns = ['type', 'score', 'property', 'row',
               'col1', 'col1_item', 'col1_string', 'col2', 'col2_string', 'col2_item']

valid_property_types = {'i', 'd', 'q', 'e'}


class CellContextMatches:
    """
    Contains the context matches for a single cell to all other cells in the same row.
    This class contains all the triples for all candidates for a cell.
    """

    def __init__(self,
                 row: str,
                 col: str,
                 ):
        """
        Create an empty CellContextMatches for a specific cell.
        """
        self.row = row
        self.col = col

        # self.ccm = pd.DataFrame(columns=ccm_columns)
        self.ccm = dict()
        self.col1_items = set()

    def add_triple(self,
                   row: str,
                   col1: str,
                   col1_item: str,
                   col1_string: str,
                   type: str,
                   score: float,
                   property: str,
                   col2: str,
                   col2_string: str,
                   best_match: str,
                   col2_item: str = None):
        """
        Add a single triple to CellContextMatches.
        """
        triple = {
            'type': type,
            'score': score,
            'property': property,
            'row': row,
            'col1': col1,
            'col1_item': col1_item,
            'col1_string': col1_string,
            'col2': col2,
            'col2_string': col2_string,
            'col2_item': col2_item,
            'best_match': best_match
        }
        if col2 not in self.ccm:
            self.ccm[col2] = list()

        self.ccm[col2].append(triple)
        self.col1_items.add(col1_item)

    def has_candidate(self, col1_item: str):
        """
        Returns true of the CellContextMatches contains information for a given q_node.
        """
        return col1_item in self.col1_items

    def get_triples(self):
        """
        Return a list of all the triples
        """
        out = []
        for k in self.ccm:
            triples = self.ccm[k]
            out.extend(triples)

        return out

    def get_triples_to_column(self, col2: str):
        """
        Return the triples to another column.
        """
        if self.col == col2:
            raise Exception(f'Cannot find context for a column with itself. col1: {self.col}, col2: {col2}')
        return self.ccm.get(col2, [])

    def get_properties(self, col2: str, q_node: str = None) -> List[Tuple[str, str, float, int]]:
        """
        list of tuples (property, type, best score, count_appears)
        -> [("P175", "i", 0.95, 4), ...]
        current_col
        for col in range(0, max_columns):
            for row in range (0, max_rows):
                cc = tcm.get_cell_context(row, col)
                props = cc.get_properties(3)
        """
        if self.col == col2:
            raise Exception(f'Cannot find context for a column with itself. col1: {self.col}, col2: {col2}')

        result = []

        col2_records = self.ccm.get(col2, [])
        if q_node:
            col2_records = [s for s in col2_records if s.get('col1_item') == q_node]
        prop_count = {}
        for record in col2_records:
            property = record['property']
            score = record['score']
            if property not in prop_count:
                prop_count[property] = {
                    'count': 0,
                    'max_score': -1.0,
                    'type': record['type'],
                    'sum': 0
                }
            prop_count[property]['count'] += 1
            prop_count[property]['sum'] += score
            if score > prop_count[property]['max_score']:
                prop_count[property]['max_score'] = score
        for property in prop_count:
            number_of_occurences = prop_count[property]['count']
            avg_score = prop_count[property]['sum'] / number_of_occurences
            max_score = prop_count[property]['max_score']
            result.append((property,
                           prop_count[property]['type'],
                           max_score,
                           avg_score,
                           number_of_occurences))
        return result


class TableContextMatches:
    """
    Contains all context matches for a table, for every cell that we have to link to all other cells in
    the same row.
    """

    def __init__(self,
                 context_path: str = None,
                 context_dict: dict = None,
                 input_df: pd.DataFrame = None,
                 input_path: str = None,
                 context_matches_path=None,
                 label_column: str = 'label_clean',
                 ignore_column: str = None,
                 relevant_properties_file: str = None,
                 use_relevant_properties: bool = False,
                 save_relevant_properties: bool = False,
                 string_similarity_threshold: float = 0.7,
                 quantity_similarity_threshold: float = 0.3,
                 output_column_name: str = "context_score"
                 ):
        """
      Maybe better to have a set of columns
      Create a ContextMatches datastructure to store the context matches between columns in a row.
      Each entry in the ContextMatches array is a list of dicts, where each dict contains
      row, col1, col2, property, score, col1_item, col2_string and col2_item.
      The internal datastructure must return the matches between two columns in a rows in constant time,
      so the backing store must be NumPy array.
        """
        self.ignore_column = ignore_column
        if self.ignore_column:
            self.prefix_column_name = "ignore_"
        else:
            self.prefix_column_name = ""
        self.row_col_label_dict = {}
        if context_path is not None:
            context_dict = self.read_context_file(context_path)
        self.output_column_name = output_column_name
        self.ccm_dict = {}
        self.string_similarity_threshold = string_similarity_threshold
        self.quantity_similarity_threshold = quantity_similarity_threshold
        self.input_df = None
        if input_path is not None:
            input_df = pd.read_csv(input_path)
        self.relevant_properties_file = relevant_properties_file
        self.use_relevant_properties = use_relevant_properties
        self.save_relevant_properties = save_relevant_properties
        self.relevant_properties = {}
        if use_relevant_properties:
            self.relevant_properties = self.read_relevant_properties()
        input_df['row'] = input_df['row'].astype('str')
        input_df['column'] = input_df['column'].astype('str')
        self.main_entity_column = self.find_main_entity_column(input_df, label_column)
        self.initialize(input_df, context_dict, label_column)

        if context_matches_path is not None:
            self.load_from_disk(context_matches_path)

    def read_relevant_properties(self) -> dict:  # or whatever datastructure makes sense
        if self.relevant_properties_file is None:
            raise TLException('Please specify a valid path for relevant properties.')

        relevant_properties_df = pd.read_csv(self.relevant_properties_file)
        relevant_properties_group = relevant_properties_df.groupby(['column', 'col2'])
        relevant_properties_dict = {}
        for cell, group in relevant_properties_group:
            column_column_pair = f"{cell[0]}_{cell[1]}"
            all_properties = set(group['property_'].unique())
            relevant_properties_dict[column_column_pair] = all_properties

        return relevant_properties_dict

    def write_relevant_properties(self, relevant_properties_df: pd.DataFrame):
        if self.relevant_properties_file is None:
            raise TLException('Please specify a valid path for relevant properties.')
        relevant_properties_df.to_csv(self.relevant_properties_file, index=False)

    def is_relevant_property(self, col1: str, col2: str, property: str) -> bool:
        column_column_pair = f"{col1}_{col2}"
        # Lookup the dictionary
        if column_column_pair in self.relevant_properties:
            column_relevant_properties = self.relevant_properties[column_column_pair]
            if property in column_relevant_properties:
                return True
        return False

    def find_main_entity_column(self, input_df, label_column) -> str:
        col_labels_dict = {}
        for col, gdf in input_df.groupby(by=['column']):
            col_labels_dict[col] = len(gdf[label_column].unique())

        max_cols = [key for (key, value) in col_labels_dict.items() if value == max(col_labels_dict.values())]
        if len(max_cols) == 1:
            return max_cols[0]
        return '0'

    def initialize(self, raw_input_df, context_dict, label_column):

        raw_input_df['kg_labels'].fillna("", inplace=True)
        raw_input_df['kg_aliases'].fillna("", inplace=True)
        raw_input_df['context'].fillna("", inplace=True)

        if self.ignore_column is not None:
            _input_df = raw_input_df[(raw_input_df[self.ignore_column].astype(float) == 0)
                                     & (raw_input_df['column'] == self.main_entity_column)]
            not_ignored_rows = set(_input_df['row'].unique())
            _input_df_2 = raw_input_df[
                (raw_input_df['row'].isin(not_ignored_rows)) & (raw_input_df["column"] != self.main_entity_column)]

            self.input_df = pd.concat([_input_df, _input_df_2])

            not_ignored_indices = self.input_df.index

            self.other_input_df = raw_input_df[~raw_input_df.index.isin(not_ignored_indices)]

            assert (len(self.input_df) + len(self.other_input_df)) == len(raw_input_df)
        else:
            self.input_df = raw_input_df
            self.other_input_df = None
        rows = set(self.input_df['row'].unique())
        columns = set(self.input_df['column'].unique())
        row_column_pairs = set()
        for row, col, label in zip(self.input_df['row'], self.input_df['column'], self.input_df[label_column]):
            key = f"{row}_{col}"
            row_column_pairs.add(key)
        # row_column_label_dict stores only the row_column pairs that need to be matched
        for row, col, context in zip(self.input_df['row'], self.input_df['column'], self.input_df['context']):
            if col == '0':
                context_vals = context.split('|')
                for i, context_val in enumerate(context_vals):
                    context_column = i + 1
                    row_col_dict_key = f"{row}_{context_column}"
                    if row_col_dict_key not in self.row_col_label_dict:
                        try:
                            date = dp.parse(context_val)
                            context_val = str(date.year)
                        except:
                            pass
                        self.row_col_label_dict[row_col_dict_key] = context_val
                        columns.add(str(context_column))
        for row, col, kg_id, kg_id_label_str, kg_id_alias_str in zip(self.input_df['row'],
                                                                     self.input_df['column'],
                                                                     self.input_df['kg_id'],
                                                                     self.input_df['kg_labels'],
                                                                     self.input_df['kg_aliases']):
            kg_id_context = context_dict.get(kg_id, None)
            kg_labels = []
            if kg_id_label_str and kg_id_label_str.strip() != "":
                kg_labels.append(kg_id_label_str.strip())
            if kg_id_alias_str and kg_id_alias_str.strip() != "":
                kg_labels.append(kg_id_alias_str.strip())
            kg_label_str = "|".join(kg_labels)

            ccm_key = f"{row}_{col}"

            if ccm_key not in self.ccm_dict:
                self.ccm_dict[ccm_key] = CellContextMatches(row, col)
            if kg_id_context is not None:
                for col2 in columns:
                    if (col != col2) and (col == self.main_entity_column or col2 == self.main_entity_column):

                        ccm_key_2 = f"{row}_{col2}"
                        if ccm_key_2 not in self.ccm_dict:
                            self.ccm_dict[ccm_key_2] = CellContextMatches(row, col2)
                        context_results = self.compute_context_similarity(kg_id_context, col,
                                                                          col2,
                                                                          self.row_col_label_dict.get(f"{row}_{col2}",
                                                                                                      None))
                        for context_result in context_results:
                            self.add_match(row=row,
                                           col1=col,
                                           col1_item=kg_id,
                                           col1_string=kg_label_str,
                                           col2=col2,
                                           col2_item=context_result['col2_item'],
                                           col2_string=context_result['col2_string'],
                                           type=context_result['type'],
                                           property=context_result['property'],
                                           score=context_result['score'],
                                           best_match=context_result['best_match']
                                           )
        self.input_df = self.process(row_column_pairs, columns)

    def process(self, row_column_pairs: set, n_context_columns: set):
        context_scores, properties, similarities = self.compute_context_scores(n_context_columns, row_column_pairs)
        self.input_df[self.output_column_name] = context_scores
        self.input_df[self.prefix_column_name + 'context_properties'] = properties
        self.input_df[self.prefix_column_name + 'context_similarity'] = similarities
        out = [self.input_df]
        if self.other_input_df is not None:
            out.append(self.other_input_df)
        return pd.concat(out).fillna(0.0)

    def correctness_of_candidate(self):
        # Number of matches are the number it matched correctly
        pass

    def compute_context_scores(self, n_context_columns: set, row_column_pairs: set) -> (
            List[int], List[str], List[int]):
        self.compute_property_scores(row_column_pairs, n_context_columns)
        context_score_list = []
        context_property_list = []
        context_similarity_list = []
        for row, col, q_node in zip(self.input_df['row'], self.input_df['column'], self.input_df['kg_id']):
            # Handle equal similarity for different properties by looping over and getting
            # the one with highest similarity.
            property_matched = []
            similarity_matched = []
            sum_of_properties = 0
            r_c = f"{row}_{col}"
            for col2 in n_context_columns:
                if col2 != col and (col == self.main_entity_column or col2 == self.main_entity_column):
                    returned_properties = self.ccm_dict[r_c].get_properties(col2, q_node=q_node)
                    if not returned_properties:
                        continue
                    best_score = 0
                    property_ = None
                    for properties in returned_properties:
                        if properties[2] > best_score:
                            property_ = properties[0]
                            best_score = properties[2]
                    # if property_ not in current_relevant_properties: pass
                    property_matched.append(property_ + "(" + str(best_score) + ")")
                    similarity_matched.append(best_score)
                    sum_of_properties = sum_of_properties + best_score
            if sum_of_properties == 0:
                context_score = 0
            else:
                context_score = (1 - 1 / pow(2, sum_of_properties))
            context_score_list.append(context_score)
            context_similarity_list.append(similarity_matched)
            context_property_list.append(property_matched)
        return context_score_list, context_property_list, context_similarity_list

    def compute_property_scores(self, row_column_pairs: set, n_context_columns: set):
        properties_df_list = []
        for r_c in row_column_pairs:
            row_col = r_c.split("_")
            row = row_col[0]
            col = row_col[1]
            for col2 in n_context_columns:
                if (col2 != col) and (col2 == self.main_entity_column or col == self.main_entity_column):
                    m = self.ccm_dict[r_c].get_properties(col2)
                    int_prop = pd.DataFrame(m, columns=["property_", "type", "best_score", "avg_score", "n_occurences"])
                    int_prop['row'] = row
                    int_prop['column'] = col
                    int_prop['col2'] = col2
                    properties_df_list.append(int_prop)
            if len(properties_df_list) > 0:
              properties_df = pd.concat(properties_df_list)
        property_value_list = []
        grouped_obj = properties_df.groupby(['column', 'col2', 'property_'])
        for cell, group in grouped_obj:
            property_score = (group['avg_score'].sum(axis=0))
            property_value_list.append([cell[2], cell[0], cell[1], property_score])
        property_value_df = pd.DataFrame(property_value_list, columns=['property_', 'column', 'col2', 'property_score'])
        property_value_df = property_value_df.sort_values(by=['column', 'property_score'], ascending=[True, False])
        # Saving the top 3 properties for each column column pair that we have.
        # <column, col2> is equivalent to <from, to>
        most_important_property_df = property_value_df.groupby(['column', 'col2']).head(3)
        if self.save_relevant_properties:
            self.write_relevant_properties(most_important_property_df)

    def compute_context_similarity(self,
                                   kg_id_context: List[dict],
                                   col: str,
                                   col2: str,
                                   col2_string: str,
                                   string_separator: str = ",",
                                   return_zero_similarity: bool = False) -> List[dict]:
        result = []

        if col2_string is None:
            return result

        if string_separator in col2_string:
            col2_string_split = col2_string.split(",")
            col2_string_set = set(col2_string_split)
        else:
            col2_string_set = {col2_string}

        for prop_val_dict in kg_id_context:
            property = prop_val_dict['p']
            if not self.use_relevant_properties or (self.use_relevant_properties
                                                    and
                                                    self.is_relevant_property(col, col2, property)):
                score, best_str_match = self.computes_similarity(prop_val_dict['v'],
                                                                 col2_string_set,
                                                                 prop_val_dict['t'])
                # TODO: remove the following if condition after rltk release: 2.0.0a19
                if score < self.string_similarity_threshold:
                    score = 0

                if score > 0.0 or (score == 0.0 and return_zero_similarity):
                    result.append({
                        "type": prop_val_dict['t'],
                        "col2_string": col2_string,
                        "best_match": best_str_match,
                        "score": score,
                        "property": property,
                        'col2_item': prop_val_dict.get('i', None)
                    })

        return result

    def return_a_number(self, col2_string: str) -> float:
        col2_string_stripped = col2_string.replace('"', '')
        to_match_1 = col2_string_stripped.replace(",", "")
        numeric_col2_value = None
        try:
            if " " in to_match_1:
                split_v = to_match_1.split(" ")
                for s in split_v:
                    if self.return_a_number(s):
                        numeric_col2_value = self.return_a_number(s)
            else:
                numeric_col2_value = float(to_match_1)
        except ValueError:
            return np.nan
        return numeric_col2_value

    @staticmethod
    def preprocess(word: str) -> list:
        word = word.lower()
        preprocessed_word = re.sub(r'[^\w\s]', '', word)
        preprocessed_word = preprocessed_word.split(" ")
        return preprocessed_word

    def compute_quantity_similarity(self, quantity_1: float, quantity_2: float) -> float:
        """
        Purpose: Calculates the score between two quantities by taking the absolute difference between them and
        dividing by the max of both.
        It is then subtracted from 1.
        Returns: score
        """
        if quantity_1 == 0.0 and quantity_2 == 0.0:
            return 1
        quantity_score = 1 - (abs(quantity_1 - quantity_2) / max(abs(quantity_1), abs(quantity_2)))
        return quantity_score if quantity_score >= self.quantity_similarity_threshold else 0

    def computes_similarity(self,
                            context_values: List[str],
                            col2_string_set: Set[str],
                            context_values_type: str) -> Tuple[float, str]:
        max_sim = 0.0
        best_matched = ""
        for col2_string in col2_string_set:
            for context_value in context_values:
                if col2_string == context_value:
                    max_sim = 1.0
                    best_matched = context_value
                    break
                else:
                    current_sim = 0
                    if context_values_type == 'q':
                        col2_num = self.return_a_number(col2_string)
                        if col2_num:
                            current_sim = self.compute_quantity_similarity(float(col2_num), float(context_value))
                    elif context_values_type == 'i':
                        current_sim = similarity.hybrid.symmetric_monge_elkan_similarity(self.preprocess(context_value),
                                                                                         self.preprocess(col2_string),
                                                                                         lower_bound=self.string_similarity_threshold)
                    if current_sim > max_sim:
                        max_sim = current_sim
                        best_matched = context_value
                        if max_sim == 1.0:
                            break
        return max_sim, best_matched

    def add_match(self, row, col1, col1_item, col1_string, col2, col2_item, col2_string, type, property, score,
                  best_match):
        """
        Add a context match to the database of context matches. The match represents a triple
        from col1 to col2, nad stores the matching score, property and the value it matcheed to.
        In addition, adds a reverse link from col2 to col1, using _ for the reverse property,
        e.g., if the property is P59, the reverse link will record the property as _P59.
        """

        ccm_key = f'{row}_{col1}'
        ccm_key_2 = f'{row}_{col2}'

        self.ccm_dict[ccm_key].add_triple(
            row=row,
            col1=col1,
            col1_item=col1_item,
            col1_string=col1_string,
            type=type,
            score=score,
            property=property,
            col2=col2,
            col2_string=col2_string,
            col2_item=col2_item,
            best_match=best_match

        )

        if type == 'i':  # add reverse context, type is item
            self.ccm_dict[ccm_key_2].add_triple(row=row,
                                                col1=col2,
                                                col1_item=col2_item,
                                                col1_string=col2_string,
                                                type=type,
                                                score=score,
                                                property=f"_{property}",
                                                col2=col1,
                                                col2_string=col1_string,
                                                col2_item=col1_item,
                                                best_match=best_match
                                                )

        # Create a CellContextMatches if none exists for this cell an dthen call cellcm.add_triple()

    def get_cell_context_mathes(self, row, col):
        """
        Return the CellContextMatch for the given cell.
        """
        return self.ccm_dict[f'{row}_{col}']

    def serialize(self, output_path):
        """Construct a serialization to save to disk."""

        out = list()
        for key in self.ccm_dict:
            triples = self.ccm_dict[key].get_triples()
            out.extend(triples)

        pd.DataFrame(out).to_csv(output_path, index=False)

    def load_from_disk(self, path):
        """
        Populate the contents of a ContextMatch from a file on disk
        """
        concatenated_df = pd.read_csv(path)
        records = concatenated_df.to_dict('records')
        for record in records:
            row = record['row']
            property = record['property']
            if property.startswith('P'):
                col = record['col1']
            elif property.startswith('_'):  # inverse property
                col = record['col2']
            else:
                raise Exception(f'invalid property: {property}')

            ccm_key = f"{row}_{col}"
            if ccm_key not in self.ccm_dict:
                self.ccm_dict[ccm_key] = CellContextMatches(row, col)
            self.ccm_dict[ccm_key].add_triple(row=row,
                                              col1=col,
                                              col1_item=record['col1_item'],
                                              col1_string=record['col1_string'],
                                              type=record['type'],
                                              score=record['score'],
                                              property=property,
                                              col2=record['col2'],
                                              col2_string=record['col2_string'],
                                              col2_item=record['col2_item']
                                              )

    @staticmethod
    def read_context_file(context_file: str) -> dict:
        f = open(context_file)
        context_dict = {}
        for line in f:
            context_dict.update(json.loads(line.strip()))

        return context_dict
