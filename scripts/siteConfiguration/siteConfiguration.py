from helperFunctions.baseClass import spatialObject,baseDataClass
from scripts.traceAnalysis.traceParameters import firstStageTrace
from scripts.siteConfiguration.hardware import hardwareModels
from ruamel.yaml.scalarstring import LiteralScalarString
from scripts.ecf32.ghgMetadata import ghgMetadataWriter
from helperFunctions.baseClass import fromYamlDefault
from scripts.defaultSettings import defaultSettings
from scripts.defaultSettings import configPath
from ruamel.yaml.comments import CommentedSeq
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo
import pandas as pd
import os
@dataclass(kw_only=True)
class configMetadata:
    AmerifluxID: str = None
    lat: float = None
    long: float = None
    siteID: str = None
    startYear: int = None
    stopYear: int = None
    timezone: str = None

rawDefault = {
    'preEvaluate':LiteralScalarString(
'''# Codespace for preEvaluate corrections
# unit conversions and corrections (e.g Convert F to C)
# rawData["sourceID.TA"]=(rawData["sourceID.TA"]-32)*5/9'''
         ),
    'Database':{},
    'ecf32':{}}

@dataclass(kw_only=True)
class configTemplate:
    Metadata: dict = None
    rawData: dict = field(default_factory=lambda:rawDefault)
    Processing: dict = field(default_factory=lambda:{'FirstStage':{},'SecondStage':{},'ThirdStage':{}})
    def __post_init__(self):
        # if isinstance(self.Metadata,str):
        self.Metadata = configMetadata(**self.Metadata).__dict__

siteConfiguration = fromYamlDefault(
    os.path.join(configPath,'siteTemplates','siteConfiguration.yml'),
)

