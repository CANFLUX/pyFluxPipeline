from scripts.siteConfiguration.hardware import dataLogger,sensor
# from scripts.siteConfiguration.rawData import rawFileParameters
from dataclasses import dataclass, field
from helperFunctions.baseClass import spatialObject,mdMap
from datetime import datetime
from scripts.project import project
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
@dataclass(kw_only=True)
class configTemplate:
    Metadata: dict = None
    rawData: dict = field(default_factory=dict)
    Processing: dict = field(default_factory=lambda:{'FirstStage':{},'SecondStage':{},'ThirdStage':{}})
    def __post_init__(self):
        # if isinstance(self.Metadata,str):
        self.Metadata = configMetadata(**self.Metadata).__dict__

@dataclass(kw_only=True)
class siteConfiguration(project):
    siteID: str = field(metadata = mdMap('Unique siteID code'))
    startDate: datetime = field(default = None,metadata = mdMap('Start Date will parse from string input (assuming Year-Month-Day order) For nested values, defaults to parent object, provide to override'))
    stopDate: datetime = field(default = None,metadata = mdMap('Stop Date will parse from string input (assuming Year-Month-Day order) For nested values, defaults to parent object, provide to override'))
    siteName: str = field(default = None,metadata = mdMap('Name of the Site'))
    sitePI: str = field(default = None,metadata=mdMap('Principal Investigator(s)'))
    lat_lon: spatialObject = field(default_factory=lambda:[None,None],metadata = mdMap('List of [Latitude, Longitude] coordinates in WGS1984 stored in decimal degrees.  Will parse coordinates if provided as strings in DMS or DDM format. For nested values, assumed to be same as parent object.  Optionally to provide if different from parent value.'))
    altitude: float = field(default = None,metadata = mdMap('Elevation (m.a.s.l).  For nested values, assumed to be same as parent object.  Optionally to provide if different from parent value.'))
    canopyHeight: float = field(default=None,metadata=mdMap('optional parameter to describe general vegetation height at site.  Can be overridden by dynamic values where appropriate'))
    siteDescription: str = field(default = None,metadata=mdMap('self explanatory'))
    dataLoggers: dict = field(default_factory=dict)
    sensors: dict = field(default_factory=dict)
    dataSources: dict = field(default_factory=dict)
    template: bool = field(default=False,repr=False)

    def __post_init__(self):
        self.checkHardware()
        super().__post_init__()
        self.loadIni()

    def checkHardware(self):
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
    
    def loadIni(self):
        self.iniPath = os.path.join(self.projectPath,'Database','Calculation_Procedures','TraceAnalysis_ini',f"{self.siteID}_config.yml")
        if os.path.isfile(self.iniPath):
            self.ini = self.loadDict(self.iniPath)
        else:
            self.ini = configTemplate(Metadata={
                'siteID':self.siteID,
                'lat':self.lat_lon[0],
                'long':self.lat_lon[1],
                }).__dict__
        self.saveDict(self.ini,self.iniPath)
