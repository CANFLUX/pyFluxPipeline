from scripts.ecf32.ghgMetadata import ghgMetadataWriter,eddyproProjectWriter
from scripts.rawFileProcessing.processor import getRawFileMetadata
from scripts.rawFileProcessing.sharedMethods import sharedMethods
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from functools import partial
from datetime import datetime
import pandas as pd
import numpy as np
import fnmatch
import json
import time
import os



@dataclass(kw_only=True)
class fileSet(sharedMethods):
    dateStart: datetime = field(default=None)
    dateStop: datetime = field(default=None)
    ignoreTraces: list = field(default_factory=list)
    renameTraces: dict = field(default_factory=dict)
    variableInstrumentMap: dict = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        # Read configuration and inventories
        # Files that are being tracked
        # File metadata groups
        # self.fileInventoryPath = os.path.join(self.metaPath,self.siteID,'.inventory','fileInventory.json')
        # self.fileInventory = self.loadDict(self.fileInventoryPath,template={})
        inventoryPath = [
            os.path.join(self.metaPath,self.siteID,fq,'.fileInventory.csv')
            for fq in ['Database','highFrequency'] if os.path.isfile(os.path.join(self.metaPath,self.siteID,fq,'.fileInventory.csv'))
                         ]
        if len(inventoryPath) == 0:
            self.fileInventory = pd.DataFrame(columns=['dataFrequency','sourceID','fileName','Processed','fileTimestamp']).set_index(['dataFrequency','sourceID'])
        else:
            self.fileInventory = pd.concat([
                pd.read_csv(inv,parse_dates=['fileTimestamp'],index_col=[0,1])
                for inv in inventoryPath
            ])
        self.fileGroups = pd.DataFrame([self.loadDict(os.path.join(self.metaPath,self.siteID,k[0],k[1])+'.yml') for k in self.fileInventory.index])
        if 'traces' in self.fileGroups.columns:
            self.fileGroups['traces'] = [json.dumps(tr) for tr in self.fileGroups['traces']]
        self.siteConfig = self.loadSiteMetadata(self.siteID)
        for key in self.siteConfig.instrumentation.keys():
            for value in self.siteConfig.instrumentation[key].values():
                c1 = (self.dateStart is not None and value.dateStart <= self.dateStart) 
                c2 = c1 and (value.dateStop is None or (value.dateStop is not None and value.dateStop>self.dateStart))
                c3 = c2 and (self.dateStop is None or value.dateStop is None or (self.dateStop is not None and value.dateStop is not None and self.dateStop<=value.dateStop))
                if c3:
                    self.variableInstrumentMap.setdefault(value.instrumentID,[])

    def loadNewDatabaseFiles(self):
        dbx = self.fileInventory.loc[self.fileInventory.index.get_level_values('dataFrequency') == 'Database'].copy()
        breakpoint()
        # pd.DataFrame.from_dict(self.fileInventory['Database'][sourceID],orient=)

