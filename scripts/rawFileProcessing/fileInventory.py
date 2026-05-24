
from scripts.rawFileProcessing.rawFile import rawFile
from ruamel.yaml.comments import CommentedSeq
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
        self.fileInventoryPath = os.path.join(self.projectPath,'Sites',self.siteID,'rawFiles',f'{self.fileID}_inventory.json')
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
                os.path.join(dir,f) not in pathList and os.path.join(dir,'.',f) not in pathList]
            if len(fname):
                T1 = time()
                if sourceDir not in self.fileInventory:
                    self.fileInventory[sourceDir] = {}
                nNew += len(fname)     
                self.uploadRawData(
                    newData = pd.concat([self.readFile(os.path.join(sourceDir,f[0],f[1])) for f in fname]),
                    siteID = self.siteID,
                    stageID = self.fileID,
                    interval = self.dataIntervalSeconds
                    )
                dtNow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')
                for subDir,fileName in fname:
                    if subDir not in self.fileInventory[sourceDir]:
                        self.fileInventory[sourceDir][subDir] = {}
                    self.fileInventory[sourceDir][subDir][fileName] = dtNow
                self.logMessage(f"loaded {len(fname)} files from {os.path.join(dir)} in {time()-T1} s")
        if nNew>0:
            self.siteConfig.ini['rawData'][self.fileID][0] = self.dateRange[0]
            self.siteConfig.ini['rawData'][self.fileID][1] = self.dateRange[1]
            self.saveDict(self.siteConfig.ini,self.siteConfig.iniPath)
            self.saveDict(self.fileInventory,self.fileInventoryPath)
        
        