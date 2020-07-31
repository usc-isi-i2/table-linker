import tl.exceptions


class Filter(object):
    @staticmethod
    def remove_previous_match_res(df):
        to_drop_cols = ["kg_id", "kg_labels", "method", "retrieval_score", "retrieval_score_normalized"]
        df = df.drop(columns=to_drop_cols, errors="ignore").drop_duplicates()
        return df

    @staticmethod
    def get_operator(s: str):
        import operator
        if s == ">":
            return operator.gt
        elif s == "=":
            return operator.eq
        elif s == "<":
            return operator.le

    @staticmethod
    def combine_result(input_df: "DataFrame", output_df: "DataFrame", filter_condition: str) -> "DataFrame":
        """
            combine the input_df and output_df base on given filtering requirements
            input_df: a pandas dataframe that need to be filtered
            output_df: a pandas dataframe that need to be add base on input_df
            returns: the combined dataframe
        """
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
                comparator.append(Filter.get_operator(each))
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