@dataclass(kw_only=True)
class fileSearch(fileSet):
    searchPath: str
    ignoreFiles: list = field(default_factory=list)
    findFiles: list = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        
        # existingFiles =  [file for format in self.fileInventory.values() for sourceSet in format.values() for file in sourceSet['fileName']]
        newFileMetadata,newFileInventory = self.search()
        self.fileInventory = pd.concat([self.fileInventory,newFileInventory])
        # if newFileInventory is not None:
        #     # Append the new Inventory to the current
        #     for (dataFrequency,sourceID),value in newFileInventory.items():
        #         self.fileInventory.setdefault(dataFrequency,{})
        #         self.fileInventory[dataFrequency].setdefault(sourceID,{key:[] for key in value.keys()})
        #         for key,val in value.items():
        #             self.fileInventory[dataFrequency][sourceID][key] += val
        # Read metadata from new inventory, merge with existing groups, or create new ones where applicable
        self.groupFiles(newFileMetadata,groupKeys=['loggerModel','fileFormat','dataIntervalSeconds','traces','timezone'])
        # Put any new file metadata into a template ini file
        for _,fileGroup in self.fileGroups.loc[self.fileGroups['dataFrequency'] == 'Database'].iterrows():
            # If new, update first stage ini, otherwise just update dates
            if fileGroup['sourceID'] not in self.siteConfig.ini['rawData']['Database'].keys():
                self.siteConfig.updateIni(sourceFile=fileGroup)
            else:
                self.siteConfig.updateRawSouces(fileGroup['dataFrequency'],fileGroup['sourceID'],fileGroup['dateStart'],fileGroup['dateStop'])
        for _,fileGroup in self.fileGroups.loc[self.fileGroups['dataFrequency'] == 'highFrequency'].iterrows():
            # if fileGroup['sourceID'] not in self.siteConfig.ini['rawData']['ecf32'].keys():
            self.siteConfig.updateRawSouces(fileGroup['dataFrequency'],fileGroup['sourceID'],fileGroup['dateStart'],fileGroup['dateStop'])
            
        # # Iterate through groups, creaet metadata file for each sensor orientation that exits
        # for group in sensorHistory.loc[((sensorHistory.index>=kwargs['dateStart'])&(sensorHistory.index<=kwargs['dateStop'])),'sensorGroup'].unique():
            dateStart = self.siteConfig.sensorHistory.index>=fileGroup['dateStart']
            dateStop = self.siteConfig.sensorHistory.index<=(fileGroup['dateStop'] or self.siteConfig.sensorHistory.index.max())
            ecGroups = self.siteConfig.sensorHistory.loc[dateStart & dateStop,'EC'].unique()
            for sg in ecGroups:
                ghgMetadata_group = self.siteConfig.ecGroups.loc[sg]
                ghgMetadata_group = {
                    section:{key:value for key,value in ghgMetadata_group[section].to_dict().items()}
                    for section in ghgMetadata_group.index.get_level_values(0).unique()\
                        }
                ghg = ghgMetadataWriter.from_dict(ghgMetadata_group)
                ghg.setFileDescription(fileGroup['traces'])
                fname=f"{fileGroup['sourceID']}~{sg}"
                fpath = f"{os.path.join(self.metaPath,self.siteID,fileGroup['dataFrequency'],fileGroup['sourceID'])}.metadata"
                ghg.writeFiles(fpath)
                ep = eddyproProjectWriter()
                ep.setDates(fileGroup['dateStart'],fileGroup['dateStop'])
                ep.fill(ghg)
                # .writeFile(ghg,filepath=fpath.replace('.metadata','.eddypro'))
        # Save updated inventory
        for fq in ['Database','highFrequency']:
            sel = self.fileInventory.loc[self.fileInventory.index.get_level_values('dataFrequency')==fq].copy()
            if len(sel):
                out = os.path.join(self.metaPath,self.siteID,fq)
                if not os.path.isdir(out):
                    os.makedirs(out)
                sel.to_csv(os.path.join(out,'.fileInventory.csv'))
            # self.saveDict(self.fileInventory.loc[self.fileInventory['dataFrequency']==df],os.path.join(self.metaPath,self.siteID,df,'.fileInventory.csv'))
        # self.saveDict(self.fileInventory,self.fileInventoryPath)
        # dbI = pd.concat([pd.DataFrame(self.fileInventory['Database'][sourceID]) for sourceID in self.fileInventory['Database'].keys()])
        # pd.DataFrame.from_dict(data={},orient=)
        
        
    def search(self):
        newFiles = [os.path.join(dir,file) for dir,_,files in os.walk(self.searchPath) 
                    for file in files if ((file.endswith(self.fileExtension) and os.path.join(dir,file) not in self.fileInventory['fileName'].values) and
                        (len(self.findFiles) == 0 or any([fnmatch.fnmatch(file,fnd) for fnd in self.findFiles])) and
                        (len(self.ignoreFiles) == 0 or not any([fnmatch.fnmatch(file,ign) for ign in self.ignoreFiles])) and
                        len(files))]
        if len(newFiles):
            newFileMetadata = self.getMetadata(newFiles)
            newFileMetadata['Processed'] = False
            newFileMetadata['fileTimestamp'] = newFileMetadata['fileTimestamp'].map(lambda x: x.isoformat())
            
            # newFileInventory = newFileMetadata[['dataFrequency','sourceID','fileName','Processed','fileTimestamp']].groupby(['dataFrequency','sourceID']).agg(list).to_dict(orient='index')
            newFileInventory = newFileMetadata[['dataFrequency','sourceID','fileName','Processed','fileTimestamp']].set_index(['dataFrequency','sourceID'])
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
                # timezone=self.timezone,
                ignoreTraces=self.ignoreTraces,
                renameTraces=self.renameTraces
                )
        if not self.useParallel:
            metadata = pd.DataFrame({f:reader(fileName=f).read() for f in newFiles}).T
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
        fileSets['dateStart'] = pd.to_datetime(fileSets['dateStart'])
        fileSets = fileSets.sort_values(by=['sourceID','dateStart'])#
        # It only matters if these columns are duplicated
        duplicates = fileSets[groupKeys].duplicated(keep=False).values
        # Any duplicates that don't yet have a sourceID, arbitrarily select the first occurence as the reff
        grouplicates = fileSets[groupKeys+['referenceFile','sourceID']].groupby(groupKeys).agg(list).reset_index()
        grouplicates['referenceFile'] = grouplicates['referenceFile'].apply(sum)
        for i,row in grouplicates.loc[grouplicates['referenceFile']==0].iterrows():
            fileSets.loc[fileSets['sourceID']==row['sourceID'][0],'referenceFile']=1
        referenceFile = fileSets.pop('referenceFile')
        # Name reference and configuration yaml
        fileSets['dateStart'] = fileSets['dateStart'].map(lambda x: x.isoformat())
        # Mask duplicates and ffill
        sourceID_pre_group = fileSets[['dataFrequency','sourceID']].rename(columns={'sourceID':'sourceID_pre_group'})
        fileSets.loc[((duplicates)&(referenceFile==False)),['sourceID']] = np.nan
        fileSets[['sourceID']] = fileSets[['sourceID']].ffill().bfill()
        sourceID_pre_group['sourceID'] = fileSets['sourceID'].copy()
        sourceID_pre_group = sourceID_pre_group.set_index(['dataFrequency','sourceID'])
        self.fileInventory = self.fileInventory.reset_index()
        for key,value in sourceID_pre_group.iterrows():
            if key[1] != value['sourceID_pre_group']:
                self.fileInventory.loc[((self.fileInventory['dataFrequency']==key[0]) & (self.fileInventory['sourceID']==value['sourceID_pre_group'])),'sourceID'] = key[1]
        self.fileInventory = self.fileInventory.set_index(['dataFrequency','sourceID'])
        self.fileGroups = fileSets.groupby(['dataFrequency','sourceID']).first().reset_index()
        self.fileGroups['traces'] = [json.loads(tr) for tr in self.fileGroups['traces']]
        # Write groups that don't yet exist
        for _,row in self.fileGroups.iterrows():
            row = row.to_dict()
            # row = self.autoLinkInstruments(row)
            fpath = f"{os.path.join(self.metaPath,self.siteID,row['dataFrequency'],row['sourceID'])}.yml"
            if not os.path.isfile(fpath):
                self.saveDict(row,fpath)
            else:
                self.logMessage(f"Not overwriting {fpath}")


