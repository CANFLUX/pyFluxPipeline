import os
import pandas as pd
from dataclasses import field, dataclass
# from helperFunctions.baseClass import baseDataClass, mdMap
from scripts.defaultSettings import defaultSettings
from scripts.siteConfiguration.siteConfiguration import siteConfiguration

@dataclass(kw_only=True)
class project(defaultSettings):
    useParallel: bool = True

    def __post_init__(self):
        self.metaPath = os.path.join(self.projectPath,'Sites')
        return super().__post_init__()

    def loadSiteConfiguration(self,siteID,sensorGropus=False):
        siteConfig = siteConfiguration.from_yaml(
                            os.path.join(self.metaPath,siteID,"siteMetadata.yml"),
                            kwargs={'projectPath':self.projectPath}
                            )
        if not sensorGropus:
            return(siteConfig)
        else:
            sensorHistory = pd.read_csv(os.path.join(self.metaPath,siteID,"sensorHistory.csv"),index_col=[0],parse_dates=[0])
            sensorGroups = pd.read_csv(os.path.join(self.metaPath,siteID,"sensorGroups.csv"),header=[0,1],index_col=[0],parse_dates=[3,4,5,6],date_format='%Y-%m-%dT%H:%M:%S%z')
            return(siteConfig,sensorGroups,sensorHistory)