@dataclass(kw_only=True)
class siteMetadata(baseDataClass,siteConfiguration,defaultSettings):
    projectPath: str = field(repr=False)
    lat_lon: spatialObject
    saveUpdates: bool = field(default=True,repr=False)

    def __post_init__(self):
        super().__post_init__()
        self.metaPath = os.path.join(self.projectPath,'Sites')
        self.fileName = os.path.join(self.metaPath,self.siteID,"siteMetadata.yml")
        self.iniPath = os.path.join(self.projectPath,'Database','Calculation_Procedures','TraceAnalysis_ini',f"{self.siteID}_config.yml")
        if self.saveUpdates or not os.path.isfile(self.fileName):
            self.validateSensors()
        else:            
            self.ecGroups = pd.read_csv(os.path.join(self.metaPath,self.siteID,"ecInstrumentGroups.csv"),header=[0,1],index_col=[0])
            self.sensorHistory = pd.read_csv(os.path.join(self.metaPath,self.siteID,"instrumentHistory.csv"),index_col=[0])
            self.sensorHistory.index = pd.to_datetime(self.sensorHistory.index)
        self.loadIni()

    def validateSensors(self):
        temp = self.instrumentation.copy()
        self.instrumentation = {}
        for kind,values in temp.items():
            self.instrumentation.setdefault(kind,{})
            if kind not in hardwareModels.keys():
                self.logError(f"Instrumentation kind = {kind} not yet supported, see/update {hardwareModels['path']}")
            for model in values.values():
                modelName = model['modelName'].lower()
                if modelName not in hardwareModels[kind].keys():
                    self.logError(f"Instrumentation model = {modelName} of kind = {kind} not yet supported, see/update {hardwareModels['path']}")
                model = hardwareModels[kind][modelName](**model)
                self.instrumentation[kind][model.instrumentID] = model
        self.instrumentHistory = pd.DataFrame()
        if len(self.instrumentation['biometSensors']):
            biometSensors = self.instrumentation['biometSensors']
            biometHistory = pd.concat([
                pd.Series(True,name=v.instrumentID,index=pd.date_range(v.dateStart.astimezone(ZoneInfo(self.timezone)),v.dateStop.astimezone(ZoneInfo(self.timezone)),freq=f"{self.databaseInterval}s"),)
                for k,v in biometSensors.items()
                ],axis=1)
            biometInstrumentHistory = pd.Series('',index=biometHistory.index,name='biometSensors')
            for sen in biometHistory.columns:
                print(sen)
                biometInstrumentHistory.loc[biometHistory[sen].notna()] += f"-{sen}"
            biometInstrumentHistory = biometInstrumentHistory.str.strip('-')
            self.instrumentHistory = pd.concat([biometInstrumentHistory])
        if len(self.instrumentation['ecSensors']):
            ecSensors = self.instrumentation['ecSensors']
            ecHistory = pd.concat([
                pd.Series(True,name=v.instrumentID,index=pd.date_range(v.dateStart.astimezone(ZoneInfo(self.timezone)),v.dateStop.astimezone(ZoneInfo(self.timezone)),freq=f"{self.databaseInterval}s"),)
                if hasattr(v,'referenceSonic') and v.referenceSonic else
                pd.Series(False,name=v.instrumentID,index=pd.date_range(v.dateStart.astimezone(ZoneInfo(self.timezone)),v.dateStop.astimezone(ZoneInfo(self.timezone)),freq=f"{self.databaseInterval}s"),)
                for k,v in ecSensors.items() 
            ],axis=1)
            if ecHistory.sum(axis=1).max()>1:
                self.logError(f"Only one reference sonic allowed per-timestamp {ecHistory.loc[ecHistory.sum(axis=1)>1]}")
            # Select reference sonics and perform positional calculations based off this for all scalar systems
            ecInstrumentHistory = pd.Series('',index=ecHistory.index,name='ecSensors')
            for ref in ecHistory.columns[ecHistory.sum()>0]:
                refSonic = self.instrumentation['ecSensors'][ref]
                if refSonic.sensorType == 'sonic_irga':
                    scalars = [ref]
                else:
                    scalars = []
                # Find all sensors referenced to the given sonic
                scalars += list(ecHistory.columns[ecHistory.loc[ecHistory[ref]==True].count()-ecHistory.loc[ecHistory[ref]==True].sum()>0])
                ecInstrumentHistory.loc[ecHistory[ref].notna()] = ref
                for scalar in scalars:
                    ecInstrumentHistory.loc[ecHistory[scalar].notna()] += f"-{scalar}"
            ecInstrumentHistory = ecInstrumentHistory.str.strip('-')
            self.instrumentHistory = pd.concat([self.instrumentHistory,ecInstrumentHistory],axis=1)
            # Generate the template .metadata file for the group, to be filled with FileDescription at a later stage (in case different files for same configuration)
            ghgMetadata = ghgMetadataWriter()
            self.ecInstrumentGroups = pd.concat(
                [
                    pd.DataFrame(
                        index = [groupID],
                        data = {(key,subKey):value 
                                for key,subSet in ghgMetadata.setSite(
                                    siteConfig = self,
                                    sensorList = [ecSensors[sensor] for sensor in groupID.split('-')],
                                    start_date = groupDates['index']['min'],
                                    stop_date = groupDates['index']['max'],
                                ).items() for subKey, value in subSet.items()
                            }
                    )
                    for groupID,groupDates in ecInstrumentHistory.str.strip('-').reset_index().groupby('ecSensors').agg(['min','max']).iterrows()
                ]
            )
        else:
            self.ecInstrumentGroups = pd.DataFrame()
            ecInstrumentHistory = pd.DataFrame()
        self.logMessage(f'saving files for {self.siteID}')
        self.saveConfigFile(self.fileName)
        self.ecInstrumentGroups.to_csv(os.path.join(self.metaPath,self.siteID,"ecInstrumentGroups.csv"))
        self.instrumentHistory.to_csv(os.path.join(self.metaPath,self.siteID,"instrumentHistory.csv"))
        
    def loadIni(self,writeNew=False):
        if os.path.isfile(self.iniPath) and not writeNew:
            self.ini = self.loadDict(self.iniPath)
        else:
            self.ini = configTemplate(Metadata={
                'siteID':self.siteID,
                'lat':self.lat_lon[0],
                'long':self.lat_lon[1],
                }).__dict__
            self.saveDict(self.ini,self.iniPath)

    def updateRawSouces(self,dataFrequency,sourceID,dateStart,dateStop):
        # Update the dates for raw files
        if sourceID in self.ini['rawData'][dataFrequency]:
            inputDates = self.ini['rawData'][dataFrequency][sourceID]
            inputDates[0] = dateStart
            inputDates[1] = dateStop
        else:
            inputDates = CommentedSeq([dateStart,dateStop])
            inputDates.yaml_set_anchor(f'{sourceID}.inputDates')
            self.ini['rawData'][dataFrequency][sourceID] = inputDates
        self.saveDict(self.ini,self.iniPath)
        return(inputDates)

    def updateIni(self,sourceID=None,sourceFile=None):
        overwrite = False
        if sourceFile is None and sourceID is not None:
            sourceFile = self.loadDict(os.path.join(self.metaPath,self.siteID,'Database',sourceID)+'.yml') 
            overwrite = True
        elif sourceFile is None:
            self.logError('Must provide sourceID')
        first = self.ini['Processing']['FirstStage']
        inputDates = self.updateRawSouces(sourceFile['dataFrequency'],sourceFile['sourceID'],sourceFile['dateStart'],sourceFile['dateStop'])
        if self.posixName not in first:
            first[self.posixName] = firstStageTrace(
                variableName=self.posixName,
                inputFiles=f"{sourceFile['sourceID']}.{self.posixName}",
                inputDates=inputDates,
                dtype='int64',
                units='s',
                notes='default time-trace (seconds since unix epoch)').to_dict()
        else:
            first[self.posixName]['inputFiles'][f"{sourceFile['sourceID']}.{self.posixName}"] = inputDates
        for value in sourceFile['traces'].values():
            if value['ignore']:
                continue
            inputFile = f"{sourceFile['sourceID']}.{value['variableName']}"
            inputTrace = firstStageTrace.from_dict(value|{'inputFiles':inputFile,'inputDates':inputDates}).to_dict()
            if value['variableName'] not in first:
                first[value['variableName']] = inputTrace
            elif inputFile not in first[value['variableName']]['inputFiles']:
                first[value['variableName']]['inputFiles'][inputFile] = inputDates
            elif overwrite:
                first[value['variableName']] = inputTrace
            else:
                self.logError(f"Unexpected duplicate in {first[value['variableName']]['inputFiles']}")
        self.saveDict(self.ini,self.iniPath)
