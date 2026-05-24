from scripts.database.database import database
from helperFunctions.baseClass import mdMap
from dataclasses import dataclass,field
import os


formats = {
    'HOBOcsv':'csv',
    'EddyProOutput':'csv',
    'TOB3':'dat',
    'TOA5':'dat',
    'MixedArray':'dat',
    'NARRcsv':'csv'
}
@dataclass(kw_only=True)
class sharedFields(database):
    fileName: str = field(repr=False)
    fileExtension: str = None
    na_values: str = None
    skipRows: int = None
    headerRows: int = None
    timestampFormat: str = None
    dataIntervalSeconds: float = None
    traces: dict = field(default_factory=dict)
    fileFormat: str = field(metadata=mdMap('used to determine which file parser', options=list(formats.keys())))
    mode: str = field(default='identifyTraces',repr=False,metadata=mdMap('extract data or inspect header',options=['extractData','identifyTraces']))
    ignore: list = None
    

    def __post_init__(self):
        if self.fileExtension is None:
            self.fileExtension = formats[self.fileFormat]
        super().__post_init__()