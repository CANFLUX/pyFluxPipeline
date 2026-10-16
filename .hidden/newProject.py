
# # from scripts.database.database import database
# from scripts.project import project
# from dataclasses import dataclass, field
# from submodules.helperFunctions.baseClass import mdMap
# from scripts.siteConfiguration.siteConfiguration import siteMetadata
# from datetime import datetime
# import shutil
# import os

# @dataclass(kw_only=True)
# class createProject(project):
#     reset: bool = field(default=False,repr=False)
#     # projectPath: str = field(repr=True)
#     sitesList: list = field(default_factory=lambda:['.templateSite'],metadata=mdMap('List of siteIDs'))
    
#     def __post_init__(self):
#         if self.reset:
#             if os.path.exists(self.projectPath):
#                 shutil.rmtree(self.projectPath)
#         breakpoint()
#         super().__post_init__()
#         if not os.path.isdir(self.projectPath) or len(os.listdir(self.projectPath))==0:
#             self.newProject()
#         elif not any([os.path.exists(os.path.join(self.projectPath,v)) for v in ['Database','Sites','projectConfig.yml']]):
#             self.logError(f'Non-empty non-project directory: {self.projectPath}')

#     def newProject(self):
#         os.makedirs(os.path.join(self.projectPath,'Database','Calculation_Procedures','TraceAnalysis_ini'))
#         os.makedirs(self.metaPath)
#         replaceMap = {}
#         if isinstance(self.sitesList,str):
#             self.sitesList = [self.sitesList]
#         for i,siteID in enumerate(self.sitesList):
#             # Load user provided template file
#             replaceMap[i],_ = self.newSite(siteID)
#         for i,v in replaceMap.items():
#             self.sitesList[i] = v
#         self.saveConfigFile(os.path.join(self.projectPath,'projectConfig.yml'))

#     def newSite(self,siteID):
#         if isinstance(siteID,str):
#             if os.path.isfile(siteID):
#                 # breakpoint()
#                 temp = siteMetadata.from_yaml(siteID,kwargs={'projectPath':self.projectPath})
#                 siteID = temp.siteID
#             elif siteID.isalnum():
#                 temp = siteMetadata(
#                     siteID=siteID,
#                     projectPath=self.projectPath,
#                     dateStart=f"{datetime.now().year}-01-01 00:00:00+00:00",
#                     lat_lon = [None,None]
#                     )
#                 siteID = temp.siteID
#             else:
#                 self.logError(f"Invalid siteID: {siteID}")
#         # Load user provided template dict
#         elif isinstance(siteID,dict):
#             siteID['projectPath'] = self.projectPath
#             temp = siteMetadata(**siteID)
#             siteID = temp.siteID
#         else:
#         # Load default template
#             self.saveDict(
#                 temp.to_dict(),
#                 os.path.join(self.metaPath,siteID,"siteMetadata.yml")
#                 )
#         return(siteID,temp)