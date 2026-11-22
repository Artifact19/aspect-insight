"""TF-IDF nearest-neighbour search used to pick in-context examples for prompting."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Sequence

import numpy as np
from scipy.sparse import csr_matrix

TOKEN = re.compile(r"[a-z0-9']+")


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


class TfidfIndex:
    def __init__(self, texts: Sequence[str]):
        docs = [Counter(tokenize(t)) for t in texts]
        df = Counter(w for d in docs for w in d)
        self.vocab = {w: i for i, w in enumerate(sorted(df))}
        self.idf = np.array([math.log((1 + len(docs)) / (1 + df[w])) + 1 for w in sorted(df)])
        self.matrix = self._vectorize(docs)

    def _vectorize(self, docs: Sequence[Counter]) -> csr_matrix:
        rows, cols, vals = [], [], []
        for r, d in enumerate(docs):
            for w, c in d.items():
                if w in self.vocab:
                    rows.append(r)
                    cols.append(self.vocab[w])
                    vals.append((1 + math.log(c)) * self.idf[self.vocab[w]])
        m = csr_matrix((vals, (rows, cols)), shape=(len(docs), len(self.vocab)))
        norms = np.sqrt(np.asarray(m.multiply(m).sum(1)).ravel())
        norms[norms == 0] = 1.0
        return csr_matrix(m.multiply(1 / norms[:, None]))

    def search(self, queries: Sequence[str], k: int) -> np.ndarray:
        """Indices of the k most similar indexed texts for each query, most similar first."""
        sims = (self._vectorize([Counter(tokenize(q)) for q in queries]) @ self.matrix.T).toarray()
        top = np.argpartition(-sims, min(k, sims.shape[1] - 1), axis=1)[:, :k]
        order = np.take_along_axis(sims, top, 1).argsort(1)[:, ::-1]
        return np.take_along_axis(top, order, 1)
