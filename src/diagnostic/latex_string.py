from pylatex.base_classes import LatexObject
from pylatex.utils import escape_latex

class LatexString(LatexObject):
    """LatexObject subclass meant to hold a given latex string and return it when self.dumps() is called"""
    def __init__(self, latex_string: str, escape: bool, *args, **kwargs):
        # if escape: latex_string = escape_latex(latex_string)
        # self.latex_string = latex_string
        super().__init__(*args, **kwargs)
    def dumps(self):
        return self.latex_string

class LatexStringTable(LatexString):
    def __init__(self, latex_string: str, escape: bool, *args, **kwargs):
        kwargs['packages'] = ()
        super().__init__(latex_string, escape, *args, **kwargs)