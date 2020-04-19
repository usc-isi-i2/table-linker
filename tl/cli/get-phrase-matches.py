import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'retrieves the identifiers of KG entities base on phrase match queries.'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True,
                        help='the column used for retrieving candidates.')

    parser.add_argument('-p', '--properties', action='store', type=str, dest='properties', default='labels^2,aliases',
                        help='a comma separated names of properties in the KG to search for exact match query')

    parser.add_argument('-n', action='store', type=int, dest='size', default=50,
                        help='maximum number of candidates to retrieve')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    # used for filtering
    parser.add_argument('--filter', action='store', nargs='?', dest='filter_condition',
                        default="", help="If set to run filtering, which kind of the data should keep.")

def remove_previous_match_res(df):
    to_drop_cols = ["kg_id", "kg_labels", "method", "retrieval_score", "retrieval_score_normalized"]
    df = df.drop(columns=to_drop_cols, errors="ignore").drop_duplicates()
    return df

def combine_result(input_df, output_df, filter_condition):
    import operator
    def get_operator(s):
        if s == ">":
            return operator.gt
        elif s == "=":
            return operator.eq
        elif s == "<":
            return operator.le
    # load expression
    expressions_parsed = []
    temp = ""
    left, right, comparator = None, None, []
    for each in filter_condition:
        if each == " ":
            continue
        if each in "|&":
            right = float(temp)
            if left is None or comparator is None or right is None:
                raise tl.exceptions.TLException("Filter equation {} seems invalid!".format(filter_condition))
            expressions_parsed.append((left, comparator, right))
            expressions_parsed.append(each)
        elif each in ">=<":
            comparator.append(get_operator(each))
            left = temp
            temp = ""
        else:
            temp += each

    right = float(temp)
    if left is None or comparator is None or right is None:
        raise tl.exceptions.TLException("Filter equation {} seems invalid!".format(filter_condition))
    expressions_parsed.append((left, comparator, right))

    # get expression result
    final_res = None
    for i, each_compare in enumerate(expressions_parsed):
        if i % 2 == 0:
            for each_comparator in each_compare[1]:
                each_res = each_comparator(input_df[each_compare[0]].astype(float).fillna(0), each_compare[2])
                if final_res is None:
                    final_res = each_res
                else:
                    final_res = each_res & final_res
            # final_res =  final_res & (input_df[each_compare[0]].astype(float), each_compare[2])
        else:
            if each_compare == "&":
                final_res = each_res & final_res
            else:
                final_res = each_res | final_res
    
    input_df_filtered = input_df[final_res]

    # mark down the data we still remained, those are not needed add
    existed_groups = set()
    for each in input_df_filtered.groupby(by=['column', 'row']):
        existed_groups.add(each[0])
    # add those data not exist
    for each in output_df.groupby(by=['column', 'row']):
        if each[0] not in existed_groups:
            input_df_filtered = input_df_filtered.append(each[1])
    # sort by column, row for human view
    input_df_filtered = input_df_filtered.astype({"column": int, "row": int})
    input_df_filtered = input_df_filtered.sort_values(by=['column', "row"])

    return input_df_filtered

def run(**kwargs):
    from tl.candidate_generation import phrase_query_candidates
    import pandas as pd
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        need_filter = False
        if kwargs.get("filter_condition"):
            need_filter = True

        if need_filter:
            query_input_df = remove_previous_match_res(df)
        else:
            query_input_df = df

        em = phrase_query_candidates.PhraseQueryMatches(es_url=kwargs['url'], es_index=kwargs['index'],
                                                        es_user=kwargs['user'],
                                                        es_pass=kwargs['password'])
        odf = em.get_phrase_matches(kwargs['column'], properties=kwargs['properties'], size=kwargs['size'], df=query_input_df)
        if need_filter:
            odf = combine_result(df, odf, kwargs["filter_condition"])

        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: get-phrase-matches\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
