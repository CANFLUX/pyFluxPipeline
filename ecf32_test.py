# from scripts.rawFileProcessing.fileInventory import fileInventory
# from scripts.rawFileProcessing.rawFile import rawFile
from scripts.traceAnalysis.firstStage import firstStage
# from scripts.rawFileProcessing.parseCSI import discoverCSI
from scripts.rawFileProcessing.rawFile import discoverFiles
from scripts.newProject import createProject
from scripts.siteConfiguration import siteConfiguration
import shutil
import os
from scripts.ecf32.ecf32 import ecf32
from scripts.database.database import highFrequencyDatabase


reset = True

# wsl Note:
# if drive not discovered, try: sudo mount -t drvfs D: /mnt/d (or E: ...)

# drive = 'E:'
# if not os.path.isdir(drive):
#     drive = 'D:'
# projectPath = f'{drive}/GSC_Work/deltaFluxes'
projectPath = 'testing/myProject'
if reset:
    if os.path.exists(projectPath):
        shutil.rmtree(projectPath)
if not os.path.isdir(projectPath):
    createProject(projectPath=projectPath,sitesList=[
        # 'configurationFiles/SCL_template.yml', # Template from preexisting metadata file for SCL
        'configurationFiles/RDEC1_Seep_template.yml', # Template from preexisting metadata file for RDEC1
        # {'siteID': 'BSP','lat_lon': [69.319431, -135.478286],'startDate':'2026-06-01'}, # Template from dict for BSP
        # 'FIL', # Generic template for site FIL and ILL
        # 'ILL'
        ])
    
SeepFlux = discoverFiles(
    projectPath=projectPath,
    siteID='SEEP',
    fileFormat='TOB3',
    searchPath='/mnt/d/data-dump/RDEC1/2026',
    ignoreFiles=['System_Operatn_Notes'],
    ignoreTraces=['buff_depth_Max','T_CDM_VOLT*','FETCH_*','separation_*','FreqFactor_*','process_time*','slowsequence_Tot','air_mass*','*_Cov','*_f_Tot','fetch_wd_*','_WPL_*','rho_*_*','alpha','beta','FC_*','ET','ET_*','FCH4_*']
    )

breakpoint()
SeepFlux = discoverFiles(projectPath=projectPath,siteID='SEEP',fileFormat='TOB3',processFiles=True)



firstStage(projectPath=projectPath,sites='SEEP',years=[2026])
# ecf32(projectPath=projectPath).make('SEEP')




