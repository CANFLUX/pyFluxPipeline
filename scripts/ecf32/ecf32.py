from dataclasses import dataclass, field
from datetime import datetime
from scripts.database.database import database
from helperFunctions.baseClass import baseClassMethods

@dataclass(kw_only=True)
class Project:
    title: str = None
    creation_date: str = datetime.strftime(datetime.now(),format='%Y-%m-%dT%H:%M:%S')
    start_date: str = None
    end_date: str = None

@dataclass(kw_only=True)
class Files:
    data_path: str = None

@dataclass(kw_only=True)
class Site:
    site_name: str = None
    site_id: str = None
    altitude: float = None
    latitude: float = None
    longitude: float = None
    canopy_height: float = None
    displacement_height: float = None
    roughness_length: float = None

@dataclass(kw_only=True)
class Timing:
    acquisition_frequency: float = None
    file_duration: int = None

@dataclass(kw_only=True)
class Instrument_shared(baseClassMethods):
    manufacturer: str = None
    model: str = None
    sw_version: id = None
    northward_separation: float = None
    eastward_separation: float = None
    vertical_separation: float = None
    vpath_lenght: float = None
    hpath_lenght: float = None
    tau: float = None

@dataclass(kw_only=True)
class Sonic(Instrument_shared):
    height: float = None
    wformat: str = 'uvw'
    wref: str = None
    north_offset: float = None

@dataclass(kw_only=True)
class IRGA(Instrument_shared):
    tube_length: float = None
    tube_diameter: float = None
    tube_flowrate: float = None
    kw: float = None
    ko: float = None

@dataclass(kw_only=True)
class Instruments:
    sensors: dict = None

    def __post_init__(self):
        for key,value in self.sensors.items():
            print(key,value)
# @dataclass(kw_only=True)
# class Instrument(Sonic,IRGA):

#     def __post_init__(self):
#         pass



# @dataclass(kw_only=True)
# class metadata:
#     Project: callable = field(default_factory=Project)
#     Files: dict = None
#     Site: dict = None
#     Station: dict = None
#     Timing: dict = None
#     Instruments: dict = None
#     FileDescription: dict = None

#     def __post_init__(self):
#         pass

# @dataclass(kw_only=True)
# class metadata:
#     Project: Project
#     Files: Files = None
#     Site: Site

class ecf32(database):
    
    
    def make(self,siteID):
        cfg = self.loadSiteConfiguration(siteID=siteID)
        self.metadata = {
            'Project':Project(
                start_date=cfg.startDate,
                end_date=cfg.stopDate
                ),
            'Site':Site(
                site_id=cfg.siteID,
                site_name=cfg.siteName,
                latitude=cfg.lat_lon[0],
                longitude=cfg.lat_lon[1],
                altitude=cfg.altitude,
                canopy_height=cfg.canopyHeight
                )
            }
        sc=0
        for sensor,info in cfg.sensors.items():
            if info.sensorType in ['irga','sonic','sonic-irga','thermocouple']:
                sc+=1
                if info.sensorType.startswith('sonic'):
                    # print(sensor,info.to_dict())
                    print(Sonic.from_dict(info.to_dict()))

        # breakpoint()

    def load(self,siteID):
        breakpoint()