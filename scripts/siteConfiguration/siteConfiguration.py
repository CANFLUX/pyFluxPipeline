from scripts.siteConfiguration.hardware import dataLogger,sensor
from scripts.siteConfiguration.rawData import rawFileParameters
from scripts.projectParameters import project
from helperFunctions import baseClass
from dataclasses import dataclass, field
mdMap = baseClass.mdMap

@dataclass(kw_only=True)
class site(project):
    siteID: str = field(metadata = mdMap('Unique siteID code'))
    siteName: str = field(default = None,metadata = mdMap('Name of the Site'))
    sitePI: str = field(default = None,metadata=mdMap('Principal Investigator(s)'))
    lat_lon: baseClass.spatialObject = field(default = None,metadata = mdMap('List of [Latitude, Longitude] coordinates in WGS1984 stored in decimal degrees.  Will parse coordinates if provided as strings in DMS or DDM format. For nested values, assumed to be same as parent object.  Optionally to provide if different from parent value.'))
    altitude: float = field(default = None,metadata = mdMap('Elevation (m.a.s.l).  For nested values, assumed to be same as parent object.  Optionally to provide if different from parent value.'))
    canopyHeight: float = field(default=None,metadata=mdMap('optional parameter to describe general vegetation height at site.  Can be overridden by dynamic values where appropriate'))
    siteDescription: str = field(default = None,metadata=mdMap('self explanatory'))
    dataLoggers: dict = field(default_factory=dict)
    sensors: dict = field(default_factory=dict)
    rawDataFiles: dict = field(default_factory=dict,repr=False)

    def __post_init__(self):
        self.checkHardware()
        self.dataCheck()
        super().__post_init__()

    def checkHardware(self):
        # dataloggers first
        IDs = list(self.dataLoggers.keys())
        for id in IDs:
            params = self.dataLoggers.pop(id)
            params = dataLogger.from_dict(params)
            self.dataLoggers[params.hardwareID] = params#.to_dict()
        # Then sensors
        IDs = list(self.sensors.keys())
        for id in IDs:
            params = self.sensors.pop(id)
            params = sensor.from_dict(params)
            self.sensors[params.hardwareID] = params#.to_dict()
    
    def dataCheck(self):
        # Check data sources
        IDs = list(self.rawDataFiles.keys())
        for id in IDs:
            params = self.rawDataFiles.pop(id)
            params = rawFileParameters.from_dict(params)
            # params = sensor.from_dict(params)
            # self.sensors[params.hardwareID] = params#.to_dict()
    

