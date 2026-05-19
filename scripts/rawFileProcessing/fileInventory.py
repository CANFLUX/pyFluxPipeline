from scripts.rawFileProcessing.rawFile import rawFile
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import fnmatch
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
        self.saveDict(self.fileInventory,self.fileInventoryPath)
        
                # breakpoint()
                #     self.dbIndex(fullDataTable.index.year[0])
                # breakpoint()
        #             if sourceDir not in self.fileInventory:
        #                 self.fileInventory[sourceDir] = {}
        #             for fileParts in fname:
        #                 if fileParts[0] not in self.fileInventory[sourceDir]:
        #                     self.fileInventory[sourceDir][fileParts[0]]={fileParts[1]:None}
        #                 elif fileParts[1] not in self.fileInventory[sourceDir][fileParts[0]]:
        #                     self.fileInventory[sourceDir][fileParts[0]][fileParts[1]]=None
        # self.logMessage(f'{nNew} new files found in {sourceDir}')
        # self.fullDataTable = None
        # print([(sourceDir,subDir,fileName)
        #        for sourceDir in self.fileInventory.keys()
        #        for subDir,file in self.fileInventory[sourceDir].items() 
        #        for fileName,dateLoaded in file.items() if dateLoaded is None])
        # breakpoint()
        # for sourceDir in self.fileInventory.keys():
        #     for subDir,file in self.fileInventory[sourceDir].items():
        #         for fileName,dateLoaded in file.items():
        #             print(sourceDir,subDir,fileName,dateLoaded)
        #             if dateLoaded is None:
        #                 self.fileName = os.path.join(sourceDir,subDir,fileName)
        #                 self.readFile()
        #                 breakpoint()
        #                 success = self.fileProcessor(sourcePath,True)
        #                 self.dataTable['sourcePath'] = sourcePath
        #                 if self.fullDataTable is None:
        #                     self.fullDataTable = self.dataTable
        #                 else:
        #                     self.fullDataTable = pd.concat([self.fullDataTable,self.dataTable])
        #                 if success:
        #                     self.fileInventory[sourceDir][subDir][fileName] = self.currentTimeString()
        # # Remove duplicates
        # keys = [val['variableFileName'] for val in self.rawTraceParameters.values() if not val['ignore']]
        # if len(keys) == 0:
        #     self.logError('Not traces passed?')
        # duplicates = (self.fullDataTable[keys].duplicated()&self.fullDataTable.index.duplicated()).values
        # self.fullDataTable = self.fullDataTable[~duplicates].sort_index()
        # if self.fullDataTable.index.duplicated().sum():
        #     self.logWarning(f'{self.fullDataTable.index.duplicated().sum()} duplicated indices remain in {self.stageID}.  Keeping last duplicate, deleting entries. Double check these timestamps/files: {self.fullDataTable.loc[self.fullDataTable.index.duplicated(keep=False),"sourcePath"]}')
        #     self.fullDataTable = self.fullDataTable[~self.fullDataTable.index.duplicated(keep='last')]
        # self.fullDataTable.drop(columns='sourcePath',inplace=True) 
        # self.writeToDatabase()
        # self.saveDict(self.fileInventory,self.fileInventoryPath,indent=True)