from datetime import datetime, timedelta
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pyodbc

# Stroj = 'BM_2'
# timeFrom = datetime(2019, 8, 18, 5, 30, 0, 0)
# timeTo = datetime(2019, 9, 8, 6, 0, 0, 0,)

# server = '10.0.0.6\SQLEXPRESS'
# server = '192.168.60.222\SQLEXPRESS'
server = '127.0.0.1\SQLEXPRESS'
database = 'Provozni_Data'
user = 'VyrobaStandalone'
password = 'Kmt0203'
# driver = 'FreeTDS'
# driver = '{ODBC Driver 17 for SQL Server}'
driver = 'SQL Server'

interval = timedelta(hours=4)

operace = 'BM'
max_barhs = 10

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


def get_data():
    now = datetime.now().replace(microsecond=0)
    timefrom = now - interval
    timeto = now
    # timeFrom = datetime(2019, 6, 2)-interval
    # timeTo = datetime(2019, 7, 3)

    cursor.execute("SELECT NAZEV_UDALOSTI, ID_UDALOSTI FROM UDALOST")  # stažení seznamu událostí
    id_udalosti = dict(cursor.fetchall())  # jako dictionary
    id_udalost_reversed = dict(map(reversed, id_udalosti.items()))  # převrácení klíč <--> hodnota

    cursor.execute("SELECT NAZEV_STROJE, ID_STROJE FROM STROJ")     # stažení seznamu strojů
    seznam_stroju = dict(cursor.fetchall())                         # jako dictionary
    seznam_stroju_reversed = dict(map(reversed, seznam_stroju.items()))  # převrácení klíč <--> hodnota

    cursor.execute(f"SELECT ID_STROJE FROM STROJ WHERE NAZEV_STROJE LIKE '%{operace}%'")
    ids_op = cursor.fetchall()
    ids_op = [str(ID[0]) for ID in ids_op]
    sql_ids_op = " OR ID_STROJE=".join(ids_op)

    string = (f"SELECT ID_UDALOSTI, ID_STROJE FROM DATA_STROJU WHERE (ID_STROJE = {sql_ids_op}) "
              f"AND (ID_UDALOSTI != {id_udalosti['Provoz']} "
              f"     AND ID_UDALOSTI != {id_udalosti['Naprazdno']} "
              f"     AND ID_UDALOSTI != {id_udalosti['Zastaveno']}) "
              f"AND CAS BETWEEN '{timefrom}' AND '{timeto}' ORDER BY CAS")

    cursor.execute(string)
    pure_data = (cursor.fetchall())

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
    print(now)
    return named


matplotlib.rcParams['toolbar'] = "None"
fig = plt.figure(figsize=(16, 8), facecolor="black")  # vytvoření okna pro graf
# fig.suptitle(operace, fontsize=16)  # hlavní titulek grafu
fig.tight_layout()
fig.subplots_adjust(bottom=0.001, left=0.1, right=0.999, top=0.999, wspace=0)  # vystředění grafu
plt.style.use(plt.style.available[2])
fig.canvas.manager.full_screen_toggle()             # toggle fullscreen mode

ax4 = plt.subplot()  # graf poruch vpravo dole
high_ax4 = 100


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
    ax4.set_yticks(yticks)
    popisky = []
    for index, ylabel in enumerate(ylabels):
        popisky.append(ylabels[index][0].replace(" ", "\n").upper())
    # exit()
    # popisky = ["\n".join(label) for label in ylabels]
    ax4.set_yticklabels(popisky, fontsize=14, verticalalignment='center', weight="bold")

    # roztažení y osy sníží výšku brok-bahrs (kosmetická úprava, pokud je málo relevantních poruch)
    if len(yticks) > 5:
        zero_ax4 = 0
    else:
        zero_ax4 = -100
    ax4.set_ylim(zero_ax4, high_ax4)  # nastavení y osy pro poruchy (vlevo a vpravo dole)

    values = []
    position = high_bahr   # první pozice podle výšky sloupce
    high = high_bahr       # výška sloupce

    # definice sloupcového grafu a popisků počtů
    for ylabel in reversed(ylabels):
        ax4.barh(width=data[ylabel], color="red", height=high*0.8, y=position - (high / 2))
        ax4.text(data[ylabel]*1.02, position - (high/2), data[ylabel], verticalalignment='center', fontsize=24, weight="bold")
        values.append(data[ylabel])
        position += high

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
