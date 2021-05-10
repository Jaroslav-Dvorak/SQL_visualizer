print("time")
import time
print("copy")
import copy
print("from datetime import datetime, timedelta")
from datetime import datetime, timedelta
print("subprocess")
import subprocess
print("os")
import os
print("importint from tkinter import *")
from tkinter import *
print("importint from tkinter import messagebox")
from tkinter import messagebox
print("importint from tkinter.ttk import *")
from tkinter.ttk import *
print("from matplotlib import backend_bases, backends")
from matplotlib import backend_bases, backends
print("from matplotlib import pyplot as plt")
from matplotlib import pyplot as plt
print("from matplotlib import dates as mdates")
from matplotlib import dates as mdates
import pyodbc
import locale
import types
import sys
import configRW

locale.setlocale(locale.LC_ALL, "czech")    # nastavení časových formátů na CZ

windows = sys.platform.startswith("win")
ConfigData = configRW.read_config("config.ini")["KMT"]
database = ConfigData["database"]
server = ConfigData["server"]
user = ConfigData["user"]
password = ConfigData["password"]
if windows:
    driver = 'SQL Server'
    # driver = '{ODBC Driver 17 for SQL Server}'
else:
    driver = 'FreeTDS'


def progress_update(val, text):
    label.configure(text=text)
    progress['value'] = val
    root.update_idletasks()
    root.update()

def get_data(stroj, time_from, time_to):
    """Downolades data from MSSQL"""

    # print(f'Connecting to database "{database}" on SQL server "{server}"...')
    progress_update(20, f'Connecting to database "{database}" on SQL server "{server}"...')

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
        # print("Connection to SQL successful!")
        cursor = conn.cursor()

    cursor.execute("SELECT NAZEV_STROJE, ID_STROJE FROM STROJ")  # stažení seznamu strojů
    seznam_stroju = dict(cursor.fetchall())  # jako dictionary

    start_time = time.time()    # proměnná pro měření času

    # print("Acquiring data...")
    progress_update(40, "Acquiring data...")

    time_from = time_from.replace(microsecond=0)
    time_to = time_to.replace(microsecond=0)

    id_stroje = seznam_stroju[stroj]    # id_stroje - int podle názvu
    cursor.execute("SELECT NAZEV_UDALOSTI, ID_UDALOSTI FROM UDALOST")   # stažení seznamu událostí
    id_udalosti = dict(cursor.fetchall())                               # jako dictionary
    id_udalost_reversed = dict(map(reversed, id_udalosti.items()))      # převrácení klíč <--> hodnota

    # zjištění stavu stroje před začátkem grafu
    cursor.execute(
        f"SELECT TOP 1 ID_UDALOSTI FROM DATA_STROJU WHERE CAS < '{time_from}' AND ID_STROJE = {id_stroje} AND "
        f"(ID_UDALOSTI = {id_udalosti['Provoz']} OR ID_UDALOSTI = {id_udalosti['Naprazdno']} OR "
        f"ID_UDALOSTI = {id_udalosti['Zastaveno']}) ORDER BY CAS DESC")

    predchozi_stav = cursor.fetchone()
    if predchozi_stav is not None:
        predchozi_stav = predchozi_stav[0]          # z databáze přichází (int, ) - je potřeba pouze int
    else:
        predchozi_stav = None                       # pokud není záznam před vybraným časovým intervalem

    # stažení relevantních dat
    cursor.execute(f"SELECT ID_UDALOSTI, CAS FROM DATA_STROJU WHERE CAS BETWEEN '{time_from}' AND '{time_to}' "
                   f"AND ID_STROJE = {id_stroje} ORDER BY CAS")
    table = cursor.fetchall()
    # print(f"Transfered in {round(time.time() - start_time, 3)}s")
    if predchozi_stav is None:
        try:
            print("info: první záznam v databázi až:", datetime.strftime(table[0][1], "%d.%m.%Y %H:%M:%S"))
        except IndexError:
            print("Žádný záznam v databázi.")
            exit()

    # print("Preparing data...")
    progress_update(60, "Preparing data...")

    start_time = time.time()                        # proměnná pro měření času
    compl_data = {}                                 # dictionary pro kompletní balík dat
    for ud in id_udalosti:                          # vytvoření klíčů podle názvu událostí s hodnotou prázdného listu
        compl_data[ud] = []

    for j in ["Provoz", "Zastaveno", "Naprazdno"]:  # nastavení začátku grafu podle zadaného času
        if predchozi_stav == id_udalosti[j]:        # zjištění stavu stroje pro začátek grafu
            compl_data[j].append(time_from)         # první hodnota

    # rozstřídění dat podle id_události
    for row in table:                                               # table [(int, datetime), (int, datetime),...]
        compl_data[id_udalost_reversed[row[0]]].append(row[1])      # id_udalost_reversed { int : nazev udalosti, ...}

    last = {}
    for j in ["Provoz", "Zastaveno", "Naprazdno"]:                  # zjištění posledního stavu stroje
        if len(compl_data[j]) > 0:                                  # ošetření indexu prázdného listu
            last[j] = compl_data[j][-1]
    compl_data[max(last, key=lambda k: last[k])].append(time_to)    # zakončení grafu podle zadaného času
    # print(f"Prepared in {round(time.time() - start_time, 3)}s")     # výpis doby přípravy datového balíku

    # data z počítadel
    cursor.execute(F"SELECT POCITADLO, CAS FROM POCITADLA WHERE ID_STROJE={id_stroje} AND "
                   f" CAS BETWEEN '{time_from}' AND '{time_to}' ORDER BY CAS")
    counter_status = cursor.fetchall()

    return compl_data, counter_status
    # example: { "Provoz" : datetime, "Naprazdno" : datetime, "Zastaveno" : datetime, "Porucha1" : datetime, ...}


