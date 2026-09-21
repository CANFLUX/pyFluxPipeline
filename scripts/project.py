import os
import pandas as pd
from dataclasses import field, dataclass
# from helperFunctions.baseClass import baseDataClass, mdMap
from scripts.defaultSettings import defaultSettings
from scripts.siteConfiguration.siteConfiguration import siteConfiguration

@dataclass(kw_only=True)
class project(defaultSettings):

    def loadSiteConfiguration(self,siteID,sensorGropus=False):
        if not sensorGropus:
            return(
                siteConfiguration.from_yaml(
                    os.path.join(self.projectPath,'Sites',siteID,"siteMetadata.yml"),
                    kwargs={'projectPath':self.projectPath}
                    )
                )
        else:
            config = siteConfiguration.from_yaml(
                                os.path.join(self.projectPath,'Sites',siteID,"siteMetadata.yml"),
                                kwargs={'projectPath':self.projectPath}
                                )
            sensorHistory = pd.read_csv(os.path.join(self.projectPath,'Sites',siteID,"sensorHistory.csv"),index_col=[0],parse_dates=[0])
            sensorGroups = pd.read_csv(os.path.join(self.projectPath,'Sites',siteID,"sensorGroups.csv"),index_col=[0],parse_dates=[3,4,5,6],date_format='%Y-%m-%dT%H:%M:%S')
            return(
                config,sensorGroups,sensorHistory
                )