"""Fixed, train-only representations for the bounded revision-information test.

This module does not load data, execute submitted programs, or fit on import.
The caller supplies a common eligible episode cohort and its prespecified
numeric feature families. Outcomes must be passed separately to ``fit``.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import token
import tokenize
from typing import Sequence
import warnings

import numpy as np
import pandas as pd
import scipy
from scipy import sparse
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ARMS = ("M0", "M1", "M2", "M1_endpoint_redundant")
TOKENIZER_VERSION = "python-token-content-with-whole-document-fallback-v1"
_FALLBACK = re.compile(
    r"(?P<STRING>(?:[rRuUbBfF]{0,2})(?:\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|"
    r'"(?:\\.|[^"\\\r\n])*"|\'(?:\\.|[^\'\\\r\n])*\'))'
    r"|(?P<COMMENT>\#[^\r\n]*)"
    r"|(?P<NUMBER>\d+(?:\.\d*)?(?:[eE][+-]?\d+)?[jJ]?)"
    r"|(?P<NAME>[^\W\d]\w*)"
    r"|(?P<NEWLINE>\r\n|\r|\n)"
    r"|(?P<SPACE>[^\S\r\n]+)"
    r"|(?P<OP>\*\*|//|<<|>>|:=|==|!=|<=|>=|->|\+=|-=|\*=|/=|%=|&=|\|=|\^=|[^\s])",
    re.UNICODE,
)


def python_code_tokens(code: str) -> list[str]:
    """Preserve identifier/literal values; never execute or repair source.

    A tokenizer exception replaces the entire token stream with a lexical
    fallback plus a failure marker. This avoids either dropping the unparsed
    suffix or duplicating its successfully tokenized prefix. The fallback
    removes comments and spaces but cannot infer reliable INDENT/DEDENT.
    """
    if not isinstance(code, str):
        raise TypeError("Code must be a string, without imputation.")
    result: list[str] = []
    try:
        for part in tokenize.generate_tokens(io.StringIO(code).readline):
            if part.type in (tokenize.COMMENT, tokenize.NL, token.ENDMARKER,
                             tokenize.ENCODING):
                continue
            if part.type in (token.INDENT, token.DEDENT, token.NEWLINE):
                result.append("<" + token.tok_name[part.type] + ">")
            elif part.type == token.ERRORTOKEN and part.string.isspace():
                continue
            else:
                result.append(token.tok_name[part.type] + ":" + part.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        result = ["<TOKENIZE_ERROR>"]
        for match in _FALLBACK.finditer(code):
            kind = match.lastgroup
            if kind in ("COMMENT", "SPACE"):
                continue
            result.append("<NEWLINE>" if kind == "NEWLINE" else
                          str(kind) + ":" + match.group())
    return result or ["<EMPTY_TOKEN_STREAM>"]


@dataclass(frozen=True)
class EpisodeInputs:
    """Every Series must have the same unique ordered index as ``numeric``.

    ``intermediate_codes`` contains only snapshots strictly between the first
    and final source submissions, in chronological order, and at least one per
    row. The caller is responsible for temporal eligibility and for ensuring
    all numeric columns are available by the source episode's final snapshot.
    """
    numeric: pd.DataFrame
    source_item: pd.Series
    target_item: pd.Series
    first_code: pd.Series
    final_code: pd.Series
    intermediate_codes: pd.Series
    user_id: pd.Series

    def validate(self, required_columns: Sequence[str]) -> None:
        if not isinstance(self.numeric, pd.DataFrame):
            raise TypeError("numeric must be a pandas DataFrame.")
        if len(self.numeric) == 0 or not self.numeric.index.is_unique:
            raise ValueError("A nonempty batch with a unique episode index is required.")
        if not self.numeric.columns.is_unique:
            raise ValueError("Numeric column names must be unique.")
        missing = set(required_columns) - set(self.numeric.columns)
        if missing:
            raise ValueError(f"Missing declared numeric columns: {sorted(missing)}")
        values = self.numeric.loc[:, list(required_columns)].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Declared numeric features must be finite; encode missingness explicitly.")
        for name in ("source_item", "target_item", "first_code", "final_code",
                     "intermediate_codes", "user_id"):
            series = getattr(self, name)
            if not isinstance(series, pd.Series) or not series.index.equals(self.numeric.index):
                raise ValueError(f"{name} must be a Series with the exact numeric index/order.")
        for name in ("source_item", "target_item", "user_id"):
            if any(not isinstance(v, str) or not v for v in getattr(self, name)):
                raise ValueError(f"{name} requires nonempty string identifiers.")
        if self.source_item.eq(self.target_item).any():
            raise ValueError("The target must be a different item from the source.")
        for name in ("first_code", "final_code"):
            if any(not isinstance(v, str) or not v.strip() for v in getattr(self, name)):
                raise ValueError(f"{name} requires a nonempty source snapshot for every row.")
        for codes in self.intermediate_codes:
            if not isinstance(codes, (list, tuple)) or not codes:
                raise ValueError("Every episode requires at least one strictly intermediate snapshot.")
            if any(not isinstance(v, str) or not v.strip() for v in codes):
                raise ValueError("Intermediate snapshots must be nonempty strings.")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _array_digest(array: np.ndarray) -> str:
    normalized = np.ascontiguousarray(array, dtype="<f8")
    return hashlib.sha256(normalized.tobytes()).hexdigest()


def _labels(values: pd.Series, batch: EpisodeInputs, name: str) -> np.ndarray:
    if not isinstance(values, pd.Series) or not values.index.equals(batch.numeric.index):
        raise ValueError(f"{name} labels must share the exact episode index/order.")
    result = values.to_numpy(dtype=float)
    if not np.isfinite(result).all() or set(np.unique(result)) != {0.0, 1.0}:
        raise ValueError(f"{name} requires observed binary labels and both classes.")
    return result.astype(np.int8)


def _fit_no_convergence_warning(model: LogisticRegression, x, y) -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(x, y)
    failures = [str(w.message) for w in captured if issubclass(w.category, ConvergenceWarning)]
    if failures:
        raise RuntimeError("The fixed solver did not converge; do not silently retune: " + "; ".join(failures))
    for warning in captured:
        if not issubclass(warning.category, ConvergenceWarning):
            warnings.warn(str(warning.message), warning.category, stacklevel=2)


class RevisionModelPipeline:
    """Three primary arms and one fixed endpoint-redundancy control.

    Feature order is M0 numeric/items; then endpoint numeric/first-code/final-code;
    then intermediate numeric/mean intermediate code. Thus M0 is an exact column
    prefix of M1, and M1 an exact column prefix of M2 before separate model fits.
    """
    def __init__(self, m0_numeric_columns: Sequence[str],
                 endpoint_numeric_columns: Sequence[str],
                 intermediate_numeric_columns: Sequence[str]):
        self.columns = {
            "M0": tuple(m0_numeric_columns),
            "endpoint": tuple(endpoint_numeric_columns),
            "intermediate": tuple(intermediate_numeric_columns),
        }
        all_columns = self.required_columns
        if any(not isinstance(c, str) for c in all_columns):
            raise TypeError("Numeric feature names must be strings.")
        if len(set(all_columns)) != len(all_columns):
            raise ValueError("Numeric feature families must be disjoint and contain no duplicates.")
        if any(not cols for cols in self.columns.values()):
            raise ValueError("Each prespecified numeric feature family must be nonempty.")
        self.scalers = {name: StandardScaler() for name in self.columns}
        self.items = OneHotEncoder(handle_unknown="ignore", sparse_output=True, dtype=np.float64)
        self.vectorizer = TfidfVectorizer(
            analyzer=python_code_tokens, lowercase=False, token_pattern=None,
            max_features=2048, sublinear_tf=True, norm="l2", use_idf=True,
            smooth_idf=True, dtype=np.float64,
        )
        self.models = {arm: LogisticRegression(C=1.0, solver="liblinear", max_iter=2000,
                                               random_state=1729) for arm in ARMS}
        self.calibrators = {arm: LogisticRegression(C=1e6, solver="lbfgs", max_iter=2000,
                                                    random_state=1729) for arm in ARMS}
        self._fitted = False
        self._started = False

    @property
    def required_columns(self) -> tuple[str, ...]:
        return tuple(c for columns in self.columns.values() for c in columns)

    @property
    def config(self) -> dict:
        return {
            "numeric_columns": {k: list(v) for k, v in self.columns.items()},
            "numeric_scaling": "Train-only StandardScaler separately per disjoint feature family; no imputation.",
            "items": {"columns": ["source_item", "target_item"], "encoding": "train-only OneHotEncoder",
                      "handle_unknown": "ignore"},
            "tokenizer": TOKENIZER_VERSION,
            "token_content": "Identifier/literal values preserved; comments/spaces omitted; standard token layout markers retained; lexical fallback on tokenizer exception.",
            "tfidf": {"max_features": 2048, "ngram": "unigrams", "sublinear_tf": True,
                      "norm": "l2", "use_idf": True, "smooth_idf": True,
                      "fit_corpus": "Every source submission snapshot in training episodes, including first, final, and strictly intermediate snapshots; occurrence-weighted, not deduplicated."},
            "intermediate_pooling": "Arithmetic mean of individually L2-normalized snapshot TFIDF vectors; no second normalization.",
            "base_logistic": {"C": 1.0, "solver": "liblinear", "max_iter": 2000,
                              "random_state": 1729, "class_weight": None, "sample_weight": None},
            "platt_logistic": {"C": 1e6, "solver": "lbfgs", "max_iter": 2000,
                               "random_state": 1729, "input": "one validation decision score",
                               "sample_weight": None},
            "primary_predictions": "Validation-calibrated probabilities; sole primary contrast M2 minus M1.",
            "secondary_control": "M1_endpoint_redundant appends (first TFIDF + final TFIDF) / 2 to M1; it adds no new source information. This is a partial capacity/penalty-geometry control because it does not match the intermediate numeric block.",
            "scope": "One common cohort, separate fits, no tuning or architecture search; no program execution.",
        }

    @staticmethod
    def _item_array(batch: EpisodeInputs) -> np.ndarray:
        return np.column_stack((batch.source_item.to_numpy(), batch.target_item.to_numpy()))

    def _matrices(self, batch: EpisodeInputs) -> dict[str, sparse.csr_matrix]:
        numeric = {name: sparse.csr_matrix(self.scalers[name].transform(
            batch.numeric.loc[:, list(columns)])) for name, columns in self.columns.items()}
        first = self.vectorizer.transform(batch.first_code)
        final = self.vectorizer.transform(batch.final_code)
        flat = [code for codes in batch.intermediate_codes for code in codes]
        counts = np.fromiter((len(codes) for codes in batch.intermediate_codes), dtype=np.int64)
        rows = np.repeat(np.arange(len(batch.numeric)), counts)
        weights = np.repeat(1.0 / counts, counts)
        average = sparse.csr_matrix((weights, (rows, np.arange(len(flat)))),
                                    shape=(len(batch.numeric), len(flat)))
        intermediate = average @ self.vectorizer.transform(flat)
        m0 = sparse.hstack((numeric["M0"], self.items.transform(self._item_array(batch))), format="csr")
        m1 = sparse.hstack((m0, numeric["endpoint"], first, final), format="csr")
        m2 = sparse.hstack((m1, numeric["intermediate"], intermediate), format="csr")
        redundant = sparse.hstack((m1, (first + final) * 0.5), format="csr")
        return {"M0": m0, "M1": m1, "M2": m2, "M1_endpoint_redundant": redundant}

    def fit(self, train: EpisodeInputs, y_train: pd.Series,
            validation: EpisodeInputs, y_validation: pd.Series) -> "RevisionModelPipeline":
        if self._started:
            raise RuntimeError("A pipeline instance may be fitted only once; construct a new prespecified instance if needed.")
        train.validate(self.required_columns)
        validation.validate(self.required_columns)
        self._train_users = frozenset(train.user_id)
        self._validation_users = frozenset(validation.user_id)
        if self._train_users & self._validation_users:
            raise ValueError("Training and calibration students must be disjoint.")
        train_y = _labels(y_train, train, "Training")
        validation_y = _labels(y_validation, validation, "Validation")
        self._started = True
        for name, columns in self.columns.items():
            self.scalers[name].fit(train.numeric.loc[:, list(columns)])
        self.items.fit(self._item_array(train))
        train_corpus = [code for first, final, middle in zip(
            train.first_code, train.final_code, train.intermediate_codes)
            for code in (first, *middle, final)]
        self.vectorizer.fit(train_corpus)
        train_x = self._matrices(train)
        validation_x = self._matrices(validation)
        for arm in ARMS:
            _fit_no_convergence_warning(self.models[arm], train_x[arm], train_y)
            score = self.models[arm].decision_function(validation_x[arm]).reshape(-1, 1)
            _fit_no_convergence_warning(self.calibrators[arm], score, validation_y)
        self._feature_counts = {arm: int(train_x[arm].shape[1]) for arm in ARMS}
        self._fit_counts = {"train_episodes": len(train.numeric), "validation_episodes": len(validation.numeric),
                            "train_users": len(self._train_users), "validation_users": len(self._validation_users),
                            "training_source_snapshots": len(train_corpus)}
        self._fitted = True
        return self

    def _prediction_matrices(self, batch: EpisodeInputs, enforce_new_users: bool):
        if not self._fitted:
            raise RuntimeError("Call fit with the fixed training/calibration partitions first.")
        batch.validate(self.required_columns)
        if enforce_new_users and set(batch.user_id) & (self._train_users | self._validation_users):
            raise ValueError("Evaluation students overlap training or calibration students.")
        return self._matrices(batch)

    def decision_function(self, batch: EpisodeInputs, *, enforce_new_users: bool = True) -> pd.DataFrame:
        matrices = self._prediction_matrices(batch, enforce_new_users)
        return pd.DataFrame({arm: self.models[arm].decision_function(matrices[arm]) for arm in ARMS},
                            index=batch.numeric.index)

    def predict_proba(self, batch: EpisodeInputs, *, calibrated: bool = True,
                      enforce_new_users: bool = True) -> pd.DataFrame:
        matrices = self._prediction_matrices(batch, enforce_new_users)
        result = {}
        for arm in ARMS:
            if calibrated:
                scores = self.models[arm].decision_function(matrices[arm]).reshape(-1, 1)
                result[arm] = self.calibrators[arm].predict_proba(scores)[:, 1]
            else:
                result[arm] = self.models[arm].predict_proba(matrices[arm])[:, 1]
        return pd.DataFrame(result, index=batch.numeric.index)

    def manifest(self) -> dict:
        """Return aggregate provenance without code tokens or student identifiers."""
        result = {"config": self.config, "config_sha256": _digest(self.config),
                  "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "fitted": self._fitted,
                  "environment": {"python": platform.python_version(), "numpy": np.__version__,
                                  "pandas": pd.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__}}
        if not self._fitted:
            return result
        result.update({"fit_counts": self._fit_counts, "arm_feature_counts": self._feature_counts,
                       "vocabulary_size": len(self.vectorizer.vocabulary_),
                       "vocabulary_sha256": _digest({k: int(v) for k, v in self.vectorizer.vocabulary_.items()}),
                       "idf_sha256": _array_digest(self.vectorizer.idf_),
                       "item_category_counts": [len(c) for c in self.items.categories_],
                       "numeric_scaler_hashes": {
                           name: {"mean": _array_digest(scaler.mean_), "scale": _array_digest(scaler.scale_)}
                           for name, scaler in self.scalers.items()},
                       "model_hashes": {
                           arm: {"coef": _array_digest(self.models[arm].coef_),
                                 "intercept": _array_digest(self.models[arm].intercept_),
                                 "iterations": self.models[arm].n_iter_.tolist(),
                                 "platt_coef": _array_digest(self.calibrators[arm].coef_),
                                 "platt_intercept": _array_digest(self.calibrators[arm].intercept_),
                                 "platt_iterations": self.calibrators[arm].n_iter_.tolist()}
                           for arm in ARMS}})
        return result
