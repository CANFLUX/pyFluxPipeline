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
class discoverFiles(sharedFields):
    siteID: str
    fileFormat: str
    fileName: str = None
    searchPath: str = None
    processFiles: bool = False
    useParalell: bool = True
    ignoreFiles: list = field(default_factory=list)
    findFiles: list = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.siteConfig = self.loadSiteConfiguration(self.siteID)
        self.metaPath = os.path.join(self.projectPath,'Sites',self.siteID)
        fileInventoryPath = os.path.join(self.metaPath,'.inventory','fileInventory.json')
        fileSetPath = os.path.join(self.metaPath,'.inventory','fileSets.json')
        if os.path.isfile(fileInventoryPath):
            self.fileInventory = self.loadDict(fileInventoryPath)
            self.fileSets = pd.DataFrame([self.loadDict(os.path.join(self.metaPath,k,f)+'.yml') for k,v in self.fileInventory.items() for f in v.keys()])
            self.fileSets['traces'] = [json.dumps(tr) for tr in self.fileSets['traces']]
            self.inList = [f for v in self.fileInventory.values() for f in v]
        else:
            os.makedirs(os.path.join(self.metaPath,'.inventory'),exist_ok=True)
            self.fileInventory = {}
            self.fileSets = pd.DataFrame()
            self.inList = []

        if self.searchPath is not None:
            self.updateInventory()
            for _,row in self.fileSets.iterrows():
                row = row.to_dict()
                # pop, format, and move to end
                traces = row.pop('traces')
                row['traces'] = json.loads(traces)
                self.saveDict(row,f"{os.path.join(self.metaPath,row['saveAs'],row['sourceID'])}.yml")
            self.saveDict(self.fileInventory,fileInventoryPath)

        if self.processFiles:
            self.formatIni()
            T1 = time.time()
            for sourceID,fileList in self.fileInventory['Database'].items():
                fileMetadata = self.loadDict(os.path.join(self.metaPath,'Database',f"{sourceID}.yml"))
                reader = partial(readRawFileData,fileFormat=self.fileFormat,fileMetadata=fileMetadata)
                if not self.useParalell:
                    dataTable = [reader(fileName=fileName) for fileName in fileList['fileName']]
                else:
                    with ProcessPoolExecutor() as executor:
                        dataTable = [table for table in executor.map(reader,fileList['fileName'])]
                processed = [True if t is not None else False for t in dataTable]
                dataTable = pd.concat(dataTable)
                self.uploadRawData(dataTable,self.siteID,os.path.join('raw',fileMetadata['sourceID']),fileMetadata['dataIntervalSeconds'])
                if len(processed)!=len(fileList['fileName']):
                    breakpoint()
                self.fileInventory['Database'][sourceID]['processed']=processed

            self.saveDict(self.fileInventory,fileInventoryPath)
            self.logMessage(f'Upload completed in : {time.time()-T1} s')
        

    def updateInventory(self):
        files = self.discovery()
        # Group by common configuration
        self.fileSets = files.groupby(['saveAs','sourceID']).first().reset_index()
        files['processed'] = False
        files = files[['sourceID','fileName','saveAs','processed','fileTimestamp']].groupby(['saveAs','sourceID']).agg(list).to_dict(orient='index')
        for key,value in files.items():
            if key[0] not in self.fileInventory:
                self.fileInventory[key[0]] = {}

            if key[1] not in self.fileInventory[key[0]]:
                self.fileInventory[key[0]][key[1]] = value
            else:
                self.fileInventory[key[0]][key[1]]['processed'] += [False for v in value['fileName'] if v not in self.fileInventory[key[0]][key[1]]['fileName']]
                self.fileInventory[key[0]][key[1]]['fileName'] += [v for v in value['fileName'] if v not in self.fileInventory[key[0]][key[1]]['fileName']]
                self.fileInventory[key[0]][key[1]]['fileTimestamp'] += [v for v in value['fileTimestamp'] if v not in self.fileInventory[key[0]][key[1]]['fileName']]
        
        
    def discovery(self):
        suffix = {'TOB3':'.dat'}
        fileList = [
            os.path.join(dir,file) for dir,_,files in os.walk(self.searchPath) 
            for file in files 
            if (file.endswith(suffix[self.fileFormat]) and os.path.join(self.searchPath,file) not in self.inList) and
            (len(self.findFiles) == 0 or any([fnmatch.fnmatch(file,fnd) for fnd in self.findFiles])) and
            (len(self.ignoreFiles) == 0 or not any([fnmatch.fnmatch(file,ign) for ign in self.ignoreFiles])) and
            len(files)]
        if len(fileList) == 0 and len(self.fileSets) == 0:
            exit('No Files discoverd')

        T1 = time.time()
        self.logMessage(f"Searching: {len(fileList)} files")
        get = partial(getRawFileMetadata,
                fileFormat=self.fileFormat,
                siteID=self.siteID,
                ignoreTraces=self.ignoreTraces)
        if not self.useParalell:
            files = pd.DataFrame({f:get(fileName=f) for f in fileList}).T
        else:
            with ProcessPoolExecutor() as executor:
                files = pd.DataFrame({f:out for f,out in zip(fileList,executor.map(get,fileList))}).T
        self.logMessage(f'Metadata extracted in : {time.time()-T1} s')

        # Remove unwated tables
        files = files.loc[((~files['tableName'].isin(self.ignoreFiles))&(files['fileFormat'].notna()))].copy()
        files['fileName'] = files.index
        files['referenceFile'] = files['fileName']
        files = pd.concat([self.fileSets,files],ignore_index=True)
        files['fileTimestamp'] = pd.to_datetime(files['fileTimestamp'])
        files = files.sort_values(by=['tableName','traces','fileTimestamp'])
        # It only matters if these columns are duplicated
        test = ['tableName','loggerModel','program','fileFormat','dataIntervalSeconds','traces','timezone']
        duplicates = files[test].duplicated().values
        # Name reference and configuration yaml
        files['fileTimestamp'] = files['fileTimestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S%z')
        # Mask duplicates and ffill
        files.loc[duplicates,['referenceFile','sourceID']] = np.nan
        files[['referenceFile','sourceID']] = files[['referenceFile','sourceID']].ffill()
        return(files)
        
    def formatIni(self):
        rawDatabase = self.siteConfig.ini['rawData']['Database']
        rawHighfrequency = self.siteConfig.ini['rawData']['ecf32']
        first = self.siteConfig.ini['Processing']['FirstStage']
        for _,file in self.fileSets.iterrows():
            if file['saveAs'] == 'Database' and file['sourceID'] not in rawDatabase:
                self.dateRange = [file['fileTimestamp'],None]
                inputDates = CommentedSeq(self.dateRange)
                inputDates.yaml_set_anchor(f'{file['sourceID']}.inputDates')
                rawDatabase[file['sourceID']] = inputDates
                if self.posixName not in first:
                    first[self.posixName] = firstStageTrace(
                        variableName=self.posixName,
                        inputFiles=f"{file['sourceID']}.{self.posixName}",
                        inputDates=inputDates,
                        dtype='int64',
                        units='s',
                        notes='default time-trace (seconds since unix epoch)').to_dict()
                else:
                    first[self.posixName]['inputFiles'][f"{file['sourceID']}.{self.posixName}"] = inputDates
                if type(file['traces']) is str:
                    file['traces'] = json.loads(file['traces'])
                for value in file['traces'].values():
                    inputFile = f"{file['sourceID']}.{value['variableName']}"
                    if value['ignore']:
                        continue
                    elif value['variableName'] not in first:
                        first[value['variableName']] = firstStageTrace.from_dict(
                            value|{
                                'inputFiles':inputFile,
                                'inputDates':inputDates
                                }).to_dict()
                    elif inputFile not in first[value['variableName']]['inputFiles']:
                        first[value['variableName']]['inputFiles'][inputFile] = inputDates
                    else:
                        print('Issue ????')
                        breakpoint()
            elif file['saveAs'] == 'ecf32' and file['sourceID'] not in rawHighfrequency:
                self.dateRange = [file['fileTimestamp'],None]
                inputDates = CommentedSeq(self.dateRange)
                inputDates.yaml_set_anchor(f'{file['sourceID']}.inputDates')
                rawHighfrequency[file['sourceID']] = inputDates
                
            elif file['saveAs'] is None:
                continue
            elif file['sourceID'] not in rawDatabase and file['sourceID'] not in rawHighfrequency:
                print('Issue ????')
        self.saveDict(self.siteConfig.ini,self.siteConfig.iniPath)

    def uploadDatabase(self):
        breakpoint()
        for fileConfigName,files in self.fileInventory['Database'].items():
            breakpoint()
            cfg = self.loadDict(os.path.join(self.metaPath,'Database',fileConfigName))
            for i, (file,processed) in enumerate(zip(files['fileName'],files['processed'])):
                print(file,cfg['fileFormat'],cfg['dataIntervalSeconds'],cfg['saveAs'])
                if cfg['saveAs'] == 'Database':
                    breakpoint()
                    tbx = processor[cfg['fileFormat']].from_dict(cfg|{'projectPath':self.projectPath,'fileName':file,'mode':'extractData'})
                    tbx.formatTable()
                    self.uploadRawData(tbx.dataTable,self.siteID,os.path.join('raw',cfg['sourceID']),cfg['dataIntervalSeconds'])
                    self.fileInventory['Database'][fileConfigName]['processed'][i]=True
                elif cfg['saveAs'] == 'ecf32':
                    print('not writing ecf32')
                    pass
                    # self.ecf32Write(tbx.dataTable,cfg['traces'],cfg['dataIntervalSeconds'],self.siteID,cfg['tableName'])

    def uploadHighFrequency(self):
        for fileConfigName, files in self.fileInventory['highfrequency'].items():
            fileConfig = self.loadDict(os.path.join(self.metaPath,'highfrequency',fileConfigName))
            # ghgMetadata.
            # kwargs = fileConfig | {'siteID':self.siteID,'projectPath':self.projectPath,'mode':'ecf32'}
            breakpoint()

            # processor

            # ecf = ecf32(
            #     projectPath=self.projectPath,
            #     siteID=self.siteID,
            #     sourceID=fileConfig['sourceID'],
            #     kwargs=self.siteConfig.to_dict()|fileConfig
            #     )
            # self.fileInventory['highfrequency'][fileConfigName]['processed'][i]=True

        #     basePath,metadata=ecf32Setup(self.highFrequencyPath,self.siteID,fileConfig['sourceID'],fileConfig['traces'],fileConfig['dataIntervalSeconds'])
        #     # breakpoint()
        #     writer = partial(mpTOB3,config=fileConfig,basePath=basePath,metadata=metadata)
        #     with ProcessPoolExecutor(max_workers=4) as executor:
        #         out = {filename:True for filename, result in
        #                         zip(files['fileName'],
        #                             executor.map(writer, files['fileName']))}
            
        #     breakpoint()
        

# def mpTOB3(fileName,config,basePath,metadata):
#     if config['fileType']:
#         out = TOB3.from_dict(config|{'fileName':fileName})
#         out.formatTable()
#         ecf32Write(out.dataTable,metadata,basePath)
    # else:
    #     return None

    # return(out.dataTable)