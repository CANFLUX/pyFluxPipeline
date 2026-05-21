
from scripts.rawFileProcessing.fileInventory import fileInventory
from scripts.rawFileProcessing.rawFile import rawFile
from scripts.traceAnalysis.firstStage import firstStage
from scripts.newProject import createProject
import shutil
import os

projectPath = 'testing/testProject'

firstStage(projectPath=projectPath,sites='SCL')#,years=[2024,2025])
