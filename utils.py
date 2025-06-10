"""Utility helpers for the Streamlit app and CLI tools."""

# This module previously contained helpers for working with Google URLs and
# persisting history to ``.tak_history.json``. Those functions were removed to
# simplify the application. The file remains so existing imports do not fail.

from typing import Iterable, List


def chunk_rows(rows: List[list], size: int = 500) -> Iterable[List[list]]:
    """Yield chunks of ``rows`` with at most ``size`` items.

    Parameters
    ----------
    rows:
        The full list of rows to chunk.
    size:
        Maximum size of each chunk.

    Yields
    ------
    list[list]
        Slices of ``rows`` containing up to ``size`` rows each.
    """

    for i in range(0, len(rows), size):
        yield rows[i : i + size]


