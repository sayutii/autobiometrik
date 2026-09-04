import sys
import os
import json
import logging
import time
import subprocess
import urllib.parse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================================
# KONFIGURASI PATH
# ============================================================

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "autobiometrik.log")

DEFAULT_CONFIG = {
    "frista_path": "C:\\frista\\frista.exe",
    "finger_path": "C:\\Program Files (x86)\\BPJS Kesehatan\\Aplikasi Sidik Jari BPJS Kesehatan\\After.exe",
    "frista_username": "user-frista-anda",
    "frista_password": "password-frista-anda",
    "finger_username": "user-aplikasi-sidik-jari",
    "finger_password": "password-aplikasi-sidik-jari",
    "host": "127.0.0.1",
    "port": 5000,
    "tls_cert": "",
    "tls_key": ""
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

# Output juga ke console / stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(console_handler)


# ============================================================
# LOAD CONFIG
# ============================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            logging.info("File config.json baru dibuat: %s", CONFIG_FILE)
        except Exception as e:
            logging.error("Gagal membuat config.json: %s", e)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Merge missing keys from default
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    except Exception as e:
        logging.error("Gagal membaca config.json: %s", e)
        return DEFAULT_CONFIG


# ============================================================
# SUBPROCESS WINDOW HIDE FLAGS
# ============================================================

if sys.platform == "win32":
    CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
else:
    CREATE_NO_WINDOW = 0


# ============================================================
# AUTOIT / GUI AUTOMATION HELPER & FALLBACK
# ============================================================

def get_autoit():
    """Mengembalikan objek AutoIt jika berjalan di Windows."""
    if sys.platform != "win32":
        return None
    try:
        import win32com.client
        autoit = win32com.client.Dispatch("AutoItX3.Control")
        try:
            autoit.AutoItSetOption("WinTitleMatchMode", 2) # Partial Title Match
        except Exception:
            pass
        return autoit
    except Exception:
        try:
            import autoit as pyautoit
            return pyautoit
        except Exception:
            return None


def is_process_running(exe_name):
    """Mengecek apakah nama file executable sedang berjalan."""
    if not exe_name:
        return False
    filename = os.path.basename(exe_name).lower()
    try:
        if sys.platform == "win32":
            output = subprocess.check_output(["tasklist"], text=True, errors="ignore", creationflags=CREATE_NO_WINDOW)
            return filename in output.lower()
        else:
            output = subprocess.check_output(["ps", "aux"], text=True, errors="ignore")
            return filename in output.lower()
    except Exception as e:
        logging.error("Error checking process list: %s", e)
        return False


def kill_process_by_exe(exe_path):
    """Menghentikan proses berdasarkan nama executable."""
    if not exe_path:
        return False
    filename = os.path.basename(exe_path)
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", filename], capture_output=True, creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.run(["pkill", "-f", filename], capture_output=True)
        logging.info("Proses %s berhasil dihentikan.", filename)
        return True
    except Exception as e:
        logging.error("Gagal menghentikan proses %s: %s", filename, e)
        return False


def activate_window_and_send_keys(title_keywords, keys_list, max_wait_sec=10):
    """
    Menunggu jendela muncul, memaksa jendela ke paling depan (Pop-Up),
    dan meng-input tombol (AutoIt / PowerShell Native Fallback).
    """
    if sys.platform != "win32":
        logging.info("[MOCK AUTOMATION] Send keys to %s: %s", title_keywords, keys_list)
        return True

    # 1. Coba lewat AutoIt jika ada
    autoit = get_autoit()
    if autoit:
        try:
            for title in title_keywords:
                if hasattr(autoit, "WinWait"):
                    if autoit.WinWait(title, "", max_wait_sec):
                        autoit.WinActivate(title)
                        time.sleep(0.4)
                        for k in keys_list:
                            autoit.Send(k)
                            time.sleep(0.2)
                        logging.info("AutoIt berhasil mengirim tombol ke window '%s'", title)
                        return True
        except Exception as e:
            logging.debug("AutoIt execution warning: %s", e)

    # 2. Fallback ke PowerShell Native (SetForegroundWindow + WScript.Shell)
    try:
        keywords_array = "@(" + ", ".join([f"'{t}'" for t in title_keywords]) + ")"

        ps_script = f"""
        $keywords = {keywords_array};
        $wshell = New-Object -ComObject wscript.shell;
        $found = $false;

        # Wait loop for window to appear (polling up to {max_wait_sec} seconds)
        for ($i = 0; $i -lt ({max_wait_sec} * 2); $i++) {{
            foreach ($t in $keywords) {{
                if ($wshell.AppActivate($t)) {{
                    $found = $true;
                    break;
                }}
            }}
            if ($found) {{ break; }}
            Start-Sleep -Milliseconds 500
        }}

        if ($found) {{
            # Force bring window to front using User32 Win32 API
            try {{
                $proc = Get-Process | Where-Object {{ $_.MainWindowTitle -ne '' }} | Where-Object {{ 
                    $title = $_.MainWindowTitle; 
                    $match = $false; 
                    foreach ($k in $keywords) {{ if ($title -like "*$k*") {{ $match = $true; break; }} }} 
                    $match 
                }} | Select-Object -First 1;
                
                if ($proc -and $proc.MainWindowHandle -ne 0) {{
                    $type = Add-Type -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);' -Name "Win32Popup" -Namespace Win32 -PassThru;
                    $type::ShowWindow($proc.MainWindowHandle, 9);
                    $type::SetForegroundWindow($proc.MainWindowHandle);
                }}
            }} catch {{ }}

            Start-Sleep -Milliseconds 500;
        """

        # Append SendKeys
        for k in keys_list:
            if k == "{TAB}":
                ps_script += "$wshell.SendKeys('{TAB}'); Start-Sleep -Milliseconds 250;\n"
            elif k == "{ENTER}":
                ps_script += "$wshell.SendKeys('{ENTER}'); Start-Sleep -Milliseconds 500;\n"
            else:
                clean_k = k.replace("'", "''")
                ps_script += f"$wshell.SendKeys('{clean_k}'); Start-Sleep -Milliseconds 200;\n"

        ps_script += "}\n"

        subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            timeout=max_wait_sec + 10,
            creationflags=CREATE_NO_WINDOW
        )
        logging.info("PowerShell SendKeys executed secara silent untuk %s", title_keywords)
        return True
    except Exception as e:
        logging.error("PowerShell SendKeys error: %s", e)
        return False


