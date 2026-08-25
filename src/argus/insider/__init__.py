"""Insider and incentives engine - the flagship module.

Decodes SEC Form 3/4/5 ownership filings into scored, ranked events rather
than a chronological tape, on the measured basis that roughly two thirds of
Form 4 rows are not decisions at all.
"""
from .codes import CODES, describe, is_discretionary
from .cluster import Cluster, find as find_clusters
from .conviction import Conviction, classify_filer, score
from .form4 import Form4, Owner, ParseError, Transaction, parse

__all__ = ["CODES", "Cluster", "Conviction", "Form4", "Owner", "ParseError",
           "Transaction", "classify_filer", "describe", "find_clusters",
           "is_discretionary", "parse", "score"]
