from datetime import datetime, timedelta
import pyodbc
import sys
import configRW
import os
import subprocess

windows = sys.platform.startswith("win")
AllconfigIpData = configRW.read_config("config.ini")
AllconfigIpData = AllconfigIpData["KMT"]
database = AllconfigIpData["database"]
server = AllconfigIpData["server"]
user = AllconfigIpData["user"]
password = AllconfigIpData["password"]
if windows:
    driver = 'SQL Server'
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
    cursor.execute("SELECT fullcode, id FROM machines")  # stažení seznamu strojů
    seznam_stroju = dict(cursor.fetchall())  # jako dictionary
    return seznam_stroju


def format2dict(pure_output_db):
    """vrátí dict ve formátu { stroj : [cislo, cislo,...] } z formátu { stroj_cislo : id_stroje }"""
    mach_nums = {}
    header_set = set(name.split('_')[0] for name in pure_output_db.keys())  # odfiltrování duplicit

    # přiloží číslo stroje do listu a pak k relevantnímu klíči
    for header_item in header_set:
        mach_nums[header_item] = []
        for machine_name in pure_output_db.keys():
            if header_item in machine_name:
                mach_nums[header_item].append(machine_name.split('_')[1])
    return mach_nums


def format2table(machines):
    """vrátí tabulku strojů a jejich čísel z formátu { stroj : [cislo, cislo,...] }"""
    header_lst = []
    rows = 0
    col_width = 0
    # definice počtu řádků a šířky tabulky
    for k, v in machines.items():
        header_lst.append(k)
        if len(v) > rows:
            rows = len(v)
        if len(k) > col_width:
            col_width = len(k)
    col_width += 4

    # první řádek - název sloupce
    header_str = "|"
    for item in header_lst:
        header_str += f"{item:^{col_width}}" + "|"
    separator1 = "_"*len(header_str)
    separator2 = "—"*len(header_str)

    # tabulka
    table = separator2 + "\n" + header_str + "\n" + separator2 + "\n"
    for n in range(rows):           # řádky
        for item in header_lst:     # pole
            try:
                table += "|" + f"{machines[item][n]:^{col_width}}"
            except IndexError:
                table += "|" + f"{' ':{col_width}}"
        table += "|" + "\n"
    table += separator1
    return table


def select_machine(db_dict):
    """vrátí název stroje a zajistí správný input, korespondující s dostupným strojem v databázi"""
    print("")
    print("Seznam dostupných strojů v databázi:")
    machines = format2dict(db_dict)
    print(format2table(machines))   # zobrazení tabulky dostupných strojů v databázi
    machine = None

    repete_message = "Zadaný výraz nesouhlasí. Příklad formátu: 'BM', 'bm', 'BM_1'."
    while True:
        stroj = input("zadejte označení stroje: ").upper()
        if stroj in machines.keys():  # případ zadání samotného názvu bez číslovky
            while True:               # přiložení čísla, pokud existuje
                cislo = input("zadejte číslo stroje: ")
                if cislo in machines[stroj]:
                    machine = stroj + "_" + cislo
                    break
                else:
                    print("Stroj " + stroj + " číslo " + cislo + " není veden v databázi.")
        elif "_" in stroj:            # případ zadání názvu stroje i s _ a číslem
            s, c = stroj.split("_")
            if s in machines.keys() and c in machines[s]:
                machine = stroj
                break
            else:
                print(repete_message)
                continue
        else:
            print(repete_message)
            continue
        break
    return machine


def start_shift(dt):
    """vrátí datetime začátuku směny"""
    ref = dt - timedelta(0, 0, 0, 0, 30, 5)     # časová "nula" na začátek ranní směny (5:30)
    if ref.hour < 8:                            # ranní směna
        return dt.replace(hour=5, minute=30, second=0, microsecond=0)
    elif 8 <= ref.hour < 16:                    # odpolední směna
        return dt.replace(hour=13, minute=30, second=0, microsecond=0)
    else:                                       # noční směna
        if dt.hour < 20:                        # překlenuta půlnoc - nutno odečíst den
            return (dt - timedelta(1)).replace(hour=21, minute=30, second=0, microsecond=0)
        else:
            return dt.replace(hour=21, minute=30, second=0, microsecond=0)


