from scripts.rawFileProcessing.parseCSV import EddyProOutput, HOBOcsv, NARRcsv
from scripts.database.database import database
from scripts.ecf32.ecf32 import ecf32
from scripts.rawFileProcessing.processor import processor,getRawFileMetadata,readRawFileData
from scripts.rawFileProcessing.sharedFields import sharedFields
from scripts.ecf32.ghgMetadata import ghgMetadata
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from functools import partial
import pandas as pd
import numpy as np
import fnmatch
import json
import time
import os

@dataclass(kw_only=True)
class fileSet(sharedFields):
    fileName: str = None

    def __post_init__(self):
        super().__post_init__()
        # Read configuration and inventories
        # Files that are being tracked
        # File metadata groups
        self.fileInventoryPath = os.path.join(self.metaPath,'.inventory','fileInventory.json')
        self.fileInventory = self.loadDict(self.fileInventoryPath,template={})
        self.fileGroups = pd.DataFrame([self.loadDict(os.path.join(self.metaPath,k,f)+'.yml') for k,v in self.fileInventory.items() for f in v.keys()])
        if 'traces' in self.fileGroups.columns:
            self.fileGroups['traces'] = [json.dumps(tr) for tr in self.fileGroups['traces']]

        self.siteConfig = self.loadSiteConfiguration(self.siteID)

        # self.siteConfig,self.sensorGroups,self.sensorHistory = self.loadSiteConfiguration(self.siteID,sensorGroups=True)

    # def generateIni(self,overwrite=False):


@dataclass(kw_only=True)
class fileSearch(fileSet):
    searchPath: str = None
    ignoreFiles: list = field(default_factory=list)
    findFiles: list = field(default_factory=list)

    def __post_init__(self):
        
        super().__post_init__()
        # Serarch for new files not in inventory
        existingFiles =  [file for format in self.fileInventory.values() for sourceSet in format.values() for file in sourceSet['fileName']]
        newFileMetadata,newFileInventory = self.search(existingFiles)
        if newFileInventory is not None:
            # Append the new Inventory to the current
            for (saveAs,sourceID),value in newFileInventory.items():
                self.fileInventory.setdefault(saveAs,{})
                self.fileInventory[saveAs].setdefault(sourceID,{key:[] for key in value.keys()})
                for key,val in value.items():
                    self.fileInventory[saveAs][sourceID][key] += val
            # Save updated inventory
            self.saveDict(self.fileInventory,self.fileInventoryPath)
        # Read metadata from new inventory, merge with existing groups, or create new ones where applicable
        self.groupFiles(newFileMetadata,groupKeys=['tableName','loggerModel','program','fileFormat','dataIntervalSeconds','traces','timezone'])
        # Put any new file metadata into a template ini file
        # self.generateIni()
        for _,fileGroup in self.fileGroups.loc[self.fileGroups['saveAs'] == 'Database'].iterrows():
            self.siteConfig.updateIni(sourceFile=fileGroup)

    def search(self,existingFiles):
        newFiles = [os.path.join(dir,file) for dir,_,files in os.walk(self.searchPath) 
                    for file in files if ((file.endswith(self.fileExtension) and os.path.join(dir,file) not in existingFiles) and
                        (len(self.findFiles) == 0 or any([fnmatch.fnmatch(file,fnd) for fnd in self.findFiles])) and
                        (len(self.ignoreFiles) == 0 or not any([fnmatch.fnmatch(file,ign) for ign in self.ignoreFiles])) and
                        len(files))]
        if len(newFiles):
            newFileMetadata = self.getMetadata(newFiles)
            newFileMetadata['Processed'] = False
            newFileMetadata['fileTimestamp'] = newFileMetadata['fileTimestamp'].map(lambda x: x.isoformat())
            if self.sourceID is not None:
                newFileMetadata['sourceID'] = self.sourceID
            newFileInventory = newFileMetadata[['saveAs','sourceID','fileName','Processed','fileTimestamp']].groupby(['saveAs','sourceID']).agg(list).to_dict(orient='index')
            return(newFileMetadata.drop(columns=['Processed','fileName','fileTimestamp']),newFileInventory)
        else:
            return(pd.DataFrame(),None)

    def getMetadata(self,newFiles):
        T1 = time.time()
        self.logMessage(f"Searching: {len(newFiles)} files")
        reader = partial(getRawFileMetadata,
                projectPath=self.projectPath,
                fileFormat=self.fileFormat,
                siteID=self.siteID,
                timezone=self.timezone,
                ignoreTraces=self.ignoreTraces)
        if not self.useParallel:
            metadata = pd.DataFrame({f:reader(fileName=f) for f in newFiles.keys()}).T
        else:
            with ProcessPoolExecutor() as executor:
                metadata = pd.DataFrame({f:out for f,out in zip(newFiles,executor.map(reader,newFiles))}).T
        self.logMessage(f'Metadata extracted in : {time.time()-T1} s')
        metadata['fileName'] = metadata.index
        metadata['referenceFile'] = metadata['fileName']
        return(metadata)

    def groupFiles(self,newFileMetadata,groupKeys):
        #Concat with existing records
        fileSets = pd.concat([self.fileGroups,newFileMetadata],ignore_index=True)
        fileSets['startDate'] = pd.to_datetime(fileSets['startDate'])
        fileSets = fileSets.sort_values(by=['sourceID','startDate'])#,'traces'])
        # It only matters if these columns are duplicated
        duplicates = fileSets[groupKeys].duplicated().values
        # Name reference and configuration yaml
        fileSets['startDate'] = fileSets['startDate'].dt.strftime('%Y-%m-%dT%H:%M:%S%z')
        # Mask duplicates and ffill
        fileSets.loc[duplicates,['referenceFile','sourceID']] = np.nan
        fileSets[['referenceFile','sourceID']] = fileSets[['referenceFile','sourceID']].ffill()
        self.fileGroups = fileSets.groupby(['saveAs','sourceID']).first().reset_index()
        # Write groups that don't yet exist
        for _,row in self.fileGroups.iterrows():
            row = row.to_dict()
            row['traces'] = json.loads(row['traces'])
            if row['saveAs'] == 'ecf32':
                breakpoint()
                # self.ecf32Metadata(kwargs=row)
            fpath = f"{os.path.join(self.metaPath,row['saveAs'],row['sourceID'])}.yml"
            if not os.path.isfile(fpath):
                self.saveDict(row,fpath)
            else:
                self.logMessage(f"Not overwriting {fpath}")
                

@dataclass(kw_only=True)
class fileUpload(fileSet):

    def __post_init__(self):
        super().__post_init__()