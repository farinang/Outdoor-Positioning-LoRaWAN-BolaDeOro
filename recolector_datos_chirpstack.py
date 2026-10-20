'''
MQTT_USERNAME = "pedro.tesis.2026"
MQTT_PASSWORD = "1c9b70db"
'''

import csv
import json
import os
import re
import ssl
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt


# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================

PATH_NODES_GATEWAYS = Path("informacion_nodos_gateways")
RAW_NODES_CSV = PATH_NODES_GATEWAYS / "datos_nodos_raw.csv"
NODES_CSV = PATH_NODES_GATEWAYS / "datos_nodos.csv"
GATEWAYS_CSV = PATH_NODES_GATEWAYS / "gateways.csv"

OUTPUT_FOLDER = "datos_chirpstack"

SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
DISPLAY_REFRESH_SECONDS = 1.0


# ============================================================
# 2. MQTT / CHIRPSTACK V3
# ============================================================

MQTT_BROKER = "mqtt2.yubox.com"
MQTT_PORT = 1883

APPLICATION_ID = "30"
MQTT_TOPIC = f"application/{APPLICATION_ID}/device/+/event/up"

CLIENT_ID = f"collector-{SESSION_ID}"

MQTT_USERNAME = "pedro.tesis.2026"
MQTT_PASSWORD = "1c9b70db"

MQTT_USE_TLS = False
MQTT_TLS_INSECURE = False


# ============================================================
# 3. AU915: DR -> SF / BW / CR
# ============================================================

AU915_DATA_RATES = {
    0: {"sf": 12, "bw": 125, "cr": "4/5"},
    1: {"sf": 11, "bw": 125, "cr": "4/5"},
    2: {"sf": 10, "bw": 125, "cr": "4/5"},
    3: {"sf": 9,  "bw": 125, "cr": "4/5"},
    4: {"sf": 8,  "bw": 125, "cr": "4/5"},
    5: {"sf": 7,  "bw": 125, "cr": "4/5"},
    6: {"sf": 8,  "bw": 500, "cr": "4/5"},
}


# ============================================================
# 4. COLUMNAS DE LOS CSV DE MEDICIONES
# ============================================================

CSV_COLUMNS = [
    "id_nodo",
    "mac",

    "collected_at",

    "dev_eui",

    "gateway_id",
    "gateway_name",

    "rssi",
    "snr",

    "frequency",
    "dr",
    "spreading_factor",
    "bandwidth",
    "coding_rate",

    "adr",
    "f_cnt",
    "f_port",
    "uplink_id",
]


# ============================================================
# 5. FUNCIONES AUXILIARES
# ============================================================

def clean_hex_id(value):
    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace(":", "")
        .replace("-", "")
        .replace(" ", "")
    )


def normalize_node_eui(value):
    """
    CSV local:
        8cbfea852f00
    ChirpStack:
        8cbfea852f000000

    Si la MAC local tiene 12 caracteres, se agregan 0000.
    """
    eui = clean_hex_id(value)

    if len(eui) == 12:
        eui += "0000"

    return eui


def normalize_gateway_id(value):
    # En gateways no se agregan ceros.
    return clean_hex_id(value)


def csv_node_mac(value):
    """
    Mantiene en datos_nodos.csv el formato local de 12 caracteres
    cuando el DevEUI de 16 caracteres termina en 0000.
    """
    mac = clean_hex_id(value)

    if len(mac) == 16 and mac.endswith("0000"):
        return mac[:-4]

    return mac


def safe_float(value):
    if value in ("", None):
        return ""

    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return value


def numeric_sort_key(value):
    text = str(value).strip()

    try:
        return (0, int(text))
    except ValueError:
        try:
            return (0, float(text))
        except ValueError:
            return (1, text.lower())


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


def gateway_label(name):
    """
    Solo para mostrar en consola y nombrar el CSV.

    gw-rak2287-rpi4-46  -> rpi-46
    gw-gye-alborada-5ta -> alborada-5ta
    """
    name = str(name).strip()
    lower = name.lower()

    match = re.search(r"rpi\d*-(\d+)", lower)
    if match:
        return f"rpi-{match.group(1)}"

    if "alborada-" in lower:
        pos = lower.index("alborada-")
        return name[pos:]

    return name


