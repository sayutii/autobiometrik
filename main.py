import sys
import os
import subprocess
import urllib.parse
import json
import logging

# ============================================================
# KONFIGURASI
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "autobiometrik.log")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ============================================================
# CONFIG
# ============================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise Exception(
            "File config.json tidak ditemukan: {}".format(CONFIG_FILE)
        )

    with open(CONFIG_FILE, "r") as file:
        return json.load(file)


# ============================================================
# VALIDASI
# ============================================================

def validate_peserta(no_peserta):
    if not no_peserta:
        raise Exception("Nomor peserta kosong.")

    no_peserta = no_peserta.strip()

    if not no_peserta:
        raise Exception("Nomor peserta kosong.")

    return no_peserta


# ============================================================
# JALANKAN APLIKASI
# ============================================================

def run_application(app_path, no_peserta, arguments=None):

    if not os.path.exists(app_path):
        raise Exception(
            "Aplikasi tidak ditemukan:\n{}".format(app_path)
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

        logging.info(
            "Aplikasi berhasil dijalankan. PID=%s",
            process.pid
        )

        return True

    except Exception as e:

        logging.exception(
            "Gagal menjalankan aplikasi: %s",
            str(e)
        )

        raise


# ============================================================
# FINGER
# ============================================================

def start_finger(no_peserta, config):

    no_peserta = validate_peserta(no_peserta)

    finger_path = config.get("finger_path")

    if not finger_path:
        raise Exception("finger_path belum dikonfigurasi.")

    # --------------------------------------------------------
    # Jika aplikasi Finger menerima nomor peserta melalui
    # command line, bagian ini bisa digunakan.
    #
    # Contoh:
    # After.exe 000123456789
    #
    # Kalau After.exe tidak menerima argument, kosongkan
    # arguments dan aplikasi hanya akan dibuka.
    # --------------------------------------------------------

    arguments = []

    if config.get("finger_send_peserta", False):
        arguments.append(no_peserta)

    return run_application(
        finger_path,
        no_peserta,
        arguments
    )


# ============================================================
# FRISTA
# ============================================================

def start_frista(no_peserta, config):

    no_peserta = validate_peserta(no_peserta)

    frista_path = config.get("frista_path")

    if not frista_path:
        raise Exception("frista_path belum dikonfigurasi.")

    arguments = []

    if config.get("frista_send_peserta", False):
        arguments.append(no_peserta)

    return run_application(
        frista_path,
        no_peserta,
        arguments
    )


# ============================================================
# PARSE URL
# ============================================================

def parse_protocol_url(url):

    logging.info("Protocol URL: %s", url)

    parsed = urllib.parse.urlparse(url)

    scheme = parsed.scheme.lower()

    query = urllib.parse.parse_qs(parsed.query)

    no_peserta = query.get("no_peserta", [None])[0]

    return scheme, no_peserta


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        config = load_config()

        # Tidak ada parameter
        if len(sys.argv) < 2:

            print("AutoBiometrik BPJS")
            print("")
            print("Gunakan:")
            print("  fingerbpjs://start?no_peserta=123456")
            print("  fristabpjs://start?no_peserta=123456")

            return

        url = sys.argv[1]

        scheme, no_peserta = parse_protocol_url(url)

        if not no_peserta:
            raise Exception(
                "Parameter no_peserta tidak ditemukan."
            )

        # ----------------------------------------------------
        # FINGER
        # ----------------------------------------------------

        if scheme == "fingerbpjs":

            start_finger(
                no_peserta,
                config
            )

            return

        # ----------------------------------------------------
        # FRISTA
        # ----------------------------------------------------

        if scheme == "fristabpjs":

            start_frista(
                no_peserta,
                config
            )

            return

        raise Exception(
            "Protocol tidak dikenal: {}".format(scheme)
        )

    except Exception as e:

        logging.exception(
            "ERROR: %s",
            str(e)
        )

        # Saat debug masih berguna.
        # Setelah build --noconsole, error tetap masuk log.
        print("ERROR:", str(e))


if __name__ == "__main__":
    main()