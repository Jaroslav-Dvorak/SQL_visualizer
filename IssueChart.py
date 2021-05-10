import sys
from datetime import datetime, timedelta
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pyodbc
import _config

# TODO:
#  implementace do funkce main
#  odchytání vyjímek při špatném připojení nebo nedostatku dat --> OK
#  udělat hranici a přizpůsobit barvy
#  přizpůsobit graf v závislosti délky ylabel
#  zalomení ylabels jen jendou

server = _config.server
database = _config.database
user = _config.user
password = _config.password
driver = _config.driver


if len(sys.argv) < 2:
    print(f"Nezadán argument operace, zvolena výchozí ({_config.operace}) ze souboru _config.py.")
    operace = _config.operace
else:
    operace = sys.argv[1]
if len(sys.argv) < 3:
    print(f"Nezadán argument intervalu, zvolen výchozí ({_config.interval}) ze souboru _config.py.")
    interval = timedelta(hours=_config.interval)
else:
    interval = timedelta(hours=int(sys.argv[2]))
if len(sys.argv) < 4:
    print(f"Nezadán argument maximálního počtu sloupců, zvolen výchozí ({_config.max_barhs}) ze souboru _config.py.")
    max_barhs = _config.max_barhs
else:
    max_barhs = int(sys.argv[3])


def get_data():
    """Vrátí četnost poruch na výrobní operaci z databáze jako {('porucha', 'stroj') : pocet} v časovém intervalu."""
    now = datetime.now().replace(microsecond=0)
    # timefrom = now - interval
    timefrom = now - interval#timedelta(0,0,0,0,0,interval)
    timeto = now

    try:
        conn = pyodbc.connect(
            f"Driver={driver};"
            f"Server={server};"
            f"Database={database};"
            f"UID={user};"
            f"PWD={password}"
        )

    except Exception as e:
        exception = str(e.__class__.__name__) + ": " + str(e)
        print(exception)
        return {(exception, "_"): 0}

    with conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT NAZEV_UDALOSTI, ID_UDALOSTI FROM UDALOST")       # stažení seznamu událostí
            if sys.platform == "linux" or sys.platform == "linux2":
                id_udalosti = {}
                for k,v in cursor.fetchall():
                    id_udalosti[k.encode("latin1").decode("cp1250")] = v
            else:
                id_udalosti = dict(cursor.fetchall())                               # jako dictionary
            id_udalost_reversed = dict(map(reversed, id_udalosti.items()))          # převrácení klíč <--> hodnota

            cursor.execute("SELECT NAZEV_STROJE, ID_STROJE FROM STROJ")             # stažení seznamu strojů
            seznam_stroju = dict(cursor.fetchall())                                 # jako dictionary
            seznam_stroju_reversed = dict(map(reversed, seznam_stroju.items()))     # převrácení klíč <--> hodnota

            cursor.execute(f"SELECT ID_STROJE FROM STROJ WHERE NAZEV_STROJE LIKE '%{operace}%'")
            ids_op = cursor.fetchall()
            if len(ids_op) == 0:
                print("Zadána neexistující výrobní operace!")
                exit()
            ids_op = [str(ID[0]) for ID in ids_op]
            sql_ids_op = " OR ID_STROJE=".join(ids_op)

            string = (f"SELECT ID_UDALOSTI, ID_STROJE FROM DATA_STROJU WHERE (ID_STROJE = {sql_ids_op}) "
                      f"AND (ID_UDALOSTI != {id_udalosti['Provoz']} "
                      f"     AND ID_UDALOSTI != {id_udalosti['Naprazdno']} "
                      f"     AND ID_UDALOSTI != {id_udalosti['Zastaveno']}) "
                      f"AND CAS BETWEEN '{timefrom}' AND '{timeto}' ORDER BY CAS")

            cursor.execute(string)
            pure_data = (cursor.fetchall())
        except Exception as e:
            exception = str(e.__class__.__name__) + ": " + str(e)
            print(exception)
            return {(exception, "_"): 0}

    counted = {tuple(u): 0 for u in pure_data}

    for pd in pure_data:
        pd = tuple(pd)
        if pd in counted.keys():
            counted[pd] += 1

    named = {}
    for k, v in counted.items():
        nazev_udalosti = id_udalost_reversed[k[0]]
        nazev_stroje = seznam_stroju_reversed[k[1]]
        named[(nazev_udalosti, nazev_stroje)] = v

    return named