# ============================================================
# 6. CREAR datos_nodos.csv DESDE datos_nodos_raw.csv
# ============================================================

def generate_nodes_csv(raw_path_str, output_path_str):
    """
    datos_nodos_raw.csv:
        mac,lat,lon,piscina,lat_piscina,lon_piscina

    Proceso:
    1. Lee todas las filas.
    2. Ordena por piscina ascendente.
    3. Cada MAC nueva recibe el siguiente id_nodo.
    4. Una MAC repetida conserva su mismo id_nodo.
    5. Genera datos_nodos.csv.
    """

    raw_path = Path(raw_path_str)
    output_path = Path(output_path_str)

    if not raw_path.exists():
        raise FileNotFoundError(
            f"No existe '{raw_path_str}'. "
            "Debe contener: mac,lat,lon,piscina,lat_piscina,lon_piscina"
        )

    required = {
        "mac",
        "lat",
        "lon",
        "piscina",
        "lat_piscina",
        "lon_piscina",
    }

    rows = []

    with raw_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        missing = required - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                "Faltan columnas en datos_nodos_raw.csv: "
                + ", ".join(sorted(missing))
            )

        for row_number, row in enumerate(reader, start=2):
            mac = csv_node_mac(row["mac"])
            piscina = str(row["piscina"]).strip()

            if not mac:
                raise ValueError(f"Fila {row_number}: MAC vacía.")

            if not piscina:
                raise ValueError(f"Fila {row_number}: piscina vacía.")

            rows.append({
                "mac": mac,
                "lat": safe_float(row["lat"]),
                "lon": safe_float(row["lon"]),
                "piscina": piscina,
                "lat_piscina": safe_float(row["lat_piscina"]),
                "lon_piscina": safe_float(row["lon_piscina"]),
            })

    # La piscina gobierna el orden.
    rows.sort(
        key=lambda row: (
            numeric_sort_key(row["piscina"]),
            row["mac"],
        )
    )

    # Validar que la misma MAC tenga siempre la misma posición.
    node_coordinates = {}

    for row in rows:
        mac = row["mac"]
        coords = (row["lat"], row["lon"])

        if mac not in node_coordinates:
            node_coordinates[mac] = coords
        elif node_coordinates[mac] != coords:
            raise ValueError(
                f"La MAC {mac} aparece con diferentes coordenadas de nodo. "
                f"Primera: {node_coordinates[mac]} / Otra: {coords}"
            )

    # Crear id_nodo por primera aparición de cada MAC.
    mac_to_id = {}
    next_id = 1

    for row in rows:
        mac = row["mac"]

        if mac not in mac_to_id:
            mac_to_id[mac] = next_id
            next_id += 1

        row["id_nodo"] = mac_to_id[mac]

    output_columns = [
        "id_nodo",
        "mac",
        "lat",
        "lon",
        "piscina",
        "lat_piscina",
        "lon_piscina",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_columns)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                "id_nodo": row["id_nodo"],
                "mac": row["mac"],
                "lat": row["lat"],
                "lon": row["lon"],
                "piscina": row["piscina"],
                "lat_piscina": row["lat_piscina"],
                "lon_piscina": row["lon_piscina"],
            })

    print(
        f"datos_nodos.csv generado: "
        f"{len(mac_to_id)} nodos únicos / {len(rows)} filas."
    )


generate_nodes_csv(
    RAW_NODES_CSV,
    NODES_CSV
)


# ============================================================
# 7. CARGAR datos_nodos.csv
# ============================================================

def load_nodes_csv(path_str):
    path = Path(path_str)

    required = {
        "id_nodo",
        "mac",
        "lat",
        "lon",
        "piscina",
        "lat_piscina",
        "lon_piscina",
    }

    nodes = {}

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        missing = required - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                "Faltan columnas en datos_nodos.csv: "
                + ", ".join(sorted(missing))
            )

        for row in reader:
            id_nodo = str(row["id_nodo"]).strip()
            raw_mac = csv_node_mac(row["mac"])
            dev_eui = normalize_node_eui(raw_mac)
            piscina = str(row["piscina"]).strip()

            if dev_eui not in nodes:
                nodes[dev_eui] = {
                    "id_nodo": id_nodo,
                    "mac": raw_mac,
                    "piscinas": [],
                }

            node = nodes[dev_eui]

            if node["id_nodo"] != id_nodo:
                raise ValueError(
                    f"La MAC {raw_mac} tiene más de un id_nodo."
                )

            if piscina not in node["piscinas"]:
                node["piscinas"].append(piscina)

    for node in nodes.values():
        node["piscinas"].sort(key=numeric_sort_key)

    node_order = sorted(
        nodes.keys(),
        key=lambda dev_eui: numeric_sort_key(
            nodes[dev_eui]["id_nodo"]
        )
    )

    return nodes, node_order