def check_strp(datestring, form):
    """vrací datetime podle stringu datestring a zadaného formátu form v případě, že je převod úspěšný, jinak None"""
    try:
        datestring = datetime.strptime(datestring, form)
        return datestring
    except ValueError:
        return None


def get_date(message):
    """vrací datetime nebo '' na základě inputů"""

    def add_time(date):
        """vrací čas z vloženého inputu přičtený k argumentu date"""
        time = None
        while time is None:
            time = check_strp(input("zadejte čas ve formátu 'HH:HH': "), "%H:%M")
            if time is None:
                print("Čas zadán ve špatném formátu. Příklad formátu: '10:45', '16:15'.")
        return date + timedelta(hours=time.hour, minutes=time.minute)

    while True:
        datestring = input(message)

        if datestring == "":        # v případě odentrování
            return datestring
        else:
            dt_out = check_strp(datestring, "%d.%m.")
            if dt_out is not None:                              # v případě nezadání roku, doplnění aktuálního
                dt_out = dt_out.replace(year=datetime.now().year)
                dt_out = add_time(dt_out)
                return dt_out

            dt_out = check_strp(datestring, "%d.%m.%Y")
            if dt_out is not None:
                dt_out = add_time(dt_out)                       # přičtení času
                return dt_out

            dt_out = check_strp(datestring, "%d.%m. %H:%M")     # v případě nezadání roku, doplnění aktuálního
            if dt_out is not None:
                dt_out = dt_out.replace(year=datetime.now().year)
                return dt_out

            dt_out = check_strp(datestring, "%d.%m.%Y %H:%M")
            if dt_out is not None:
                return dt_out

            print("Datum zadáno ve špatném formátu. "
                  "Příklad formátu: '15.3.', '5.10.2019', '18.5.2020 8:45', '18.5. 8:45'")


def select_datetime():
    """vrátí datetime, datetime ohraničující časový úsek od-do"""
    time_from = None
    time_to = None
    while time_from is None:        # ověření smyslu zadaného datetime oproti reálnému času
        time_from = get_date("zadejte počáteční datum nebo stiskněte enter pro začátek aktuální směny: ")
        if time_from == "":
            time_from = start_shift(datetime.now())
        if time_from > datetime.now():
            print("Zadaný čas je budoucnu.")
            time_from = None

    while time_to is None:          # ověření smyslu zadaného datetime oproti reálnému času
        time_to = get_date("zadejte konečné datum nebo stiskněte enter pro momentální okamžik: ")
        if time_to == "":
            time_to = datetime.now()
        if time_to > datetime.now():
            print("Zadaný čas je budoucnu.")
            time_to = None
            continue
        if time_to < time_from:     # ověření smyslu začátku a konce
            print("zadaný konečný čas je dřívější než počáteční.")
            time_to = None

    # SQL server nepřijímá formát s mikrosekundy
    time_from = time_from.replace(microsecond=0)
    time_to = time_to.replace(microsecond=0)
    return time_from, time_to

while True:
    stroj = select_machine(get_data())
    timefrom, timeto = [t.strftime("%d.%m.%Y_%H:%M:%S") for t in select_datetime()]
    cwd = os.getcwd()
    if os.path.isfile(os.path.join(cwd, "MachineChart.exe")):
        subprocess.Popen(f'{cwd}\MachineChart.exe {stroj} {timefrom} {timeto}')
    else:
        subprocess.Popen(f'{cwd}\WPy64-3771\python-3.7.7.amd64\pythonw.exe "{cwd}\MachineChart.pyw" {stroj} {timefrom} {timeto}')

