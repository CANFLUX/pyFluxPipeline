from helperFunctions import baseClass
from scripts.siteConfiguration.siteConfiguration import site
from scripts.projectParameters import project
from dataclasses import dataclass, field
import os
mdMap = baseClass.mdMap

@dataclass(kw_only=True)
class openProject(project):
    projectPath: str = field(metadata=mdMap('Root path of the current project'))
    sites: list = field(default_factory=list,metadata=mdMap('List of siteIDs'))
    siteInventory: dict = field(init=False,default_factory=dict,repr=False)
    
    def __post_init__(self):
        self.projectStructure()
        self.readSiteInventory()
        super().__post_init__()
        self.saveConfigFile(os.path.join(self.projectPath,'projectConfig.yml'),keepNull=False,sorted=False)

    def projectStructure(self):
        if not os.path.isdir(self.projectPath) or len(os.listdir(self.projectPath))==0:
            os.makedirs(os.path.join(self.projectPath,'Database'))
            os.makedirs(os.path.join(self.projectPath,'Sites'))
            with open(os.path.join(self.projectPath,'projectConfig.yml'),'w'):
                pass
        elif os.path.isdir(self.projectPath) and (
            not any([os.path.exists(os.path.join(self.projectPath,v)) for v in ['Database','Sites','projectConfig.yml']])
        ):
            self.logError(f'Non-empty non-project directory: {self.projectPath}')
        if self.configFile is None:
            self.logMessage('loading from existing configuration')
            configFile = self.loadDict(os.path.join(self.projectPath,'projectConfig.yml'))
            for key in self.__annotations__:
                setattr(self,key,configFile[key])

    def readSiteInventory(self):
        if isinstance(self.sites,dict):
            siteParameters = [self.sites.pop(id) for id in list(self.sites.keys())]
            self.sites = []
            for params in siteParameters:
                params = site.from_dict(params|{'projectPath':self.projectPath})
                params.saveConfigFile(os.path.join(self.projectPath,'Sites',params.siteID,f"{params.siteID}_siteConfig.yml"))
                self.siteInventory[params.siteID] = params
                self.sites.append(params.siteID)
