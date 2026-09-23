import os
import pandas as pd
from dataclasses import field, dataclass
# from helperFunctions.baseClass import baseDataClass, mdMap
from scripts.defaultSettings import defaultSettings
from scripts.siteConfiguration.siteConfiguration import siteConfiguration

@dataclass(kw_only=True)
class project(defaultSettings):
    useParallel: bool = field(default=True,repr=False)

    def __post_init__(self):
        self.metaPath = os.path.join(self.projectPath,'Sites')
        return super().__post_init__()

    def loadSiteConfiguration(self,siteID):
        siteConfig = siteConfiguration.from_yaml(
                            os.path.join(self.metaPath,siteID,"siteMetadata.yml"),
                            kwargs={'projectPath':self.projectPath}
                            )
        return(siteConfig)
