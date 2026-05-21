from scripts.rawFileProcessing.parseCSV import EddyProOutput, HOBOcsv
from scripts.rawFileProcessing.parseCSI import TOB3, TOA5
from helperFunctions.baseClass import mdMap
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import os

@dataclass(kw_only=True)
class rawFile(TOB3,TOA5,EddyProOutput,HOBOcsv):
    templateFile: str = None
    fileNameMatch: str = None
    siteID: str
    fileID: str
    dateRange: list = None
    traces: dict = field(default_factory=dict)
    searchDir: str = field(default=None,repr=False)
    fileInventory: dict = field(default_factory=dict,repr=False)
    configFileName: str = field(default=None,repr=False)

    def __post_init__(self):
        super().__post_init__()
        configFileName = os.path.join(self.projectPath,'Sites',self.siteID,'rawFiles',f'{self.fileID}.yml')
        if self.mode == 'extractData' and self.configFile is None:
            if not os.path.isfile(configFileName):
                self.logError(f"does not exist: {configFileName}")
            params = self.loadDict(configFileName)
            for key in params:
                if key in self.__dataclass_fields__.keys():
                    setattr(self,key,params[key])
        self.siteConfig = self.loadSiteConfiguration(self.siteID)
        
        if self.fileName is not None:
            self.readFile()

    def readFile(self,fileName=None):
        if fileName is not None:
            self.fileName = fileName

        if self.fileFormat == 'EddyProOutput':
            self.readEddyProOutput()
        elif self.fileFormat == 'HOBOcsv':
            self.readHOBOcsv()
        elif self.fileFormat == 'TOB3':
            self.readTOB3()
        elif self.fileFormat == 'TOA5':
            self.readTOA5()
        if self.mode == 'identifyTraces':
            self.templateFile = self.fileName
            # Update ignores (user provided or defaults from processor)
            if self.ignore is not None:
                for ignore in self.ignore:
                    self.traces[ignore]['ignore'] = True
            self.saveConfigFile(os.path.join(self.projectPath,'Sites',self.siteID,'rawFiles',f'{self.fileID}.yml'))
            if self.dataIntervalSeconds is None:
                self.logMessage(f'confirm dataIntervalSeconds inferred from table correctly: {self.dataIntervalSeconds}')
                self.dataIntervalSeconds = self.dataTable.index.diff().median().total_seconds()
            self.siteConfig.saveConfigFile(os.path.join(self.projectPath,'Sites',self.siteID,f"{self.siteID}_siteMetadata.yml"))
            return None
        elif self.dataTable.empty:
            return None
        else:
            self.formatTable()
            return (self.dataTable)

    def formatTable(self):
        
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

        if self.dataIntervalSeconds is None:
            self.logError(f'Determine data interval or set to default for {self.fileFormat}')
        # drop duplicated indexes (first considered valid)
        if self.dataTable.index.duplicated().sum():
            self.logWarning(f"Duplicated indices at in position:\n{self.dataTable[self.dataTable.index.duplicated(keep=False)]}")
            self.dataTable = self.dataTable[~self.dataTable.index.duplicated()].copy()
        self.dataTable = self.dataTable.resample(f"{self.dataIntervalSeconds}s").nearest()
        if self.dataTable.index.unit=='us':
            #Default in pandas >=3.0
            posixtime_int64 = ((self.dataTable.index.astype(int)//1e6).values).astype('int64')
        elif self.dataTable.index.unit == 'ns':
            #Default in pandas <3.0
            posixtime_int64 = ((self.dataTable.index.astype(int)//1e9).values).astype('int64')
        self.dataTable[self.posixName] = posixtime_int64
        self.dataTable.index = self.dataTable.index.tz_localize(self.timezone)

        if self.dateRange is None:
            self.dateRange = [self.dataTable.index.min().isoformat(),self.dataTable.index.max().isoformat()]
        else:
            self.dateRange = pd.to_datetime(self.dateRange)
            self.dateRange = [
                min(self.dateRange[0],self.dataTable.index.min()).isoformat(),
                max(self.dateRange[1],self.dataTable.index.max()).isoformat()
            ]

# python -m scripts.rawFileProcessing.rawFile --fileName testing\data\eddypro_t_full_output_2025-05-02T224906_exp.csv --siteID SCL --projectPath testing/testProject --fileFormat EddyProOutput --fileID EP_recalc_2024 
# python -m scripts.rawFileProcessing.rawFile --fileName testing\data\Met_Data122.dat --siteID SCL --projectPath testing/testProject --fileFormat TOB3 --fileID EC_Met_2024 

# python -m scripts.rawFileProcessing.rawFile --fileName testing\data\20750528-SHSC.SSM.SGT.240720_240913readout.csv --siteID SCL --projectPath testing/testProject --fileFormat HOBOcsv --fileID TS_SSM
if __name__ == '__main__':
    current = rawFile.from_cmd(safeMode=False)

    breakpoint()