NODES_BY_EUI, NODE_ORDER = load_nodes_csv(
    NODES_CSV
)


# ============================================================
# 8. CARGAR gateways.csv
# ============================================================

def load_gateways_csv(path_str):
    path = Path(path_str)

    if not path.exists():
        raise FileNotFoundError(
            f"No existe '{path_str}'. "
            "Debe contener: mac,nombre,lat,lon"
        )

    required = {
        "mac",
        "nombre",
        "lat",
        "lon",
    }

    gateways = {}

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        missing = required - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                "Faltan columnas en gateways.csv: "
                + ", ".join(sorted(missing))
            )

        for row_number, row in enumerate(reader, start=2):
            gateway_id = normalize_gateway_id(row["mac"])
            name = str(row["nombre"]).strip()

            if not gateway_id:
                raise ValueError(
                    f"Fila {row_number}: MAC de gateway vacía."
                )

            if gateway_id in gateways:
                raise ValueError(
                    f"Gateway duplicado en gateways.csv: {gateway_id}"
                )

            gateways[gateway_id] = {
                "name": name,
                "label": gateway_label(name),
                "lat": safe_float(row["lat"]),
                "lon": safe_float(row["lon"]),
            }

    return gateways


GATEWAYS = load_gateways_csv(
    GATEWAYS_CSV
)


# ============================================================
# 9. CONTADORES
# ============================================================

counts = {
    dev_eui: {
        gateway_id: 0
        for gateway_id in GATEWAYS
    }
    for dev_eui in NODE_ORDER
}

stats = {
    "mqtt_messages": 0,
    "rows_saved": 0,
    "unknown_devices": 0,
    "ignored_gateways": 0,
    "duplicate_rx": 0,
    "json_errors": 0,
}

seen_rx = set()

lock = threading.Lock()
stop_event = threading.Event()


# ============================================================
# 10. UN CSV POR GATEWAY
# ============================================================

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

gateway_files = {}
gateway_writers = {}
gateway_paths = {}

for gateway_id, gateway in GATEWAYS.items():
    filename = (
        f"mediciones_{gateway['label']}_{SESSION_ID}.csv"
    )

    path = os.path.join(
        OUTPUT_FOLDER,
        filename
    )

    file_obj = open(
        path,
        "w",
        encoding="utf-8",
        newline="",
        buffering=1,
    )

    writer = csv.DictWriter(
        file_obj,
        fieldnames=CSV_COLUMNS
    )

    writer.writeheader()
    file_obj.flush()

    gateway_files[gateway_id] = file_obj
    gateway_writers[gateway_id] = writer
    gateway_paths[gateway_id] = path


# ============================================================
# 11. ORDEN FINAL DE LOS CSV POR id_nodo
# ============================================================

def sort_measurement_csv(path_str):
    path = Path(path_str)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    rows.sort(
        key=lambda row: (
            numeric_sort_key(
                row.get("id_nodo", "")
            ),
            int(row["f_cnt"])
            if str(row.get("f_cnt", "")).isdigit()
            else -1,
            row.get("collected_at", ""),
        )
    )

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=CSV_COLUMNS
        )

        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# 12. TABLA EN TIEMPO REAL
# ============================================================

