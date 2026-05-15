from scripts.projectParameters import project
from helperFunctions.baseClass import mdMap
from dataclasses import dataclass,field
import os


@dataclass(kw_only=True)
class sharedFields(project):
    fileName: str
    na_values: str = None
    skipRows: int = None
    headerRows: int = None
    timestampFormat: str = None
    dataIntervalSeconds: float = None
    traces: dict = field(default_factory=dict)
    mode: str = field(default='identifyTraces',repr=False,metadata=mdMap('extract data or inspect header',options=['extractData','identifyTraces']))
    

