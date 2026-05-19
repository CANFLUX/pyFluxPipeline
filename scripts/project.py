
from dataclasses import field, dataclass
from helperFunctions.baseClass import baseDataClass, mdMap

@dataclass(kw_only=True)
class project(baseDataClass):
    projectPath: str = field(repr=False,metadata=mdMap('Root path of the current project'))