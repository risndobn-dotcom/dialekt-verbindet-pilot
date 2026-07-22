#!/usr/bin/env python3
"""Dialekt-Vokabel-Manager - Desktop-App fuer die Plattform "Dialekt verbindet".

Verwaltet die Dialekt-Vokabeln (Unterland / Oberland / Triesenbergerisch),
importiert sie aus .db-, CSV- oder JSON-Dateien und schreibt sie in die
Website index.html - alles ohne Kommandozeile.

Nur Python-Standardbibliothek (Tkinter), damit die App problemlos mit
PyInstaller zu einer Windows-.exe paketiert werden kann.

Start:  python dialekt_app.py
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Import funktioniert sowohl als Modul (python -m app.dialekt_app) als auch als
# direkt gestartetes Skript / gefrorene .exe.
try:
    from core import (
        CATEGORIES, REGION_LABELS, VocabStore, ImportError_, import_into,
        inspect_db, list_tables, load_source, update_index_html, default_index_path,
    )
except ImportError:  # pragma: no cover - Pfad-Fallback
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from core import (
        CATEGORIES, REGION_LABELS, VocabStore, ImportError_, import_into,
        inspect_db, list_tables, load_source, update_index_html, default_index_path,
    )

APP_TITLE = "Dialekt-Vokabel-Manager"
# Label -> kanonischer Schluessel und zurueck.
LABEL_TO_CAT = {REGION_LABELS[c]: c for c in CATEGORIES}


class ImportDialog(tk.Toplevel):
    """Modaler Dialog: Datei einer Region zuordnen und Spalten mappen."""

    def __init__(self, parent, path):
        super().__init__(parent)
        self.title("Importieren")
        self.transient(parent)
        self.resizable(False, False)
        self.result = None
        self.path = path
        self.grab_set()

        ext = os.path.splitext(path)[1].lower()
        self.tables = list_tables(path) if ext in (".db", ".sqlite", ".sqlite3") else []

        pad = {"padx": 10, "pady": 6}
        row = 0
        ttk.Label(self, text=os.path.basename(path), font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", **pad)
        row += 1

        # Tabellenwahl (nur SQLite mit mehreren Tabellen)
        self.table_var = tk.StringVar(value=self.tables[0] if self.tables else "")
        if len(self.tables) > 1:
            ttk.Label(self, text="Tabelle:").grid(row=row, column=0, sticky="w", **pad)
            box = ttk.Combobox(self, textvariable=self.table_var, values=self.tables,
                               state="readonly", width=28)
            box.grid(row=row, column=1, sticky="w", **pad)
            box.bind("<<ComboboxSelected>>", lambda e: self._reload_columns())
            row += 1

        # Region: automatisch oder fest
        self.mode = tk.StringVar(value="auto")
        ttk.Radiobutton(self, text="Region automatisch aus einer Spalte erkennen",
                        variable=self.mode, value="auto",
                        command=self._toggle).grid(row=row, column=0, columnspan=2, sticky="w", **pad)
        row += 1
        frm = ttk.Frame(self)
        frm.grid(row=row, column=0, columnspan=2, sticky="w", padx=10)
        ttk.Radiobutton(frm, text="Feste Region:", variable=self.mode, value="fixed",
                        command=self._toggle).pack(side="left")
        self.region_var = tk.StringVar(value=REGION_LABELS[CATEGORIES[0]])
        self.region_box = ttk.Combobox(frm, textvariable=self.region_var,
                                       values=[REGION_LABELS[c] for c in CATEGORIES],
                                       state="disabled", width=20)
        self.region_box.pack(side="left", padx=8)
        row += 1

        # Spalten-Mapping (optional / manuell)
        ttk.Separator(self, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=8)
        row += 1
        ttk.Label(self, text="Spalten (leer = automatisch):").grid(
            row=row, column=0, columnspan=2, sticky="w", **pad)
        row += 1
        self.hoch_var = tk.StringVar()
        self.dialekt_var = tk.StringVar()
        self.cat_var = tk.StringVar()
        self._col_widgets = {}
        for label, var, key in (("Hochdeutsch-Spalte", self.hoch_var, "hoch"),
                                 ("Dialekt-Spalte", self.dialekt_var, "dialekt"),
                                 ("Regions-Spalte", self.cat_var, "cat")):
            ttk.Label(self, text=label + ":").grid(row=row, column=0, sticky="w", **pad)
            cb = ttk.Combobox(self, textvariable=var, values=[], state="readonly", width=28)
            cb.grid(row=row, column=1, sticky="w", **pad)
            self._col_widgets[key] = cb
            row += 1

        # Buttons
        btns = ttk.Frame(self)
        btns.grid(row=row, column=0, columnspan=2, sticky="e", padx=10, pady=12)
        ttk.Button(btns, text="Abbrechen", command=self._cancel).pack(side="right", padx=4)
        ttk.Button(btns, text="Importieren", command=self._ok).pack(side="right")

        self._reload_columns()
        self._toggle()
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())

    def _reload_columns(self):
        try:
            columns, _ = load_source(self.path, self.table_var.get() or None)
        except Exception:
            columns = []
        options = [""] + columns
        for cb in self._col_widgets.values():
            cb["values"] = options

    def _toggle(self):
        fixed = self.mode.get() == "fixed"
        self.region_box.configure(state="readonly" if fixed else "disabled")
        self._col_widgets["cat"].configure(state="disabled" if fixed else "readonly")

    def _ok(self):
        params = {"table": self.table_var.get() or None}
        if self.mode.get() == "fixed":
            params["category"] = LABEL_TO_CAT[self.region_var.get()]
        else:
            params["category_col"] = self.cat_var.get() or None
        params["hoch_col"] = self.hoch_var.get() or None
        params["dialekt_col"] = self.dialekt_var.get() or None
        self.result = params
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=0)
        self.master = master
        self.store = VocabStore()
        self.json_path = None
        guess = default_index_path()
        self.index_path = guess if os.path.exists(guess) else None
        self.dirty = False

        self.pack(fill="both", expand=True)
        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()
        self._refresh_all()
        self._update_title()

    # -- UI-Aufbau ---------------------------------------------------------
    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=(8, 8))
        bar.pack(fill="x")
        def b(text, cmd):
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=3)
        b("Neu", self.new_file)
        b("Öffnen…", self.open_json)
        b("Speichern", self.save_json)
        b("Speichern unter…", self.save_json_as)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        b("Importieren…", self.import_file)
        b("Struktur prüfen…", self.inspect_file)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        b("Website aktualisieren…", self.update_website)

    def _build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.trees = {}
        for cat in CATEGORIES:
            frame = ttk.Frame(self.nb, padding=8)
            self.nb.add(frame, text=REGION_LABELS[cat])

            cols = ("hoch", "dialekt")
            tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
            tree.heading("hoch", text="Hochdeutsch")
            tree.heading("dialekt", text="Dialekt")
            tree.column("hoch", width=280, anchor="w")
            tree.column("dialekt", width=280, anchor="w")
            vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=vsb.set)
            tree.grid(row=0, column=0, columnspan=4, sticky="nsew")
            vsb.grid(row=0, column=4, sticky="ns")
            tree.bind("<Double-1>", lambda e, c=cat: self.edit_entry(c))
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)

            # Eingabezeile
            hv, dv = tk.StringVar(), tk.StringVar()
            ttk.Label(frame, text="Hoch:").grid(row=1, column=0, sticky="e", pady=(8, 0))
            e1 = ttk.Entry(frame, textvariable=hv, width=24)
            e1.grid(row=1, column=1, sticky="ew", pady=(8, 0), padx=4)
            ttk.Label(frame, text="Dialekt:").grid(row=1, column=2, sticky="e", pady=(8, 0))
            e2 = ttk.Entry(frame, textvariable=dv, width=24)
            e2.grid(row=1, column=3, sticky="ew", pady=(8, 0), padx=4)
            e2.bind("<Return>", lambda ev, c=cat: self.add_entry(c))
            e1.bind("<Return>", lambda ev, c=cat: self.add_entry(c))

            actions = ttk.Frame(frame)
            actions.grid(row=2, column=0, columnspan=5, sticky="w", pady=8)
            ttk.Button(actions, text="Hinzufügen", command=lambda c=cat: self.add_entry(c)).pack(side="left", padx=3)
            ttk.Button(actions, text="Bearbeiten", command=lambda c=cat: self.edit_entry(c)).pack(side="left", padx=3)
            ttk.Button(actions, text="Löschen", command=lambda c=cat: self.delete_entry(c)).pack(side="left", padx=3)

            self.trees[cat] = {"tree": tree, "hoch": hv, "dialekt": dv}

    def _build_statusbar(self):
        self.status = tk.StringVar()
        bar = ttk.Frame(self, relief="sunken", padding=(8, 4))
        bar.pack(fill="x", side="bottom")
        ttk.Label(bar, textvariable=self.status).pack(side="left")

    # -- Helpers -----------------------------------------------------------
    def _current_cat(self):
        return CATEGORIES[self.nb.index(self.nb.select())]

    def _refresh_tree(self, cat):
        tree = self.trees[cat]["tree"]
        tree.delete(*tree.get_children())
        for i, e in enumerate(self.store.data[cat]):
            tree.insert("", "end", iid=str(i), values=(e["hoch"], e["dialekt"]))

    def _refresh_all(self):
        for cat in CATEGORIES:
            self._refresh_tree(cat)
        self._refresh_status()

    def _refresh_status(self):
        c = self.store.counts()
        parts = " · ".join(f"{REGION_LABELS[cat]}: {c[cat]}" for cat in CATEGORIES)
        idx = self.index_path or "keine gewählt"
        self.status.set(f"{parts}   ·   Gesamt: {self.store.total()}   ·   Website: {idx}")

    def _mark_dirty(self, dirty=True):
        self.dirty = dirty
        self._update_title()

    def _update_title(self):
        name = os.path.basename(self.json_path) if self.json_path else "ungespeichert"
        star = "* " if self.dirty else ""
        self.master.title(f"{star}{name} — {APP_TITLE}")

    # -- Aktionen: Einträge ------------------------------------------------
    def add_entry(self, cat):
        fields = self.trees[cat]
        if self.store.add(cat, fields["hoch"].get(), fields["dialekt"].get()):
            fields["hoch"].set("")
            fields["dialekt"].set("")
            self._refresh_tree(cat)
            self._refresh_status()
            self._mark_dirty()
        else:
            messagebox.showinfo(APP_TITLE, "Eintrag ist leer oder existiert bereits in dieser Region.")

    def edit_entry(self, cat):
        tree = self.trees[cat]["tree"]
        sel = tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Bitte zuerst eine Zeile auswählen.")
            return
        index = int(sel[0])
        entry = self.store.data[cat][index]
        hoch = _ask_string(self.master, "Bearbeiten", "Hochdeutsch:", entry["hoch"])
        if hoch is None:
            return
        dialekt = _ask_string(self.master, "Bearbeiten", "Dialekt:", entry["dialekt"])
        if dialekt is None:
            return
        if self.store.update(cat, index, hoch, dialekt):
            self._refresh_tree(cat)
            self._mark_dirty()
        else:
            messagebox.showinfo(APP_TITLE, "Beide Felder müssen ausgefüllt sein.")

    def delete_entry(self, cat):
        tree = self.trees[cat]["tree"]
        sel = tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Bitte zuerst eine Zeile auswählen.")
            return
        index = int(sel[0])
        entry = self.store.data[cat][index]
        if messagebox.askyesno(APP_TITLE, f"„{entry['hoch']} → {entry['dialekt']}“ löschen?"):
            self.store.remove(cat, index)
            self._refresh_tree(cat)
            self._refresh_status()
            self._mark_dirty()

    # -- Aktionen: Datei ---------------------------------------------------
    def new_file(self):
        if self.dirty and not messagebox.askyesno(APP_TITLE, "Ungespeicherte Änderungen verwerfen?"):
            return
        self.store = VocabStore()
        self.json_path = None
        self._refresh_all()
        self._mark_dirty(False)

    def open_json(self):
        path = filedialog.askopenfilename(
            title="Vokabeldatei öffnen", filetypes=[("JSON", "*.json"), ("Alle Dateien", "*.*")])
        if not path:
            return
        try:
            self.store = VocabStore.load(path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Konnte nicht öffnen:\n{exc}")
            return
        self.json_path = path
        self._refresh_all()
        self._mark_dirty(False)

    def save_json(self):
        if not self.json_path:
            return self.save_json_as()
        self.store.save(self.json_path)
        self._mark_dirty(False)
        self._refresh_status()

    def save_json_as(self):
        path = filedialog.asksaveasfilename(
            title="Vokabeldatei speichern", defaultextension=".json",
            initialfile="vokabeln.json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        self.json_path = path
        self.store.save(path)
        self._mark_dirty(False)
        self._update_title()

    def import_file(self):
        path = filedialog.askopenfilename(
            title="Vokabeln importieren",
            filetypes=[("Vokabelquellen", "*.db *.sqlite *.sqlite3 *.csv *.tsv *.json"),
                       ("SQLite", "*.db *.sqlite *.sqlite3"), ("CSV/TSV", "*.csv *.tsv"),
                       ("JSON", "*.json"), ("Alle Dateien", "*.*")])
        if not path:
            return
        dlg = ImportDialog(self.master, path)
        self.master.wait_window(dlg)
        if not dlg.result:
            return
        try:
            stats = import_into(self.store, path, **dlg.result)
        except ImportError_ as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Import fehlgeschlagen:\n{exc}")
            return
        self._refresh_all()
        self._mark_dirty()
        messagebox.showinfo(
            APP_TITLE,
            "Import abgeschlossen.\n\n"
            f"Gelesen: {stats['gelesen']}\nNeu: {stats['neu']}\n"
            f"Duplikate: {stats['duplikate']}\nUnvollständig: {stats['unvollstaendig']}\n"
            f"Ohne erkennbare Region: {stats['ohne_region']}")

    def inspect_file(self):
        path = filedialog.askopenfilename(
            title="SQLite-Struktur prüfen",
            filetypes=[("SQLite", "*.db *.sqlite *.sqlite3"), ("Alle Dateien", "*.*")])
        if not path:
            return
        try:
            text = inspect_db(path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Konnte nicht lesen:\n{exc}")
            return
        top = tk.Toplevel(self.master)
        top.title(f"Struktur: {os.path.basename(path)}")
        st = scrolledtext.ScrolledText(top, width=80, height=24, wrap="none")
        st.pack(fill="both", expand=True)
        st.insert("1.0", text)
        st.configure(state="disabled")

    def update_website(self):
        path = self.index_path or default_index_path()
        if not os.path.exists(path):
            path = filedialog.askopenfilename(
                title="index.html der Website wählen",
                filetypes=[("HTML", "*.html *.htm"), ("Alle Dateien", "*.*")])
            if not path:
                return
        self.index_path = path
        try:
            res = update_index_html(self.store, path)
        except FileNotFoundError:
            messagebox.showerror(APP_TITLE, f"index.html nicht gefunden:\n{path}")
            return
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._refresh_status()
        if res["changed"]:
            c = res["counts"]
            messagebox.showinfo(
                APP_TITLE,
                "Website aktualisiert.\n\n"
                + "\n".join(f"{REGION_LABELS[cat]}: {c[cat]}" for cat in CATEGORIES)
                + (f"\n\nBackup: {res['backup_path']}" if res["backup_path"] else ""))
        else:
            messagebox.showinfo(APP_TITLE, "Keine Änderung nötig – Inhalt ist bereits aktuell.")


def _ask_string(parent, title, prompt, initial=""):
    """Kleiner Ersatz fuer simpledialog.askstring mit Vorbelegung."""
    from tkinter import simpledialog
    return simpledialog.askstring(title, prompt, initialvalue=initial, parent=parent)


def main():
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("680x560")
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
