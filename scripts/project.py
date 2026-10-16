import os
import shutil
import pandas as pd
import geopandas as gpd
from dataclasses import field, dataclass
from submodules.helperFunctions.baseClass import baseDataClass
from scripts.defaultSettings import defaultSettings,projectTemplate
from scripts.siteConfiguration.siteConfiguration import siteMetadata

@dataclass(kw_only=True)
class project(baseDataClass, defaultSettings):
    projectPath: str = field(repr=False)
    Sites: dict = field(default_factory=dict,init=False,repr=False)

    def __post_init__(self):
        self.metaPath = os.path.join(self.projectPath,'Sites')
        super().__post_init__()

    def initalize(self):
        # to start up a full session
        data = {'dateStart':[],'dateStop':[]}
        x,y=[],[]
        index = []

        for siteID in os.listdir(self.metaPath):
            self.Sites[siteID] = self.loadSiteMetadata(siteID)
            index.append(siteID)
            x.append(self.Sites[siteID].lat_lon[1])
            y.append(self.Sites[siteID].lat_lon[0])
            data['dateStart'].append((self.Sites[siteID]).dateStart)
            data['dateStop'].append((self.Sites[siteID]).dateStop)
        self.siteCoordinates = gpd.GeoDataFrame(data=data,index=index,geometry=gpd.points_from_xy(x=x,y=y),crs='WGS1984')
        self.siteCoordinates.to_file(os.path.join(self.projectPath,'siteCoordinates.geojson'),driver='geojson')
        return(self)

    def loadSiteMetadata(self,siteID):
        siteConfig = siteMetadata.from_yaml(
                            os.path.join(self.metaPath,siteID,"siteMetadata.yml"),
                            kwargs={'projectPath':self.projectPath}
                            )
        return(siteConfig)

    def newSite(self,siteID,kwargs={}):
        if isinstance(kwargs,str):
            if os.path.isfile(kwargs):
                kwargs = self.loadDict(kwargs)
            else:
                self.logError(f"not a vailid template file {kwargs}")
        sm = siteMetadata.from_dict({'projectPath':self.projectPath,'siteID':siteID}|kwargs)

   
@dataclass(kw_only=True)
class newProject(project):
    reset: bool = False

    def __post_init__(self):
        if self.reset and os.path.exists(self.projectPath):
            shutil.rmtree(self.projectPath)
        temp = self.unpackDict(projectTemplate)
        for key,value in temp.items():
            key = key.replace('projectPath',self.projectPath)
            if value is None:
                os.makedirs(key)
                continue
            elif isinstance(value,list):
                value = value[0]
                self.saveDict(value,key)
            elif isinstance(value,dict):
                value = value
                self.saveDict(value,key)
            else:
                self.logError(f'Not yet an option {value} of type {type(value)}')
        super().__post_init__()
