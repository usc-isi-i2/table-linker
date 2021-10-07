import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException


class DedupCandidates(object):
    def process(self, column: str = 'kg_id', file_path: str = None, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        
        Args:
            column: column in the file which has candidate ids  to be deduplicated
            file_path: input file path
            df: input dataframe

        Returns: a dataframe with deduplicated candidates

        """
        if file_path is None and df is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("file_path", "df"))

        if file_path:
            df = pd.read_csv(file_path, dtype=object)

        df.fillna(value="", inplace=True)

        # remove all blank cells
        df = df[df[column] != ""].copy()

        if len(df) > 0:

            df['is_exact_match'] = 0
            df.loc[df['method'] == 'exact-match', 'is_exact_match'] = 1

            grouped = df.groupby(by=['column', 'row', 'kg_id'])

            out = []

            for key, gdf in grouped:
                if len(gdf) == 1:
                    gdf['num_occurences'] = 1
                    out.append(gdf)
                else:
                    gdf['num_occurences'] = len(gdf)
                    fgdf = gdf[gdf['method'] == 'exact-match']
                    if len(fgdf) == 1:
                        out.append(fgdf)
                    else:
                        out.append(gdf.head(1))
            return pd.concat(out).astype({'column': int, 'row': int})
        else:
            return pd.DataFrame()
