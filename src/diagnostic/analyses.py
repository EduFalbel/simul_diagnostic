import pandas as pd
import geopandas as gpd
import numpy as np

from enum import Enum, member
from collections import defaultdict
from abc import ABC, abstractmethod
from pathlib import PurePath
from tempfile import TemporaryDirectory, mkdtemp

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pylatex import Document, Section, Subsection, Command, Figure
from pylatex.base_classes import LatexObject

from .latex_string import LatexString, LatexStringTable, FigureContainer

plt.ioff()

class Abbreviations(Enum):
    pass

class CountComparisonAbbreviation(Abbreviations):
    DIFF = 'Difference'
    SQV = 'Scalable Quality Value'

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
        # MEAN_OBS_COUNT = member(lambda comp: comp['count_obs'].mean())
        # MEAN_SIM_COUNT = member(lambda comp: comp['count_sim'].mean())
        # MAE = member(lambda comp: comp['DIFF'].mean()) # Diff might not exist, need to figure out whether to call CCO, replicate diff function here or check if exists
        # RMSE = member(lambda comp: np.sqrt((comp['DIFF']**2).mean()))
        # MPE = member(lambda comp: comp['PCT_DIFF'].mean())
        MIN = member(lambda df: df.min())
        MAX = member(lambda df: df.max())
        MEDIAN = member(lambda df: df.median())
        MEAN = member(lambda df: df.mean())
        QUARTILE_1 = member(lambda df: df.quantile(0.25))
        QUARTILE_3 = member(lambda df: df.quantile(0.75))


class Analysis(ABC):

    options: Options
    section_title: str


    def __init__(self, comparison: pd.DataFrame, selection: list[str]=None) -> None:
        logging.info("%s", type(self))
        logging.info("%s", self.options)
        if selection is None:
            logging.info("Using standard options")
            self.selection = [option.name for option in self.options]
        else:
            logging.info("Using custom options")
            self.selection = selection
        self.generate_analysis(comparison)
        
        return

    @abstractmethod
    def generate_analysis(self, comparison) -> None:
        pass
    
    @abstractmethod
    def to_latex(self, **kwargs) -> LatexObject:
        pass

    def to_pdf(self) -> None:
        pass

class CountComparison(Analysis):

    options = CountComparisonOptions
    section_title: str = "Link counts comparison analyses"


    def generate_analysis(self, comparison) -> None:
        for name in self.selection:
            comparison[name] = self.options[name].value(comparison)
        self.comparison = comparison

    def to_latex(self, **kwargs) -> LatexObject:
        styler = self.comparison[self.comparison.columns.difference(['geometry'])].style
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

    options = CountSummaryStatsOptions
    section_title: str = "Link counts summary statistics"

    # TODO: Allow user to specify mapping of columns to stats. For example:
    # mapping = {'count_obs': [min, max, mean], 'diff' : [RMS, MA]}
    # This way, we don't have to calculate every supplied statistic for every column in the comparison df
    # This can become an issue if the specified column was not calculated in CC

    def generate_analysis(self, comparison: pd.DataFrame) -> None:
        # statistics = defaultdict(list)

        # for name in self.selection:
        #     logging.debug('%s', name)
        #     statistics[name].append(self.options[name].value(comparison))
        # print(statistics)
        # self.statistics = pd.DataFrame.from_dict(statistics)

        statistics = pd.DataFrame(index=self.selection, columns=comparison.columns.drop(['geometry'], errors='ignore'))
        for column in statistics.columns:
            for stat in statistics.index:
                statistics.loc[stat, column] = self.options[stat].value(comparison[column])
        # self.statistics = statistics.astype(float).round(2)
        self.statistics = statistics.astype(float).round(2)
        print(self.statistics)


    def to_latex(self, **kwargs) -> LatexObject:
        styler = self.statistics.style
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

    options = CountComparisonOptions

    def __init__(self, comparison: pd.DataFrame, network: gpd.GeoDataFrame, selection: list[str]=None) -> None:
        comparison = network.merge(comparison, on='link_id', how='left')
        
        super().__init__(comparison, selection, network=network)

    def generate_analysis(self, comparison: gpd.GeoDataFrame, **kwargs) -> None:
                
        self.plots: dict[str, Figure] = {}
        for name in self.selection:
            fig, ax = plt.subplots()
            comparison.plot(column=name, ax=ax, legend=True)
            ax.set_title(f"{name}")
            ax.axis('off')
            # ax.set_axis_off()
            ax.set_frame_on(True)
            self.plots[name] = fig

    def to_latex(self, **kwargs) -> LatexObject:
        paths = self.to_file(**kwargs)
        print(f"Paths: {paths}")
        # fig = Figure().add_image(str(paths[0]))
        return FigureContainer(paths)

    def to_file(self, directory: PurePath = None, extension: str = 'pdf', **kwargs) -> list[PurePath]:
        if directory is None:
            directory = PurePath(mkdtemp())
        paths: list[PurePath] = []
        for title, plot in self.plots.items():
            filepath = PurePath(directory, f"{title}.{extension}")
            plot.savefig(filepath)
            paths.append(filepath)
        return paths

class Report():
    def __init__(self, title: str, simulated: pd.DataFrame, observed: pd.DataFrame, analyses: dict[Analysis, list[str]]) -> None:
        self.title = title
        self.comparison = self.create_comparison_df(simulated, observed)
        print(self.comparison)
        self.analyses: list[Analysis] = [analysis(self.comparison, selection) for (analysis, selection) in analyses.items()]

    def create_comparison_df(self, simulated: pd.DataFrame, observed: pd.DataFrame):
        return observed.merge(simulated, on='link_id', how='left', suffixes=['_obs', '_sim'])

    def fill_latex_doc(self, doc: Document):

        for analysis in self.analyses:
            with doc.create(Section(analysis.section_title)):
                doc.append(analysis.to_latex())

    def to_latex(self, filepath: str):
        doc = Document('basic')
        self.fill_latex_doc(doc)
        doc.generate_tex(filepath)

    def to_file(self, filepath: str):
        for analysis in self.analyses:
            analysis.to_file(filepath)
        pass