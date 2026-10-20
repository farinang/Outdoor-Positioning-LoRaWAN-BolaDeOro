import paho.mqtt.client as mqtt
import json

BROKER = "mqtt2.yubox.com"
PORT = 1883

APPLICATION_ID = "30"
TOPIC = f"application/{APPLICATION_ID}/device/+/event/up"

MQTT_USERNAME = "pedro.tesis.2026"
MQTT_PASSWORD = "1c9b70db"


# ============================================================
# TABLA AU915: DR -> SF / BW / CODING RATE
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


def on_connect(client, userdata, flags, rc):

    print("Resultado conexión:", rc)

    if rc == 0:
        print("Conectado al broker")
        print("Suscribiendo a:", TOPIC)

        client.subscribe(TOPIC)

    elif rc == 4:
        print("ERROR: usuario o contraseña incorrectos")

    elif rc == 5:
        print("ERROR: conexión no autorizada")

    else:
        print("ERROR DE CONEXIÓN:", rc)


def on_message(client, userdata, msg):

    try:

        payload = json.loads(
            msg.payload.decode(
                "utf-8",
                errors="replace"
            )
        )

        # ====================================================
        # INFORMACIÓN DEL NODO
        # ====================================================

        application_id = payload.get(
            "applicationID",
            ""
        )

        application_name = payload.get(
            "applicationName",
            ""
        )

        device_name = payload.get(
            "deviceName",
            ""
        )

        dev_eui = payload.get(
            "devEUI",
            ""
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

        # ====================================================
        # INFORMACIÓN TX
        # ====================================================

        tx_info = payload.get(
            "txInfo",
            {}
        )

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
            "DESCONOCIDO"
        )

        bandwidth = dr_info.get(
            "bw",
            "DESCONOCIDO"
        )

        coding_rate = dr_info.get(
            "cr",
            "DESCONOCIDO"
        )

        # ====================================================
        # IMPRIMIR INFORMACIÓN GENERAL DEL UPLINK
        # ====================================================

        print("\n")
        print("=" * 90)
        print("UPLINK RECIBIDO")
        print("=" * 90)

        print(
            f"Application ID   : {application_id}"
        )

        print(
            f"Application Name : {application_name}"
        )

        print(
            f"Device Name      : {device_name}"
        )

        print(
            f"DevEUI           : {dev_eui}"
        )

        print(
            f"ADR              : {adr}"
        )

        print(
            f"Frame Counter    : {f_cnt}"
        )

        print(
            f"FPort            : {f_port}"
        )

        print()

        print(
            f"Frequency        : {frequency} Hz"
        )

        print(
            f"Data Rate        : DR{dr}"
        )

        print(
            f"Spreading Factor : SF{spreading_factor}"
        )

        print(
            f"Bandwidth        : {bandwidth} kHz"
        )

        print(
            f"Coding Rate      : {coding_rate}"
        )

        # ====================================================
        # GATEWAYS
        # ====================================================

        rx_info_list = payload.get(
            "rxInfo",
            []
        )

        print()
        print(
            f"Gateways que recibieron el uplink: "
            f"{len(rx_info_list)}"
        )

        print("-" * 90)

        for index, rx_info in enumerate(
            rx_info_list,
            start=1
        ):

            gateway_id = rx_info.get(
                "gatewayID",
                ""
            )

            gateway_name = rx_info.get(
                "name",
                ""
            )

            uplink_id = rx_info.get(
                "uplinkID",
                ""
            )

            rssi = rx_info.get(
                "rssi",
                ""
            )

            snr = rx_info.get(
                "loRaSNR",
                ""
            )

            location = rx_info.get(
                "location",
                {}
            )

            gateway_lat = location.get(
                "latitude",
                ""
            )

            gateway_lon = location.get(
                "longitude",
                ""
            )

            gateway_alt = location.get(
                "altitude",
                ""
            )

            gateway_time = rx_info.get(
                "time",
                ""
            )

            print()
            print(
                f"GATEWAY #{index}"
            )

            print(
                f"  Gateway ID   : {gateway_id}"
            )

            print(
                f"  Gateway Name : {gateway_name}"
            )

            print(
                f"  RSSI         : {rssi} dBm"
            )

            print(
                f"  SNR          : {snr} dB"
            )

            print(
                f"  Latitude     : {gateway_lat}"
            )

            print(
                f"  Longitude    : {gateway_lon}"
            )

            print(
                f"  Altitude     : {gateway_alt}"
            )

            print(
                f"  Time         : {gateway_time}"
            )

            print(
                f"  Uplink ID    : {uplink_id}"
            )

        print()
        print("=" * 90)
        print()
        print()
        


    except json.JSONDecodeError:

        print(
            "ERROR: payload recibido no es JSON válido"
        )

    except Exception as error:

        print(
            "ERROR procesando mensaje:"
        )

        print(
            error
        )


def on_disconnect(
    client,
    userdata,
    rc
):

    print(
        "\nDesconectado del broker."
    )

    print(
        "Código:",
        rc
    )


client = mqtt.Client()

client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)

client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect


print("=" * 90)
print("PRUEBA MQTT - INFORMACIÓN COMPLETA POR DevEUI")
print("=" * 90)

print(
    "Broker:",
    BROKER
)

print(
    "Puerto:",
    PORT
)

print(
    "Topic:",
    TOPIC
)

print(
    "\nConectando..."
)


try:

    client.connect(
        BROKER,
        PORT,
        keepalive=60
    )

    print(
        "\nEsperando uplinks..."
    )

    print(
        "Presiona Ctrl+C para detener.\n"
    )

    client.loop_forever()


except KeyboardInterrupt:

    print(
        "\nInterrupción manual detectada."
    )

    client.disconnect()


except Exception as error:

    print(
        "\nERROR:"
    )

    print(
        error
    )