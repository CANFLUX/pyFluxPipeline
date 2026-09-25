from scripts.rawFileProcessing.parseCSV import EddyProOutput, HOBOcsv, NARRcsv
from scripts.database.database import database
# from scripts.ecf32.ecf32 import ecf32
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
        self.fileInventoryPath = os.path.join(self.metaPath,self.siteID,'.inventory','fileInventory.json')
        self.fileInventory = self.loadDict(self.fileInventoryPath,template={})
        self.fileGroups = pd.DataFrame([self.loadDict(os.path.join(self.metaPath,self.siteID,k,f)+'.yml') for k,v in self.fileInventory.items() for f in v.keys()])
        if 'traces' in self.fileGroups.columns:
            self.fileGroups['traces'] = [json.dumps(tr) for tr in self.fileGroups['traces']]
        self.siteConfig = self.loadSiteConfiguration(self.siteID)



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
            for (dataFormat,sourceID),value in newFileInventory.items():
                self.fileInventory.setdefault(dataFormat,{})
                self.fileInventory[dataFormat].setdefault(sourceID,{key:[] for key in value.keys()})
                for key,val in value.items():
                    self.fileInventory[dataFormat][sourceID][key] += val
        # Read metadata from new inventory, merge with existing groups, or create new ones where applicable
        self.groupFiles(newFileMetadata,groupKeys=['tableName','loggerModel','program','fileFormat','dataIntervalSeconds','traces','timezone'])
        # Put any new file metadata into a template ini file
        for _,fileGroup in self.fileGroups.loc[self.fileGroups['dataFormat'] == 'Database'].iterrows():
            # If new, update first stage ini, otherwise just update dates
            if fileGroup['sourceID'] not in self.siteConfig.ini['rawData']['Database'].keys():
                self.siteConfig.updateIni(sourceFile=fileGroup)
            else:
                self.siteConfig.updateRawSouces(fileGroup['dataFormat'],fileGroup['sourceID'],fileGroup['startDate'],fileGroup['stopDate'])
        for _,fileGroup in self.fileGroups.loc[self.fileGroups['dataFormat'] == 'ecf32'].iterrows():
            # if fileGroup['sourceID'] not in self.siteConfig.ini['rawData']['ecf32'].keys():
            self.siteConfig.updateRawSouces(fileGroup['dataFormat'],fileGroup['sourceID'],fileGroup['startDate'],fileGroup['stopDate'])
            
        # # Iterate through groups, creaet metadata file for each sensor orientation that exits
        # for group in sensorHistory.loc[((sensorHistory.index>=kwargs['startDate'])&(sensorHistory.index<=kwargs['stopDate'])),'sensorGroup'].unique():
            startDate = self.siteConfig.sensorHistory.index>=fileGroup['startDate']
            stopDate = self.siteConfig.sensorHistory.index<=(fileGroup['stopDate'] or self.siteConfig.sensorHistory.index.max())
            ecGroups = self.siteConfig.sensorHistory.loc[startDate & stopDate,'EC'].unique()
            for sg in ecGroups:
                ghgMetadata_group = self.siteConfig.ecGroups.loc[sg]
                ghgMetadata_group = {
                    section:{key:value for key,value in ghgMetadata_group[section].to_dict().items()}
                    for section in ghgMetadata_group.index.get_level_values(0).unique()\
                        }
                ghg = ghgMetadata.from_dict(ghgMetadata_group)
                ghg.setFileDescription(fileGroup['traces'])
                ghg.writeFiles()
        # Save updated inventory
        self.saveDict(self.fileInventory,self.fileInventoryPath)

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
            newFileInventory = newFileMetadata[['dataFormat','sourceID','fileName','Processed','fileTimestamp']].groupby(['dataFormat','sourceID']).agg(list).to_dict(orient='index')
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
        return(metadata)

    def groupFiles(self,newFileMetadata,groupKeys):
        #Concat with existing records
        self.fileGroups['referenceFile'] = 1
        newFileMetadata['referenceFile'] = 0
        fileSets = pd.concat([self.fileGroups,newFileMetadata],ignore_index=True)
        fileSets['startDate'] = pd.to_datetime(fileSets['startDate'])
        fileSets = fileSets.sort_values(by=['sourceID','startDate'])#
        # It only matters if these columns are duplicated
        duplicates = fileSets[groupKeys].duplicated(keep=False).values
        # Any duplicates that don't yet have a sourceID, arbitrarily select the first occurence as the reff
        grouplicates = fileSets[groupKeys+['referenceFile','sourceID']].groupby(groupKeys).agg(list).reset_index()
        grouplicates['referenceFile'] = grouplicates['referenceFile'].apply(sum)
        for i,row in grouplicates.loc[grouplicates['referenceFile']==0].iterrows():
            fileSets.loc[fileSets['sourceID']==row['sourceID'][0],'referenceFile']=1
        referenceFile = fileSets.pop('referenceFile')
        # Name reference and configuration yaml
        fileSets['startDate'] = fileSets['startDate'].map(lambda x: x.isoformat())
        # Mask duplicates and ffill
        sourceID_pre_group = fileSets[['dataFormat','sourceID']].copy()
        fileSets.loc[((duplicates)&(referenceFile==False)),['sourceID']] = np.nan
        fileSets[['sourceID']] = fileSets[['sourceID']].ffill().bfill()
        sourceID_pre_group.index = fileSets['sourceID'].values
        for key,value in sourceID_pre_group.iterrows():
            if key != value['sourceID']:
                vx = self.fileInventory[value['dataFormat']].pop(value['sourceID'])
                for k,v in vx.items():
                    self.fileInventory[value['dataFormat']][key][k]+=v
        self.fileGroups = fileSets.groupby(['dataFormat','sourceID']).first().reset_index()
        self.fileGroups['traces'] = [json.loads(tr) for tr in self.fileGroups['traces']]
        # Write groups that don't yet exist
        for _,row in self.fileGroups.iterrows():
            row = row.to_dict()
            fpath = f"{os.path.join(self.metaPath,self.siteID,row['dataFormat'],row['sourceID'])}.yml"
            if not os.path.isfile(fpath):
                self.saveDict(row,fpath)
            else:
                self.logMessage(f"Not overwriting {fpath}")
                

@dataclass(kw_only=True)
class fileUpload(fileSet):

    def __post_init__(self):
        super().__post_init__()