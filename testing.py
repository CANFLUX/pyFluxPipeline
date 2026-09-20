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
import yaml

if __name__ == '__main__':

    reset = True

    # wsl Note:
    # if drive not discovered, try: sudo mount -t drvfs D: /mnt/d (or E: ...)

    data_dump = 'data-dump'
    for drive in ['E:','D:','/mnt/d','/mnt/e']:
        if os.path.isdir(os.path.join(drive,data_dump)):
            data_dump = os.path.join(drive,data_dump)
            break
        else: drive = None
    if drive is None:
        exit('No drive/mnt present where expected, if using wsl, try: sudo mount -t drvfs D: /mnt/d (or E: ...)')
        
    # projectPath = f'{drive}/GSC_Work/deltaFluxes'
    projectPath = 'testing/myProject'
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
        
    # Get met files loaded first
    CSFormat = {
        'fileFormat':'TOB3',
        'findFiles':['*Flux_CSFormat*'],
        'ignoreTraces':['Bowen_ratio','daytime','d','sampleTime','Drop_rate_*','CH4_mole_fraction','nanoseconds_*','seconds_*','milliseconds_*','buff_depth_Max','T_CDM_VOLT*','FETCH_*','separation_*','FreqFactor_*','process_time*','slowsequence_Tot','air_mass*','*_Cov','*_f_Tot','fetch_wd_*','_WPL_*','rho_*_*','alpha','beta','FC_*','ET','ET_*','FCH4_*','sun_*','height_*','hour_*','iteration_*'],
        'renameTraces':{'SW_IN':'SW_IN_1_1_1','LW_IN':'LW_IN_1_1_1','SW_OUT':'SW_OUT_1_1_1','LW_OUT':'LW_OUT_1_1_1'},
    }
    with open('configurationFiles/CSFormat.yml','w+') as f:
        f.write(yaml.safe_dump(CSFormat))

    with open('configurationFiles/CSFormat.yml') as f:
        CSFormat = yaml.safe_load(f)


    # Get met files loaded first
    Time_Series = {
        'fileFormat':'TOB3',
        'findFiles':['*Time_Series*'],
        # 'ignoreTraces':['Bowen_ratio','daytime','d','sampleTime','Drop_rate_*','CH4_mole_fraction','nanoseconds_*','seconds_*','milliseconds_*','buff_depth_Max','T_CDM_VOLT*','FETCH_*','separation_*','FreqFactor_*','process_time*','slowsequence_Tot','air_mass*','*_Cov','*_f_Tot','fetch_wd_*','_WPL_*','rho_*_*','alpha','beta','FC_*','ET','ET_*','FCH4_*','sun_*','height_*','hour_*','iteration_*'],
        # 'renameTraces':{'SW_IN':'SW_IN_1_1_1','LW_IN':'LW_IN_1_1_1','SW_OUT':'SW_OUT_1_1_1','LW_OUT':'LW_OUT_1_1_1'},
    }
    with open('configurationFiles/Time_Series.yml','w+') as f:
        f.write(yaml.safe_dump(Time_Series))

    with open('configurationFiles/Time_Series.yml') as f:
        Time_Series = yaml.safe_load(f) 
    SeepFlux = discoverFiles(
        projectPath=projectPath,
        siteID='SEEP',
        searchPath=data_dump+'/RDEC1/2026',#/20260614',        
        # processFiles=True,
        # useParalell=False,
        **Time_Series
        )
    fs = firstStage(projectPath=projectPath,sites='SEEP',years=[2026])


