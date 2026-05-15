from scripts.openProject import openProject
import shutil

if __name__ == '__main__':
    shutil.rmtree('testing')
    current = openProject.from_cmd(safeMode=False)
    # current.loadSiteConfiguration()
    print(current.siteInventory)
    breakpoint()