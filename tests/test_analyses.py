import pytest

import pandas as pd
import numpy as np

from diagnostic import analyses

@pytest.fixture
def link_comparison_df() -> pd.DataFrame:
    comp_dict = {
        'link_id' : [i for i in range(1, 4)],
        'count_obs' : [i for i in range(0, 3)],
        'count_sim' : [i for i in range(1, 4)]
    }

    return pd.DataFrame.from_dict(comp_dict)

@pytest.fixture
def count_comparison_selection_default() -> analyses.CountComparisonOptions:
    return analyses.CountComparisonOptions

def test_count_comparison_options_diff(count_comparison_selection_default: analyses.CountComparisonOptions, link_comparison_df: pd.DataFrame):
    assert count_comparison_selection_default.DIFF.value(link_comparison_df).equals(pd.Series([1 - 0, 2 - 1, 3 - 2]))

def test_count_comparison_options_pct_diff(count_comparison_selection_default: analyses.CountComparisonOptions, link_comparison_df: pd.DataFrame):
    assert count_comparison_selection_default.PCT_DIFF.value(link_comparison_df).equals(pd.Series([np.inf, (2 - 1)/1, (3 - 2)/2]))

def test_count_comparison_options_geh(count_comparison_selection_default: analyses.CountComparisonOptions, link_comparison_df: pd.DataFrame):
    assert count_comparison_selection_default.GEH.value(link_comparison_df).equals(pd.Series([np.sqrt(2*(1 - 0)**2/(1 + 0)), np.sqrt(2*(2 - 1)**2/(2 + 1)), np.sqrt(2*(3 - 2)**2/(3 + 2))]))

def test_count_comparison_options_sqv(count_comparison_selection_default: analyses.CountComparisonOptions, link_comparison_df: pd.DataFrame):
    assert count_comparison_selection_default.SQV.value(link_comparison_df).equals(pd.Series([0, 1/(1 + np.sqrt((2 - 1)**2/1)), 1/(1 + np.sqrt((3 - 2)**2/2))]))

@pytest.fixture
def count_comparison_analysis(link_comparison_df):
    return analyses.CountComparison(link_comparison_df)

def test_link_comparison_df(link_comparison_df):
    assert not link_comparison_df.isnull().values.any()

def test_count_comparison_analysis(link_comparison_df):
    pass