# import yaml

# with open(r'C:\Users\User\GSC_Work\pyFluxPipeline\configurationFiles\rawFileSettings\Flux_CSFormat.yml') as f:
#     test = yaml.safe_load(f)

# fS = fileSearch(useParallel=False,projectPath = 'testing/myProject',siteID='SEEP',searchPath=r'C:\data-dump\RDEC1\2026\20260614',**test)#,variableInstrumentMap={'irgason_1':['Ux','Uy','Uz','T_SONIC']})
# #     dateStart='2025-06-11T00:00:00+00:00',
# #     dateStop='2025-08-05T00:00:00+00:00')




# @dataclass(kw_only=True)
# class fileSearchie(fileSet):
#     searchPath: str = None
#     ignoreFiles: list = field(default_factory=list)
#     findFiles: list = field(default_factory=list)

#     def __post_init__(self):
#         super().__post_init__()
#         # Serarch for new files not in inventory
#         existingFiles =  [file for format in self.fileInventory.values() for sourceSet in format.values() for file in sourceSet['fileName']]
#         newFileMetadata,newFileInventory = self.search(existingFiles)
#         if newFileInventory is not None:
#             # Append the new Inventory to the current
#             for (dataFormat,sourceID),value in newFileInventory.items():
#                 # print(dataFormat)
#                 # self.fileInventory.setdefault(dataFormat,{})
#                 # self.fileInventory[dataFormat]
#                 self.fileInventory.setdefault(sourceID,{key:[] for key in value.keys()})
#                 for key,val in value.items():
#                     self.fileInventory[sourceID][key] += val
#         # Read metadata from new inventory, merge with existing groups, or create new ones where applicable
#         self.groupFiles(newFileMetadata,groupKeys=['tableName','loggerModel','program','fileFormat','dataIntervalSeconds','traces','timezone'])
#         # Put any new file metadata into a template ini file
#         for _,fileGroup in self.fileGroups.loc[self.fileGroups['dataFormat'] == 'Database'].iterrows():
#             # If new, update first stage ini, otherwise just update dates
#             if fileGroup['sourceID'] not in self.siteConfig.ini['rawData']['Database'].keys():
#                 self.siteConfig.updateIni(sourceFile=fileGroup)
#             else:
#                 self.siteConfig.updateRawSouces(fileGroup['dataFormat'],fileGroup['sourceID'],fileGroup['dateStart'],fileGroup['dateStop'])
#         for _,fileGroup in self.fileGroups.loc[self.fileGroups['dataFormat'] == 'ecf32'].iterrows():
#             # if fileGroup['sourceID'] not in self.siteConfig.ini['rawData']['ecf32'].keys():
#             self.siteConfig.updateRawSouces(fileGroup['dataFormat'],fileGroup['sourceID'],fileGroup['dateStart'],fileGroup['dateStop'])
            
