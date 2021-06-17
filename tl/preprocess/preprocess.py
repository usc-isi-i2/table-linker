import ftfy
import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException
from tl.exceptions import RequiredColumnMissingException


def canonicalize(columns, output_column='label', file_path=None, df=None, file_type='csv',
                 add_context=False, context_column_name="context"):
    """
    translate an input CSV or TSV file to canonical form

    Args:
        columns: the columns in the input file to be linked to KG entities. Multiple columns are specified as a comma separated string.
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
    for column in columns:
        if column not in df.columns:
            raise RequiredColumnMissingException("The input column {} does not exist in given data.".format(column))
    out = list()
    for i, v in df.iterrows():
        for column in columns:
            if add_context:
                remaining_columns = v.keys().tolist()
                remaining_columns.remove(column)
                remaining_values = "|".join(v[remaining_columns].dropna().values.tolist())
                out.append({
                    'column': df.columns.get_loc(column),
                    'row': i,
                    output_column: v[column],
                    context_column_name: remaining_values
                })
            else:
                out.append({
                    'column': df.columns.get_loc(column),
                    'row': i,
                    output_column: v[column]
                })
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

    for symbol in symbols:
        clean_label = clean_label.replace(symbol, ' ') if replace_by_space else clean_label.replace(symbol, '')

    return '{}|{}'.format(label, clean_label) if keep_original else clean_label
