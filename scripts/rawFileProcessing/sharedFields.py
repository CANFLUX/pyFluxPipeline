from dataclasses import dataclass,field
from helperFunctions.baseClass import baseDataClass, mdMap


@dataclass(kw_only=True)
class sharedFields(baseDataClass):
    fileName: str
    traces: dict = field(default_factory=dict)

