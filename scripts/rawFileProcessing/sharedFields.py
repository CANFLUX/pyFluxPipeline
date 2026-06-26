from scripts.database.database import database
from helperFunctions.baseClass import mdMap
from dataclasses import dataclass,field
from datetime import datetime
import os

formats = {
    'HOBOcsv':'csv',
    'EddyProOutput':'csv',
    'GHG':'ghg',
    'TOB3':'dat',
    'TOA5':'dat',
    'MixedArray':'dat',
    'NARRcsv':'csv'
}
superFormats = {
    'HOBOcsv':None,
    'EddyProOutput':'LICOR',
    'GHG':'LICOR',
    'TOB3':'CSI',
    'TOA5':'CSI',
    'MixedArray':'CSI',
    'NARRcsv':None
}

@dataclass(kw_only=True)
class superFormat(database):
    mode: str = field(default='identifyTraces',repr=False,metadata=mdMap('extract data or inspect header',options=['extractData','identifyTraces']))
 

    def __post_init__(self):
        super().__post_init__()
    #     if superFormat[self.fileFormat] == 'CSI' and self.mode == 'identifyTraces':
            
    #     tableName: str = field(default=None,init=False,repr=False)
    #     fileTimestamp: datetime = field(default=None,init=False,repr=False)
    #     stationName: str = field(default=None,init=False,repr=False)
    #     loggerModel: str = field(default=None,init=False,repr=False)
    #     serialNumber: str = field(default=None,init=False,repr=False)
    #     program: str = field(default=None,init=False,repr=False)

@dataclass(kw_only=True)
class sharedFields(superFormat):
    fileName: str = field(repr=False)
    fileExtension: str = field(default=None,repr=False)
    na_values: str = field(default=None,repr=False)
    skipRows: int = field(default=None,repr=False)
    headerRows: int = field(default=None,repr=False)
    
    tableName: str = field(default=None,init=False)#,repr=False)
    fileTimestamp: datetime = field(default=None,init=False,repr=False)
    stationName: str = field(default=None,init=False)#,repr=False)
    loggerModel: str = field(default=None,init=False)#,repr=False)
    serialNumber: str = field(default=None,init=False)#,repr=False)
    program: str = field(default=None,init=False)#,repr=False)
    
    
    fileFormat: str = field(default = None,metadata=mdMap('used to determine which file parser', options=list(formats.keys())))
    dataIntervalSeconds: float = field(default = None,metadata=mdMap('Autoparsed from file'))
    ignore: list = field(default = None,metadata=mdMap('Optional list of parameters to ignore'))
    timestampFormat: str = field(default = None,metadata=mdMap('provide if cannot be parsed automatically', options=list(formats.keys())))
    traces: dict = field(default_factory=dict,metadata=mdMap('Autoparsed from file or user provieded'))
    

    def __post_init__(self):
        if self.fileFormat is None:
            self.fileFormat = type(self).__name__
            self.logMessage(f'Setting fileFormat: {self.fileFormat}')
        if self.fileExtension is None:
            self.fileExtension = formats[self.fileFormat]
        super().__post_init__()