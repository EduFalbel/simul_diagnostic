import pytest

import pandas as pd
from pandas.testing import assert_frame_equal
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

##### Test CountComparisonOptions #####

@pytest.fixture
def count_comparison_options() -> analyses.CountComparisonOptions:
    return analyses.CountComparisonOptions

@pytest.fixture
def complete_link_comparison_df(link_comparison_df, count_comparison_options):
    link_comparison_df[count_comparison_options.DIFF.name] = pd.Series([1 - 0, 2 - 1, 3 - 2])
    link_comparison_df[count_comparison_options.RATIO.name] = pd.Series([np.inf, 2/1, 3/2])
    link_comparison_df[count_comparison_options.GEH.name] = pd.Series([np.sqrt(2*(1 - 0)**2/(1 + 0)), np.sqrt(2*(2 - 1)**2/(2 + 1)), np.sqrt(2*(3 - 2)**2/(3 + 2))])
    link_comparison_df[count_comparison_options.SQV.name] = pd.Series([0, 1/(1 + np.sqrt((2 - 1)**2/1000)), 1/(1 + np.sqrt((3 - 2)**2/2000))])

    return link_comparison_df

class TestCountComparisonOptions:
    def test_count_comparison_options_diff(self, count_comparison_options: analyses.CountComparisonOptions, link_comparison_df: pd.DataFrame, complete_link_comparison_df):
        assert count_comparison_options.DIFF.value(link_comparison_df).equals(complete_link_comparison_df.DIFF)

    def test_count_comparison_options_ratio(self, count_comparison_options: analyses.CountComparisonOptions, link_comparison_df: pd.DataFrame, complete_link_comparison_df):
        assert count_comparison_options.RATIO.value(link_comparison_df).equals(complete_link_comparison_df.RATIO)

    def test_count_comparison_options_geh(self, count_comparison_options: analyses.CountComparisonOptions, link_comparison_df: pd.DataFrame, complete_link_comparison_df):
        assert count_comparison_options.GEH.value(link_comparison_df).equals(complete_link_comparison_df.GEH)

    def test_count_comparison_options_sqv(self, count_comparison_options: analyses.CountComparisonOptions, link_comparison_df: pd.DataFrame, complete_link_comparison_df):
        assert count_comparison_options.SQV.value(link_comparison_df).equals(complete_link_comparison_df.SQV)

##### Test CountComparison analysis #####

@pytest.fixture
def count_comparison_analysis(link_comparison_df) -> analyses.CountComparison:
    return analyses.CountComparison()

def test_count_comparison_analysis(count_comparison_analysis, link_comparison_df, complete_link_comparison_df):
    count_comparison_analysis.generate_analysis(link_comparison_df)
    assert_frame_equal(count_comparison_analysis.result, complete_link_comparison_df)

##### Test CountSummaryStatsOptions #####

@pytest.fixture
def count_summary_stats_options():
    return analyses.CountSummaryStatsOptions

@pytest.fixture
def count_summary_stats_result(count_summary_stats_options):
    result_dict = {
        count_summary_stats_options.MIN.name: [0, 1],
        count_summary_stats_options.QUARTILE_1.name: [0.5, 1.5],
        count_summary_stats_options.MEDIAN.name: [1, 2],
        count_summary_stats_options.MEAN.name: [1, 2],
        count_summary_stats_options.QUARTILE_3.name: [1.5, 2.5],
        count_summary_stats_options.MAX.name: [2, 3]
    }
    return pd.DataFrame.from_dict(result_dict, columns=['count_obs', 'count_sim'], orient='index', dtype='float64')

@pytest.mark.parametrize(
    "column", ['count_sim', 'count_obs']
)
class TestCountSummaryStatsOptions:

    def test_css_option_min(self, count_summary_stats_options, link_comparison_df, count_summary_stats_result, column):
        assert count_summary_stats_options.MIN.value(link_comparison_df[column]) == count_summary_stats_result.loc['MIN', column]

    def test_css_option_quartile_1(self, count_summary_stats_options, link_comparison_df, count_summary_stats_result, column):
        assert count_summary_stats_options.QUARTILE_1.value(link_comparison_df[column]) == count_summary_stats_result.loc['QUARTILE_1', column]

    def test_css_option_median(self, count_summary_stats_options, link_comparison_df, count_summary_stats_result, column):
        assert count_summary_stats_options.MEDIAN.value(link_comparison_df[column]) == count_summary_stats_result.loc['MEDIAN', column]

    def test_css_option_mean(self, count_summary_stats_options, link_comparison_df, count_summary_stats_result, column):
        assert count_summary_stats_options.MEAN.value(link_comparison_df[column]) == count_summary_stats_result.loc['MEAN', column]

    def test_css_option_quartile_3(self, count_summary_stats_options, link_comparison_df, count_summary_stats_result, column):
        assert count_summary_stats_options.QUARTILE_3.value(link_comparison_df[column]) == count_summary_stats_result.loc['QUARTILE_3', column]

    def test_css_option_max(self, count_summary_stats_options, link_comparison_df, count_summary_stats_result, column):
        assert count_summary_stats_options.MAX.value(link_comparison_df[column]) == count_summary_stats_result.loc['MAX', column ]

##### Test CountSummaryStats #####

@pytest.fixture
def count_summary_stats_analysis():
    return analyses.CountSummaryStats()

def test_count_summary_stats(count_summary_stats_analysis, link_comparison_df, count_summary_stats_result):
    count_summary_stats_analysis.generate_analysis(link_comparison_df)
    assert_frame_equal(count_summary_stats_analysis.result, count_summary_stats_result)