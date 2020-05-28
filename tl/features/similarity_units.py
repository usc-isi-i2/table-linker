from abc import ABC, abstractmethod
import rltk.similarity as sim


class StringSimilarityModule(ABC):
    def __init__(self, **kwargs):
        self._ignore_case = 'ignore_case' in kwargs['tl_args']

    @abstractmethod
    def get_name(self) -> str:
        # return the module name and corresponding config
        # for example: "ngram:n=3"
        raise NotImplementedError

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
    def __init__(self, tl_args):
        super().__init__(tl_args=tl_args)

    def _similarity(self, str1: str, str2: str):
        return sim.levenshtein_similarity(str1, str2)

    def get_name(self):
        return 'levenshtein_similarity'