class Dataformat:
    """Zformátuje data pro grafické zobrazení"""
    def __init__(self, tmstmps, time_from, time_to):
        # print("Formating...")
        progress_update(80, "Formating...")

        start_time = time.time()                                        # měření času
        self.time_from = time_from                                      # začátek grafu
        self.time_to = time_to                                          # konec grafu
        self.timestamps, self.counter_status = copy.deepcopy(tmstmps)   # kopie vložených dat

        self.F_T = self.stamps2from_to()                                # vytvoření začátku a konce stavu
        # print(f"Formated in {round(time.time() - start_time, 3)}s")

    def stamps2from_to(self):
        """Převede časové známky z listu to listu o dvou hodnotách - kdy stav začal a kdy skončil"""
        out = {}
        # příprava dict s relevantními keys
        for k in self.timestamps.keys():
            out[k] = []

        def lstfirsts(lsts):
            """Vrátí dict s prvním záznamem z listu hodnot, pokud existuje, jinak None"""
            res = {}
            for k, v in lsts.items():
                try:
                    res[k] = v[0]
                except IndexError:
                    res[k] = None
            return res

        cmp = lstfirsts(self.timestamps)  # načtení nejdřívějších časů všech stavů

        while True:
            start = min(v for v in cmp.values() if v is not None)  # prvotní - nejnižší pro iteraci
            for k, v in cmp.items():                               # nalezení názvu události pro prvotní
                if v == start:
                    what = k
            self.timestamps[what].pop(0)                           # vymazání prvotního
            cmp = lstfirsts(self.timestamps)                       # nové načtení nejdřívějších časů
            if all(v is None for v in cmp.values()):               # konec třídění
                return out
            else:
                if what == "Provoz" or what == "Naprazdno" or what == "Zastaveno":  # čas konce provozní události
                    stop = min(v for k, v in cmp.items() if v is not None
                               and(k == "Provoz" or k == "Naprazdno" or k == "Zastaveno"))
                else:
                    try:
                        stop = min(v for k, v in cmp.items() if v is not None      # čas konce poruchové události
                                   and (k == "Provoz" or k == "Naprazdno"))
                    except ValueError:
                        stop = self.time_to                         # pro případ, že graf končí poruchovým stavem
            start = mdates.date2num(start)                # převedení datetime na float
            stop = mdates.date2num(stop)                  # převedení datetime na float
            out[what].append((start, stop))                         # připnutí kompletního tuplu na dict

    def durations(self, time_from=None, time_to=None):
        """spočítá dobu trvání událostí"""
        out = {}
        if time_from is None and time_to is None:   # pokud nejsou zadány časové parametry
            f_t = self.F_T
        else:
            f_t = self.cut(time_from, time_to)      # vystřižení časového úseku
        for K, V in f_t.items():
            out[K] = []
            for v in V:
                out[K].append(v[1]-v[0])
        return out      # { "provoz" : [1.415, 0.47], "porucha1" : [0.124] }  kde float je timestamp pro matplotlib

    def brokenbarh(self):
        """převede tuple start-stop ve slovníku na start-duration"""
        out = {}
        durs = self.durations()
        for K, V in self.F_T.items():
            out[K] = []
            for i, v in enumerate(V):
                out[K].append((v[0], durs[K][i]))
        return out

    def cut(self, time_from, time_to):
        """vystřihne data a ohradí vloženými časovými známkami"""
        out = {}
        for K, V in self.F_T.items():
            out[K] = []
            for i, v in enumerate(V):
                if v[0] < time_from < v[1]:
                    out[K].append((time_from, v[1]))
                if time_from <= v[0] and time_to >= v[1]:
                    out[K].append(v)
                if v[0] < time_to < v[1]:
                    out[K].append((v[0], time_to))
        return out

    def suma(self, time_from=None, time_to=None):
        """spočítá kompletní dobu trvání jednotlivých událostí"""
        res = {}
        for k, poleTupls in self.durations(time_from, time_to).items():
            sm = 0.0
            for tupl in poleTupls:
                sm += tupl
            sm = mdates.num2timedelta(sm)     # převod z float na timedelta
            res[k] = sm                                 # připnutí na dict
        return res

    def pocet(self, time_from=None, time_to=None):
        """vrátí počet výskytů jednotlivých událostí"""
        out = {}
        if time_from is None and time_to is None:
            f_t = self.F_T
        else:
            f_t = self.cut(time_from, time_to)          # výběr specifického časového úseku
        for K, V in f_t.items():
            out[K] = len(V)
        return out

    def production(self, time_from, time_to):
        """vrátí počet vyrobených kusů v časovém období"""
        data = [d[0] for d in self.counter_status if time_from < d[1] < time_to]
        counter_states = []
        for i, d in enumerate(data, 1):
            try:
                r = data[i] - d
            except IndexError:
                break
            if r >= 0:
                counter_states.append(r)
            else:
                counter_states.append(data[i])
        producted = sum(counter_states)
        return producted