def print_live_table():
    while not stop_event.is_set():
        with lock:
            local_counts = {
                dev_eui: values.copy()
                for dev_eui, values in counts.items()
            }

            local_stats = stats.copy()

        clear_terminal()

        print("=" * 110)
        print(" CHIRPSTACK V3 - RECOLECCIÓN POR GATEWAY")
        print("=" * 110)
        print(f"Topic: {MQTT_TOPIC}")
        print()

        gateway_ids = list(GATEWAYS.keys())

        node_width = 16
        gateway_width = 18

        header = (
            f"{'ID':>5} "
            f"{'Nodo':<{node_width}}"
        )

        for gateway_id in gateway_ids:
            header += (
                f"{GATEWAYS[gateway_id]['label']:>{gateway_width}}"
            )

        header += f"{'TOTAL':>12}"
        header += f"{'Piscinas':>20}"

        print(header)
        print("-" * len(header))

        gateway_totals = {
            gateway_id: 0
            for gateway_id in gateway_ids
        }

        grand_total = 0

        for dev_eui in NODE_ORDER:
            node = NODES_BY_EUI[dev_eui]
            id_nodo = node["id_nodo"]

            nodo_name = (
                f"Tablero-{int(id_nodo):02d}"
                if str(id_nodo).isdigit()
                else f"Tablero-{id_nodo}"
            )

            line = (
                f"{id_nodo:>5} "
                f"{nodo_name:<{node_width}}"
            )

            total_node = 0

            for gateway_id in gateway_ids:
                value = local_counts[
                    dev_eui
                ][gateway_id]

                line += (
                    f"{value:>{gateway_width}}"
                )

                total_node += value
                gateway_totals[gateway_id] += value

            pools = ",".join(
                node["piscinas"]
            )

            line += f"{total_node:>12}"
            line += f"{pools:>20}"

            grand_total += total_node

            print(line)

        print("-" * len(header))

        total_line = (
            f"{'':>5} "
            f"{'TOTAL':<{node_width}}"
        )

        for gateway_id in gateway_ids:
            total_line += (
                f"{gateway_totals[gateway_id]:>{gateway_width}}"
            )

        total_line += f"{grand_total:>12}"

        print(total_line)

        print()

        print(
            f"Mensajes MQTT: {local_stats['mqtt_messages']} | "
            f"Filas guardadas: {local_stats['rows_saved']} | "
            f"Nodos no válidos: {local_stats['unknown_devices']} | "
            f"Gateways ignorados: {local_stats['ignored_gateways']} | "
            f"Duplicados: {local_stats['duplicate_rx']}"
        )

        print()
        print("Presiona Ctrl+C para finalizar.")

        stop_event.wait(
            DISPLAY_REFRESH_SECONDS
        )


# ============================================================
# 13. MQTT
# ============================================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties=None
):
    try:
        ok = int(reason_code) == 0
    except (TypeError, ValueError):
        ok = str(reason_code).lower() in (
            "success",
            "0",
        )

    if ok:
        client.subscribe(
            MQTT_TOPIC,
            qos=0
        )
    else:
        print(
            f"Error MQTT: {reason_code}"
        )


