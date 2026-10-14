from submodules.helperFunctions.baseClass import fromYamlDefault,fromIniDefault
import os

configPath = os.path.join(os.path.split(__file__)[0].split('scripts')[0],'configurationFiles')

defaultSettings = fromYamlDefault(os.path.join(configPath,'defaults',"defaultSettings.yml"))
firstStageMetDefaults = fromYamlDefault(os.path.join(configPath,'defaults',"firstStageMetDefaults.yml"),asDataclass=False)

eddyproTemplate = fromIniDefault(os.path.join(configPath,'ghgTemplates','eddyproTemplate.eddypro'))
ghgTemplate = fromIniDefault(os.path.join(configPath,'ghgTemplates','ghgTemplate.metadata'))
ghgTranslator = fromYamlDefault(os.path.join(configPath,'ghgTemplates','ghgTranslations.yml'),asDataclass=False)

# variableInstrumentMap = fromYamlDefault(os.path.join(configPath,'rawFileSettings','variableInstrumentMap.yml'),asDataclass=False)
fileMetadata = fromYamlDefault(os.path.join(configPath,'rawFileSettings','fileMetadata.yml'))
