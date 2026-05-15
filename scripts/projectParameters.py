from helperFunctions.baseClass import baseDataClass,mdMap
from dataclasses import dataclass, field
import os

@dataclass(kw_only=True)
class project(baseDataClass):
    projectPath: str = field(repr=False,metadata=mdMap('Root path of the current project'))

    def __post_init__(self):
        pass
    