from datetime import datetime, timedelta
import matplotlib
import matplotlib.pyplot as plt
import pyodbc

# Stroj = 'BM_2'
# timeFrom = datetime(2019, 8, 18, 5, 30, 0, 0)
# timeTo = datetime(2019, 9, 8, 6, 0, 0, 0,)

# server = '10.0.0.6\SQLEXPRESS'
server = '192.168.60.222\SQLEXPRESS'
# server = '127.0.0.1\SQLEXPRESS'
database = 'Provozni_Data'
user = 'VyrobaStandalone'
password = 'Kmt0203'
# driver = 'FreeTDS'
# driver = '{ODBC Driver 17 for SQL Server}'
driver = 'SQL Server'

timeFrom = datetime(2019, 6, 2)
timeTo = datetime(2019, 7, 3)

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

operace = 'BM'

cursor.execute("SELECT NAZEV_UDALOSTI, ID_UDALOSTI FROM UDALOST")  # stažení seznamu událostí
id_udalosti = dict(cursor.fetchall())  # jako dictionary
id_udalost_reversed = dict(map(reversed, id_udalosti.items()))  # převrácení klíč <--> hodnota

cursor.execute("SELECT NAZEV_STROJE, ID_STROJE FROM STROJ")     # stažení seznamu strojů
seznam_stroju = dict(cursor.fetchall())                         # jako dictionary
seznam_stroju_reversed = dict(map(reversed, seznam_stroju.items()))  # převrácení klíč <--> hodnota

cursor.execute(f"SELECT ID_STROJE FROM STROJ WHERE NAZEV_STROJE LIKE '%{operace}%'")
ids_op = cursor.fetchall()
ids_op = [str(ID[0]) for ID in ids_op]
SQL_ids_op = " OR ID_STROJE=".join(ids_op)

string = (f"SELECT ID_UDALOSTI, ID_STROJE FROM DATA_STROJU WHERE (ID_STROJE = {SQL_ids_op}) "
          f"AND (ID_UDALOSTI != {id_udalosti['Provoz']} "
          f"     AND ID_UDALOSTI != {id_udalosti['Naprazdno']} "
          f"     AND ID_UDALOSTI != {id_udalosti['Zastaveno']}) ORDER BY CAS")

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
    # named[(nazev_udalosti + '\n' + nazev_stroje)] = v

fig = plt.figure(figsize=(16, 8))  # vytvoření okna pro graf
fig.suptitle(operace, fontsize=16)  # hlavní titulek grafu
fig.tight_layout()
# fig.subplots_adjust(bottom=0.11, left=0.1, right=0.98, top=0.94, wspace=0.05)  # vystředění grafu

# ax4 = plt.subplot2grid((4, 4), (1, 3), rowspan=3)  # graf poruch vpravo dole

ax4 = plt.subplot()  # graf poruch vpravo dole
high_ax3 = 100

def poruchy_labels(data):
    """vrátí pozici ukazatelů, popisků osy y a výšky sloupce"""
    ylabels = []
    yticks = []
    max = 10
    data = reversed(sorted(data.items(), key=lambda kv: kv[1]))
    i = 0
    for k, v in data:
        ylabels.append(k)
        i += 1
        if max == i:
            break

    # pokud žádní porucha - vrací prázdné hodnoty (ošetření)
    pocet_poruch = len(ylabels)
    if pocet_poruch == 0:
        return [], [], 0

    # výška sloupce v závislosti na počtu poruch
    high_barh = (high_ax3 / pocet_poruch)
    position = high_barh
    for _ in ylabels:
        yticks.append(position - (high_barh / 2))
        position += high_barh
    return yticks, ylabels, high_barh


yticks, ylabels, high_bahr = poruchy_labels(named)
ax4.set_yticks(yticks)
popisky = ["\n".join(label) for label in ylabels]
ax4.set_yticklabels(popisky)
print(ylabels)

def poruchy_4(data):
    """vytvoří sloupcový graf relevantních poruch podle počtu jejich zápisu"""
    barhs = []
    barhs_vals = []
    # odstranění grafu kvůli překreslení
    for index, _ in enumerate(barhs):
        barhs[index].remove()
        barhs_vals[index].remove()

    values = []
    position = high_bahr   # první pozice podle výšky sloupce
    high = high_bahr       # výška sloupce
    pocty = data     # získávání dat po každém překreslení

    # definice sloupcového grafu a popisků počtů
    for ylabel in ylabels:
        barhs.append(ax4.barh(width=pocty[ylabel], color="steelblue", height=high*0.9,
                          y=position - (high / 2)))
        barhs_vals.append(ax4.text(pocty[ylabel]*1.01, position - (high/2), pocty[ylabel],
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
    ax4.set_xlim((0, scale*1.14))
    i = 0

poruchy_4(named)

# print(named)

plt.show()


