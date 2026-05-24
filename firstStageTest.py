from scripts.traceAnalysis.firstStage import firstStage
from scripts.database.database import database
import matplotlib.pyplot as plt
import pandas as pd
import os

drive = 'E:'
if not os.path.isdir(drive):
    drive = 'D:'
projectPath = f'{drive}/GSC_Work/deltaFluxes'

firstStage(projectPath=projectPath,sites='SCL',years=[2024,2025,2026])

db = database(projectPath=projectPath)
fld = os.path.join(db.projectPath,'Database','YYYY','SCL','FirstStage')
df = pd.concat([
    db.loadTraceFolder(fld.replace('YYYY',str(y))) for y in range(2024,2027)
])
plt.figure()
plt.plot(df['SW_IN_NARR'].interpolate(limit=6,limit_area='inside'),marker='*')
plt.plot(df['SW_IN_1_1_1'])
plt.figure()
plt.plot(df['TA_1_1_1'])
plt.show()
breakpoint()
