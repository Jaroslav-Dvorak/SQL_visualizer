from tkinter import *
from tkinter import messagebox
from tkinter.ttk import *

class ChartPicker:
    def __init__(self):
        self.geometry = "400x200"
        self.title = "Select"
        self.root = Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.callback_exit)
        self.quitFlag = False
        self.root.title(self.title)
        self.root.geometry(self.geometry)

        self.combo = Combobox(values=list(self.rpidict) + ["<new>"], state="readonly")
        self.combo.current(list(self.rpidict).index(last))
        self.combo.bind("<<ComboboxSelected>>", self.callback_combo)
        self.combo.pack()

        self.delete = Button(text="delete", command=self.callback_delete)
        self.delete.pack()

        self.OK = Button(text="OK", command=self.callback_OK)
        self.OK.pack()

        self.IPEntrys = []
        self.LabIPin = Label(text="IP:").pack(side=LEFT, padx=2)

        for e in range(0, 4):
            self.IPEntrys.append(Entry(width=3))
            self.IPEntrys[e].pack(side=LEFT)
            if e < 3:
                self.tecka = Label(text=".").pack(side=LEFT)

        self.dvojtecka = Label(text=":").pack(side=LEFT)
        self.PortIn = Entry(width=5)
        self.PortIn.pack(side=LEFT)

        self.namelab = Label(text="  název:").pack(side=LEFT)
        self.name = Entry()
        self.name.pack(side=LEFT)

        self.SAVE = Button(text="SAVE", command=self.callback_SAVE)
        self.SAVE.pack(side=BOTTOM)

        self.callback_combo()

        self.root.mainloop()

    def callback_combo(self, _=None):
        selected = self.combo.get()

        for e in self.IPEntrys:
            e.delete(0, "end")
        self.PortIn.delete(0, "end")
        self.name.delete(0, "end")

        if selected != "<new>":
            ip, port = self.rpidict[selected].split(":")
            for i, e in enumerate(ip.split(".")):
                self.IPEntrys[i].insert(0, e)
            self.PortIn.insert(0, port)
            self.name.insert(0, selected)

    def callback_delete(self):
        selected = self.combo.get()
        if selected != "<new>":
            self.rpidict.pop(self.combo.get())
            self.combo.configure(values=list(self.rpidict) + ["<new>"])
            self.combo.current(0)

    def callback_OK(self):
        self.IP_PORT = self.ip_parse()
        self.laststate = self.combo.get()
        if self.IP_PORT is None:
            return
        self.root.destroy()
        self.root.quit()

    def callback_SAVE(self):
        selected = self.combo.get()
        name = self.name.get()
        ip_port = self.ip_parse()
        if ip_port is None:
            return
        else:
            ip, port = ip_port
            port = str(port)
        if len(name) == 0 or " " in name or name == "<new>":
            messagebox.showerror("Bad name", "Název není ve správném formátu!")
            return
        if selected != "<new>":
            self.rpidict.pop(selected)

        self.rpidict[name] = ":".join([ip, port])
        self.combo.configure(values=list(self.rpidict) + ["<new>"])
        self.combo.current(list(self.rpidict).index(name))


    def callback_exit(self):
        self.root.quit()
        self.quitFlag = True