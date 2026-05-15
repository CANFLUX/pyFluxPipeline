from scripts.openProject import openProject


if __name__ == '__main__':
    current = openProject.from_cmd(safeMode=False)
    print(current)