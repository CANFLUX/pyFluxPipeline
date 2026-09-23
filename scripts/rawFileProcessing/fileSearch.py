from scripts.rawFileProcessing.parseCSV import EddyProOutput, HOBOcsv, NARRcsv
from scripts.traceAnalysis.traceParameters import firstStageTrace
from scripts.database.database import database
from ruamel.yaml.comments import CommentedSeq
from scripts.ecf32.ecf32 import ecf32#ecf32Setup,ecf32Write
# from helperFunctions.baseClass import mdMap
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
class fileSearch(sharedFields):
    # siteID: str
    # fileFormat: str
    fileName: str = None
    searchPath: str = None
    # processFiles: bool = False
    ignoreFiles: list = field(default_factory=list)
    findFiles: list = field(default_factory=list)

    def __post_init__(self):
        
        super().__post_init__()
        # Read configuration and inventories
        # Files that are being tracked
        fileInventoryPath = os.path.join(self.metaPath,'.inventory','fileInventory.json')
        fileInventory = self.loadDict(fileInventoryPath,template={})
        # File metadata groups
        currentGroups = pd.DataFrame([self.loadDict(os.path.join(self.metaPath,k,f)+'.yml') for k,v in fileInventory.items() for f in v.keys()])
        if 'traces' in currentGroups.columns:
            currentGroups['traces'] = [json.dumps(tr) for tr in currentGroups['traces']]
            self.debug=True
        # Serarch for new files not in inventory
        existingFiles =  [file for format in fileInventory.values() for sourceSet in format.values() for file in sourceSet['fileName']]
        newFileMetadata,newFileInventory = self.search(existingFiles)
        if newFileInventory is not None:
            # Append the new Inventory to the current
            for (saveAs,sourceID),value in newFileInventory.items():
                fileInventory.setdefault(saveAs,{})
                fileInventory[saveAs].setdefault(sourceID,{key:[] for key in value.keys()})
                for key,val in value.items():
                    fileInventory[saveAs][sourceID][key] += val
            # Save updated inventory
            self.saveDict(fileInventory,fileInventoryPath)
        # Read metadata from new inventory, merge with existing groups, or create new ones where applicable
        fileSets = self.groupFiles(currentGroups,newFileMetadata,groupKeys=['tableName','loggerModel','program','fileFormat','dataIntervalSeconds','traces','timezone'])
        for i,row in fileSets.iterrows():
            row = row.to_dict()
            row['traces'] = json.loads(row['traces'])
            if row['saveAs'] == 'ecf32':
                breakpoint()
                # self.ecf32Metadata(kwargs=row)
            self.saveDict(row,f"{os.path.join(self.metaPath,row['saveAs'],row['sourceID'])}.yml")

    def search(self,existingFiles):
        # self.fileSets = pd.DataFrame([self.loadDict(os.path.join(self.metaPath,k,f)+'.yml') for k,v in self.fileInventory.items() for f in v.keys()])
        newFiles = [os.path.join(dir,file) for dir,_,files in os.walk(self.searchPath) 
                    for file in files if ((file.endswith(self.fileSuffix) and os.path.join(dir,file) not in existingFiles) and
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
            return(newFileMetadata.drop(columns=['Processed']),newFileInventory)
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
    #     # Remove unwanted tables
        # metadata = metadata.loc[((~metadata['tableName'].isin(self.ignoreFiles))&(metadata['fileFormat'].notna()))].copy()
        metadata['fileName'] = metadata.index
        metadata['referenceFile'] = metadata['fileName']
        return(metadata)

    def groupFiles(self,currentGroups,newFileMetadata,groupKeys):
        if self.debug:
            breakpoint()
        #Concat with existing records
        fileSets = pd.concat([currentGroups,newFileMetadata],ignore_index=True)
        fileSets['fileTimestamp'] = pd.to_datetime(fileSets['fileTimestamp'])
        self.logError('Update sort?')
        fileSets = fileSets.sort_values(by=['tableName','traces','fileTimestamp'])
        # It only matters if these columns are duplicated
        duplicates = fileSets[groupKeys].duplicated().values
        # Name reference and configuration yaml
        fileSets['fileTimestamp'] = fileSets['fileTimestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S%z')
        # Mask duplicates and ffill
        fileSets.loc[duplicates,['referenceFile','sourceID']] = np.nan
        fileSets[['referenceFile','sourceID']] = fileSets[['referenceFile','sourceID']].ffill()
        
        fileSets = fileSets.groupby(['saveAs','sourceID']).first().reset_index()
        return(fileSets)

