from scripts.traceAnalysis.firstStage import firstStage
from scripts.rawFileProcessing.fileTools import fileSearch,fileSet
from scripts.newProject import createProject
from scripts.project import project
from scripts.siteConfiguration.siteConfiguration import siteConfiguration
import os
from scripts.ecf32.ecf32 import ecf32
import yaml

def driveCheck(path):
    for drive in ['E:','D:','/mnt/d','/mnt/e']:
        if os.path.isdir(os.path.join(drive,path)):
            path = os.path.join(drive,path)
        else: drive = None
    if drive is None:
        exit('No drive/mnt present where expected, if using wsl, try: sudo mount -t drvfs D: /mnt/d (or sudo mount -t drvfs E: /mnt/e)')

    return(path)

if __name__ == '__main__':
    reset = True
    data_dump = driveCheck('data-dump')
    projectPath = 'testing/myProject'
    if reset:
        createProject(
            reset=reset,
            projectPath=projectPath,
            sitesList=[
            'configurationFiles/siteTemplates/SCL_template.yml', # Template from preexisting metadata file for SCL
            'configurationFiles/siteTemplates/RDEC1_Seep_template.yml', # Template from preexisting metadata file for RDEC1
            ])

    with open('configurationFiles/rawFileSettings/CSFormat.yml') as f:
        CSFormat = yaml.safe_load(f)
    with open('configurationFiles/rawFileSettings/Time_Series.yml') as f:
        Time_Series = yaml.safe_load(f) 
    fileSearch(
        projectPath=projectPath,
        siteID='SEEP',
        searchPath=data_dump+'/RDEC1/2026',        
        **CSFormat
    )

    # print('Check ini then proceed')
    # breakpoint()
    # SEEP = project(projectPath=projectPath).loadSiteConfiguration('SEEP').updateIni('TOB3_Flux_CSFormat_202606111732')
    
    fileSearch(
        projectPath=projectPath,
        siteID='SEEP',
        searchPath=data_dump+'/RDEC1/2026',        
        **Time_Series
    )
    # SeepFlux = discoverFiles(
    #     projectPath=projectPath,
    #     siteID='SEEP',
    #     searchPath=data_dump+'/RDEC1/2026/20260614',        
    #     # processFiles=True,
    #     useParallel=False,
    #     **CSFormat
    #     )
    
# #     # breakpoint()
#     SeepFlux = discoverFiles(
#         projectPath=projectPath,
#         siteID='SEEP',
#         searchPath=data_dump+'/RDEC1/2026/20260614',        
#         processFiles=False,
#         useParallel=False,
#         timezone='American/Vancouver',
#         **Time_Series,
        
#         # **{'fileFormat':'TOB3'}
#         )
# #     fs = firstStage(projectPath=projectPath,sites='SEEP',years=[2026])


