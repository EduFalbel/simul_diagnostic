from pathlib import PurePath
from typing import Any

import pandas as pd
from pylatex import Document, Section

from diagnostic.analyses import Analysis

class Report():
    class LatexReport(Document):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)




    def __init__(self, title: str, simulated: pd.DataFrame, observed: pd.DataFrame, analyses: list[Analysis], analysis_dependence_dict=None) -> None:
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
        ATTENTION: This implementation requires that, should one wish for analysis1 to use the result from analysis2, then analysis2 must be before analysis in the passed in analyses list
        """
        generated: list[Analysis] = []
        for analysis in self.analyses:
            if analysis in self.add and self.add[analysis] in generated:
                analysis.generate_analysis(self.add[analysis].result)
            else:
                analysis.generate_analysis(analysis.create_comp_df(simulated, observed))
            generated.append = analysis

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