class Graf:
    """vykreslí graf pomocí knihovny matplotlib"""
    def __init__(self, stroj, time_from, time_to):

        self.time_from = time_from
        self.time_to = time_to

        start_time = time.time()
        self.data = get_data(stroj=stroj, time_from=time_from, time_to=time_to)    # stažení dat z db
        self.formated = Dataformat(tmstmps=self.data, time_from=time_from, time_to=time_to)  # formát (start, stop)
        self.BrokData = self.formated.brokenbarh()      # formát (start, duration)

        # print(self.formated.production(time_from=time_from, time_to=time_to))

        # plt.style.use(plt.style.available[4])
        # plt.xkcd()

        progress_update(100, "Rendering...")

        self.fig = plt.figure(figsize=(16, 8))      # vytvoření okna pro graf
        self.fig.suptitle(stroj, fontsize=16)       # hlavní titulek grafu
        self.fig.tight_layout()
        self.fig.subplots_adjust(bottom=0.11, left=0.1, right=0.98, top=0.94, wspace=0.05)  # vystředění grafu

        self.ax1 = plt.subplot2grid((4, 4), (0, 0), colspan=3, rowspan=1)                   # graf provozu vlevo nahoře
        self.ax2 = plt.subplot2grid((4, 4), (0, 3), rowspan=1)                              # graf provozu vpravo nahoře
        self.ax3 = plt.subplot2grid((4, 4), (1, 0), colspan=3, rowspan=3, sharex=self.ax1)  # graf poruch vlevo dole
        self.ax4 = plt.subplot2grid((4, 4), (1, 3), rowspan=3, sharey=self.ax3)             # graf poruch vpravo dole

        plt.setp(self.ax1.get_xticklabels(), visible=False)                 # skrýt osu x vlevo nahoře
        plt.setp(self.ax3.get_xticklabels(), rotation=45, ha="right")       # popisky časové osy pootočit
        plt.setp(self.ax4.get_yticklabels(), visible=False)                 # skrýt osu y vpravo dole

        # volání funkce, která simuluje při zoomu stisknuté x pro zoom pouze x osy
        self.fig.canvas.toolbar.press_zoom = types.MethodType(self.press_zoom, self.fig.canvas.toolbar)
        self.ax1.callbacks.connect('xlim_changed', self.on_xlims_change_1)  # callback pro vykreslení po zoomu
        self.ax3.callbacks.connect('xlim_changed', self.on_xlims_change_3)  # callback pro vykreslení po zoomu

        # definice pro vykreslování časové osy
        self.locator = mdates.AutoDateLocator()
        self.formatter = mdates.ConciseDateFormatter(self.locator)

        f = ['%Y',          # ticks are mostly years
             '%B',          # ticks are mostly months
             '%#d.%#m.',    # ticks are mostly days
             '%#H:%M',      # hrs
             '%#H:%M',      # min
             '%S.%f', ]     # secs
        self.formatter.formats = f
        self.formatter.zero_formats = f
        self.formatter.offset_formats = ['', '', '', '', '', '', '']           # vpravo pod osou - nic

        left_date = datetime.strftime(time_from, "%d.%m.%Y\n%H:%M:%S")         # dt přesného začátku grafu
        right_date = datetime.strftime(time_to, "%d.%m.%Y\n%H:%M:%S")          # dt přesného konce grafu

        self.left_date = self.fig.text(0.01, 0.1, left_date, weight='bold')    # pozice dt začátku
        self.right_date = self.fig.text(1.76, 0.1, right_date, weight='bold')  # pozice dt konce

        self.production = self.fig.text(0.43, 0.01, "", weight='bold',         # pozice production textu (vyrobeno kusů)
                                        horizontalalignment='center')

        self.high_ax3 = 100                                                 # výška grafu poruch
        self.yticks, self.ylabels, self.high_bahr = self.poruchy_labels()   # pozice popisků, popisky, výška brok-bahrs

        # roztažení y osy sníží výšku brok-bahrs (kosmetická úprava, pokud je málo relevantních poruch)
        if len(self.yticks) > 5:
            self.zero_ax3 = 0
        else:
            self.zero_ax3 = -100
        self.ax3.set_ylim(self.zero_ax3, self.high_ax3)     # nastavení y osy pro poruchy (vlevo a vpravo dole)

        # odebrání tick marks
        for tick in self.ax3.yaxis.get_major_ticks():
            tick.tick1line.set_markersize(0)
        for tick in self.ax4.yaxis.get_major_ticks():
            tick.tick1line.set_markersize(0)
        self.ax4.grid(which="minor")

        self.barhs = []
        self.barhs_vals = []

        self.p_n_z_1()      # graf vlevo nahoře
        # self.pie_2()      # graf vpravo nahoře
        self.poruchy_3()    # graf vlevo dole
        # self.poruchy_4()  # graf vpravo dole

        # print(f"Rendered in {round(time.time() - start_time, 3)}s")
        root.destroy()
        root.quit()

    def p_n_z_1(self):
        """vytvoří graf broken-barh pro tři základní stavy stroje"""
        self.ax1.set_ylim(0, 30)    # výška
        self.ax1.set_xlim(self.time_from, self.time_to)     # osa x - začátek a konec

        self.ax1.set_yticks([25, 15, 5])                                # definice pozic ukazatelů
        self.ax1.set_yticklabels(["Provoz", "Naprazdno", "Zastaveno"])  # definice labels sloupců

        # odstranění ukazatelů na y-ose
        for tick in self.ax1.yaxis.get_major_ticks():
            tick.tick1line.set_markersize(0)

        # nastavení ukazatelů podle definice v __init__
        self.ax1.xaxis.set_major_locator(self.locator)
        self.ax1.xaxis.set_major_formatter(self.formatter)

        self.ax1.set_yticks([10, 20, 30], minor=True)   # pozice sloupců
        self.ax1.grid(which="minor")                    # oddělení sloupců

        # definice grafu
        self.ax1.broken_barh(self.BrokData["Provoz"], (20, 10), facecolors='tab:green')
        self.ax1.broken_barh(self.BrokData["Naprazdno"], (10, 10), facecolors='tab:orange')
        self.ax1.broken_barh(self.BrokData["Zastaveno"], (0, 10), facecolors='tab:red')

    def pie_2(self, time_from=None, time_to=None):
        """vytvoří pie chart základních stavů stroje v závislosti na aktuálním zoomu"""
        sumy = self.formated.suma(time_from, time_to)   # celkový čas jednotlivých stavů

        def dt2str(dt):
            dt = dt - timedelta(microseconds=dt.microseconds)
            return str(dt).replace(", ", "\n")

        suma_p = sumy["Provoz"]
        suma_n = sumy["Naprazdno"]
        suma_z = sumy["Zastaveno"]
        suma_celkem = suma_p + suma_n + suma_z
        size1 = suma_p / suma_celkem
        size2 = suma_n / suma_celkem
        size3 = suma_z / suma_celkem
        suma_p = dt2str(suma_p)
        suma_n = dt2str(suma_n)
        suma_z = dt2str(suma_z)

        sizes = [size1, size2, size3]
        colors = ["tab:green", "tab:orange", "tab:red"]
        self.ax2.clear()        # odstranění grafu kvůli překreslení
        self.ax2.axis('off')    # odstranění ohraničení
        self.ax2.set_ylim(ymin=-0.9, ymax=0.7)  # vystředění y
        self.ax2.set_xlim(xmin=-1.5, xmax=0.5)  # vystředění x

        # nastavení procentuálních popisků, pokud je záznam více než jednoho stavu
        pocet_nula = 0
        for size in sizes:
            if size == 0:
                pocet_nula += 1
        if pocet_nula < 2:
            autoptc = '%1.1f%%'
        else:
            autoptc = None

        # definice grafu
        self.ax2.pie(sizes, shadow=True, colors=colors, pctdistance=0.7, frame=True, autopct=autoptc)

        # definice pie grafu celkových časů
        self.ax2.text(-1.8, 0.4, suma_p, color="tab:green", horizontalalignment='center', fontsize=12, weight="bold")
        self.ax2.text(-1.8, -0.13, suma_n, color="tab:orange", horizontalalignment='center', fontsize=12, weight="bold")
        self.ax2.text(-1.8, -0.7, suma_z, color="tab:red", horizontalalignment='center', fontsize=12, weight="bold")

    def poruchy_3(self):
        """vytvoří broken-barh poruchových stavů stroje"""
        position = self.high_bahr   # první pozice podle výšky sloupce
        high = self.high_bahr       # výška sloupce

        # definice všech sloupců relevantních poruch
        for ylabel in self.ylabels:
            self.ax3.broken_barh(xranges=self.BrokData[ylabel], yrange=(position - high*0.95, high*0.9))
            position += high

        # nastavení záhlaví grafu (popisky, ukazatele, mřížka)
        self.ax3.set_yticks([y*self.high_bahr for y in range(1, len(self.yticks))], minor=True)
        self.ax3.set_yticks(self.yticks)
        self.ax3.set_yticklabels(self.ylabels)
        self.ax3.grid(which="minor")

    def poruchy_4(self, time_from=None, time_to=None):
        """vytvoří sloupcový graf relevantních poruch podle počtu jejich zápisu"""
        # odstranění grafu kvůli překreslení
        for index, _ in enumerate(self.barhs):
            self.barhs[index].remove()
            self.barhs_vals[index].remove()
        self.barhs = []
        self.barhs_vals = []

        values = []
        position = self.high_bahr   # první pozice podle výšky sloupce
        high = self.high_bahr       # výška sloupce
        pocty = self.formated.pocet(time_from, time_to)     # získávání dat po každém překreslení

        # definice sloupcového grafu a popisků počtu
        for ylabel in self.ylabels:
            self.barhs.append(self.ax4.barh(width=pocty[ylabel], color="steelblue", height=high*0.9,
                              y=position - (high / 2)))
            self.barhs_vals.append(self.ax4.text(pocty[ylabel]*1.01, position - (high/2), pocty[ylabel],
                                   verticalalignment='center'))
            values.append(pocty[ylabel])
            position += high

        # velikost osy x podle umístění popiskků
        if len(values) == 0:
            scale = 1
        else:
            if max(values) > 0:
                scale = max(values)
            else:
                scale = 1
        self.ax4.set_xlim((0, scale*1.14))

    def poruchy_labels(self):
        """vrátí pozici ukazatelů, popisků osy y a výšky sloupce"""
        ylabels = []
        yticks = []
        # odfiltrování provozních od poruchových stavů
        for k, v in sorted(self.formated.pocet().items(), key=lambda kv: kv[1]):
            if k == "Provoz" or k == "Naprazdno" or k == "Zastaveno":
                continue
            if v > 0:
                ylabels.append(k)

        # pokud žádní porucha - vrací prázdné hodnoty (ošetření)
        pocet_poruch = len(ylabels)
        if pocet_poruch == 0:
            return [], [], 0

        # výška sloupce v závislosti na počtu poruch
        high_barh = (self.high_ax3 / pocet_poruch)
        position = high_barh
        for _ in ylabels:
            yticks.append(position - (high_barh / 2))
            position += high_barh
        return yticks, ylabels, high_barh

    @staticmethod
    def press_zoom(self, event):
        """simulace x klávesy během zoomu"""
        event.key = 'x'
        backends.backend_tkagg.NavigationToolbar2Tk.press_zoom(self, event)

    def on_xlims_change_1(self, axes):
        """provede úpravy po zoomu na grafu 1"""
        self.redraw(self.ax1.get_xlim()[0], self.ax1.get_xlim()[1])

    def on_xlims_change_3(self, axes):
        """provede úpravy po zoomu na grafu 3"""
        self.redraw(self.ax3.get_xlim()[0], self.ax3.get_xlim()[1])

    def redraw(self, time_from, time_to):
        """překreslí grafy a textové artist značky"""
        self.left_date.remove()                 # odstranění dt přesného začátku grafu
        self.right_date.remove()                # odstranění dt přesného konce grafu
        self.pie_2(time_from, time_to)          # vykreslení vpravo nahoře
        self.poruchy_4(time_from, time_to)      # vykreslení vpravo dole

        self.production.remove()                # odstanění production textu

        # převod float --> dt --> string a vložení na okraje osy x
        left_date = datetime.strftime(mdates.num2date(time_from), "%d.%m.%Y\n%H:%M:%S")
        right_date = datetime.strftime(mdates.num2date(time_to), "%d.%m.%Y\n%H:%M:%S")
        self.left_date = self.fig.text(0.1, 0.01, left_date, weight='bold', horizontalalignment='center')
        self.right_date = self.fig.text(0.76, 0.01, right_date, weight='bold', horizontalalignment='center')

        # počítadlo kusů:
        time_from_dt = mdates.num2date(time_from).replace(tzinfo=None)  # konverze float --> dt
        time_to_dt = mdates.num2date(time_to).replace(tzinfo=None)      # konverze float --> dt
        production = self.formated.production(time_from=time_from_dt, time_to=time_to_dt)   # získání dat
        production_txt = f"vyrobeno: {production:n} ks"      # formát podle locale

        # insert as text into chart
        self.production = self.fig.text(0.43, 0.01, production_txt, weight='bold',
                                        horizontalalignment='center', fontsize=12)


