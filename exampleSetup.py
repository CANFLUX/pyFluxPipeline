from scripts.rawFileProcessing.rawFile import rawFile
from scripts.rawFileProcessing.fileInventory import fileInventory
from scripts.newProject import createProject
import shutil
import os

projectPath = 'testing/testProject'
if os.path.exists(projectPath):
    shutil.rmtree(projectPath)

createProject(projectPath=projectPath,sites=[
    'configurationFiles/SCL_template.yml', # Template from preexisting metadata file for SCL
    {'siteID': 'BSP','lat_lon': [69.319431, -135.478286]}, # Template from dict for BSP
    'FIL' # Generic template for site FIL
    ])

fileName = r"E:\data-dump\SCL\EddyPro\2024\eddypro_t_full_output_2025-05-02T224906_exp.csv"

# inspect the traces in raw files
fr = rawFile(
    fileName=fileName,
    fileID='EP_recalc_2024',
    siteID='SCL',
    fileNameMatch='eddypro_t_full_output*.csv',
    fileFormat='EddyProOutput',
    projectPath=projectPath,
    mode='identifyTraces'
    )
print('Edit: ',os.path.join(fr.projectPath,'Sites',fr.siteID,fr.fileFormat,f'{fr.fileID}.yml'))
# breakpoint()
fileInventory(
    fileID='EP_recalc_2024',
    siteID='SCL',
    fileFormat='EddyProOutput',
    projectPath=projectPath).fileSearch(r'E:\data-dump\SCL\2024')

# breakpoint()



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
    