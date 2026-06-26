# from scripts.rawFileProcessing.fileInventory import fileInventory
from scripts.rawFileProcessing.rawFile import rawFile
# from scripts.traceAnalysis.firstStage import firstStage
from scripts.rawFileProcessing.parseCSI import discoverCSI
from scripts.newProject import createProject
from scripts.siteConfiguration import siteConfiguration
import shutil
import os
from scripts.ecf32.ecf32 import ecf32
from scripts.database.database import database


reset = True

drive = 'E:'
if not os.path.isdir(drive):
    drive = 'D:'
# projectPath = f'{drive}/GSC_Work/deltaFluxes'
projectPath = 'testing/myProject'
if reset:
    if os.path.exists(projectPath):
        shutil.rmtree(projectPath)
if not os.path.isdir(projectPath):
    createProject(projectPath=projectPath,sites=[
        # 'configurationFiles/SCL_template.yml', # Template from preexisting metadata file for SCL
        'configurationFiles/RDEC1_Seep_template.yml', # Template from preexisting metadata file for RDEC1
        # {'siteID': 'BSP','lat_lon': [69.319431, -135.478286],'startDate':'2026-06-01'}, # Template from dict for BSP
        # 'FIL', # Generic template for site FIL and ILL
        # 'ILL'
        ])
    
SeepFlux = discoverCSI(projectPath=projectPath,siteID='SEEP',searchPath='/mnt/d/data-dump/RDEC1/20260614')
# ecf32(projectPath=projectPath).make('SEEP')