# odstranění nežádoucích/nepotřebných ovládacích prvků
backend_bases.NavigationToolbar2.toolitems = (
         ('Home', 'Reset original view', 'home', 'home'),
         ('Back', 'Back to  previous view', 'back', 'back'),
         ('Forward', 'Forward to next view', 'forward', 'forward'),
         (None, None, None, None),
         ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
         (None, None, None, None),
         ('Save', 'Save the figure', 'filesave', 'save_figure'),
         )


def printhelp():
    err = "Argumenty nezadány ve správném formátu!"
    helptext = \
"""   
1. arg - označení stroje\n
2. arg - čas začátku grafu ve formátu:
            den.měsíc.rok_hodina:minuta:vteřina
nebo
       - specifický interval 
          (v tom případě třetí argument nesmí existovat)
            - zs (začátek směny)
            - 24 (posledních 24h)
            - t  (poslední týden)
            - m  (posledních 30 dní)
3. arg - čas konce grafu ve formátu:
            den.měsíc.rok_hodina:minuta:vteřina
    
příklad:
MachineChart.exe BL_4 4.5.2020_12:55:30 8.5.2020_18:30:00

příklad:
MachineChart.exe R_10 24

Pro manuální výběr nezadávejte žádný argument.
"""
    messagebox.showerror("Špatně zadáno", err, detail=helptext)
    print(helptext)
    exit()


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


