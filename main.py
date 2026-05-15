from scripts.rawFileProcessing.rawFile import rawFile
from scripts.openProject import openProject
import shutil
import os


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
# # breakpoint()
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
# # breakpoint()
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
# # breakpoint()
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

# breakpoint()


# python -m main --projectPath testing/testProject --sites configurationFiles/SCL_template.yml
if __name__ == '__main__':
    if os.path.exists('testing/testProject'):
        shutil.rmtree('testing/testProject')
    current = openProject.from_cmd(safeMode=False)
    # current.loadSiteConfiguration()
    print(current.defaultSettings)
    breakpoint()