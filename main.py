import sys
import os
import subprocess
import urllib.parse
import json
import logging

# ============================================================
# KONFIGURASI PATH
# ============================================================

# Jika dijalankan sebagai PyInstaller EXE (frozen), sys.executable adalah path exe.
# Jika script .py biasa, __file__ adalah path script.
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "autobiometrik.log")

DEFAULT_CONFIG = {
    "finger_path": "C:\\Program Files (x86)\\BPJS Kesehatan\\Aplikasi Sidik Jari BPJS Kesehatan\\After.exe",
    "frista_path": "C:\\Program Files (x86)\\FRISTA\\Frista.exe",
    "finger_send_peserta": False,
    "frista_send_peserta": False
}


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)


# ============================================================
# HELPER POPUP NOTIFIKASI / ERROR
# ============================================================

def show_msg(title, message, is_error=False):
    """Menampilkan popup dialog agar tidak langsung tertutup tanpa pesan."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        if is_error:
            messagebox.showerror(title, message)
        else:
            messagebox.showinfo(title, message)
        root.destroy()
    except Exception:
        print(f"[{title}] {message}")


# ============================================================
# CONFIG
# ============================================================

def load_config():
    # Buat file config default jika belum ada
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as file:
                json.dump(DEFAULT_CONFIG, file, indent=4)
            logging.info("File config.json dibuat otomatis: %s", CONFIG_FILE)
        except Exception as e:
            raise Exception(f"Gagal membuat file config.json di: {CONFIG_FILE}\nError: {e}")

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        raise Exception(f"Gagal membaca file config.json: {CONFIG_FILE}\nError: {e}")


# ============================================================
# VALIDASI
# ============================================================

def validate_peserta(no_peserta):
    if not no_peserta:
        raise Exception("Nomor peserta kosong.")

    no_peserta = str(no_peserta).strip()

    if not no_peserta:
        raise Exception("Nomor peserta kosong.")

    return no_peserta


# ============================================================
# JALANKAN APLIKASI
# ============================================================

def run_application(app_path, no_peserta, arguments=None):
    if not os.path.exists(app_path):
        raise Exception(
            f"Aplikasi target tidak ditemukan pada path:\n{app_path}\n\n"
            f"Silakan periksa dan sesuaikan path pada file config.json:\n{CONFIG_FILE}"
        )

    app_directory = os.path.dirname(app_path)
    command = [app_path]

    if arguments:
        command.extend(arguments)

    logging.info("Menjalankan aplikasi: %s", command)

    try:
        process = subprocess.Popen(
            command,
            cwd=app_directory,
            shell=False
        )

        logging.info("Aplikasi berhasil dijalankan. PID=%s", process.pid)
        return True

    except Exception as e:
        logging.exception("Gagal menjalankan aplikasi: %s", str(e))
        raise Exception(f"Gagal memanggil proses '{app_path}':\n{e}")


# ============================================================
# FINGER
# ============================================================

def start_finger(no_peserta, config):
    no_peserta = validate_peserta(no_peserta)
    finger_path = config.get("finger_path")

    if not finger_path:
        raise Exception("`finger_path` belum dikonfigurasi dalam config.json.")

    arguments = []
    if config.get("finger_send_peserta", False):
        arguments.append(no_peserta)

    return run_application(finger_path, no_peserta, arguments)


# ============================================================
# FRISTA
# ============================================================

def start_frista(no_peserta, config):
    no_peserta = validate_peserta(no_peserta)
    frista_path = config.get("frista_path")

    if not frista_path:
        raise Exception("`frista_path` belum dikonfigurasi dalam config.json.")

    arguments = []
    if config.get("frista_send_peserta", False):
        arguments.append(no_peserta)

    return run_application(frista_path, no_peserta, arguments)


# ============================================================
# PARSE URL
# ============================================================

def parse_protocol_url(url):
    url = url.strip('"\' ')
    logging.info("Protocol URL diterima: %s", url)

    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    query = urllib.parse.parse_qs(parsed.query)

    no_peserta = query.get("no_peserta", [None])[0]

    # Fallback jika URL dikirim tanpa nama query param (misal: fingerbpjs://123456789)
    if not no_peserta and parsed.netloc and parsed.netloc.isdigit():
        no_peserta = parsed.netloc

    return scheme, no_peserta


# ============================================================
# MAIN
# ============================================================

def main():
    try:
        config = load_config()

        # Jika di-double click langsung tanpa parameter URL
        if len(sys.argv) < 2:
            info_text = (
                "AutoBiometrik BPJS Siap Digunakan.\n\n"
                "Aplikasi ini bekerja secara otomatis memanggil Finger / Frista dari browser via URL Protocol:\n"
                " • fingerbpjs://start?no_peserta=123456789\n"
                " • fristabpjs://start?no_peserta=123456789\n\n"
                f"Lokasi Config: {CONFIG_FILE}\n"
                f"Lokasi Log: {LOG_FILE}"
            )
            show_msg("AutoBiometrik BPJS", info_text, is_error=False)
            return

        url = sys.argv[1]
        scheme, no_peserta = parse_protocol_url(url)

        if not no_peserta:
            raise Exception("Parameter 'no_peserta' tidak ditemukan dalam URL protocol.")

        if scheme == "fingerbpjs":
            start_finger(no_peserta, config)
            return

        if scheme == "fristabpjs":
            start_frista(no_peserta, config)
            return

        raise Exception(f"Protocol tidak dikenal: '{scheme}'")

    except Exception as e:
        err_msg = str(e)
        logging.exception("ERROR: %s", err_msg)
        show_msg(
            "AutoBiometrik - Error",
            f"Terjadi Kesalahan:\n\n{err_msg}\n\nDetail log dapat dilihat di:\n{LOG_FILE}",
            is_error=True
        )


if __name__ == "__main__":
    main()