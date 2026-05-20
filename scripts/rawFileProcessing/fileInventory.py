from scripts.traceAnalysis.traceParameters import firstStageTrace
from scripts.rawFileProcessing.rawFile import rawFile
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import fnmatch
from ruamel.yaml.comments import CommentedSeq
from time import time
import os

@dataclass(kw_only=True)
class fileInventory(rawFile):
    fileName: str = field(default=None,repr=False)
    mode: str = field(default='extractData',repr=False)
    fileInventory: dict = field(default_factory=dict,repr=False)

    def __post_init__(self):
        self.fileInventoryPath = os.path.join(self.projectPath,'Sites',self.siteID,self.fileFormat,f'{self.fileID}_inventory.json')
        if os.path.isfile(self.fileInventoryPath):
            self.fileInventory = self.loadDict(self.fileInventoryPath)
        super().__post_init__()

        
    def fileSearch(self,sourceDir):
        if self.fileNameMatch is None and self.verbose:
            self.logWarning('searching without fileNameMatch may generate unwanted data and increase processing time')
        pathList = self.unpackDict(self.fileInventory).keys()
        sourceDir = self.normpath(sourceDir)
        if not os.path.isdir(sourceDir):
            self.logError(f'Not a directory: {sourceDir}')
        nNew = 0
        for dir,_,fname in os.walk(sourceDir):
            fname = [
                [os.path.relpath(dir,sourceDir),f]
                for f in fname if f.endswith(self.fileExtension) and
                (self.fileNameMatch is None or fnmatch.fnmatch(f,self.fileNameMatch)) and
                os.path.join(dir,f) not in pathList]
            if len(fname):
                T1 = time()
                if sourceDir not in self.fileInventory:
                    self.fileInventory[sourceDir] = {}
                nNew += len(fname)     
                self.uploadRawData(
                    newData = pd.concat([self.readFile(os.path.join(sourceDir,f[0],f[1])) for f in fname]),
                    siteID = self.siteID,
                    stageID = self.fileID
                    )
                dtNow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')
                for subDir,fileName in fname:
                    if subDir not in self.fileInventory[sourceDir]:
                        self.fileInventory[sourceDir][subDir] = {}
                    self.fileInventory[sourceDir][subDir][fileName] = dtNow
                self.logMessage(f"loaded contents of {os.path.join(dir)} in {time()-T1} s")

        self.formatIni()
        self.saveDict(self.fileInventory,self.fileInventoryPath)
        
        
    def formatIni(self):
        raw = self.siteConfig.ini['rawData']
        first = self.siteConfig.ini['Processing']['FirstStage']
        if self.fileFormat not in raw:
            raw[self.fileFormat] = {}
        inputDates = CommentedSeq(self.dateRange)
        inputDates.yaml_set_anchor(f'{self.fileID}_inputDatess')
        raw[self.fileFormat][self.fileID] = inputDates
        for value in self.traces.values():
            if not value['ignore']:
                inputFile = os.path.join(self.fileFormat,self.fileID,value['variableName'])
                key = value['variableName']
                if key not in first:
                    first[key] = firstStageTrace.from_dict(value|{'inputFiles':inputFile,'inputDates':inputDates}).to_dict()
                elif inputFile not in first[key]['inputFiles']:
                    incomingDates = pd.to_datetime(inputDates)
                    for current,value in first[key]['inputFiles'].items():
                        currentDates = pd.to_datetime(value)
                        test = (incomingDates[0]>=currentDates[0] and incomingDates[0]<=currentDates[1]) or (incomingDates[1]>=currentDates[0] and incomingDates[1]<=currentDates[1])
                        if test:
                            self.logWarning(f'inputDates for {current} and {inputFile} overlap.  Default behavior is for last file listed to over-write all previous where ranges overlap.  Double check config ensure this is desired behavior.')
                    
                    first[key]['inputFiles'][inputFile] = inputDates
                else:
                    first[key]['inputFiles'][inputFile] = inputDates

        self.saveConfigFile(os.path.join(self.projectPath,'Sites',self.siteID,self.fileFormat,f'{self.fileID}.yml'))
        self.saveDict(self.siteConfig.ini,self.siteConfig.iniPath)
        