# ============================================================
# OTOMASI THREAD BACKGROUND
# ============================================================

def process_start_frista(no_peserta, config):
    logging.info("[FRISTA THREAD] Memulai otomasi FRISTA untuk no_peserta: %s", no_peserta)
    app_path = config.get("frista_path", "")
    username = config.get("frista_username", "")
    password = config.get("frista_password", "")

    if not app_path or not os.path.exists(app_path):
        logging.error("[FRISTA THREAD] File aplikasi tidak ditemukan: %s", app_path)
        return

    already_running = is_process_running(app_path)
    title_keywords = ["FRISTA", "Frista", "frista", "Face Recognition", "Biometrik", "BPJS", "Login", "login"]

    if not already_running:
        logging.info("[FRISTA THREAD] Membuka FRISTA: %s", app_path)
        try:
            subprocess.Popen([app_path], cwd=os.path.dirname(app_path))
        except Exception as e:
            logging.error("[FRISTA THREAD] Gagal launching app: %s", e)
            return

        # 1. Kirim Username & Password jika diisi di config.json
        login_keys = []
        if username:
            login_keys.append(username)
            login_keys.append("{TAB}")
            if password:
                login_keys.append(password)
                login_keys.append("{ENTER}")

        if login_keys:
            logging.info("[FRISTA THREAD] Menunggu layar login & memasukkan Username/Password...")
            activate_window_and_send_keys(title_keywords, login_keys, max_wait_sec=12)
            time.sleep(3)

        # 2. Kirim Nomor BPJS
        logging.info("[FRISTA THREAD] Memasukkan Nomor Peserta BPJS: %s", no_peserta)
        activate_window_and_send_keys(title_keywords, [no_peserta], max_wait_sec=8)

    else:
        logging.info("[FRISTA THREAD] FRISTA sudah berjalan. Mengaktifkan & meng-input nomor BPJS...")
        activate_window_and_send_keys(title_keywords, [no_peserta], max_wait_sec=5)

    logging.info("[FRISTA THREAD] Otomasi FRISTA selesai.")


def process_start_finger(no_peserta, config):
    logging.info("[FINGER THREAD] Memulai otomasi Finger untuk no_peserta: %s", no_peserta)
    app_path = config.get("finger_path", "")
    username = config.get("finger_username", "")
    password = config.get("finger_password", "")

    if not app_path or not os.path.exists(app_path):
        logging.error("[FINGER THREAD] File aplikasi tidak ditemukan: %s", app_path)
        return

    already_running = is_process_running(app_path)
    title_keywords = ["Sidik Jari", "Aplikasi Sidik Jari", "BPJS", "After", "finger", "Login", "login"]

    if not already_running:
        logging.info("[FINGER THREAD] Membuka Finger Sidik Jari: %s", app_path)
        try:
            subprocess.Popen([app_path], cwd=os.path.dirname(app_path))
        except Exception as e:
            logging.error("[FINGER THREAD] Gagal launching app: %s", e)
            return

        # 1. Kirim Username & Password jika diisi di config.json
        login_keys = []
        if username:
            login_keys.append(username)
            login_keys.append("{TAB}")
            if password:
                login_keys.append(password)
                login_keys.append("{ENTER}")

        if login_keys:
            logging.info("[FINGER THREAD] Menunggu layar login & memasukkan Username/Password...")
            activate_window_and_send_keys(title_keywords, login_keys, max_wait_sec=12)
            time.sleep(3)

        # 2. Kirim Nomor BPJS
        logging.info("[FINGER THREAD] Memasukkan Nomor Peserta BPJS: %s", no_peserta)
        activate_window_and_send_keys(title_keywords, [no_peserta], max_wait_sec=8)

    else:
        logging.info("[FINGER THREAD] Finger sudah berjalan. Mengaktifkan & meng-input nomor BPJS...")
        activate_window_and_send_keys(title_keywords, [no_peserta], max_wait_sec=5)

    logging.info("[FINGER THREAD] Otomasi Finger selesai.")