#         # # Iterate through groups, creaet metadata file for each sensor orientation that exits
#         # for group in sensorHistory.loc[((sensorHistory.index>=kwargs['dateStart'])&(sensorHistory.index<=kwargs['dateStop'])),'sensorGroup'].unique():
#             dateStart = self.siteConfig.sensorHistory.index>=fileGroup['dateStart']
#             dateStop = self.siteConfig.sensorHistory.index<=(fileGroup['dateStop'] or self.siteConfig.sensorHistory.index.max())
#             ecGroups = self.siteConfig.sensorHistory.loc[dateStart & dateStop,'EC'].unique()
#             for sg in ecGroups:
#                 ghgMetadata_group = self.siteConfig.ecGroups.loc[sg]
#                 ghgMetadata_group = {
#                     section:{key:value for key,value in ghgMetadata_group[section].to_dict().items()}
#                     for section in ghgMetadata_group.index.get_level_values(0).unique()\
#                         }
#                 ghg = ghgMetadataWriter.from_dict(ghgMetadata_group)
#                 ghg.setFileDescription(fileGroup['traces'])
#                 fname=f"{fileGroup['sourceID']}~{sg}"
#                 fpath = f"{os.path.join(self.metaPath,self.siteID,fileGroup['dataFormat'],fileGroup['sourceID'])}.metadata"
#                 ghg.writeFiles(fpath)
#                 ep = eddyproProjectWriter()
#                 ep.setDates(fileGroup['dateStart'],fileGroup['dateStop'])
#                 ep.fill(ghg)
#                 # .writeFile(ghg,filepath=fpath.replace('.metadata','.eddypro'))
#         # Save updated inventory
#         self.saveDict(self.fileInventory,self.fileInventoryPath)

