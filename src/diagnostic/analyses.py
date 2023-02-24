import pandas as pd
import geopandas as gpd
import numpy as np
from enum import Enum, member

from abc import ABC, abstractmethod

simulation_counts_path = 'simulation_counts.csv'
observed_counts_path = 'observed_counts.csv'
output_path = 'comparison.csv'

simulation_counts = pd.read_csv(simulation_counts_path)
observed_counts = pd.read_csv(observed_counts_path)

# For the comparison we keep only links which have observed counts

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
        SQV = member(lambda comp: 1/(1+np.sqrt((comp['count_sim'] - comp['count_obs'])**2/(comp['count_obs']*(comp['count_obs']**np.log10(comp['count_obs']))))))
        GEH = member(lambda comp: np.sqrt(2*(comp['count_sim'] - comp['count_obs'])**2/(comp['count_sim'] + comp['count_obs'])))

class CountSummaryStatsOptions(Options):
        MEAN_OBS_COUNT = member(lambda comp: comp['count_obs'].mean())
        MEAN_SIM_COUNT = member(lambda comp: comp['count_sim'].mean())
        MAE = member(lambda comp: comp['DIFF'].mean()) # Diff might not exist, need to figure out whether to call CCO, replicate diff function here or check if exists
        RMSE = member(lambda comp: np.sqrt((comp['DIFF']**2).mean()))
        MPE = member(lambda comp: comp['PCT_DIFF'].mean())


class Analysis(ABC):

    options: Options

    def __init__(self, comparison: pd.DataFrame, selection: list[str]=None) -> None:
        if selection is None:
            self.selection = [option.name for option in self.options]
        else:
            self.selection = selection
        self.generate_analysis(comparison)
        
        return

    @abstractmethod
    def generate_analysis(self, comparison) -> None:
        pass

    def to_pdf(self) -> None:
        pass

class CountComparison(Analysis):

    options = CountComparisonOptions

    def __init__(self, comparison: pd.DataFrame, selection: list[str]=None) -> None:
        super().__init__(comparison, selection)

    def generate_analysis(self, comparison) -> None:
        for name in self.selection:
            comparison[name] = self.options[name].value(comparison)

class CountSummaryStats(Analysis):

    options = CountSummaryStatsOptions

    # def __init__(self, comparison: pd.DataFrame, selection: list[str]=None) -> None:
    #     # TODO: Allow user to specify mapping of columns to stats. For example:
    #     # mapping = {'count_obs': [min, max, mean], 'diff' : [RMS, MA]}
    #     # This way, we don't have to calculate every supplied statistic for every column in the comparison df
    #     # This can become an issue if the specified column was not calculated in CC
    #     super().__init__(comparison, selection)

    def generate_analysis(self, comparison) -> None:
        self.statistics = {}

        for name in self.selection:
            self.statistics[name] = self.options[name].value(comparison)

class CountVisualization(Analysis):

    options = CountComparisonOptions

    def __init__(self, comparison: pd.DataFrame, network: gpd.GeoDataFrame, selection: list[str]=None) -> None:
        comparison = network.merge(comparison, on='link_id', how='left')
        
        super().__init__(comparison, selection, network=network)

    def generate_analysis(self, comparison, **kwargs) -> None:
                
        self.plots = {}
        for name in self.selection:
            fig, ax = plt.subplots()
            comparison.plot(column=name, ax=ax)
            self.plots[name] = fig

class Report():
    def __init__(self, title: str, simulated: pd.DataFrame, observed: pd.DataFrame, analyses: dict[Analysis, list[str]]) -> None:
        self.title = title
        self.comparison = self.create_comparison_df(simulated, observed)
        self.analyses = [analysis(self.comparison, selection) for (analysis, selection) in analyses.items()]

    def create_comparison_df(simulated: pd.DataFrame, observed: pd.DataFrame):
        return observed.merge(simulated, on='link_id', how='left', suffixes=['obs', 'sim'])

    def to_file(self, filename: str):
        for analysis in self.analyses:
            analysis.to_file(filename)
        pass