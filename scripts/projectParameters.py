from helperFunctions import baseClass
from dataclasses import dataclass, field
import os

defaultSettings = baseClass.baseClassMethods().loadDict(os.path.join(os.getcwd(),'configurationFiles','defaultSettings.yml'))

@dataclass(kw_only=True)
class project(baseClass.baseDataClass):
    projectPath: str = field(repr=False,metadata=baseClass.mdMap('Root path of the current project'))
    defaultSettings: dict = field(default_factory=lambda:defaultSettings,init=False,repr=False)