#     def search(self,existingFiles):
#         newFiles = [os.path.join(dir,file) for dir,_,files in os.walk(self.searchPath) 
#                     for file in files if ((file.endswith(self.fileExtension) and os.path.join(dir,file) not in existingFiles) and
#                         (len(self.findFiles) == 0 or any([fnmatch.fnmatch(file,fnd) for fnd in self.findFiles])) and
#                         (len(self.ignoreFiles) == 0 or not any([fnmatch.fnmatch(file,ign) for ign in self.ignoreFiles])) and
#                         len(files))]
#         if len(newFiles):
#             newFileMetadata = self.getMetadata(newFiles)
#             newFileMetadata['Processed'] = False
#             newFileMetadata['fileTimestamp'] = newFileMetadata['fileTimestamp'].map(lambda x: x.isoformat())
#             if self.sourceID is not None:
#                 newFileMetadata['sourceID'] = self.sourceID
#             newFileInventory = newFileMetadata[['dataFormat','sourceID','fileName','Processed','fileTimestamp']].groupby(['dataFormat','sourceID']).agg(list).to_dict(orient='index')
#             return(newFileMetadata.drop(columns=['Processed','fileName','fileTimestamp']),newFileInventory)
#         else:
#             return(pd.DataFrame(),None)

#     def getMetadata(self,newFiles):
#         T1 = time.time()
#         self.logMessage(f"Searching: {len(newFiles)} files")
#         reader = partial(getRawFileMetadata,
#                 projectPath=self.projectPath,
#                 fileFormat=self.fileFormat,
#                 siteID=self.siteID,
#                 # timezone=self.timezone,
#                 ignoreTraces=self.ignoreTraces)
#         if not self.useParallel:
#             metadata = pd.DataFrame({f:reader(fileName=f) for f in newFiles}).T
#         else:
#             with ProcessPoolExecutor() as executor:
#                 metadata = pd.DataFrame({f:out for f,out in zip(newFiles,executor.map(reader,newFiles))}).T
#         self.logMessage(f'Metadata extracted in : {time.time()-T1} s')
#         metadata['fileName'] = metadata.index
#         return(metadata)


#     def autoLinkInstruments(self,row):
#         # vInst = pd.DataFrame({key:pd.Series(value) for key,value in variableInstrumentMap.items()})
#         # temp = self.siteConfig.instrumentHistory[self.siteConfig.instrumentHistory.index==pd.to_datetime(row['dateStart']).ceil('30min')].iloc[0]
#         # instruments = pd.Series(
#         #     {value:self.siteConfig.instrumentation[key][value].sensorType 
#         #     for key,values in temp.items() for value in values.split('-')},
#         #     name='sensorType')
#         # for key,trace in row['traces'].items():
#         #     vN = trace['variableName']
#         #     if trace['instrumentID'] is None:
#         #         if vN in vInst.columns:
#         #             # assign all to first occurrence, leave to user to correct
#         #             row['traces'][key]['instrumentID'] = list(instruments[instruments.isin(vInst[vN])].index)#.index[0]
#         #         # except:

#         #         # elif vN.endswith('*') and any(vInst.columns.str.startswith(vN[:-1])):
#         #         else:
#         #             mtch = [v for v in vInst.columns[vInst.columns.str.endswith('*')] if vN.startswith(v[:-1])]
#         #             if len(mtch):

#         # return row

# @dataclass(kw_only=True)
# class fileUpload(fileSet):

#     def __post_init__(self):
#         super().__post_init__()