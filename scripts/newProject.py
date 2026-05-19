
from scripts.database.database import database
from dataclasses import dataclass, field
from helperFunctions.baseClass import mdMap
from scripts.siteConfiguration.siteConfiguration import siteConfiguration
import os

@dataclass(kw_only=True)
class createProject(database):
    projectPath: str = field(metadata=mdMap('Root path of the current project'))
    sites: list = field(default_factory=lambda:['.templateSite'],metadata=mdMap('List of siteIDs'))
    # siteConfigTemplates: dict = field(default_factory=dict,repr=False)
    
    def __post_init__(self):
        if not os.path.isdir(self.projectPath) or len(os.listdir(self.projectPath))==0:
            self.newProject()
        elif not any([os.path.exists(os.path.join(self.projectPath,v)) for v in ['Database','Sites','projectConfig.yml']]):
            self.logError(f'Non-empty non-project directory: {self.projectPath}')

        super().__post_init__()
        # self.readSiteInventory()

    def newProject(self):
        os.makedirs(os.path.join(self.projectPath,'Database','Calculation_Procedures','TraceAnalysis_ini'))
        os.makedirs(os.path.join(self.projectPath,'Sites'))
        self.saveConfigFile(os.path.join(self.projectPath,'projectConfig.yml'))
        replaceMap = {}
        if isinstance(self.sites,str):
            self.sites = [self.sites]
        for i,siteID in enumerate(self.sites):
            # Load user provided template file
            replaceMap[i],_ = self.newSite(siteID)
        for i,v in replaceMap.items():
            self.sites[i] = v

    def newSite(self,siteID):
        if isinstance(siteID,str):
            if os.path.isfile(siteID):
                temp = siteConfiguration.from_yaml(siteID,kwargs={'projectPath':self.projectPath})
                siteID = temp.siteID
            elif siteID.isalnum():
                temp = siteConfiguration(siteID=siteID,projectPath=self.projectPath,template=True)
                siteID = temp.siteID
            else:
                self.logError(f"Invalid siteID: {siteID}")
        # Load user provided template dict
        elif isinstance(siteID,dict):
            siteID['projectPath'] = self.projectPath
            temp = siteConfiguration(**siteID)
            siteID = temp.siteID
        # Load default template
        self.saveDict(
            temp.to_dict(),
            os.path.join(self.projectPath,'Sites',siteID,f"{siteID}_siteMetadata.yml")
            )
        return(siteID,temp)