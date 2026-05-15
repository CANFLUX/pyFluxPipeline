from scripts.siteConfiguration.siteConfiguration import site
from scripts.projectParameters import project
from dataclasses import dataclass, field
from helperFunctions.baseClass import mdMap
import os

@dataclass(kw_only=True)
class openProject(project):
    projectPath: str = field(metadata=mdMap('Root path of the current project'))
    sites: list = field(default_factory=lambda:['.templateSite'],metadata=mdMap('List of siteIDs'))
    siteInventory: dict = field(init=False,default_factory=dict,repr=False)
    
    def __post_init__(self):
        if not os.path.isdir(self.projectPath) or len(os.listdir(self.projectPath))==0:
            self.newProject()
        elif not any([os.path.exists(os.path.join(self.projectPath,v)) for v in ['Database','Sites','projectConfig.yml']]):
            self.logError(f'Non-empty non-project directory: {self.projectPath}')

        self.readSiteInventory()
        super().__post_init__()
        # self.saveConfigFile(os.path.join(self.projectPath,'projectConfig.yml'),keepNull=False,sorted=False)


    def newProject(self):
        os.makedirs(os.path.join(self.projectPath,'Database'))
        os.makedirs(os.path.join(self.projectPath,'Sites'))
        self.saveConfigFile(os.path.join(self.projectPath,'projectConfig.yml'))
        replaceMap = {}
        for i,siteID in enumerate(self.sites):
            # Load user provided template, or default template
            if os.path.isfile(siteID):
                temp = self.loadSiteConfiguration(siteID).to_dict()
                siteID = temp['siteID']
                replaceMap[i] = siteID
                self.siteInventory[siteID] = temp
            else:
                self.siteInventory[siteID] = self.templateSite(siteID)
            self.saveDict(
                self.siteInventory[siteID] ,
                os.path.join(self.projectPath,'Sites',siteID,f"{siteID}_siteConfig.yml")
                )
        for i,v in replaceMap.items():
            self.sites[i] = v

    def templateSite(self,siteID):
        self.logMessage(f"Creating empty template for {siteID}")
        return(site.from_dict({'siteID':siteID,'projectPath':self.projectPath}).to_dict())


    def readSiteInventory(self):
        self.allSites = os.listdir(os.path.join(self.projectPath,'Sites'))
        if any([s not in self.allSites for s in self.sites]):
            self.logError(f"sites do not exist: {[s for s in self.sites if s not in self.allSites]}")
            
        self.siteInventory = {siteID:self.loadSiteConfiguration(siteID) for siteID in self.sites}

    def loadSiteConfiguration(self,siteID):
        # read a user-provided file
        if os.path.isfile(siteID):
            return(
                site.from_yaml(
                    siteID,
                    kwargs={'projectPath':self.projectPath}
                    )
                )
        # read a project file
        else:
            return(
                site.from_yaml(
                    os.path.join(self.projectPath,'Sites',siteID,f"{siteID}_siteConfig.yml"),
                    kwargs={'projectPath':self.projectPath}
                    )
                )
        # breakpoint()

    # def projectStructure(self):
    #     if not os.path.isdir(self.projectPath) or len(os.listdir(self.projectPath))==0:
    #         self.newProject()
    #     elif os.path.isdir(self.projectPath) and (
    #         not any([os.path.exists(os.path.join(self.projectPath,v)) for v in ['Database','Sites','projectConfig.yml']])
    #     ):
    #         self.logError(f'Non-empty non-project directory: {self.projectPath}')
    #     if self.configFile is None:
    #         self.logMessage('loading from existing configuration')
    #         configFile = self.loadDict(os.path.join(self.projectPath,'projectConfig.yml'))
    #         for key in self.__annotations__:
    #             if key in configFile:
    #                 setattr(self,key,configFile[key])
                