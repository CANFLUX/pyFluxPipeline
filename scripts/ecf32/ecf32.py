import os
import pandas as pd
from datetime import datetime
from configparser import ConfigParser
from dataclasses import dataclass, field
from scripts.database.database import database
from scripts.ecf32.ghgMetadata import ghgMetadata
from helperFunctions.baseClass import baseClassMethods


biometHeader = baseClassMethods().loadDict(os.path.join(os.path.split(__file__)[0],'Biomet.yml'))
eddyproProjectTemplate = ConfigParser()
eddyproProjectTemplate.read(os.path.join(os.path.split(__file__)[0],'template.eddypro'))


@dataclass(kw_only=True)
class ecf32(database):
    siteID: str
    sourceID: str 
    kwargs: dict = field(default=None)
    
    def __post_init__(self):
        super().__post_init__()
        self.basePath = os.path.join(self.highFrequencyPath,self.siteID,self.sourceID)
        self.ecf32HeaderFile = os.path.join(self.basePath,'ecf32Variables.yml')
        if not os.path.isdir(self.basePath):
            os.makedirs(self.basePath)
        if self.kwargs is not None:
            self.ecf32Metadata(self.kwargs)
        else:
            self.ecf32Header = self.loadDict(self.ecf32HeaderFile)
       
    def ecf32Metadata(self,kwargs):#,sourceID,traces,dataInterval):
        # siteConfig = self.loadSiteConfiguration(self.siteID)
        # self.metadata = ghgMetadata()
        breakpoint()
        # self.metadata.generate(siteConfig)
        def measurementType(units):
            # Translate to eddypro specific expectation (gas samples only)
            if 'm-3' in units or 'm^3' in units:
                mType = 'density'
            elif 'mol' in units:
                mType = 'mixing ratio'
            else:
                mType = None
            return(mType)
        self.ecf32Header = {variable['variableName']:{
            'units':variable['units'],
            'sensorID':variable['sensorID'],
            'measurementType':measurementType(variable['units']),
            } for variable in kwargs['traces'].values() if not variable['ignore'] and variable['dtype'] == '<f4'}
        if not os.path.isdir(self.basePath):
            os.makedirs(self.basePath)
        if not os.path.isfile(self.ecf32HeaderFile):
            self.saveDict(self.ecf32Header,self.ecf32HeaderFile)

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
        self.ecf32Header = {
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

