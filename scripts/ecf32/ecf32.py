import os
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
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

biometHeader = baseClassMethods().loadDict(os.path.join(os.path.split(__file__)[0],'Biomet.yml'))

@dataclass(kw_only=True)
class ecf32(database):
    siteID: str
    sourceID: str 
    
    def __post_init__(self):
        self.basePath = os.path.join(self.highFrequencyPath,self.siteID,self.sourceID)
        super().__post_init__()
        
    def ecf32Metadata(sourceID,traces,dataInterval):
        def measurementType(units):
            # Translate to eddypro specific expectation (gas samples only)
            if 'm-3' in units or 'm^3' in units:
                mType = 'density'
            elif 'mol' in units:
                mType = 'mixing ratio'
            else:
                mType = None
            return(mType)
        metadata = {variable['variableName']:{
            'units':variable['units'],
            'sensorID':variable['sensorID'],
            'measurementType':measurementType(variable['units']),
            } for variable in traces.values() if not variable['ignore'] and variable['dtype'] == '<f4'}
        mdName = os.path.join(self.basePath,'ecf32Variables.yml')
        if not os.path.isdir(self.basePath):
            os.makedirs(self.basePath)
        if not os.path.isfile(mdName):
            baseClassMethods().saveDict(metadata,mdName)
        return(basePath,metadata)

    def biometCSV(self,years,traces=biometHeader['traces'],index=biometHeader['index']):
        if not isinstance(years,list): years = [years]
        for y in years:
            df = self.loadTraceFolder(
                self.getStagePath(self.siteID,'FirstStage',year=y)
                )
            cols = {c['databaseName']:(c['headerName'],c['units']) for c in traces.values() if c['databaseName'] in df.columns}
            cix = pd.MultiIndex.from_tuples(cols.values())
            df = df[list(cols.keys())].copy()
            df.columns = cix
            yPath = os.path.join(self.basePath,str(y))
            if not os.path.isdir(yPath):
                os.makedirs(yPath)
            df = df.fillna(-9999)
            df[(index['headerName'],index['units'])] = df.index.strftime(index['fmt'])
            df[df.columns[::-1]].to_csv(os.path.join(yPath,'biomet.csv'),index=False)

    def ecf32Write(self,dataTable,metadata):
        dataTable['fIndex'] = dataTable.index.floor('30min')
        for fIndex in dataTable['fIndex'].unique():
            fileSlice = dataTable.loc[dataTable['fIndex']==fIndex,list(metadata.keys())]
            fname = fileSlice.index[0].strftime(f'%Y%m%d%H%M%S.ecf32')
            fpath = os.path.join(self.basePath,str(fIndex.year),str(fIndex.month).zfill(2))
            if not os.path.isdir(fpath):
                os.makedirs(fpath,exist_ok=True)
            ecf32 = fileSlice.values.T.flatten().astype('float32')
            ecf32.tofile(os.path.join(fpath,fname))
    
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


# def biometCSV(basePath,siteID):


def ecf32Setup(basePath,siteID,sourceID,traces,dataInterval):
    def measurementType(units):
        # Translate to eddypro specific expectation (gas samples only)
        if 'm-3' in units or 'm^3' in units:
            mType = 'density'
        elif 'mol' in units:
            mType = 'mixing ratio'
        else:
            mType = None
        return(mType)
    metadata = {variable['variableName']:{
        'units':variable['units'],
        'sensorID':variable['sensorID'],
        'measurementType':measurementType(variable['units']),
        } for variable in traces.values() if not variable['ignore'] and variable['dtype'] == '<f4'}
    basePath = os.path.join(basePath,siteID,sourceID)
    mdName = os.path.join(basePath,'ecf32Variables.yml')
    if not os.path.isdir(basePath):
        os.makedirs(basePath)
    if not os.path.isfile(mdName):
        baseClassMethods().saveDict(metadata,mdName)
    return(basePath,metadata)

# def ecf32Write(dataTable,metadata,basePath):
#     dataTable['fIndex'] = dataTable.index.floor('30min')
#     for fIndex in dataTable['fIndex'].unique():
#         fileSlice = dataTable.loc[dataTable['fIndex']==fIndex,list(metadata.keys())]
#         fname = fileSlice.index[0].strftime(f'%Y%m%d%H%M%S.ecf32')
#         fpath = os.path.join(basePath,str(fIndex.year),str(fIndex.month).zfill(2))
#         if not os.path.isdir(fpath):
#             os.makedirs(fpath,exist_ok=True)
#         ecf32 = fileSlice.values.T.flatten().astype('float32')
#         ecf32.tofile(os.path.join(fpath,fname))