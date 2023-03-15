import pandas as pd
import geopandas as gpd
import numpy as np

from enum import Enum, member
from abc import ABC, abstractmethod
from pathlib import PurePath
from tempfile import mkdtemp
from typing import Any

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

class CreateComparisonDF(Enum):
    LINK_COMP = member(lambda sim, obs: sim.merge(obs, on='link_id', how='right', suffixes=['_sim', '_obs']).set_index('link_id').sort_index())

class Analysis(ABC):

    options: Options
    section_title: str
    result: Any
    create_comp_df: CreateComparisonDF

    def __init__(self, options: Options=Options) -> None:
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
    create_comp_df = CreateComparisonDF.LINK_COMP

    def __init__(self, options: Options = CountComparisonOptions) -> None:
        super().__init__(options)

    def generate_analysis(self, comparison: pd.DataFrame) -> None:
        result = comparison.copy()
        for name in self.selection:
            result[name] = self.options[name].value(result)
        self.result = result

    def to_latex(self, **kwargs) -> LatexObject:
        styler = self.result[self.result.columns.difference(['geometry'])].style
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
    create_comp_df = CreateComparisonDF.LINK_COMP

    def __init__(self, options: Options = CountSummaryStatsOptions) -> None:
        super().__init__(options)

    def generate_analysis(self, comparison: pd.DataFrame) -> None:
        result = pd.DataFrame(index=self.selection, columns=comparison.columns.drop(['geometry'], errors='ignore'))
        for column in result.columns:
            for stat in result.index:
                result.loc[stat, column] = self.options[stat].value(comparison[column])
        self.result = result.astype(float).round(2)

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
    create_comp_df = CreateComparisonDF.LINK_COMP


    def __init__(self, options: Options = CountComparisonOptions) -> None:
        super().__init__(options)

    def generate_analysis(self, comparison: gpd.GeoDataFrame, **kwargs) -> None:
                
        self.result: dict[str, Figure] = {}
        for name in self.selection:
            fig, ax = plt.subplots()
            comparison.plot(column=name, ax=ax, legend=True)
            ax.set_title(f"{name}")
            ax.axis('off')
            ax.set_frame_on(True)
            self.result[name] = fig

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