def run_selector():
    cwd = os.getcwd()
    if os.path.isfile(os.path.join(cwd, "Selector.exe")):
        subprocess.Popen(f'{cwd}\Selector.exe')
    else:
        subprocess.Popen(f'{cwd}\WPy64-3771\python-3.7.7.amd64\pythonw.exe "{cwd}\Selector.pyw"')
    sys.exit()


if len(sys.argv) == 4:
    Stroj = sys.argv[1]
    try:
        TimeFrom = datetime.strptime(sys.argv[2], "%d.%m.%Y_%H:%M:%S")
        TimeTo = datetime.strptime(sys.argv[3], "%d.%m.%Y_%H:%M:%S")
    except ValueError:
        printhelp()

elif len(sys.argv) == 3:
    Stroj = sys.argv[1]

    if sys.argv[2] == "zs":
        TimeFrom = start_shift(datetime.now())
        TimeTo = datetime.now()
    elif sys.argv[2] == "24":
        TimeFrom = datetime.now() - timedelta(hours=24)
        TimeTo = datetime.now()
    elif sys.argv[2] == "t":
        TimeFrom = datetime.now() - timedelta(days=7)
        TimeTo = datetime.now()
    elif sys.argv[2] == "m":
        TimeFrom = datetime.now() - timedelta(days=30)
        TimeTo = datetime.now()
    else:
        printhelp()

elif len(sys.argv) == 1:
    run_selector()
else:
    printhelp()

root = Tk()
label = Label()
label.pack()
progress = Progressbar(root, orient=HORIZONTAL, length=100, mode='determinate')
progress.pack()

inst = Graf(stroj=Stroj, time_from=TimeFrom, time_to=TimeTo)

plt.show()
