import os
import shutil
import win32com.client
import pyodbc
import configRW


windows = True
AllconfigIpData = configRW.read_config("config.ini")
AllconfigIpData = AllconfigIpData["KMT"]
database = AllconfigIpData["database"]
server = AllconfigIpData["server"]
user = AllconfigIpData["user"]
password = AllconfigIpData["password"]
if windows:
    driver = 'SQL Server'
    # driver = '{ODBC Driver 17 for SQL Server}'
else:
    driver = 'FreeTDS'


def get_data():
    # připojení k databázi
    print(f'Connecting to database "{database}" on SQL server "{server}"...')
    try:
        conn = pyodbc.connect(
            f"Driver={driver};"
            f"Server={server};"
            f"Database={database};"
            f"UID={user};"
            f"PWD={password}"
        )
    except Exception as e:
        print("Error SQL:")
        print(e)
        exit()
    else:
        print("Connection to SQL successful!")
    cursor = conn.cursor()
    cursor.execute("SELECT NAZEV_STROJE, ID_STROJE FROM STROJ")  # stažení seznamu strojů
    data = dict(cursor.fetchall())  # jako dictionary

    mach_nums = {}
    header_set = set(name.split('_')[0] for name in data.keys())
    for header_item in sorted(header_set):
        mach_nums[header_item] = []
        for machine_name in data.keys():
            if header_item == machine_name.split("_")[0]:
                mach_nums[header_item].append(machine_name.split('_')[1])
    return mach_nums


data = get_data()
shell = win32com.client.Dispatch("WScript.Shell")
cwd = os.getcwd()

intervals = {"tato směna": "zs", "den": "24", "týden": "t", "měsíc": "m"}
#\\10.110.10.36
# path = r'\\10.110.10.36\KMTDaten\01_Public\Dvořák\SQL_visualizer\dist\MachineChart'
PythonPath = f'{cwd}/WPy64-3771/python-3.7.7.amd64/pythonw.exe'
ProgramPath = f'{cwd}'
ProgramFile = "MachineChart.pyw"
IconFile = "icon.ico"
# program = "MachineChart.exe"

# path_program = os.path.join(PythonPath, ProgramFile)

mf = "stroje"

try:
    shutil.rmtree(mf)
except Exception as e:
    print(e)

os.mkdir(mf)
shortcut = shell.CreateShortCut(os.path.join(mf, "selector.lnk"))
shortcut.Targetpath = PythonPath
shortcut.WorkingDirectory = ProgramPath
shortcut.Arguments = f'"{os.path.join(ProgramPath, "Selector.pyw")}"'
shortcut.IconLocation = f"{os.path.join(ProgramPath, 'TFicon.ico')}"
shortcut.save()

for k in data:
    r = os.path.join(mf, k)
    os.mkdir(r)
    for n in data[k]:
        subdir = os.path.join(r, n)
        os.mkdir(subdir)
        for interval in intervals:
            file = os.path.join(subdir, interval)

            shortcut = shell.CreateShortCut(file + ".lnk")
            shortcut.Targetpath = PythonPath
            shortcut.WorkingDirectory = ProgramPath
            shortcut.Arguments = f'"{os.path.join(ProgramPath, ProgramFile)}" {k}_{n} {intervals[interval]}'
            shortcut.IconLocation = f"{os.path.join(ProgramPath, IconFile)}"
            shortcut.save()
            print(f"generated: {file}")
