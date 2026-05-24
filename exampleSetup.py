
from scripts.rawFileProcessing.fileInventory import fileInventory
from scripts.rawFileProcessing.rawFile import rawFile
from scripts.traceAnalysis.firstStage import firstStage
from scripts.newProject import createProject
import shutil
import os

reset = True

drive = 'E:'
if not os.path.isdir(drive):
    drive = 'D:'
projectPath = f'{drive}/GSC_Work/deltaFluxes'
if reset:
    if os.path.exists(projectPath):
        shutil.rmtree(projectPath)
if not os.path.isdir(projectPath):
    createProject(projectPath=projectPath,sites=[
        'configurationFiles/SCL_template.yml', # Template from preexisting metadata file for SCL
        {'siteID': 'BSP','lat_lon': [69.319431, -135.478286],'startDate':'2026-06-01'}, # Template from dict for BSP
        'FIL', # Generic template for site FIL and ILL
        'ILL'
        ])


# inspect the traces in raw files
Met2024 = rawFile(
    fileName=f"{drive}/data-dump/SCL/2024/20240912/Met_Data120.dat",
    fileID='Met2024',
    siteID='SCL',
    fileNameMatch='Met_Data*.dat',
    fileFormat='TOB3',
    projectPath=projectPath,
    mode='identifyTraces'
    )

MetWx2024 = rawFile(
    templateFile=f"{drive}/data-dump/SCL/2024/20240914/OverWinter.DEF",
    fileName=f"{drive}/data-dump/SCL/2024/20240914/WX_data.dat",
    fileID='MetWx2024',
    siteID='SCL',
    fileNameMatch='WX_data.dat',
    fileFormat='MixedArray',
    projectPath=projectPath,
    mode='identifyTraces'
)

# inspect the traces in raw files
Flux2024 = rawFile(
    fileName=f"{drive}/data-dump/SCL/2024/eddypro_t_full_output_2025-05-02T224906_exp.csv",
    fileID='Flux2024',
    siteID='SCL',
    fileNameMatch='eddypro_t_full_output*.csv',
    fileFormat='EddyProOutput',
    projectPath=projectPath,
    mode='identifyTraces',
    ignore=['DOY','daytime','x_peak','x_offset','x_10%','x_30%','x_50%','x_70%','x_90%','daytime','model','amplitude_resolution_hf','drop_out_hf','h2o_def_timelag','co2_def_timelag','ch4_def_timelag','bad_aux_tc1_LI-7700','bad_aux_tc2_LI-7700','bad_aux_tc1_LI-7700']
    )

Flux2025 = rawFile(
    fileName=f"{drive}/data-dump/SCL/2025/20250806/57840_Flux_CSFormat_19.dat",
    fileID='Flux2025',
    siteID='SCL',
    fileNameMatch='57840_Flux_CSFormat_*.dat',
    fileFormat='TOB3',
    projectPath=projectPath,
    mode='identifyTraces',
    ignore=['FETCH_MAX','FETCH_90','FETCH_80','FETCH_70','FETCH_FILTER','FETCH_INTRST','FP_FETCH_INTRST','FP_FETCH_INTRST','FP_EQUATION']
)

SSM = rawFile(
    fileName=f"{drive}/data-dump/SCL/2024/20240914/20750528-SHSC.SSM.SGT.240720_240913readout.csv",
    fileID='SSM_TS',
    siteID='SCL',
    fileNameMatch='20750528-SHSC.SSM.SGT*.csv',
    fileFormat='HOBOcsv',
    projectPath=projectPath,
    mode='identifyTraces',
    dataIntervalSeconds=3600.0 # were temporarily set to half-hourly, can just drop those data
    )


WSM = rawFile(
    fileName=f"{drive}/data-dump/SCL/2024/20240914/20750527-SHSC.WSM.SGT.240720_240913readout.csv",
    fileID='SSM_TS',
    siteID='SCL',
    fileNameMatch='20750527-SHSC.WSM.SGT*.csv',
    fileFormat='HOBOcsv',
    projectPath=projectPath,
    mode='identifyTraces',
    dataIntervalSeconds=3600.0 # were temporarily set to half-hourly, can just drop those data
    )

Met2024 = fileInventory(
    fileID=Met2024.fileID,
    siteID=Met2024.siteID,
    fileFormat=Met2024.fileFormat,
    projectPath=projectPath).fileSearch(f"{drive}/data-dump/SCL/2024")

MetWx2024 = fileInventory(
    fileID=MetWx2024.fileID,
    siteID=MetWx2024.siteID,
    fileFormat=MetWx2024.fileFormat,
    projectPath=projectPath)
MetWx2024.fileSearch(f"{drive}/data-dump/SCL/2024/20240914")
MetWx2024.fileSearch(f"{drive}/data-dump/SCL/2025/20250414")
MetWx2024.fileSearch(f"{drive}/data-dump/SCL/2025/20250619")

Flux2024 = fileInventory(
    fileID=Flux2024.fileID,
    siteID=Flux2024.siteID,
    fileFormat=Flux2024.fileFormat,
    projectPath=projectPath).fileSearch(f"{drive}/data-dump/SCL/2024")

Flux2025 = fileInventory(
    fileID=Flux2025.fileID,
    siteID=Flux2025.siteID,
    fileFormat=Flux2025.fileFormat,
    projectPath=projectPath)
Flux2025.fileSearch(f"{drive}/data-dump/SCL/2025")
Flux2025.fileSearch(f"{drive}/data-dump/SCL/2026")

SSM = fileInventory(
    fileID=SSM.fileID,
    siteID=SSM.siteID,
    fileFormat=SSM.fileFormat,
    projectPath=projectPath)
SSM.fileSearch(f"{drive}/data-dump/SCL/2024/20240914")
SSM.fileSearch(f"{drive}/data-dump/SCL/2025/20250718")

WSM = fileInventory(
    fileID=WSM.fileID,
    siteID=WSM.siteID,
    fileFormat=WSM.fileFormat,
    projectPath=projectPath)
WSM.fileSearch(f"{drive}/data-dump/SCL/2024/20240914")
WSM.fileSearch(f"{drive}/data-dump/SCL/2025/20250718")


NARR_SCL = rawFile(
    fileName=f"{drive}/data-dump/ncFiles/interpolatedTimeSeries.csv",
    fileID='NARR',
    siteID='SCL',
    fileNameMatch='interpolatedTimeSeries.csv',
    fileFormat='NARRcsv',
    projectPath=projectPath,
    mode='identifyTraces'
)

fileInventory(
    fileID=NARR_SCL.fileID,
    siteID=NARR_SCL.siteID,
    fileFormat=NARR_SCL.fileFormat,
    projectPath=projectPath).fileSearch(f"{drive}/data-dump/ncFiles")


NARR_BSP = rawFile(
    fileName=f"{drive}/data-dump/ncFiles/interpolatedTimeSeries.csv",
    fileID='NARR',
    siteID='BSP',
    fileNameMatch='interpolatedTimeSeries.csv',
    fileFormat='NARRcsv',
    projectPath=projectPath,
    mode='identifyTraces'
)

fileInventory(
    fileID=NARR_BSP.fileID,
    siteID=NARR_BSP.siteID,
    fileFormat=NARR_BSP.fileFormat,
    projectPath=projectPath).fileSearch(f"{drive}/data-dump/ncFiles")


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
    