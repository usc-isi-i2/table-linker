import re
import pandas as pd
from typing import List, Tuple

ccm_columns = ['type', 'score', 'property', 'row',
               'col1', 'col1_item', 'col1_string', 'col2', 'col2_string', 'col2_item']


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

        self.ccm = pd.DataFrame(columns=ccm_columns)

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
            'col2_item': col2_item
        }
        self.ccm = pd.concat([self.ccm, pd.DataFrame(triple)], ignore_index=True)

    def has_candidate(self, col1_item: str):
        """
        Returns true of the CellContextMatches contains information for a given q_node.
        """
        return len(self.ccm[self.ccm['col1_item'] == col1_item]) > 0

    def get_triples(self):
        """
        Return a list of all the triples
        """
        return self.ccm.to_dict('records')  # returns a list of dicts

    def get_triples_df(self):
        """
        Return a list of all the triples
        """
        return self.ccm

    def get_triples_to_column(self, col2: str):
        """
        Return the triples to another column.
        """
        if self.col == col2:
            raise Exception(f'Cannot find context for a column with itself. col1: {self.col}, col2: {col2}')
        return self.ccm[self.ccm.col2 == col2].to_dict('records')

    def get_properties(self, col2: str) -> List[Tuple[str, str, float, int]]:
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
        df = self.ccm[self.ccm.col2 == col2].copy()
        grouped_df = df.groupby(by=['property', 'type'])

        result = []
        for key, pdf in grouped_df:
            property = key[0]
            type = key[1]
            best_score = pdf['score'].max()
            count_appears = len(pdf)
            result.append((property, type, best_score, count_appears))
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
                 label_column: str = 'label_clean'
                 ):
        """
        Maybe better to have a set of columns

      Create a ContextMatches datastructure to store the context matches between columns in a row.
      Each entry in the ContextMatches array is a list of dicts, where each dict contains
      row, col1, col2, property, score, col1_item, col2_string and col2_item.

      The internal datastructure must return the matches between two columns in a rows in constant time,
      so the backing store must be NumPy array.
        """

        if context_path is not None:
            context_dict = self.read_context_file(context_path)

        self.ccm_dict = {}

        if input_df is not None:
            self.initialize(input_df, context_dict, label_column)

        if input_path is not None:
            self.load_from_disk(input_path)

    def initialize(self, input_df, context_dict, label_column):
        columns = set(input_df['column'].unique())

        row_col_label_dict = {}

        for row, col, label in zip(input_df['row'], input_df['column'], input_df[label_column]):
            key = f"{row}_{col}"
            row_col_label_dict[key] = label

        for row, col, kg_id, kg_id_label_str, kg_id_alias_str in zip(input_df['row'],
                                                                     input_df['column'],
                                                                     input_df['kg_id'],
                                                                     input_df['kg_labels'],
                                                                     input_df['kg_aliases']):
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
                    if col != col2:
                        context_results = self.compute_context_similarity(kg_id_context,
                                                                          row_col_label_dict.get(f"{row}_{col2}", None))
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
                                           score=context_result['score']
                                           )

    def compute_context_similarity(self,
                                   kg_id_context: List[dict],
                                   col2_string: str) -> List[dict]:
        result = []

        if col2_string is None:
            return result

        for prop_val_dict in kg_id_context:
            score, best_str_match = self.computes_string_similarity(prop_val_dict['values'], col2_string)
            result.append({
                "type": prop_val_dict['t'],
                "col2_string": best_str_match,
                "score": score,
                "property": prop_val_dict['p'],
                'col2_item': prop_val_dict.get('i', None)
            })

        return result

    def computes_string_similarity(self, values: List[str], col2_string: str) -> Tuple[float, str]:
        return 0.0, "best_matched_string"

    def add_match(self, row, col1, col1_item, col1_string, col2, col2_item, col2_string, type, property, score):
        """
        Add a context match to the database of context matches. The match represents a triple
        from col1 to col2, nad stores the matching score, property and the value it matcheed to.

        In addition, adds a reverse link from col2 to col1, using _ for the reverse property,
        e.g., if the property is P59, the reverse link will record the property as _P59.
        """

        ccm_key = f'{row}_{col1}'
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
            col2_item=col2_item

        )

        if type == 'i':  # add reverse context, type is item
            self.ccm_dict[ccm_key].add_triple(row=row,
                                              col1=col2,
                                              col1_item=col2_item,
                                              col1_string=col2_string,
                                              type=type,
                                              score=score,
                                              property=f"_{property}",
                                              col2=col1,
                                              col2_string=col1_string,
                                              col2_item=col1_item,
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
            out.append(self.ccm_dict[key].get_triples_df())
        pd.concat(out).to_csv(output_path, index=False)

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
    def parse_context_string(qnode, context_string: str) -> dict:

        context_dict = {
            qnode: []
        }

        p_v_dict = {}
        try:
            if context_string:
                prop_val_list = re.split(r'(?<!\\)\|', context_string)

                for prop_val in prop_val_list:
                    _type = prop_val[0]

                    values, property, item = TableContextMatches.parse_prop_val(qnode, prop_val)

                    if item is None:
                        key = property
                        if key not in p_v_dict:
                            p_v_dict[key] = {
                                'p': property,
                                "t": _type,
                                'v': []
                            }
                        p_v_dict[key]['v'].append(values)

                    else:
                        key = f"{property}_{item}"
                        if key not in p_v_dict:
                            p_v_dict[key] = {
                                'p': property,
                                'i': item,
                                'v': [],
                                "t": _type
                            }
                        p_v_dict[key]['v'].append(values)
        except Exception as e:
            raise Exception(e)

        for k in p_v_dict:
            context_dict[qnode].append(p_v_dict[k])

        return context_dict

    @staticmethod
    def parse_prop_val(qnode, property_value_string):
        line_started = False
        string_value = list()

        property_value_string = property_value_string[1:]

        for i, c in enumerate(property_value_string):
            if i == 0 and c == '"':  # start of the string value:
                line_started = True
            if line_started:
                string_value.append(c)
            if (i > 0 and c == '"' and property_value_string[i - 1] != "\\") \
                    or \
                    (i > 0 and c == '"' and property_value_string[i + 1] == ":" and property_value_string[
                        i + 2] == "P"):
                line_started = False
        string_val = "".join(string_value)
        length_remove = len(string_val) + 1  # ":" eg i"utc+01:00":P421:Q6655
        rem_vals = property_value_string[length_remove:].split(":")
        n = len(string_val)
        string_val = string_val[1: n - 1]

        property = rem_vals[0]

        if not property.startswith('P'):
            raise Exception(
                f"Unexpected format of the context string, Qnode: {qnode}, context string: {property_value_string}. "
                f"Property does not starts with 'P'")

        if len(rem_vals) == 2:
            item = rem_vals[1]
            if not item.startswith('Q'):
                raise Exception(
                    f"Unexpected format of the context string, Qnode: {qnode}, context string: {property_value_string}"
                    f". Item does not start with 'Q'")
            return string_val, rem_vals[0], item

        if len(rem_vals) == 1:
            return string_val, property, None

        if len(rem_vals) > 2:
            raise Exception(
                f"Unexpected format of the context string, Qnode: {qnode}, context string: {property_value_string}")

    @staticmethod
    def read_context_file(context_file: str) -> dict:
        f = open(context_file)
        context_dict = {}
        for line in f:
            vals = line.split("\t")
            qnode = vals[0]
            context = vals[2]

            context_dict.update(TableContextMatches.parse_context_string(qnode, context))
        return context_dict
