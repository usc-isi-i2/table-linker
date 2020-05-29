from abc import ABC, abstractmethod
import rltk.similarity as sim


class StringSimilarityModule(ABC):
    def __init__(self, tl_args, **method_args):
        # set tl args
        self._ignore_case = tl_args['ignore_case']

        # set method args
        for k, v in method_args.items():
            setattr(self, '_{}'.format(k), v)
        self._arg_str = ','.join(['{}={}'.format(k, v) for k, v in method_args.items()])

    def get_name(self) -> str:
        # return the module name and corresponding config
        # for example: "ngram:n=3"
        return '{}({})'.format(self.__class__.__name__, self._arg_str)

    def similarity(self, str1: str, str2: str, threshold=0) -> float:
        # return the similarity score, if the similarity score is lower than threshold, return 0
        if self._ignore_case:
            str1 = str1.lower()
            str2 = str2.lower()
        similarity = self._similarity(str1, str2)
        # if the score less than some threshold, return 0
        if threshold > similarity:
            return 0
        return similarity

    @abstractmethod
    def _similarity(self, str1: str, str2: str) -> float:
        # detail implementation of the method
        raise NotImplementedError


class LevenshteinSimilarity(StringSimilarityModule):
    def _similarity(self, str1: str, str2: str):
        return sim.levenshtein_similarity(str1, str2)


class JarowinklerSimilarity(StringSimilarityModule):
    def __init__(self, tl_args, threshold=0.7, scaling_factor=0.1, prefix_len=4):
        threshold = float(threshold)
        scaling_factor = float(scaling_factor)
        prefix_len = int(prefix_len)
        super().__init__(tl_args,
            threshold=threshold, scaling_factor=scaling_factor, prefix_len=prefix_len)

    def _similarity(self, str1: str, str2: str):
        return sim.jaro_winkler_similarity(str1, str2,
            threshold=self._threshold, scaling_factor=self._scaling_factor, prefix_len=self._prefix_len)


class NeedlemanSimilarity(StringSimilarityModule):
    def __init__(self, tl_args, match=2, mismatch=-1, gap=-0.5):
        match = float(match)
        mismatch = float(mismatch)
        gap = float(gap)
        super().__init__(tl_args,
            match=match, mismatch=mismatch, gap=gap)

    def _similarity(self, str1: str, str2: str):
        return sim.needleman_wunsch_similarity(str1, str2,
            match=self._match, mismatch=self._mismatch, gap=self._gap)


class SoundexSimilarity(StringSimilarityModule):
    def _similarity(self, str1: str, str2: str):
        return sim.soundex_similarity(str1, str2)


class MetaphoneSimilarity(StringSimilarityModule):
    def _similarity(self, str1: str, str2: str):
        return sim.metaphone_similarity(str1, str2)


class NysiisSimilarity(StringSimilarityModule):
    def _similarity(self, str1: str, str2: str):
        return sim.nysiis_similarity(str1, str2)
