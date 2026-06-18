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

# shutil.copy2(f"{projectPath}/Database/Calculation_Procedures/TraceAnalysis_ini/SCL_config.yml",r'./configurationFiles/SCL_config.yml')
shutil.copy2(r'./configurationFiles/SCL_config.yml',f"{projectPath}/Database/Calculation_Procedures/TraceAnalysis_ini/SCL_config.yml")

firstStage(projectPath=projectPath,sites='SCL',years=[2024,2025,2026])
secondStage(projectPath=projectPath,sites='SCL',years=[2024,2025,2026])
db = database(projectPath=projectPath)
fld = os.path.join(db.projectPath,'Database','YYYY','SCL','SecondStage')
df = pd.concat([
    db.loadTraceFolder(fld.replace('YYYY',str(y))) for y in range(2024,2027)
])

df.to_csv('C:/Users/jskeeter/gsc-permafrost/neuralNetworkAnalysisTool/SCL_data.csv')

# import numpy as np
# df.loc[df['FCO2'].isna(),'FCO2_csi'] = np.nan
# print(df[['H','LE','FCO2','FCH4','FCO2_csi']].groupby(df.index.month).mean())
# df.to_csv('testing/SCL_data.csv',index_label='timestamp')
# A = df.loc[df.index.month<=5,['FCO2','SW_IN_1_1_1','FCO2_csi','FCH4']].dropna(how='any').copy() 
# fig = plt.figure()
# plt.grid()
# plt.scatter(A.index,A['FCO2'],marker='o')
# plt.scatter(A.index,A['FCO2_csi'],marker='*')
# fig.autofmt_xdate()
# plt.figure()
# plt.grid()
# plt.scatter(df['FCO2'],df['FCO2_csi'],marker='*')
# plt.figure()
# plt.grid()
# plt.scatter(df['H'],df['H_csi'],marker='*')
# plt.show()
# breakpoint()

