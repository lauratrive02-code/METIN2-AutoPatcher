import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import urllib.request
import hashlib
import subprocess
import threading
import json
import os

APP_TITLE = "METIN2 AutoPatcher"
GAME_EXE = "Metin2Distribute.exe"

PATCHER_VERSION = "1.0.0"
VERSION_URL = "https://github.com/lauratrive02-code/METIN2-AutoPatcher/releases/download/latest/version.txt"
PATCHER_URL = "https://github.com/lauratrive02-code/METIN2-AutoPatcher/releases/download/latest/METIN2_AutoPatcher.exe"

MANIFEST_ID = "1kondvh40JgAWVAf7BVClSyaKZcSRBPOw"
MANIFEST_URL = (
    "https://drive.usercontent.google.com/download"
    f"?id={MANIFEST_ID}&export=download&confirm=t"
)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def version_tuple(v):
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        return (0,)

def check_self_update():
    if not getattr(sys, "frozen", False):
        return False

    try:
        req = urllib.request.Request(VERSION_URL, headers={"User-Agent": "METIN2-AutoPatcher"})
        with urllib.request.urlopen(req, timeout=15) as response:
            remote_version = response.read().decode("utf-8").strip()

        if version_tuple(remote_version) <= version_tuple(PATCHER_VERSION):
            return False

        current_exe = Path(sys.executable).resolve()
        update_exe = current_exe.with_name("METIN2_AutoPatcher_UPDATE.exe")
        batch_file = current_exe.with_name("METIN2_AutoPatcher_UPDATE.bat")

        req = urllib.request.Request(PATCHER_URL, headers={"User-Agent": "METIN2-AutoPatcher"})
        with urllib.request.urlopen(req, timeout=120) as response:
            with open(update_exe, "wb") as f:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

        if update_exe.stat().st_size < 100000:
            raise RuntimeError("Download AutoPatcher non valido")

        batch = "@echo off\r\n"
        batch += "timeout /t 2 /nobreak >nul\r\n"
        batch += f'del /f /q "{current_exe}" >nul 2>&1\r\n'
        batch += f'move /y "{update_exe}" "{current_exe}" >nul\r\n'
        batch += f'start "" "{current_exe}"\r\n'
        batch += 'del /f /q "%~f0"\r\n'

        batch_file.write_text(batch, encoding="utf-8")

        subprocess.Popen(
            ["cmd.exe", "/c", str(batch_file)],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        return True

    except Exception:
        return False

class Patcher:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("650x360")
        self.root.resizable(False, False)

        self.base = Path(sys_executable_dir()) / "METIN2"
        self.base.mkdir(parents=True, exist_ok=True)

        tk.Label(
            root,
            text="METIN2",
            font=("Arial", 30, "bold")
        ).pack(pady=(25, 2))

        tk.Label(
            root,
            text="AUTOPATCHER",
            font=("Arial", 15, "bold")
        ).pack()

        self.status = tk.StringVar(value="Pronto")
        tk.Label(
            root,
            textvariable=self.status,
            font=("Arial", 11)
        ).pack(pady=(25, 8))

        self.progress = ttk.Progressbar(
            root,
            length=540,
            mode="determinate",
            maximum=100
        )
        self.progress.pack()

        self.percent = tk.StringVar(value="0%")
        tk.Label(root, textvariable=self.percent).pack(pady=7)

        self.detail = tk.StringVar(value="")
        tk.Label(
            root,
            textvariable=self.detail,
            font=("Arial", 9)
        ).pack()

        frame = tk.Frame(root)
        frame.pack(pady=25)

        self.update_button = tk.Button(
            frame,
            text="AGGIORNA",
            width=20,
            height=2,
            command=self.start_update
        )
        self.update_button.pack(side="left", padx=10)

        self.play_button = tk.Button(
            frame,
            text="GIOCA",
            width=20,
            height=2,
            command=self.play
        )
        self.play_button.pack(side="left", padx=10)

    def ui(self, status=None, percent=None, detail=None):
        def apply():
            if status is not None:
                self.status.set(status)
            if percent is not None:
                self.progress["value"] = percent
                self.percent.set(f"{percent:.0f}%")
            if detail is not None:
                self.detail.set(detail)
        self.root.after(0, apply)

    def start_update(self):
        self.update_button.config(state="disabled")
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        try:
            self.ui("Scarico il catalogo aggiornamenti...", 0, "")

            with urllib.request.urlopen(MANIFEST_URL, timeout=60) as response:
                manifest = json.loads(response.read().decode("utf-8"))

            total = len(manifest)
            to_download = []

            # Controllo dei file
            for i, item in enumerate(manifest, 1):
                rel = Path(item["path"])
                local = self.base / rel

                self.ui(
                    "Controllo file...",
                    (i / total) * 40,
                    f"{i}/{total} - {item['path']}"
                )

                valid = False

                if local.exists() and local.is_file():
                    try:
                        if local.stat().st_size == item["size"]:
                            valid = sha256_file(local) == item["sha256"]
                    except Exception:
                        valid = False

                if not valid:
                    to_download.append(item)

            if not to_download:
                self.ui(
                    "Client già aggiornato!",
                    100,
                    f"{total} file verificati"
                )
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "METIN2",
                        "Il client è già aggiornato."
                    )
                )
                return

            count = len(to_download)

            # Download file mancanti/modificati
            for i, item in enumerate(to_download, 1):
                rel = Path(item["path"])
                dest = self.base / rel
                dest.parent.mkdir(parents=True, exist_ok=True)

                temp = dest.with_name(dest.name + ".download")

                url = (
                    "https://drive.usercontent.google.com/download"
                    f"?id={item['drive_id']}&export=download&confirm=t"
                )

                self.ui(
                    "Download aggiornamenti...",
                    40 + (i / count) * 58,
                    f"{i}/{count} - {item['path']}"
                )

                try:
                    urllib.request.urlretrieve(url, temp)

                    # Verifica dimensione
                    if temp.stat().st_size != item["size"]:
                        raise RuntimeError(
                            f"Dimensione errata per {item['path']}"
                        )

                    # Verifica SHA256
                    if sha256_file(temp) != item["sha256"]:
                        raise RuntimeError(
                            f"Hash errato per {item['path']}"
                        )

                    os.replace(temp, dest)

                finally:
                    if temp.exists():
                        try:
                            temp.unlink()
                        except Exception:
                            pass

            self.ui(
                "Aggiornamento completato!",
                100,
                f"{count} file aggiornati"
            )

            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "METIN2",
                    "Aggiornamento completato!\nOra puoi premere GIOCA."
                )
            )

        except Exception as e:
            error = str(e)
            self.ui("ERRORE", 0, error)

            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Errore AutoPatcher",
                    error
                )
            )

        finally:
            self.root.after(
                0,
                lambda: self.update_button.config(state="normal")
            )

    def play(self):
        exe = self.base / GAME_EXE

        if not exe.exists():
            messagebox.showwarning(
                "METIN2",
                "Il client non è ancora installato.\n\nPremi prima AGGIORNA."
            )
            return

        try:
            subprocess.Popen([str(exe)], cwd=str(self.base))
        except Exception as e:
            messagebox.showerror("Errore", str(e))

def sys_executable_dir():
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent

if __name__ == "__main__":
    if check_self_update():
        sys.exit(0)

    root = tk.Tk()
    Patcher(root)
    root.mainloop()
