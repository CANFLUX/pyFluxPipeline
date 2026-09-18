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


reset = True

# wsl Note:
# if drive not discovered, try: sudo mount -t drvfs D: /mnt/d (or E: ...)

# drive = 'E:'
# if not os.path.isdir(drive):
#     drive = 'D:'
# projectPath = f'{drive}/GSC_Work/deltaFluxes'
projectPath = 'testing/myProject'
data_dump = '/mnt/e/data-dump'
if reset:
    if os.path.exists(projectPath):
        shutil.rmtree(projectPath)
if not os.path.isdir(projectPath):
    createProject(projectPath=projectPath,sitesList=[
        'configurationFiles/SCL_template.yml', # Template from preexisting metadata file for SCL
        'configurationFiles/RDEC1_Seep_template.yml', # Template from preexisting metadata file for RDEC1
        # {'siteID': 'BSP','lat_lon': [69.319431, -135.478286],'startDate':'2026-06-01'}, # Template from dict for BSP
        # 'FIL', # Generic template for site FIL and ILL
        # 'ILL'
        ])

if __name__ == '__main__' and reset:
    SeepFlux = discoverFiles(
        projectPath=projectPath,
        siteID='SEEP',
        fileFormat='TOB3',
        searchPath=data_dump+'/RDEC1/2026',
        findFiles=['*Flux_CSFormat*'],
        # ignoreFiles=['Time_Series'],
        ignoreTraces=['Bowen_ratio','daytime','d','sampleTime','Drop_rate_*','CH4_mole_fraction','nanoseconds_*','seconds_*','milliseconds_*','buff_depth_Max','T_CDM_VOLT*','FETCH_*','separation_*','FreqFactor_*','process_time*','slowsequence_Tot','air_mass*','*_Cov','*_f_Tot','fetch_wd_*','_WPL_*','rho_*_*','alpha','beta','FC_*','ET','ET_*','FCH4_*'],
        renameTraces={'SW_IN':'SW_IN_1_1_1','LW_IN':'LW_IN_1_1_1','SW_OUT':'SW_OUT_1_1_1','LW_OUT':'LW_OUT_1_1_1'},
        processFiles=False
        )
    breakpoint()
    SeepFlux = discoverFiles(projectPath=projectPath,siteID='SEEP',fileFormat='TOB3',processFiles=True)
    firstStage(projectPath=projectPath,sites='SEEP',years=[2026])
# SeepFlux = discoverFiles(
#     projectPath=projectPath,
#     siteID='SEEP',
#     fileFormat='TOB3',
#     searchPath='/mnt/d/data-dump/RDEC1/2026',
#     ignoreFiles=['System_Operatn_Notes'],
#     ignoreTraces=['buff_depth_Max','T_CDM_VOLT*','FETCH_*','separation_*','FreqFactor_*','process_time*','slowsequence_Tot','air_mass*','*_Cov','*_f_Tot','fetch_wd_*','_WPL_*','rho_*_*','alpha','beta','FC_*','ET','ET_*','FCH4_*']
# # =======
# #     searchPath=data_dump+'/RDEC1/20260614',
# #     findFiles=['Time_Series'],
# #     processFiles=True    
# #     # ignoreTraces=['sampleTime','Drop_rate_*','CH4_mole_fraction','nanoseconds_*','seconds_*','milliseconds_*','buff_depth_Max','T_CDM_VOLT*','FETCH_*','separation_*','FreqFactor_*','process_time*','slowsequence_Tot','air_mass*','*_Cov','*_f_Tot','fetch_wd_*','_WPL_*','rho_*_*','alpha','beta','FC_*','ET','ET_*','FCH4_*'],
# #     # renameTraces={'SW_IN':'SW_IN_1_1_1','LW_IN':'LW_IN_1_1_1','SW_OUT':'SW_OUT_1_1_1','LW_OUT':'LW_OUT_1_1_1'}
# # >>>>>>> f61a22d621677573e3a6d3043efdac0547024dc8
#     )



# ecf = ecf32(projectPath=projectPath,siteID='SEEP')
# ecf.biometCSV(years = [2026])
# breakpoint()




