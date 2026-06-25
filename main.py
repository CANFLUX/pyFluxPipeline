from scripts.rawFileProcessing.rawFile import rawFile
from scripts.rawFileProcessing.fileInventory import fileInventory
from scripts.newProject import createProject
import shutil
import os

import pandas as pd
import numpy as np


# ts = np.fromfile(r'C:\Users\jskeeter\gsc-permafrost\pyFluxPipeline\testing\testProject\Database\2024\SCL\raw\SSM_TS\posix_time.int64',dtype='int64')
# ts = pd.to_datetime(ts,unit='s')
# breakpoint()


# fileName = r"E:\data-dump\SCL\EddyPro\2024\eddypro_t_full_output_2025-05-02T224906_exp.csv"
# projectPath = 'testing/testProject'

# rf = rawFile(
#     fileName=fileName,
#     fileID='EP_recalc_2024',
#     siteID='SCL',
#     fileFormat='EddyProOutput',
#     projectPath=projectPath,
#     mode='identifyTraces'
#     )
# 
# rf = rawFile(
#     fileName=fileName,
#     fileID='EP_recalc_2024',
#     siteID='SCL',
#     fileFormat='EddyProOutput',
#     projectPath=projectPath,
#     mode='extractData'
# )

# fileName = r"E:\data-dump\SCL\2025\20250718\20750527-SHSC.WSM.SGT.240720_250718.csv"

# rf = rawFile(
#     fileName=fileName,
#     fileID='HOBO_WSM',
#     siteID='SCL',
#     fileFormat='HOBOcsv',
#     projectPath=projectPath,
#     mode='identifyTraces'
#     )
# 
# rf = rawFile(
#     fileName=fileName,
#     fileID='HOBO_WSM',
#     siteID='SCL',
#     fileFormat='HOBOcsv',
#     projectPath=projectPath,
#     mode='extractData'
# )

# fileName = r"E:\data-dump\SCL\2024\20240912\Met_Data122.dat"

# rf = rawFile(
#     fileName=fileName,
#     fileID='EC_Met',
#     siteID='SCL',
#     fileFormat='TOB3',
#     projectPath=projectPath,
#     mode='identifyTraces'
#     )
# 
# rf = rawFile(
#     fileName=fileName,
#     fileID='EC_Met',
#     siteID='SCL',
#     fileFormat='TOB3',
#     projectPath=projectPath,
#     mode='extractData'
#     )

# fileName = r'testing\data\TOA5_BBS.FLUX_2023_08_01_1530.dat'


# rf = rawFile(
#     fileName=fileName,
#     fileID='EC_Met',
#     siteID='BBS',
#     fileFormat='TOA5',
#     projectPath=projectPath,
#     mode='identifyTraces'
#     )




# python -m main --projectPath testing/testProject --sites configurationFiles/SCL_template.yml
if __name__ == '__main__':
    if os.path.exists('testing/testProject'):
        shutil.rmtree('testing/testProject')
    current = createProject.from_cmd(safeMode=False)
    breakpoint()
    # current.loadSiteConfiguration()
    # print(current.defaultSettings)
    

    # fileName = r"E:\data-dump\SCL\EddyPro\2024\eddypro_t_full_output_2025-05-02T224906_exp.csv"
    # projectPath = 'testing/testProject'

    # rf = rawFile(
    #     fileName=fileName,
    #     fileID='EP_recalc_2024',
    #     siteID='SCL',
    #     fileNameMatch='eddypro_t_full_output*.csv',
    #     fileFormat='EddyProOutput',
    #     projectPath=projectPath,
    #     mode='identifyTraces'
    #     )
    # 
    # fileInventory(
    #     fileID='EP_recalc_2024',
    #     siteID='SCL',
    #     fileFormat='EddyProOutput',
    #     projectPath=projectPath).fileSearch(r'E:\data-dump\SCL\2024')

    
    fileName = r"E:\data-dump\SCL\2024\20240912\Met_Data122.dat"
    projectPath = 'testing/testProject'

    rf = rawFile(
        fileName=fileName,
        fileID='EC_Met',
        siteID='SCL',
        fileNameMatch='Met_Data*.dat',
        fileFormat='TOB3',
        projectPath=projectPath,
        mode='identifyTraces'
        )
    
    fileInventory(
        fileID='EC_Met',
        siteID='SCL',
        fileFormat='TOB3',
        projectPath=projectPath).fileSearch(r'E:\data-dump\SCL\2024')
    