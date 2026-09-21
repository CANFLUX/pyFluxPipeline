from scripts.database.database import database
from helperFunctions.baseClass import mdMap
from dataclasses import dataclass,field
from datetime import datetime
import pandas as pd
import fnmatch
import random
import string
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
    mode: str = field(
        default='identifyTraces',
        repr=False,
        metadata=mdMap('extract data or inspect header',options=['extractData','identifyTraces']))
 

    def __post_init__(self):
        super().__post_init__()

@dataclass(kw_only=True)
class sharedFields(superFormat):
    fileName: str = field(repr=False)
    fileExtension: str = field(default=None,repr=False)
    na_values: str = field(default=None,repr=False)
    skipRows: int = field(default=None,repr=False)
    headerRows: int = field(default=None,repr=False)
    
    ignoreTraces: list = field(default_factory=list,repr=False,metadata=mdMap('Optional list of parameters to ignore'))
    renameTraces: dict = field(default_factory=dict,repr=False,metadata=mdMap('Traces to rename'))
    
    sourceID: str = field(default=None)
    siteID: str = field(default=None)

    tableName: str = field(default=None,init=False)#,repr=False)
    tableSize: str = field(default=None,init=False)#,repr=False)
    fileTimestamp: datetime = field(default=None,init=False)
    stationName: str = field(default=None,init=False)#,repr=False)
    loggerModel: str = field(default=None,init=False)#,repr=False)
    serialNumber: str = field(default=None,init=False)#,repr=False)
    program: str = field(default=None,init=False)#,repr=False)
    
    fileFormat: str = field(default = None,metadata=mdMap('used to determine which file parser', options=list(formats.keys())))
    # outputFormat: str = field(default='Database',metadata=mdMap('used to determine which file parser', options=['Database','highfrequency']))
    dataIntervalSeconds: float = field(default = None,metadata=mdMap('Autoparsed from file'))
    timestampFormat: str = field(default = None,metadata=mdMap('provide if cannot be parsed automatically', options=list(formats.keys())))
    traces: dict = field(default_factory=dict,metadata=mdMap('Autoparsed from file or user provieded'))

    startDate: datetime = field(default=None)
    stopDate: datetime = field(default=None)
    saveAs: str = field(default=None)

    def __post_init__(self):
        if self.fileFormat is None:
            self.fileFormat = type(self).__name__
            self.logMessage(f'Setting fileFormat: {self.fileFormat}')
        if self.fileExtension is None:
            self.fileExtension = formats[self.fileFormat]
        super().__post_init__()

    def formatTraces(self):
        if self.dataIntervalSeconds > 60:
            self.saveAs = 'Database'
        elif self.dataIntervalSeconds > 0 and self.dataIntervalSeconds<60:
            self.saveAs = 'ecf32'
        self.fileTimestamp = self.fileTimestamp.tz_localize(self.timezone)
        if self.sourceID is None:
            self.sourceID = f"{self.fileFormat}_{self.tableName}_{self.fileTimestamp.strftime('%Y%m%d%H%M')}"
        if len(self.ignoreTraces) or len(self.renameTraces):
            for trace in self.traces.values():
                if any([fnmatch.fnmatch(trace['originalVariable'],ignore) for ignore in self.ignoreTraces]):
                    trace['ignore'] = True
                if trace['originalVariable'] in self.renameTraces:
                    trace['variableName'] = self.renameTraces[trace['variableName']]

    def formatTable(self):        
        if hasattr(self,'gpsDriftCorrection') and self.gpsDriftCorrection:
            # Identify gaps in time series
            Offset = (self.dataTable.index.diff().fillna(self.dataIntervalSeconds)-self.dataIntervalSeconds).cumsum()
            self.dataTable.index -= Offset
            if self.verbose:
                self.logMessage(f"Total GPS induced offset in {self.fileName} is {Offset.iloc[-1]}s",verbose=False)
        if self.dataIntervalSeconds == 0:
            self.saveAs = None
        elif self.dataIntervalSeconds<1:
            self.saveAs = 'ecf32'
        
        
        # Any expected traces missing from the input file, generated as missing data
        missingTraces = {key:value['dtype'] for key,value in self.traces.items() if key not in self.dataTable.columns}
        if len(missingTraces):
            self.logWarning(f'Missing expected traces in {self.fileName}, filling with nodata')
            missingTraces = self.noDataTable(self.dataTable.index,missingTraces)
            self.dataTable = pd.concat([self.dataTable,missingTraces],axis=1)

        # Drop extra columns not included in traces definition
        self.dataTable = self.dataTable.drop(columns = self.dataTable.columns[~self.dataTable.columns.isin(list(self.traces.keys()))])
        # rename columns according to traces
        self.dataTable = self.dataTable.rename(columns = {key:value['variableName'] for key,value in self.traces.items()})
        # drop ignore columns
        self.dataTable = self.dataTable.drop(columns=[value['variableName'] for value in self.traces.values() if value['ignore'] if value['variableName'] in self.dataTable.columns])
        # drop nan rows
        self.dataTable = self.dataTable.dropna(how='all')
        if self.dataTable.empty:
            self.saveAs = None
            return None
        
        if self.dataIntervalSeconds is None:
            self.logError(f'Determine data interval or set to default for {self.fileFormat}')
        # drop duplicated indexes (first considered valid)
        if self.dataTable.index.duplicated().sum():
            self.logWarning(f"Duplicated indices at in position:\n{self.dataTable[self.dataTable.index.duplicated(keep=False)]}")
            self.dataTable = self.dataTable[~self.dataTable.index.duplicated()].copy()
        if not self.saveAs == 'ecf32':
            self.dataTable = self.dataTable.resample(f"{self.dataIntervalSeconds}s").nearest()
        if self.dataTable.index.unit=='us':
            #Default in pandas >=3.0
            posixtime_int64 = ((self.dataTable.index.astype(int)//1e6).values).astype('int64')
        elif self.dataTable.index.unit == 'ns':
            #Default in pandas <3.0
            posixtime_int64 = ((self.dataTable.index.astype(int)//1e9).values).astype('int64')
        self.dataTable[self.posixName] = posixtime_int64
        if self.dataTable.index.tz is None:
            self.dataTable.index = self.dataTable.index.tz_localize(self.timezone)
        elif str(self.dataTable.index.tz) != self.timezone:
            self.logError('Mismatching timezones.  Add timezone converter here')
        self.logMessage('Set Date Range Parameter? No - Date range not necisarilly explicity enough?')