# ============================================================
# HTTP REST API HANDLER
# ============================================================

class AutoBiometrikHTTPHandler(BaseHTTPRequestHandler):

    def set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")

    def do_OPTIONS(self):
        self.send_response(200)
        self.set_cors_headers()
        self.end_headers()

    def respond_json(self, status_code, data):
        self.send_response(status_code)
        self.set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_GET(self):
        config = load_config()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed.query)

        # ----------------------------------------------------
        # GET /health
        # ----------------------------------------------------
        if path == "/health" or path == "":
            autoit_available = bool(get_autoit() is not None or sys.platform == "win32")
            has_credentials = bool(config.get("frista_username") and config.get("frista_password"))
            has_finger_credentials = bool(config.get("finger_username") and config.get("finger_password"))
            scheme = "https" if config.get("tls_cert") else "http"

            response = {
                "status": "ok",
                "service": "autobiometrik-bpjs",
                "version": "1.0.1",
                "autoit": autoit_available,
                "has_credentials": has_credentials,
                "has_finger_credentials": has_finger_credentials,
                "scheme": scheme
            }
            return self.respond_json(200, response)

        # ----------------------------------------------------
        # GET /start_frista
        # ----------------------------------------------------
        if path == "/start_frista":
            no_peserta_list = query.get("no_peserta")
            if not no_peserta_list or not no_peserta_list[0].strip():
                return self.respond_json(400, {
                    "status": "error",
                    "message": "Parameter no_peserta dibutuhkan"
                })

            no_peserta = no_peserta_list[0].strip()

            # Jalankan di background thread
            thread = threading.Thread(
                target=process_start_frista,
                args=(no_peserta, config),
                daemon=True
            )
            thread.start()

            return self.respond_json(200, {
                "status": "running",
                "target": "frista",
                "no_peserta": no_peserta
            })

        # ----------------------------------------------------
        # GET /start_finger
        # ----------------------------------------------------
        if path == "/start_finger":
            no_peserta_list = query.get("no_peserta")
            if not no_peserta_list or not no_peserta_list[0].strip():
                return self.respond_json(400, {
                    "status": "error",
                    "message": "Parameter no_peserta dibutuhkan"
                })

            no_peserta = no_peserta_list[0].strip()

            # Jalankan di background thread
            thread = threading.Thread(
                target=process_start_finger,
                args=(no_peserta, config),
                daemon=True
            )
            thread.start()

            return self.respond_json(200, {
                "status": "running",
                "target": "finger",
                "no_peserta": no_peserta
            })

        # ----------------------------------------------------
        # GET /stop_frista
        # ----------------------------------------------------
        if path == "/stop_frista":
            frista_path = config.get("frista_path", "frista.exe")
            kill_process_by_exe(frista_path)
            return self.respond_json(200, {
                "status": "ok",
                "target": "frista"
            })

        # ----------------------------------------------------
        # GET /stop_finger
        # ----------------------------------------------------
        if path == "/stop_finger":
            finger_path = config.get("finger_path", "After.exe")
            kill_process_by_exe(finger_path)
            return self.respond_json(200, {
                "status": "ok",
                "target": "finger"
            })

        # ----------------------------------------------------
        # 404 NOT FOUND
        # ----------------------------------------------------
        return self.respond_json(404, {
            "status": "error",
            "message": f"Endpoint '{path}' tidak ditemukan."
        })

    def log_message(self, format, *args):
        # Override log HTTP request bawaan ke logging.info
        logging.info("HTTP %s - - [%s] %s", self.client_address[0], self.log_date_time_string(), format % args)


# ============================================================
# MAIN SERVER RUNNER
# ============================================================

def main():
    config = load_config()
    host = config.get("host", "127.0.0.1")
    port = int(config.get("port", 5000))

    server_address = (host, port)
    httpd = HTTPServer(server_address, AutoBiometrikHTTPHandler)

    logging.info("=" * 60)
    logging.info("AutoBiometrik BPJS Local REST Service v1.0.1")
    logging.info("Server berjalan pada: http://%s:%d", host, port)
    logging.info("Endpoint tersedia:")
    logging.info("  GET http://%s:%d/health", host, port)
    logging.info("  GET http://%s:%d/start_frista?no_peserta=XXX", host, port)
    logging.info("  GET http://%s:%d/start_finger?no_peserta=XXX", host, port)
    logging.info("  GET http://%s:%d/stop_frista", host, port)
    logging.info("  GET http://%s:%d/stop_finger", host, port)
    logging.info("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server dihentikan oleh pengguna.")
        httpd.server_close()


if __name__ == "__main__":
    main()