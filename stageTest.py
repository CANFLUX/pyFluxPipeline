from scripts.traceAnalysis.firstStage import firstStage
from scripts.traceAnalysis.secondStage import secondStage
from scripts.database.database import database
import matplotlib.pyplot as plt
import pandas as pd
import shutil
import os

drive = 'E:'
if not os.path.isdir(drive):
    drive = 'D:'
# projectPath = f'{drive}/GSC_Work/deltaFluxes'
projectPath = 'testing/myProject'

firstStage(projectPath=projectPath,sites='SCL',years=[2024,2025,2026])
shutil.copy2(f"{projectPath}/Database/Calculation_Procedures/TraceAnalysis_ini/SCL_config.yml",r'./configurationFiles/SCL_config.yml')
secondStage(projectPath=projectPath,sites='SCL',years=[2024,2025,2026])
db = database(projectPath=projectPath)
fld = os.path.join(db.projectPath,'Database','YYYY','SCL','SecondStage')
df = pd.concat([
    db.loadTraceFolder(fld.replace('YYYY',str(y))) for y in range(2024,2027)
])
# breakpoint()
# df['FCH4']*=1e3
# fig,ax=plt.subplots(2)
# ax[0].plot(df['FCO2'])#.interpolate(limit=6,limit_area='inside'),marker='*')
# ax[1].plot(df['FCH4'])
# # plt.figure()
# # plt.plot(df['TA_1_1_1'])
# # plt.show()

# # plt.figure()
# # plt.scatter(df['FCO2'],df['FCO2_QC'])
print(df[['H','LE','FCO2','FCH4']].describe())
df.to_csv('testing/SCL_data.csv',index_label='timestamp')

