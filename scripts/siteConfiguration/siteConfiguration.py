from scripts.siteConfiguration.hardware import dataLogger,sensor
from helperFunctions.baseClass import spatialObject,mdMap
from ruamel.yaml.scalarstring import LiteralScalarString
from scripts.ecf32.ghgMetadata import ghgMetadata
from scripts.defaultSettings import defaultSettings
from scripts.traceAnalysis.traceParameters import firstStageTrace
from ruamel.yaml.comments import CommentedSeq
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np
from zoneinfo import ZoneInfo
import json
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

@dataclass(kw_only=True)
class siteConfiguration(defaultSettings):
    siteID: str = field(metadata = mdMap('Unique siteID code'))
    siteName: str = field(default = None,metadata = mdMap('Long-format name'))
    startDate: datetime = field(default = None, metadata = mdMap('Start Date will parse from string input (assuming Year-Month-Day order) For nested values, defaults to parent object, provide to override'))
    stopDate: datetime = field(default = None,metadata = mdMap('Stop Date will parse from string input (assuming Year-Month-Day order) For nested values, defaults to parent object, provide to override'))
    sitePI: str = field(default = None,metadata=mdMap('Principal Investigator(s)'))
    lat_lon: spatialObject = field(default_factory=lambda:[None,None],metadata = mdMap('List of [Latitude, Longitude] coordinates in WGS1984 stored in decimal degrees.  Will parse coordinates if provided as strings in DMS or DDM format. For nested values, assumed to be same as parent object.  Optionally to provide if different from parent value.'))
    altitude: float = field(default = None,metadata = mdMap('Elevation (m.a.s.l).  For nested values, assumed to be same as parent object.  Optionally to provide if different from parent value.'))
    canopyHeight: float = field(default=None,metadata=mdMap('optional parameter to describe general vegetation height at site.  Can be overridden by dynamic values where appropriate'))
    siteDescription: str = field(default = None,metadata=mdMap('self explanatory'))
    dataLoggers: dict = field(default_factory=dict)
    sensors: dict = field(default_factory=dict)
    dataSources: dict = field(default_factory=dict)
    fromYAML: bool = field(default=True,repr=False)

    def __post_init__(self):
        super().__post_init__()
        self.metaPath = os.path.join(self.projectPath,'Sites')
        self.fileName = os.path.join(self.metaPath,self.siteID,"siteMetadata.yml")
        self.iniPath = os.path.join(self.projectPath,'Database','Calculation_Procedures','TraceAnalysis_ini',f"{self.siteID}_config.yml")
        if not os.path.isfile(self.fileName):
            self.validateConfiguration(writeNew=True)
            self.loadIni(writeNew=True)
        else:
            self.sensorGroups = pd.read_csv(os.path.join(self.metaPath,self.siteID,"sensorGroups.csv"),header=[0,1],index_col=[0])
            self.sensorHistory = pd.read_csv(os.path.join(self.metaPath,self.siteID,"sensorHistory.csv"),index_col=[0])
            self.sensorHistory.index = pd.to_datetime(self.sensorHistory.index)
            self.loadIni()

    def validateConfiguration(self,writeNew):
        # dataloggers first
        IDs = list(self.dataLoggers.keys())
        for id in IDs:
            params = self.dataLoggers.pop(id)
            params = dataLogger.from_dict(params)
            self.dataLoggers[params.hardwareID] = params
        # Then sensors
        IDs = list(self.sensors.keys())
        for id in IDs:
            params = self.sensors.pop(id)
            params = sensor.from_dict(params)
            self.sensors[params.hardwareID] = params
            # breakpoint()
        dates = []
        for k,v in self.sensors.items():
            if v.dateIn.tzinfo is None:
                self.logError(f'Error in {self.siteID}: dateIn:{v.dateIn}, must specify UTC offset in yaml timestamp, e.g., +00:00, -06:00, etc. ')
            if v.dateOut is not None:
                if v.dateOut.tzinfo is None:
                    self.logError(f'Error in {self.siteID}: dateOut: {v.dateOut}, must specify UTC offset in yaml timestamp, e.g., +00:00, -06:00, etc. ')
                rng = pd.date_range(
                    v.dateIn.astimezone(ZoneInfo(self.timezone)).isoformat(),
                    v.dateOut.astimezone(ZoneInfo(self.timezone)).isoformat(),
                    inclusive='left',freq=f"{self.dataIntervalSeconds}s").floor(f"{self.dataIntervalSeconds}s")
            else:
                rng = pd.date_range(
                    v.dateIn.astimezone(ZoneInfo(self.timezone)).isoformat(),
                    datetime.now().astimezone(ZoneInfo(self.timezone)).isoformat(),inclusive='left',freq=f"{self.dataIntervalSeconds}s").floor(f"{self.dataIntervalSeconds}s")
            dates.append(pd.DataFrame(index=rng,data={k:[k for i in range(rng.shape[0])]}))
        self.sensorGroups(dates)
        if writeNew:
            self.logMessage(f'saving files for {self.siteID}')
            self.saveConfigFile(self.fileName)
            self.sensorGroups.to_csv(os.path.join(self.metaPath,self.siteID,"sensorGroups.csv"))
            self.sensorHistory.to_csv(os.path.join(self.metaPath,self.siteID,"sensorHistory.csv"))

    def sensorGroups(self,dates):
        # Group system sensors
        self.sensorHistory = pd.concat(dates,axis=1).fillna('')
        self.sensorHistory['sensorGroup'] = self.sensorHistory.agg('_'.join,axis=1).str.replace(r'(_)\1+', '_', regex=True).str.strip('_')
        self.sensorHistory = self.sensorHistory[['sensorGroup']]
        tmp = self.sensorHistory.reset_index().groupby(['sensorGroup']).count()
        groupMeta = ghgMetadata()
        self.sensorGroups = pd.concat([
            pd.DataFrame(index=[sensorGroup],
                         data = {
                            (key,subKey):value for key,subSet in
                            groupMeta.setSite(
                                self,
                                sensorGroup.split('_'),
                                start_date=self.sensorHistory.loc[self.sensorHistory.sensorGroup==sensorGroup].index.min(),
                                stop_date=self.sensorHistory.loc[self.sensorHistory.sensorGroup==sensorGroup].index.max(),
                                ).items()
                            for subKey,value in subSet.items()
                         }
            )
            for sensorGroup in tmp.index
        ])
          
    
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

    def updateIni(self,sourceID=None,sourceFile=None):
        overwrite = False
        if sourceFile is None and sourceID is not None:
            sourceFile = self.loadDict(os.path.join(self.metaPath,self.siteID,'Database',sourceID)+'.yml') 
            overwrite = True
        elif sourceFile is None:
            self.logError('Must provide sourceID')
        rawDatabase = self.ini['rawData']['Database']
        first = self.ini['Processing']['FirstStage']
        inputDates = CommentedSeq([sourceFile['startDate'],sourceFile['stopDate']])
        inputDates.yaml_set_anchor(f'{sourceFile["sourceID"]}.inputDates')
        rawDatabase[sourceFile['sourceID']] = inputDates
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
        if type(sourceFile['traces']) is str:
            sourceFile['traces'] = json.loads(sourceFile['traces'])
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
