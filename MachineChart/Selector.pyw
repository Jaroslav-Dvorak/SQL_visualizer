from tkinter import *
from tkinter import messagebox
from tkinter.ttk import *
from datetime import datetime as dt
from datetime import timedelta as tdelta
import sys
from functools import partial
import os
import subprocess
import pyodbc
import configRW


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
    cursor.execute("SELECT NAZEV_STROJE, ID_STROJE FROM STROJ")  # stažení seznamu strojů
    seznam_stroju = dict(cursor.fetchall())  # jako dictionary
    return seznam_stroju


class ChartPicker:
    def __init__(self, seznam_stroju):

        def start_shift(_dt):
            """vrátí datetime začátuku směny"""
            ref = _dt - tdelta(0, 0, 0, 0, 30, 5)  # časová "nula" na začátek ranní směny (5:30)
            if ref.hour < 8:  # ranní směna
                return _dt.replace(hour=5, minute=30, second=0, microsecond=0)
            elif 8 <= ref.hour < 16:  # odpolední směna
                return _dt.replace(hour=13, minute=30, second=0, microsecond=0)
            else:  # noční směna
                if _dt.hour < 20:  # překlenuta půlnoc - nutno odečíst den
                    return (_dt - tdelta(1)).replace(hour=21, minute=30, second=0, microsecond=0)
                else:
                    return _dt.replace(hour=21, minute=30, second=0, microsecond=0)

        if sys.platform.startswith("win"): self.dateformat, self.timeformat = ("%#d.%#m.", "%#H:%M")
        else: self.dateformat, self.timeformat = ("%-d.%-m.", "%-H:%M")

        minus_a_day = (dt.now() - tdelta(hours=24)).timestamp()
        current_shift_start = start_shift(dt.now()).timestamp()
        minus_a_min = dt.now().timestamp() - 60
        now = dt.now().timestamp()

        self.geometry = "850x600+50+10"
        self.title = "Selector"
        self.root = Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.callback_exit)
        self.root.title(self.title)
        self.root.geometry(self.geometry)

        nrow = 0
        ncolumn = 0

        picker_area = Frame(self.root)

        self.label_from = Label(picker_area, text="ZAČÁTEK GRAFU")
        self.label_from.grid(row=nrow, column=ncolumn)
        ncolumn += 1
        self.date_from = Entry(picker_area, width=5)
        self.date_from.grid(row=nrow, column=ncolumn)
        self.date_from.bind('<Key-Return>', lambda _: self.callback_enter("from"))
        ncolumn += 1
        self.time_from = Entry(picker_area, width=5)
        self.time_from.bind('<Key-Return>', lambda _: self.callback_enter("from"))
        self.time_from.grid(row=nrow, column=ncolumn)
        ncolumn += 1

        self.scale_from = Scale(picker_area,
                                from_=minus_a_day,
                                value=current_shift_start,
                                to=minus_a_min,
                                orient=HORIZONTAL, length=450,
                                command=self.callback_scale_from)
        self.scale_from.grid(row=nrow, column=ncolumn)
        ncolumn += 1
        ncolumn += 1

        nrow += 1
        ncolumn = 0

        ncolumn += 1
        ncolumn += 1
        ncolumn += 1
        self.scale_to = Scale(picker_area,
                              from_=minus_a_day,
                              value=now,
                              to=now,
                              orient=HORIZONTAL, length=450,
                              command=self.callback_scale_to)
        self.scale_to.grid(row=nrow, column=ncolumn)
        ncolumn += 1
        self.date_to = Entry(picker_area, width=5)
        self.date_to.grid(row=nrow, column=ncolumn)
        self.date_to.bind('<Key-Return>', lambda _: self.callback_enter("to"))
        ncolumn += 1
        self.time_to = Entry(picker_area, width=5)
        self.time_to.grid(row=nrow, column=ncolumn)
        self.time_to.bind('<Key-Return>', lambda _: self.callback_enter("to"))
        ncolumn += 1
        self.label_to = Label(picker_area, text="KONEC GRAFU")
        self.label_to.grid(row=nrow, column=ncolumn)
        picker_area.pack(expand=1)

        self.select_area = Frame(self.root)

        self.create_buttons(seznam_stroju)

        self.select_area.pack(expand=1)
        self.helpbutton = Button(text="?", command=self.callback_help, width=3)
        self.helpbutton.pack(side=RIGHT)
        self.consolebutton = Button(text=":/>", command=self.callback_console, width=3)
        self.consolebutton.pack(side=RIGHT)
        self.insert_time(_from=current_shift_start, _to=now)

        self.root.mainloop()

    def callback_scale_from(self, value):
        value = float(value)
        self.insert_time(_from=value)
        if value >= self.scale_to.get():
            self.scale_to.config(value=value+60)
            self.insert_time(_to=value+60)

    def callback_scale_to(self, value):
        value = float(value)
        self.insert_time(_to=value)
        if value <= self.scale_from.get():
            self.scale_from.config(value=value-60)
            self.insert_time(_from=value-60)

    def insert_time(self, _from=None, _to=None):
        if _from:
            self.date_from.delete(0, "end")
            self.time_from.delete(0, "end")
            self.date_from.insert(0, dt.strftime(dt.fromtimestamp(_from), self.dateformat))
            self.time_from.insert(0, dt.strftime(dt.fromtimestamp(_from), self.timeformat))
        if _to:
            self.date_to.delete(0, "end")
            self.time_to.delete(0, "end")
            self.date_to.insert(0, dt.strftime(dt.fromtimestamp(_to), self.dateformat))
            self.time_to.insert(0, dt.strftime(dt.fromtimestamp(_to), self.timeformat))

    def callback_enter(self, which):
        _dt = self.dt_parse()
        if not _dt:
            return
        _dt_from, _dt_to = _dt
        _dt_from = _dt_from.timestamp()
        _dt_to = _dt_to.timestamp()
        if which == "from":
            self.scale_to.config(from_=_dt_from)
            if _dt_from < self.scale_from.cget("from"):
                self.scale_from.config(from_=_dt_from, value=_dt_from)
            else:
                self.scale_from.config(from_=_dt_from)
        elif which == "to":
            self.scale_from.config(to=_dt_to)
            self.scale_to.config(value=_dt_to, to=_dt_to)

    def callback_buttons(self, item, n):
        parsed = self.dt_parse()
        if parsed:
            stroj = (item + "_" + str(n))
            timefrom, timeto = [t.strftime("%d.%m.%Y_%H:%M:%S") for t in parsed]
            cwd = os.getcwd()
            if os.path.isfile(os.path.join(cwd, "MachineChart.exe")):
                subprocess.Popen(f'{cwd}\MachineChart.exe {stroj} {timefrom} {timeto}')
            else:
                subprocess.Popen(f'python.exe "{cwd}\MachineChart.pyw" {stroj} {timefrom} {timeto}')

    def callback_console(self):
        self.callback_exit()
        cwd = os.getcwd()
        program = "ui_console"
        cesta = os.path.join(cwd, program)
        if os.path.isfile(cesta + ".exe"):
            subprocess.Popen(cesta + ".exe")
        else:
            subprocess.Popen(f'python.exe "{cesta}.py"')

    def callback_help(self):
        description = \
                """
    BL  - Balící linka
    BM  - BoMa (obráběcí automat)
    KFM - Plnící automat
    KMP - Kompletovač uzávěrů
    LL  - Lakovací linka
    LS  - Laser
    R   - Rážovačka
    TMP - Tampoprint
    VH  - Váha
                """
        geometry = "+860+50"
        self.help = Tk()
        # self.root.protocol("WM_DELETE_WINDOW", self.callback_exit)
        self.help.title("vysvětlivky")
        self.description = Label(self.help, text=description, font="Courier")
        self.description.pack(side=BOTTOM)
        self.help.geometry(geometry)

    def callback_exit(self):
        self.root.destroy()
        self.root.quit()

    def dt_parse(self):
        dateformat = self.dateformat.replace("#", "").replace("-", "")
        timeformat = self.timeformat.replace("#", "").replace("-", "")
        current_year = str(dt.now().year)
        try:
            _dt_from = dt.strptime(current_year+self.date_from.get()+self.time_from.get(), "%Y"+dateformat+timeformat)
            _dt_to = dt.strptime(current_year+self.date_to.get()+self.time_to.get(), "%Y"+dateformat+timeformat)
        except ValueError:
            messagebox.showerror("Špatně zadáno", "Špatně zadáno")
        else:
            if _dt_from < _dt_to <= dt.now():
                return _dt_from, _dt_to
            else:
                messagebox.showerror("špatné časy", "Špatné časy")

    def create_buttons(self, data):
        mach_nums = {}
        header_set = set(name.split('_')[0] for name in data.keys())
        for header_item in sorted(header_set):
            mach_nums[header_item] = []
            for machine_name in data.keys():
                if header_item == machine_name.split("_")[0]:
                    mach_nums[header_item].append(machine_name.split('_')[1])

        header_lst = []
        rows = 0
        # definice počtu řádků a šířky tabulky
        for k, v in mach_nums.items():
            header_lst.append(k)
            if len(v) > rows:
                rows = len(v)

        # první řádek - název sloupce
        for i, item in enumerate(header_lst):
            self.header = (Label(self.select_area, text=item))
            self.header.grid(row=0, column=i)

        r = 1
        c = 0
        for n in range(rows):  # řádky
            for item in header_lst:  # pole
                try:
                    self.number = Button(self.select_area, text=mach_nums[item][n],
                                         command=partial(self.callback_buttons, item, mach_nums[item][n]))
                    self.number.grid(row=r, column=c)
                except IndexError:
                    pass
                c += 1
            r += 1
            c = 0


inst = ChartPicker(get_data())
