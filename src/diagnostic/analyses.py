import pandas as pd
import geopandas as gpd
import numpy as np

from enum import Enum, member
from abc import ABC, abstractmethod
from pathlib import PurePath
from tempfile import mkdtemp
from typing import Any
from functools import partial, reduce

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pylatex import Figure
from pylatex.base_classes import LatexObject

from .latex_string import LatexString, LatexStringTable, FigureContainer

plt.ioff()

class Options(Enum):
    def __call__(self, *args):
        self.value(*args)
    pass

class CountComparisonOptions(Options):
        DIFF = member(lambda comp: comp['count_sim'] - comp['count_obs'])
        PCT_DIFF = member(lambda comp: (comp['count_sim'] - comp['count_obs'])/comp['count_obs'])
        SQV = member(lambda comp: 1/(1+np.sqrt((comp['count_sim'] - comp['count_obs'])**2/(comp['count_obs']*10**(comp['count_obs']//10)))))
        GEH = member(lambda comp: np.sqrt(2*(comp['count_sim'] - comp['count_obs'])**2/(comp['count_sim'] + comp['count_obs'])))

class CountSummaryStatsOptions(Options):
        MIN = member(lambda df: df.min())
        MAX = member(lambda df: df.max())
        MEDIAN = member(lambda df: df.median())
        MEAN = member(lambda df: df.mean())
        QUARTILE_1 = member(lambda df: df.quantile(0.25))
        QUARTILE_3 = member(lambda df: df.quantile(0.75))

class EMDOptions(Options):
    EMD15 = 15
    EMD30 = 30
    EMD60 = 60

    def __new__(cls, value):
        """Changes Enum creation process so that each member.value points to the _emd_grouping method with their hard-coded interval_duration"""
        obj = object.__new__(cls)
        obj._value_ = partial(cls._emd_grouping, interval_duration=value)
        return obj

    @classmethod
    def _emd_grouping(cls, df: pd.DataFrame, interval_duration: float) -> pd.DataFrame:
        """Sums counts by link and supplied interval duration"""
        df['interval'] = df.apply(cls._interval, interval_duration=interval_duration, axis=1)
        df = df.groupby(['link_id', 'interval'])[['count_sim', 'count_obs']].sum().reset_index()
        # print(df)
        return df

    @classmethod
    def _interval(cls, row, interval_duration: float) -> str:
        quotient = row['time']//interval_duration
        return f"[{quotient * interval_duration},{(quotient + 1) * interval_duration})"

class Filter(ABC):
    """Abstract base class for filters"""
    def __init__(self, rules: dict) -> None:
        self.rules = rules

    @abstractmethod
    def apply_filter(self, result: pd.DataFrame) -> pd.DataFrame:
        pass

    def __repr__(self) -> str:
        return "%s(%r)" % (self.__class__, self.__dict__)

class FilterNothing(Filter):
    def __init__(self) -> None:
        super().__init__(None)

    def apply_filter(self, result: pd.DataFrame) -> pd.DataFrame:
        return result

    def __str__(self) -> str:
        return "No filter was applied"

class FilterByValue(Filter):
    """
        Given a dictionary of dataframe columns and lists of values in those columns, returns a dataframe in which rows have the given values for the given columns
    """
    def __init__(self, rules: dict[str, list]) -> None:
        super().__init__(rules)

    def apply_filter(self, result: pd.DataFrame) -> pd.DataFrame:

        if len(self.rules) > 1:
            # Based it on Ben Saunders' answer at https://stackoverflow.com/questions/34157811/filter-a-pandas-dataframe-using-values-from-a-dict
            return result.loc[reduce(lambda left, right: result[left[0]].isin(left[1]) & result[right[0]].isin(right[1]), self.rules.items()), :]
        else:
            return result[result[list(self.rules)[0]].isin(self.rules.values())]


    def __str__(self) -> str:
        strings = ["Filter by value:"] + [f"\n\t{col}: {values}" for col, values in self.rules.items()]
        return ''.join(strings)

class FilterByLargest(Filter):
    """
        Given a dictionary {int: list[str]} with only one entry (n: cols) and a dataframe, returns the n rows with the largest values in columns 'cols'
    """
    def __init__(self, rules: dict) -> None:
        n, cols = list(self.rules.items())
        self.n = n
        self.cols = cols
        super().__init__(rules)

    def apply_filter(self, result: pd.DataFrame) -> pd.DataFrame:
        return result.nlargest(self.n, self.cols)

    def __str__(self) -> str:
        return f"Filter by {self.n} largest values in columns {self.cols}"

class Analysis(ABC):

    filter: Filter
    options: Options
    section_title: str
    result: Any

    def __init__(self, filter: Filter, options: Options=Options) -> None:
        self.filter = filter if filter is not None else FilterNothing()
        self.options = options
        
        logging.info("%s", type(self))
        logging.info("%s", self.options)

        return

    @abstractmethod
    def generate_analysis(self, comparison) -> None:
        pass
    
    @abstractmethod
    def to_latex(self, **kwargs) -> LatexObject:
        pass

class CountComparison(Analysis):

    section_title: str = "Link counts comparison analyses"

    def __init__(self, filter: Filter = None, options: Options = CountComparisonOptions) -> None:
        super().__init__(filter, options)

    def generate_analysis(self, comparison: pd.DataFrame) -> None:
        result = comparison.copy()
        for member in self.options:
            result[member.name] = member.value(result)
        self.result = result

    def to_latex(self, **kwargs) -> LatexObject:
        styler = self.result.select_dtypes(include=np.number).sort_index().style
        styler.format(escape='latex', precision=2)
        return LatexStringTable(
            styler.to_latex(
                caption="Link by link comparison of traffic counts",
                position="H",
                label="table:link-count",
                environment="longtable"
            ),
            ["_"]
        )


class CountSummaryStats(Analysis):

    section_title: str = "Link counts summary statistics"

    def __init__(self, filter: Filter = None, options: Options = CountSummaryStatsOptions) -> None:
        super().__init__(filter, options)

    def generate_analysis(self, comparison: pd.DataFrame) -> None:
        result = pd.DataFrame(index=[stat.name for stat in self.options], columns=comparison.select_dtypes(include=np.number).columns)
        for column in result.columns:
            for stat in self.options:
                result.loc[stat.name, column] = stat.value(comparison[column])
        self.result: pd.DataFrame = result.astype(float).round(2)

    def to_latex(self, **kwargs) -> LatexObject:
        styler = self.result.style
        styler.format(escape='latex', precision=2)
        return LatexStringTable(
            styler.to_latex(
                caption="Summary statistics for traffic counts",
                position="H",
                label="table:summary-stats",
                position_float="centering"
            ),
            ["_"]
        )

class CountVisualization(Analysis):

    section_title: str = "Count visualization"

    def __init__(self, filter: Filter = None, options: Options = CountComparisonOptions) -> None:
        super().__init__(filter, options)

    def generate_analysis(self, comparison: gpd.GeoDataFrame, **kwargs) -> None:
                
        result: dict[str, Figure] = {}
        for col in comparison.columns.difference(['geometry']):
            print(col)
            fig, ax = plt.subplots()
            comparison.plot(column=col, ax=ax, legend=True)
            ax.set_title(f"{col}")
            ax.axis('off')
            ax.set_frame_on(True)
            result[col] = fig

        self.result = result

    def to_latex(self, **kwargs) -> LatexObject:
        paths = self.to_file(**kwargs)
        print(f"Paths: {paths}")
        return FigureContainer(paths)

    def to_file(self, directory: PurePath = None, extension: str = 'pdf', **kwargs) -> list[PurePath]:
        if directory is None:
            directory = PurePath(mkdtemp())
        paths: list[PurePath] = []
        for title, plot in self.result.items():
            filepath = PurePath(directory, f"{title}.{extension}")
            plot.savefig(filepath)
            paths.append(filepath)
        return paths

class EarthMoverDistance(Analysis):
    """
        Calculate the EMD between the simulated and observed counts.
    """
    section_title = "Earth Mover's Distance"

    def __init__(self, filter: Filter = None, options: Options = EMDOptions) -> None:
        super().__init__(filter, options)

    def generate_analysis(self, comparison: pd.DataFrame) -> None:
        result = comparison.copy().sort_values(by="link_id", ascending=True)

        dataframes: list[pd.DataFrame] = []

        for member in self.options:
            dataframes.append(member.value(result).groupby('link_id').apply(self._vector_wasser).rename(member.name))

        result = result["link_id"].drop_duplicates()
        result = reduce(lambda left, right: pd.merge(left, right, on=['link_id'], how='outer'), [result] + dataframes)
        self.result = result.set_index('link_id')

    def _vector_wasser(self, group) -> float:
        return (group['count_sim']/(group['count_sim'].sum()) - group['count_obs']/(group['count_obs'].sum())).abs().sum()

    def to_latex(self, **kwargs) -> LatexObject:
        styler = self.result.style
        styler.format(escape='latex', precision=2)
        return LatexStringTable(
            styler.to_latex(
                caption="Traffic counts Earth Mover's Distance",
                position="H",
                label="table:emd",
                environment="longtable"
            ),
            ["_"]
        )