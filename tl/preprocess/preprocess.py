import ftfy
import pandas as pd
from typing import List
from tl.exceptions import RequiredInputParameterMissingException
from tl.exceptions import RequiredColumnMissingException


def canonicalize(columns, output_column='label', file_path=None, df=None, file_type='csv',
                 add_context=False, context_column_name="context", file_name=None, skip_columns: List[str] = None):
    """
    translate an input CSV or TSV file to canonical form

    Args:
        columns: the columns in the input file to be linked to KG entities. Multiple columns are specified as a comma
        separated string.
        output_column: specifies the name of a new column to be added. Default output column name is label
        file_path: input file path
        df: or input dataframe
        file_type: csv or tsv
        add_context: choose whether to add other information or not to canonicalize files
        context_column_name: the column name for the other information
    Returns: a dataframe in canonical form

    """
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {}or {}'.format("file_path", "df"))

    if file_path:
        df = pd.read_csv(file_path, sep=',' if file_type == 'csv' else '\t', dtype=object)

    columns = columns.split(',')
    remaining_columns = df.columns.tolist()
    for column in columns:
        if column not in df.columns:
            raise RequiredColumnMissingException("The input column {} does not exist in given data.".format(column))

    if skip_columns:
        for c in skip_columns:
            remaining_columns.remove(c)

    remaining_col_ids = [df.columns.get_loc(x) for x in remaining_columns]

    df.fillna("", inplace=True)
    out = list()

    row_num = 0
    for tup in zip(*[df[col] for col in df]):
        for column in columns:
            column_idx = df.columns.get_loc(column)
            context_columns = remaining_col_ids.copy()
            context_columns.remove(column_idx)
            new_row = {
                'column': column_idx,
                'row': row_num,
                output_column: tup[column_idx]
            }
            if add_context:
                remaining_values = "|".join([tup[x] for x in context_columns])
                new_row[context_column_name] = remaining_values
            if file_name is not None:
                new_row['filename'] = file_name
                new_row['column-id'] = f'{file_name}-{column_idx}'

            out.append(new_row)
        row_num += 1
    return pd.DataFrame(out).sort_values(by=['column', 'row'])


def extract_ground_truth(target_column, kg_id_column, kg_label_column, file_path=None, df=None, file_type='csv'):
    """
    Returns ground truth dataframe by extracting columns from input dataframe

    Args:
        target_column: the column in the input file to be linked to KG entities
        kg_id_column: the column in the input file containing the kg identifier
        kg_label_column: the column in the input file containing the kg label
        file_path: input file path
        df: or input dataframe
        file_type: csv or tsv
    Returns: ground truth dataframe in canonical format
    """

    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {}or {}'.format("file_path", "df"))

    for column in [target_column, kg_id_column, kg_label_column]:
        if column not in df.columns:
            raise RequiredColumnMissingException("The input column {} does not exist in given data.".format(column))

    if file_path:
        df = pd.read_csv(file_path, sep=',' if file_type == 'csv' else '\t', dtype=object)

    target_column_index = df.columns.get_loc(target_column)
    out = list()
    for i, v in df.iterrows():
        out.append({
            'column': target_column_index,
            'row': i,
            'kg_id': v[kg_id_column],
            'kg_label': v[kg_label_column]
        })
    return pd.DataFrame(out).sort_values(by=['column', 'row'])


def clean(column, output_column=None, file_path=None, df=None, symbols='!@#$%^&*()+={}[]:;’\”/<>',
          replace_by_space=True, keep_original=False):
    """
    cleans the cell values in a column, creating a new column with the clean values.

    Args:
        column: the column to be cleaned.
        output_column: the name of the column where cleaned column values are stored. If not provided, the name of the
        new column is the name of the input column with the suffix _clean.
        file_path: input file path
        df: or input dataframe
        symbols: a string containing the set of characters to be removed: default is “!@#$%^&*()+={}[]:;’\”/<>”
        replace_by_space: when True (default) all instances of the symbols are replaced by a space. In case of removal
        of multiple consecutive characters, they’ll be replaced by a single space. The value False causes the symbols to be deleted.
        keep_original: when True, the output column will contain the original value and the clean value will be
        appended, separated by |. Default is False

    Returns: a dataframe with the new output clean containing clean values

    """
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format(file_path, df))
    symbols = list(symbols)

    if output_column is None:
        output_column = '{}_clean'.format(column)
    if file_path:
        df = pd.read_csv(file_path)

    df[output_column] = df[column].map(lambda x: string_clean(x, symbols, replace_by_space, keep_original))
    return df


def string_clean(label, symbols, replace_by_space, keep_original):
    if not isinstance(label, str):
        label = str(label)
    clean_label = ftfy.fix_encoding(label)
    clean_label = ftfy.fix_text(clean_label)
    _no_brackets_label = remove_text_inside_brackets(clean_label)
    if _no_brackets_label.strip() != "":
        clean_label = _no_brackets_label

    for symbol in symbols:
        clean_label = clean_label.replace(symbol, ' ') if replace_by_space else clean_label.replace(symbol, '')
    clean_label = " ".join(clean_label.split())

    return '{}|{}'.format(label, clean_label) if keep_original else clean_label


def remove_text_inside_brackets(text, brackets="()[]"):
    count = [0] * (len(brackets) // 2)  # count open/close brackets
    saved_chars = []
    for character in text:
        for i, b in enumerate(brackets):
            if character == b:  # found bracket
                kind, is_close = divmod(i, 2)
                count[kind] += (-1) ** is_close  # `+1`: open, `-1`: close
                if count[kind] < 0:  # unbalanced bracket
                    count[kind] = 0  # keep it
                else:  # found bracket to remove
                    break
        else:  # character is not a [balanced] bracket
            if not any(count):  # outside brackets
                saved_chars.append(character)
    return ''.join(saved_chars).strip()
