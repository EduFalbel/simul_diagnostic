from pathlib import PurePath
from typing import Any

import pandas as pd
from pylatex import Document, Section

from diagnostic.analyses import Analysis, CountComparison, CountSummaryStats, CountVisualization, EarthMoverDistance



class CreateComparisonDF():

    @staticmethod
    def link_comp(sim: pd.DataFrame, obs: pd.DataFrame) -> pd.DataFrame:
        assert set(['link_id', 'count']).issubset(sim.columns) and set(['link_id', 'count']).issubset(obs.columns)

        if 'time' in sim.columns:
            sim = sim.groupby(['link_id']).sum().reset_index()
        if 'time' in obs.columns:
            obs = obs.groupby(['link_id']).sum().reset_index()

        comp = sim.merge(obs, on='link_id', how='right', suffixes=['_sim', '_obs'])
        return comp[comp.columns.intersection(set(['link_id', 'count_sim', 'count_obs', 'geometry']))]

    @staticmethod
    def emd(sim: pd.DataFrame, obs: pd.DataFrame):
        sim = sim[['link_id', 'time', 'count']].groupby(['link_id', 'time'])['count'].sum().reset_index()
        obs = obs[['link_id', 'time', 'count']].groupby(['link_id', 'time'])['count'].sum().reset_index()

        return sim.merge(obs, on=['link_id', 'time'], how='outer', suffixes=['_sim', '_obs']).fillna(0)

class CCDFMapper():
    mapping = {
        CountComparison : CreateComparisonDF.link_comp,
        CountSummaryStats : CreateComparisonDF.link_comp,
        CountVisualization : CreateComparisonDF.link_comp,
        EarthMoverDistance : CreateComparisonDF.emd
    }

class Report():

    def __init__(self, title: str, simulated: pd.DataFrame, observed: pd.DataFrame, analyses: list[Analysis], analysis_dependence_dict: dict[Analysis, Analysis]=None) -> None:
        """
        analysis_dependence_dict = {
            CountSummaryStats() : CountComparison(),
            CountVisualization() : CountComparison()
        }
        """
        self.title = title
        self.analyses = analyses
        if analysis_dependence_dict is None:
            analysis_dependence_dict = {}
        self.add = analysis_dependence_dict

        self.generate_analyses(simulated, observed)

    def generate_analyses(self, simulated: pd.DataFrame, observed: pd.DataFrame):
        """
        Method to automatically generate the given analyses while making sure to pass in the result of one analysis to the input of another if specified by the analysis dependence dictionary
        ATTENTION: This implementation requires that, should one wish for analysis1 to use the result from analysis2, then analysis2 must be before analysis1 in the passed-in analyses list
        """
        generated: list[Analysis] = []
        for analysis in self.analyses:
            print(f"Analysis:{analysis}")
            if (analysis in self.add and self.add.get(analysis) in generated):
                analysis.generate_analysis(self.add[analysis].result)
            else:
                    analysis.generate_analysis((CCDFMapper.mapping[type(analysis)](simulated.copy(), observed.copy())))
            generated.append(analysis)

    def to_latex(self, filepath: PurePath):
        doc = Document()
        self._fill_latex_document(doc)
        doc.generate_tex(filepath)

    def _fill_latex_document(self, document: Document):
        for analysis in self.analyses:
            latex_object = analysis.to_latex()
            with document.create(Section(analysis.section_title)):
                document.append(latex_object)

    def to_file(self, filepath: PurePath):
        raise NotImplementedError
        for analysis in self.analyses:
            analysis.to_file(filepath)
        pass