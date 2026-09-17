from scripts.rawFileProcessing.parseCSV import EddyProOutput, HOBOcsv, NARRcsv
from scripts.traceAnalysis.traceParameters import firstStageTrace
from scripts.rawFileProcessing.parseCSI import TOB3, TOA5, MixedArray
from scripts.database.database import database
from ruamel.yaml.comments import CommentedSeq
from scripts.ecf32.ecf32 import ecf32#ecf32Setup,ecf32Write
# from helperFunctions.baseClass import mdMap
from scripts.rawFileProcessing.sharedFields import sharedFields
from scripts.ecf32.ghgMetadata import ghgMetadata
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import json
import os

processor = {
    'TOB3':TOB3
}

@dataclass(kw_only=True)
class discoverFiles(sharedFields):
    siteID: str
    fileFormat: str
    fileName: str = None
    searchPath: str = None
    processFiles: bool = False
    ignoreFiles: list = field(default_factory=list)
    findFiles: list = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.siteConfig = self.loadSiteConfiguration(self.siteID)
        self.metaPath = os.path.join(self.projectPath,'Sites',self.siteID)
        fileInventoryPath = os.path.join(self.metaPath,'.inventory','fileInventory.json')
        fileSetPath = os.path.join(self.metaPath,'.inventory','fileSets.json')
        if os.path.isfile(fileInventoryPath):
            self.inventory = self.loadDict(fileInventoryPath)
            self.fileSets = pd.read_json(fileSetPath)
            self.fileSets['traces'] = [json.dumps(tr) for tr in self.fileSets['traces']]
            self.inList = [f for v in self.inventory.values() for f in v]
        else:
            os.makedirs(os.path.join(self.metaPath,'.inventory'),exist_ok=True)
            self.inventory = {}
            self.fileSets = pd.DataFrame()
            self.inList = []

        if self.searchPath is not None:
            self.updateInventory()
            for configFile,row in self.fileSets.iterrows():
                configFile = os.path.sep.join(configFile)
                row = row.to_dict()
                row['traces'] = json.loads(row['traces'])
                breakpoint()
                self.saveDict(row,os.path.join(self.metaPath,configFile))
            with open(fileInventoryPath,'w+') as fout:
                json.dump(self.inventory,fout)
            self.fileSets['traces'] = [json.loads(tr) for tr in self.fileSets['traces']]
            self.fileSets.to_json(fileSetPath)
        
        if self.processFiles:
            self.formatIni()
            if 'Database' in self.inventory and len(self.inventory['Database']):
                self.uploadDatabase()
            if 'highfrequency' in self.inventory and len(self.inventory['highfrequency']):
                self.uploadHighFrequency()

    def updateInventory(self):
        files = self.discovery()
        # Group by common configuration
        self.fileSets = files.groupby(['outputFormat','configFile']).first()
        files['processed'] = False
        files = files[['configFile','fileName','outputFormat','processed','fileTimestamp']].groupby(['outputFormat','configFile']).agg(list).to_dict(orient='index')
        for key,value in files.items():
            if key[0] not in self.inventory:
                self.inventory[key[0]] = {}

            if key[1] not in self.inventory[key[0]]:
                self.inventory[key[0]][key[1]] = value
            else:
                self.inventory[key[0]][key[1]]['processed'] += [False for v in value['fileName'] if v not in self.inventory[key[0]][key[1]]['processed']]
                self.inventory[key[0]][key[1]]['fileName'] += [v for v in value['fileName'] if v not in self.inventory[key[0]][key[1]]['fileName']]
                self.inventory[key[0]][key[1]]['fileTimestamp'] += [v for v in value['fileTimestamp'] if v not in self.inventory[key[0]][key[1]]['fileName']]
        
        
    def discovery(self):
        suffix = {'TOB3':'.dat'}
        fileList = [os.path.join(dir,file) for dir,_,files in os.walk(self.searchPath) for file in files if file.endswith(suffix[self.fileFormat]) and os.path.join(self.searchPath,file) not in self.inList and len(files)]
        files = pd.DataFrame({f:self.getMetadata(f) for f in fileList}).T
        # Remove unwated tables
        files = files.loc[((~files['tableName'].isin(self.ignoreFiles))&(files['fileFormat'].notna()))].copy()
        if len(self.ignoreFiles):
            # Remove unwated tables
            files = files.loc[~files['tableName'].isin(self.ignoreFiles)].copy()
        elif len(self.findFiles):
            # Or only keep wated tables
            files = files.loc[files['tableName'].isin(self.findFiles)].copy()

        files['fileName'] = files.index
        files['referenceFile'] = files['fileName']
        files = pd.concat([self.fileSets,files])
        files['fileTimestamp'] = pd.to_datetime(files['fileTimestamp'])
        files = files.sort_values(by=['tableName','traces','fileTimestamp'])
        # It only matters if these columns are duplicated
        test = ['tableName','loggerModel','program','fileFormat','dataIntervalSeconds','traces','timezone']
        duplicates = files[test].duplicated().values
        # Name reference and configuration yaml
        files['fileTimestamp'] = files['fileTimestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S%z')
        files['configFile'] = files['sourceID']+'.yml'
        # Mask duplicates and ffill
        files.loc[duplicates,['referenceFile','configFile']] = np.nan
        files[['referenceFile','configFile']] = files[['referenceFile','configFile']].ffill()
        return(files)
    
    def getMetadata(self,fpath):
        if self.fileFormat in processor.keys():
            out = processor[self.fileFormat](
                siteID=self.siteID,
                fileName=fpath,
                projectPath=None,
                ignoreTraces=self.ignoreTraces,
                renameTraces=self.renameTraces
                )
        else:
            print(self.fileFormat)
        out = out.to_dict()
        if out['dataIntervalSeconds'] is None or out['dataIntervalSeconds'] <= 0:
            out['saveAs'] = None
        elif out['dataIntervalSeconds']<60:
            out['saveAs'] = 'ecf32'
        out['traces'] = json.dumps(out['traces'])
        return(out)
    
    def formatIni(self):
        rawDatabase = self.siteConfig.ini['rawData']['Database']
        rawHighfrequency = self.siteConfig.ini['rawData']['highfrequency']
        first = self.siteConfig.ini['Processing']['FirstStage']

        for i,file in self.fileSets.iterrows():
            if file['sourceID'] not in rawData and file['saveAs'] is not None:

            self.logMessage('Do thisss?')
        # for i,file in self.fileSets.loc[self.fileSets['dataIntervalSeconds']<1].iterrows():
        #     self.dateRange = [file['fileTimestamp'],None]
        #     inputDates = CommentedSeq(self.dateRange)
        #     inputDates.yaml_set_anchor(f'{file['sourceID']}.inputDates')
        #     rawHighfrequency[file['sourceID']] = inputDates

        # for i,file in self.fileSets.loc[self.fileSets['dataIntervalSeconds']>=1].iterrows():
        #     if file['sourceID'] not in rawDatabase:

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
                for value in json.loads(file['traces']).values():
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
                        print('????')
                        breakpoint()

            # self.saveConfigFile(self.fileConfigPath)
        self.saveDict(self.siteConfig.ini,self.siteConfig.iniPath)

    def uploadDatabase(self):
        for fileConfigName,files in self.inventory['Database'].items():
            cfg = self.loadDict(os.path.join(self.metaPath,'Database',fileConfigName))
            for i, (file,processed) in enumerate(zip(files['fileName'],files['processed'])):
                print(file,cfg['fileFormat'],cfg['dataIntervalSeconds'],cfg['saveAs'])
                if cfg['saveAs'] == 'dbBinary':
                    tbx = TOB3.from_dict(cfg|{'projectPath':self.projectPath,'fileName':file,'mode':'extractData'})
                    tbx.formatTable()
                    print(tbx.dataTable)
                    self.uploadRawData(tbx.dataTable,self.siteID,os.path.join('raw',cfg['sourceID']),cfg['dataIntervalSeconds'])
                    self.inventory['Database'][fileConfigName]['processed'][i]=True
                elif cfg['saveAs'] == 'ecf32':
                    print('not writing ecf32')
                    pass
                    # self.ecf32Write(tbx.dataTable,cfg['traces'],cfg['dataIntervalSeconds'],self.siteID,cfg['tableName'])

    def uploadHighFrequency(self):
        for fileConfigName, files in self.inventory['highfrequency'].items():
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
            # self.inventory['highfrequency'][fileConfigName]['processed'][i]=True

        #     basePath,metadata=ecf32Setup(self.highFrequencyPath,self.siteID,fileConfig['sourceID'],fileConfig['traces'],fileConfig['dataIntervalSeconds'])
        #     # breakpoint()
        #     writer = partial(mpTOB3,config=fileConfig,basePath=basePath,metadata=metadata)
        #     with ProcessPoolExecutor(max_workers=4) as executor:
        #         out = {filename:True for filename, result in
        #                         zip(files['fileName'],
        #                             executor.map(writer, files['fileName']))}
            
        #     breakpoint()
        

def mpTOB3(fileName,config,basePath,metadata):
    if config['fileType']:
        out = TOB3.from_dict(config|{'fileName':fileName})
        out.formatTable()
        ecf32Write(out.dataTable,metadata,basePath)
    # else:
    #     return None

    # return(out.dataTable)