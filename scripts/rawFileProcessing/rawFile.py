from scripts.rawFileProcessing.parseCSV import EddyProOutput, HOBOcsv, NARRcsv
from scripts.traceAnalysis.traceParameters import firstStageTrace
from scripts.rawFileProcessing.parseCSI import TOB3, TOA5, MixedArray
from ruamel.yaml.comments import CommentedSeq
# from helperFunctions.baseClass import mdMap
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import os

@dataclass(kw_only=True)
class rawFile(TOB3,TOA5,EddyProOutput,HOBOcsv,MixedArray,NARRcsv):
    templateFile: str = None
    fileNameMatch: str = None
    siteID: str
    fileID: str
    dateRange: list = field(default_factory=lambda:[None,None])
    dataIntervalSeconds: float = None
    traces: dict = field(default_factory=dict)
    # mapIniTemplate: bool = True
    searchDir: str = field(default=None,repr=False)
    fileInventory: dict = field(default_factory=dict,repr=False)
    fileConfigPath: str = field(default=None,repr=False)

    def __post_init__(self):
        self.readers = {
            'EddyProOutput':self.readEddyProOutput,
            'HOBOcsv':self.readHOBOcsv,
            'TOB3':self.readTOB3,
            'TOA5':self.readTOA5,
            'MixedArray':self.readMixedArray,
            'NARRcsv':self.readNARRcsv
        }
        super().__post_init__()
        self.fileConfigPath = os.path.join(self.projectPath,'Sites',self.siteID,'rawFiles',f'{self.fileID}.yml')
        if os.path.isfile(self.fileConfigPath) and self.mode == 'identifyTraces':
            self.logMessage(f'Auto-update not supported.  Move {self.fileConfigPath} first.')
            return
        elif self.mode == 'extractData':
            if not os.path.isfile(self.fileConfigPath):
                self.logError(f"does not exist: {self.fileConfigPath}")
            else:
                params = self.loadDict(self.fileConfigPath)
                for key in params:
                    if key in self.__dataclass_fields__.keys():
                        setattr(self,key,params[key])
        self.siteConfig = self.loadSiteConfiguration(self.siteID)
        
        if self.fileName is not None:
            self.readFile()

    def readFile(self,fileName=None):
        if fileName is not None:
            self.fileName = fileName
        self.readers[self.fileFormat]()
        # if self.fileFormat == 'EddyProOutput':
        #     self.readEddyProOutput()
        # elif self.fileFormat == 'HOBOcsv':
        #     self.readHOBOcsv()
        # elif self.fileFormat == 'TOB3':
        #     self.readTOB3()
        # elif self.fileFormat == 'TOA5':
        #     self.readTOA5()
        # elif self.fileFormat == 'MixedArray':
        #     self.readMixedArray()
        if self.mode == 'identifyTraces':
            self.templateFile = self.fileName
            # Update ignores (user provided or defaults from processor)
            if self.ignore is not None:
                for ignore in self.ignore:
                    self.traces[ignore]['ignore'] = True
            self.saveConfigFile(self.fileConfigPath)
            if self.dataIntervalSeconds is None:
                self.logMessage(f'confirm dataIntervalSeconds inferred from table correctly: {self.dataIntervalSeconds}')
                self.dataIntervalSeconds = self.dataTable.index.diff().median().total_seconds()
            self.formatIni()
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
        if self.dataTable.index.tz is None:
            self.dataTable.index = self.dataTable.index.tz_localize(self.timezone)
        elif str(self.dataTable.index.tz) != self.timezone:
            self.logError('Mismatching timezones.  Add timezone converter here')
            breakpoint()
        if self.dateRange == self.__dataclass_fields__['dateRange'].default_factory():
            self.dateRange = [self.dataTable.index.min().isoformat(),self.dataTable.index.max().isoformat()]
        else:
            self.dateRange = pd.to_datetime(self.dateRange)
            self.dateRange = [
                min(self.dateRange[0],self.dataTable.index.min()).isoformat(),
                max(self.dateRange[1],self.dataTable.index.max()).isoformat()
            ]
        self.saveConfigFile(self.fileConfigPath)

    def formatIni(self):
        rawData = self.siteConfig.ini['rawData']
        first = self.siteConfig.ini['Processing']['FirstStage']

        if self.fileID not in rawData:
            inputDates = CommentedSeq(self.dateRange)
            inputDates.yaml_set_anchor(f'{self.fileID}.inputDates')
            rawData[self.fileID] = inputDates
            if self.posixName not in first:
                first[self.posixName] = firstStageTrace(
                    variableName=self.posixName,
                    inputFiles=f"{self.fileID}.{self.posixName}",
                    inputDates=inputDates,
                    dtype='int64',
                    units='s',
                    notes='default time-trace (seconds since unix epoch)').to_dict()
            else:
                first[self.posixName]['inputFiles'][f"{self.fileID}.{self.posixName}"] = inputDates
            
            self.saveConfigFile(self.fileConfigPath)
            self.saveDict(self.siteConfig.ini,self.siteConfig.iniPath)
            # breakpoint()

        # for value in self.traces.values():
        #     if not value['ignore']:
        #         inputFile = f"{self.fileID}.{value['variableName']}"
        #         key = value['variableName']
        #         if key not in first:
        #             first[key] = firstStageTrace.from_dict(value|{'inputFiles':inputFile,'inputDates':inputDates}).to_dict()
        #         elif inputFile not in first[key]['inputFiles']:
        #             incomingDates = pd.to_datetime(inputDates)
        #             for current,value in first[key]['inputFiles'].items():
        #                 currentDates = pd.to_datetime(value)
        #                 test = (incomingDates[0]>=currentDates[0] and incomingDates[0]<=currentDates[1]) or (incomingDates[1]>=currentDates[0] and incomingDates[1]<=currentDates[1])
        #                 if test:
        #                     self.logWarning(f'inputDates for {current} and {inputFile} overlap.  Default behavior is for last file listed to over-write all previous where ranges overlap.  Double check config ensure this is desired behavior.')
                    
        #             first[key]['inputFiles'][inputFile] = inputDates
        #         else:
        #             first[key]['inputFiles'][inputFile] = inputDates

        


# python -m scripts.rawFileProcessing.rawFile --fileName testing\data\eddypro_t_full_output_2025-05-02T224906_exp.csv --siteID SCL --projectPath testing/testProject --fileFormat EddyProOutput --fileID EP_recalc_2024 
# python -m scripts.rawFileProcessing.rawFile --fileName testing\data\Met_Data122.dat --siteID SCL --projectPath testing/testProject --fileFormat TOB3 --fileID EC_Met_2024 

# python -m scripts.rawFileProcessing.rawFile --fileName testing\data\20750528-SHSC.SSM.SGT.240720_240913readout.csv --siteID SCL --projectPath testing/testProject --fileFormat HOBOcsv --fileID TS_SSM
if __name__ == '__main__':
    current = rawFile.from_cmd(safeMode=False)

    breakpoint()