def on_message(
    client,
    userdata,
    msg
):
    try:
        payload = json.loads(
            msg.payload.decode(
                "utf-8",
                errors="replace"
            )
        )

    except (
        json.JSONDecodeError,
        UnicodeDecodeError
    ):
        with lock:
            stats["json_errors"] += 1

        return

    with lock:
        stats["mqtt_messages"] += 1

    # --------------------------------------------------------
    # ChirpStack v3 - nodo
    # --------------------------------------------------------

    dev_eui = normalize_node_eui(
        payload.get(
            "devEUI",
            ""
        )
    )

    adr = payload.get(
        "adr",
        ""
    )

    f_cnt = payload.get(
        "fCnt",
        ""
    )

    f_port = payload.get(
        "fPort",
        ""
    )

    node = NODES_BY_EUI.get(
        dev_eui
    )

    if node is None:
        with lock:
            stats["unknown_devices"] += 1

        return

    # --------------------------------------------------------
    # TX
    # --------------------------------------------------------

    tx_info = payload.get(
        "txInfo",
        {}
    ) or {}

    frequency = tx_info.get(
        "frequency",
        ""
    )

    dr = tx_info.get(
        "dr",
        ""
    )

    dr_info = AU915_DATA_RATES.get(
        dr,
        {}
    )

    spreading_factor = dr_info.get(
        "sf",
        ""
    )

    bandwidth = dr_info.get(
        "bw",
        ""
    )

    coding_rate = dr_info.get(
        "cr",
        ""
    )

    # --------------------------------------------------------
    # Gateway(s)
    # --------------------------------------------------------

    rx_info_list = payload.get(
        "rxInfo",
        []
    ) or []

    for rx_info in rx_info_list:
        gateway_id = normalize_gateway_id(
            rx_info.get(
                "gatewayID",
                ""
            )
        )

        if gateway_id not in GATEWAYS:
            with lock:
                stats["ignored_gateways"] += 1

            continue

        gateway = GATEWAYS[
            gateway_id
        ]

        gateway_name = gateway[
            "name"
        ]

        rssi = rx_info.get(
            "rssi",
            ""
        )

        snr = rx_info.get(
            "loRaSNR",
            ""
        )


        uplink_id = rx_info.get(
            "uplinkID",
            ""
        )

        # Evitar duplicados.
        rx_key = (
            dev_eui,
            f_cnt,
            gateway_id,
            uplink_id,
        )

        with lock:
            if rx_key in seen_rx:
                stats["duplicate_rx"] += 1
                continue

            seen_rx.add(
                rx_key
            )

        row = {
            "id_nodo":
                node["id_nodo"],

            "mac":
                node["mac"],

            "collected_at":
                datetime.now()
                .astimezone()
                .isoformat(),


            "dev_eui":
                dev_eui,

            "gateway_id":
                gateway_id,

            "gateway_name":
                gateway_name,

            "rssi":
                rssi,

            "snr":
                snr,

            "frequency":
                frequency,

            "dr":
                dr,

            "spreading_factor":
                spreading_factor,

            "bandwidth":
                bandwidth,

            "coding_rate":
                coding_rate,

            "adr":
                adr,

            "f_cnt":
                f_cnt,

            "f_port":
                f_port,

            "uplink_id":
                uplink_id,
        }

        with lock:
            gateway_writers[
                gateway_id
            ].writerow(
                row
            )

            gateway_files[
                gateway_id
            ].flush()

            counts[
                dev_eui
            ][
                gateway_id
            ] += 1

            stats["rows_saved"] += 1


def on_disconnect(
    client,
    userdata,
    disconnect_flags=None,
    reason_code=None,
    properties=None
):
    pass


def create_client():
    try:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=CLIENT_ID,
            protocol=mqtt.MQTTv311,
        )

    except AttributeError:
        client = mqtt.Client(
            client_id=CLIENT_ID,
            protocol=mqtt.MQTTv311,
        )

    if MQTT_USERNAME:
        client.username_pw_set(
            MQTT_USERNAME,
            MQTT_PASSWORD
        )

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    if MQTT_USE_TLS:
        client.tls_set(
            cert_reqs=ssl.CERT_REQUIRED
        )

        client.tls_insecure_set(
            MQTT_TLS_INSECURE
        )

    try:
        client.reconnect_delay_set(
            min_delay=1,
            max_delay=30
        )
    except AttributeError:
        pass

    return client


# ============================================================
# 14. CIERRE
# ============================================================

def close_and_sort():
    for file_obj in gateway_files.values():
        try:
            file_obj.flush()
            file_obj.close()
        except Exception:
            pass

    print()
    print("Ordenando archivos por id_nodo...")

    for gateway_id, path in gateway_paths.items():
        sort_measurement_csv(
            path
        )

        print(
            f"OK - "
            f"{GATEWAYS[gateway_id]['label']}: "
            f"{path}"
        )


# ============================================================
# 15. MAIN
# ============================================================

def main():
    print("Inicializando recolector...")
    print(f"Nodos válidos: {len(NODES_BY_EUI)}")
    print(f"Gateways válidos: {len(GATEWAYS)}")
    print(f"Topic: {MQTT_TOPIC}")
    print()

    client = create_client()

    display_thread = threading.Thread(
        target=print_live_table,
        daemon=True,
    )

    display_thread.start()

    try:
        client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            keepalive=60
        )

        client.loop_start()

        while not stop_event.is_set():
            time.sleep(0.25)

    except KeyboardInterrupt:
        pass

    except Exception as exc:
        print(
            f"Error: {exc}",
            file=sys.stderr
        )

    finally:
        stop_event.set()

        try:
            client.disconnect()
        except Exception:
            pass

        try:
            client.loop_stop()
        except Exception:
            pass

        close_and_sort()

        print()
        print("RECOLECCIÓN FINALIZADA")


if __name__ == "__main__":
    main()