matplotlib.rcParams['toolbar'] = "None"                                         # vyp toolbar
matplotlib.rcParams['ytick.major.pad'] = '65'                                   # posuv ylabels mimo graf
fig = plt.figure(figsize=(16, 8), facecolor="black")                            # vytvoření okna pro graf
# fig.suptitle(operace, fontsize=16)                                            # hlavní titulek grafu
fig.tight_layout()
fig.subplots_adjust(bottom=0.001, left=0.1, right=0.92, top=0.999, wspace=0)    # vystředění grafu
plt.style.use('dark_background')                                                # černé téma
fig.canvas.manager.full_screen_toggle()                                         # toggle fullscreen mode

ax4 = plt.subplot()                                                             # samotný graf poruch
ax_r = ax4.twinx()                                                              # duplikát kvůli ylabels napravo
high_ax4 = 100                                                                  # výška grafu

cmap = matplotlib.cm.get_cmap('autumn', max_barhs)                              # paleta barev
colors = []
for i in range(cmap.N):
    colors.append(cmap(i)[:3])  # returns rgba, we take only first 3 so we get rgb


def labels(data):
    """vrátí pozici ukazatelů, popisků osy y a výšky sloupce"""
    ylabels = []
    yticks = []
    data = reversed(sorted(data.items(), key=lambda kv: kv[1]))

    i = 0
    for k, v in data:
        ylabels.append(k)
        i += 1
        if max_barhs == i:
            break

    # pokud žádná porucha - vrací prázdné hodnoty (ošetření)
    pocet_poruch = len(ylabels)
    if pocet_poruch == 0:
        return [], [], 0

    # výška sloupce v závislosti na počtu poruch
    high_barh = (high_ax4 / pocet_poruch)
    position = high_barh
    for _ in ylabels:
        yticks.append(position - (high_barh / 2))
        position += high_barh
    return yticks, ylabels, high_barh


def drawchart(_):
    """vytvoří sloupcový graf relevantních poruch podle počtu jejich zápisu"""
    data = get_data()
    yticks, ylabels, high_bahr = labels(data)

    ax4.clear()
    ax_r.clear()
    ax4.set_yticks(yticks)
    ax_r.set_yticks(yticks)

    leftlabels = []
    rightlabels = []
    for index, ylabel in enumerate(reversed(ylabels)):
        leftlabels.append(ylabel[0].replace(" ", "\n").upper())
        rightlabels.append((ylabel[1].split("_"))[1])

    ax4.set_yticklabels(leftlabels, fontsize=14, verticalalignment='center',
                        horizontalalignment='center', weight="bold", color="white")
    ax_r.set_yticklabels(rightlabels, fontsize=50, verticalalignment='center',
                         horizontalalignment='center',  weight="bold", color = "white")

    # roztažení y osy sníží výšku brok-bahrs (kosmetická úprava, pokud je málo relevantních poruch)
    if len(yticks) > 5:
        zero_ax4 = 0
    else:
        zero_ax4 = -100
    ax4.set_ylim(zero_ax4, high_ax4)  # nastavení y osy pro poruchy (vlevo a vpravo dole)
    ax_r.set_ylim(zero_ax4, high_ax4)
    values = []
    position = high_bahr   # první pozice podle výšky sloupce
    high = high_bahr       # výška sloupce

    # definice sloupcového grafu a popisků počtů
    index = max_barhs - 1
    for ylabel in reversed(ylabels):
        ax4.barh(width=data[ylabel], color=colors[index], height=high*0.8, y=position - (high / 2))
        ax4.text(data[ylabel]*1.02, position - (high/2), data[ylabel],
                 verticalalignment='center', fontsize=24, weight="bold")
        values.append(data[ylabel])
        position += high
        index -= 1

    # velikost osy x podle umístění popisků
    if len(values) == 0:
        scale = 1
    else:
        if max(values) > 0:
            scale = max(values)
        else:
            scale = 1
    ax4.set_xlim((0, scale*1.14))


ani = animation.FuncAnimation(fig, drawchart, interval=60000)

plt.show()

