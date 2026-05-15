from helperFunctions import baseClass
from dataclasses import dataclass, field
import os
mdMap = baseClass.mdMap

@dataclass(kw_only=True)
class project(baseClass.baseDataClass):
    projectPath: str = field(repr=False,metadata=mdMap('Root path of the current project'))
    # sites: list = field(default_factory=list,metadata=mdMap('List of siteIDs'),repr=False)
    # siteInventory: dict = field(init=False,default_factory=dict,repr=False)

    