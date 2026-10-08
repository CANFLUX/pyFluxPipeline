import os
import pandas as pd
from dataclasses import field, dataclass
from helperFunctions.baseClass import baseDataClass
from scripts.defaultSettings import defaultSettings
from scripts.siteConfiguration.siteConfiguration import siteMetadata

@dataclass(kw_only=True)
class project(baseDataClass, defaultSettings):
    projectPath: str = field(repr=False)

    def __post_init__(self):
        self.metaPath = os.path.join(self.projectPath,'Sites')
        return super().__post_init__()

    def loadSiteMetadata(self,siteID):
        siteConfig = siteMetadata.from_yaml(
                            os.path.join(self.metaPath,siteID,"siteMetadata.yml"),
                            kwargs={'projectPath':self.projectPath}
                            )
        return(siteConfig)
