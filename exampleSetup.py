
from scripts.rawFileProcessing.fileInventory import fileInventory
from scripts.rawFileProcessing.rawFile import rawFile
from scripts.traceAnalysis.firstStage import firstStage
from scripts.newProject import createProject
import shutil
import os

projectPath = 'testing/testProject'
if os.path.exists(projectPath):
    shutil.rmtree(projectPath)

createProject(projectPath=projectPath,sites=[
    'configurationFiles/SCL_template.yml', # Template from preexisting metadata file for SCL
    {'siteID': 'BSP','lat_lon': [69.319431, -135.478286],'startDate':'2026-06-01'}, # Template from dict for BSP
    'FIL' # Generic template for site FIL
    ])

root=  r'E:\data-dump\SCL'
if not os.path.isdir(root):
    root = r'D:\data-dump\SCL'

# inspect the traces in raw files
Met2024 = rawFile(
    fileName=root + r"\2024\20240912\Met_Data120.dat",
    fileID='Met2024',
    siteID='SCL',
    fileNameMatch='Met_Data*.dat',
    fileFormat='TOB3',
    projectPath=projectPath,
    mode='identifyTraces'
    )

# inspect the traces in raw files
Flux2024 = rawFile(
    fileName=root +r'\2024\eddypro_t_full_output_2025-05-02T224906_exp.csv',
    fileID='Flux2024',
    siteID='SCL',
    fileNameMatch='eddypro_t_full_output*.csv',
    fileFormat='EddyProOutput',
    projectPath=projectPath,
    mode='identifyTraces',
    ignore=['DOY','daytime','x_peak','x_offset','x_10%','x_30%','x_50%','x_70%','x_90%']
    )

Flux2025 = rawFile(
    fileName=root +'/2025/20250806/57840_Flux_CSFormat_19.dat',
    fileID='Flux2025',
    siteID='SCL',
    fileNameMatch='57840_Flux_CSFormat_*.dat',
    fileFormat='TOB3',
    projectPath=projectPath,
    mode='identifyTraces',
    ignore=['FETCH_MAX','FETCH_90','FETCH_80','FETCH_70','FETCH_FILTER','FETCH_INTRST','FP_FETCH_INTRST','FP_FETCH_INTRST','FP_EQUATION','daytime']
)


# inspect the traces in raw files
SSM = rawFile(
    fileName=root + r"\2024\20240914\20750528-SHSC.SSM.SGT.240720_240913readout.csv",
    fileID='SSM_TS',
    siteID='SCL',
    fileNameMatch='20750528-SHSC.SSM.SGT*.csv',
    fileFormat='HOBOcsv',
    projectPath=projectPath,
    mode='identifyTraces',
    dataIntervalSeconds=3600.0 # set to were temporarily set to half-hourly, can just drop those data
    )
print('Edit: ',os.path.join(Met2024.projectPath,'Sites',Met2024.siteID,'rawFiles',f'{Met2024.fileID}.yml'))
print('Edit: ',os.path.join(Flux2024.projectPath,'Sites',Flux2024.siteID,F'rawFiles',f'{Flux2024.fileID}.yml'))
# breakpoint()
fileInventory(
    fileID=Met2024.fileID,
    siteID=Met2024.siteID,
    fileFormat=Met2024.fileFormat,
    projectPath=projectPath).fileSearch(root + r'\2024')
fileInventory(
    fileID=Flux2024.fileID,
    siteID=Flux2024.siteID,
    fileFormat=Flux2024.fileFormat,
    projectPath=projectPath).fileSearch(root + r'\2024')
fileInventory(
    fileID=Flux2025.fileID,
    siteID=Flux2025.siteID,
    fileFormat=Flux2025.fileFormat,
    projectPath=projectPath).fileSearch(root + r'\2025')
fileInventory(
    fileID=Flux2025.fileID,
    siteID=Flux2025.siteID,
    fileFormat=Flux2025.fileFormat,
    projectPath=projectPath).fileSearch(root + r'\2026')
fileInventory(
    fileID=SSM.fileID,
    siteID=SSM.siteID,
    fileFormat=SSM.fileFormat,
    projectPath=projectPath).fileSearch(root)

# firstStage(projectPath=projectPath,sites='SCL',years=[2024,2025])

# # breakpoint()
# fileInventory(
#     fileID='EP_recalc_2024',
#     siteID='SCL',
#     fileFormat='EddyProOutput',
#     projectPath=projectPath).fileSearch(root + r'data-dump\SCL\2024')

# # breakpoint()



# # python -m main --projectPath testing/testProject --sites configurationFiles/SCL_template.yml
# if __name__ == '__main__':
#     if os.path.exists('testing/testProject'):
#         shutil.rmtree('testing/testProject')
#     current = createProject.from_cmd(safeMode=False)
#     breakpoint()

#     # current.loadSiteConfiguration()
#     # print(current.defaultSettings)
#     # breakpoint()

#     fileName = r"E:\data-dump\SCL\EddyPro\2024\eddypro_t_full_output_2025-05-02T224906_exp.csv"
#     projectPath = 'testing/testProject'

    # rf = rawFile(
    #     fileName=fileName,
    #     fileID='EP_recalc_2024',
    #     siteID='SCL',
    #     fileNameMatch='eddypro_t_full_output*.csv',
    #     fileFormat='EddyProOutput',
    #     projectPath=projectPath,
    #     mode='identifyTraces'
    #     )
    # # breakpoint()
    # fileInventory(
    #     fileID='EP_recalc_2024',
    #     siteID='SCL',
    #     fileFormat='EddyProOutput',
    #     projectPath=projectPath).fileSearch(r'E:\data-dump\SCL\2024')

    
    # fileName = r"E:\data-dump\SCL\2024\20240912\Met_Data122.dat"
    # projectPath = 'testing/testProject'

    # rf = rawFile(
    #     fileName=fileName,
    #     fileID='EC_Met',
    #     siteID='SCL',
    #     fileNameMatch='Met_Data*.dat',
    #     fileFormat='TOB3',
    #     projectPath=projectPath,
    #     mode='identifyTraces'
    #     )
    # # breakpoint()
    # fileInventory(
    #     fileID='EC_Met',
    #     siteID='SCL',
    #     fileFormat='TOB3',
    #     projectPath=projectPath).fileSearch(r'E:\data-dump\SCL\2024')
    