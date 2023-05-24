from pylatex.base_classes import LatexObject, Container
from pylatex.utils import NoEscape
from pylatex.package import Package
from pylatex import Figure


class LatexString(LatexObject):
    """LatexObject subclass meant to hold a given latex string and return it when self.dumps() is called"""

    def __init__(self, latex_string: str, escape: list[str], *args, **kwargs):
        if escape:
            print(f"Escape chars: {escape}")
            latex_string = self.escape(latex_string, escape)
        self.latex_string = latex_string
        super().__init__(*args, **kwargs)

    def dumps(self):
        return self.latex_string

    def escape(self, string: str, escape_chars: list[str]) -> str:
        for char in escape_chars:
            replacement = "\\" + char
            string = string.replace(char, replacement)
        return string


class LatexStringTable(LatexString):
    packages = [Package("tabularx"), Package("float"), Package("longtable"), Package("numprint")]

    def __init__(self, latex_string: str, escape: bool, *args, **kwargs):
        super().__init__(latex_string, escape, *args, **kwargs)


class FigureContainer(Container):
    def __init__(self, paths, *, data=None, width=NoEscape(r"\textwidth"), position="H"):
        data = [Figure(position=position) for path in paths]
        for fig, path in zip(data, paths):
            fig.add_image(str(path), width=width)
        print(f"Data: {data}\nWidth: {width}")
        super().__init__(data=data)

    def dumps(self):
        return self.dumps_content()
