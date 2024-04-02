# pylint: disable=missing-module-docstring,missing-function-docstring

import json
import random
import string
import time

import bcrypt
import configargparse
import paho.mqtt.client as mqttClient
from flask import Flask
from flask_httpauth import HTTPBasicAuth
from prometheus_client import Gauge, make_wsgi_app

app = Flask(__name__)
app.config["SECRET_KEY"] = "".join(random.sample(string.ascii_lowercase, 16))
auth = HTTPBasicAuth()

# ENERGY
teleinfo_total = Gauge("teleinfo_total", "energy total")
teleinfo_yesterday = Gauge("teleinfo_yesterday", "energy yesterday")
teleinfo_today = Gauge("teleinfo_today", "energy today")
teleinfo_power = Gauge("teleinfo_power", "active power")
teleinfo_apparent_power = Gauge("teleinfo_apparent_power", "apparent power")
teleinfo_reactive_power = Gauge("teleinfo_reactive_power", "reactive power")
teleinfo_power_factor = Gauge("teleinfo_power_factor", "power factor")
teleinfo_voltage = Gauge("teleinfo_voltage", "voltage")
teleinfo_current = Gauge("teleinfo_current", "current")

# METER
teleinfo_phases_count = Gauge("teleinfo_phases_count", "number of phases")
teleinfo_max_current_per_phase = Gauge(
    "teleinfo_current_per_phase", "current per phase in the contract"
)
teleinfo_max_power_per_phase = Gauge(
    "teleinfo_max_power_per_phase", "power per phase in the contract (VA)"
)
teleinfo_max_power_per_phase_with_overload = Gauge(
    "teleinfo_max_power_per_phase_with_overload",
    "maximum power per phase including an accetable % of overload (VA)",
)
teleinfo_instant_voltage_per_phase = Gauge(
    "teleinfo_instant_voltage_per_phase",
    "instant voltage on phase x",
    ["phase"],
)
teleinfo_instant_apparent_power_per_phase = Gauge(
    "teleinfo_instant_apparent_power_per_phase",
    "instant apparent power on phase x",
    ["phase"],
)
teleinfo_instant_active_power_per_phase = Gauge(
    "teleinfo_instant_active_power_per_phase",
    "instant active power on phase x",
    ["phase"],
)
teleinfo_instant_current_per_phase = Gauge(
    "teleinfo_instant_current_per_phase",
    "instant current on phase x",
    ["phase"],
)
teleinfo_power_factor_per_phase = Gauge(
    "teleinfo_power_factor_per_phase",
    "current calculated power factor (cos φ) on phase x",
    ["phase"],
)
teleinfo_total_apparent_power = Gauge(
    "teleinfo_total_apparent_power", "total instant apparent power (on all phases)"
)
teleinfo_total_active_power = Gauge(
    "teleinfo_total_active_power", "total instant active power (on all phases)"
)
teleinfo_total_current = Gauge(
    "teleinfo_total_current", "total instant current (on all phases)"
)

# PROD
teleinfo_production_instant_apparent_power = Gauge(
    "teleinfo_production_instant_apparent_power", "instant apparent power"
)
teleinfo_production_instant_active_power = Gauge(
    "teleinfo_production_instant_active_power", "instant active power"
)
teleinfo_production_power_factor = Gauge(
    "teleinfo_production_power_factor", "current calculated power factor (cos φ)"
)

# TIC
teleinfo_contract_number = Gauge(
    "teleinfo_contract_number", "contract number", ["number"]
)
teleinfo_contract_type = Gauge("teleinfo_contract_type", "contract type", ["type"])


def on_connect(client, userdata, flags, rc):  # pylint: disable=unused-argument
    client.subscribe("teleinfo/tele/SENSOR")
    if rc == 0:
        print("Connected to broker")
    else:
        print("Connection failed")


def on_message(client, userdata, message):  # pylint: disable=unused-argument
    try:
        message = json.loads(message.payload.decode("utf-8"))
    except UnicodeDecodeError:
        pass

    if "ENERGY" in message:
        teleinfo_total.set(message.get("ENERGY", {}).get("Total", 0))
        teleinfo_yesterday.set(message.get("ENERGY", {}).get("Yesterday", 0))
        teleinfo_today.set(message.get("ENERGY", {}).get("Today", 0))
        teleinfo_power.set(message.get("ENERGY", {}).get("Power", 0))
        teleinfo_apparent_power.set(message.get("ENERGY", {}).get("ApparentPower", 0))
        teleinfo_reactive_power.set(message.get("ENERGY", {}).get("ReactivePower", 0))
        teleinfo_power_factor.set(message.get("ENERGY", {}).get("Factor", 0))
        teleinfo_voltage.set(message.get("ENERGY", {}).get("Voltage", 0))
        teleinfo_current.set(message.get("ENERGY", {}).get("Current", 0))
    elif "METER" in message:
        teleinfo_phases_count.set(message.get("METER", {}).get("PH", 0))
        teleinfo_max_current_per_phase.set(message.get("METER", {}).get("ISUB", 0))
        teleinfo_max_power_per_phase.set(message.get("METER", {}).get("PSUB", 0))
        teleinfo_max_power_per_phase_with_overload.set(
            message.get("METER", {}).get("PMAX", 0)
        )
        teleinfo_total_apparent_power.set(message.get("METER", {}).get("P", 0))
        teleinfo_total_active_power.set(message.get("METER", {}).get("W", 0))
        teleinfo_total_current.set(message.get("METER", {}).get("I", 0))
        for i in range(1, 4):
            if not message.get("METER", {}).get(f"U{i}"):
                break
            teleinfo_instant_voltage_per_phase.labels(f"U{i}").set(
                message.get("METER", {}).get(f"U{i}", 0)
            )
            teleinfo_instant_apparent_power_per_phase.labels(f"P{i}").set(
                message.get("METER", {}).get(f"P{i}", 0)
            )
            teleinfo_instant_active_power_per_phase.labels(f"W{i}").set(
                message.get("METER", {}).get(f"W{i}", 0)
            )
            teleinfo_instant_current_per_phase.labels(f"I{i}").set(
                message.get("METER", {}).get(f"I{i}", 0)
            )
            teleinfo_power_factor_per_phase.labels(f"C{i}").set(
                message.get("METER", {}).get(f"C{i}", 0)
            )

    elif "PROD" in message:
        teleinfo_production_instant_apparent_power.set(
            message.get("PROD", {}).get("VA", 0)
        )
        teleinfo_production_instant_active_power.set(message.get("PROD", {}).get("W", 0))
        teleinfo_production_power_factor.set(message.get("PROD", {}).get("COS", 0))
    elif "TIC" in message:
        teleinfo_contract_number.labels(message.get("TIC", {}).get("ADCO", 0)).set(0)
        teleinfo_contract_type.labels(message.get("TIC", {}).get("OPTARIF", 0)).set(0)


def on_disconnect(client, userdata, rc):  # pylint: disable=unused-argument
    print("Diconnected from broker, reconnecting...")
    while True:
        try:
            if not client.reconnect():
                break
        except ConnectionRefusedError:
            time.sleep(1)


@app.before_request
@auth.login_required()
def global_auth():
    return


@auth.verify_password
def verify_password(username, password):
    if (
        not app.config.get("USERS")
        or username in app.config["USERS"]
        and bcrypt.hashpw(password.encode(), app.config["USERS"].get(username))
    ):
        return username
    return None


@app.route("/metrics")
def metrics():
    return make_wsgi_app()


def main():
    p = configargparse.ArgParser()
    p.add("--broker_host", required=True, help="MQTT Host", env_var="BROKER_HOST")
    p.add("--broker_port", help="MQTT Port", env_var="BROKER_PORT", default=1883)
    p.add(
        "--broker_topic",
        help="Teleinfo Topic",
        env_var="BROKER_TOPIC",
        default="teleinfo/tele/SENSOR",
    )
    p.add("--broker_user", help="MQTT user", env_var="BROKER_USER")
    p.add("--broker_password", help="MQTT Password", env_var="BROKER_PASSWORD")
    p.add("--auth_user", help="Basic Auth user", env_var="AUTH_USER")
    p.add("--auth_hash", help="Basic Auth hash", env_var="AUTH_HASH")
    p.add("--http_port", help="HTTP Server Port", env_var="HTTP_PORT", default=8000)
    p.add("--http_cert", help="HTTP Server Certificate", env_var="HTTP_CERT")
    p.add("--http_key", help="HTTP Server Key", env_var="HTTP_KEY")
    options = p.parse_args()

    if options.auth_user and options.auth_hash:
        app.config["USERS"] = {options.auth_user: options.auth_hash.encode()}

    client = mqttClient.Client(
        f"teleinfo-exporter_{''.join(random.sample(string.ascii_lowercase, 8))}"
    )

    if options.broker_user and options.broker_password:
        client.username_pw_set(options.broker_user, password=options.broker_password)

    client.connect(options.broker_host, port=options.broker_port)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.loop_start()

    if options.http_cert and options.http_key:
        ssl_context = (options.http_cert, options.http_key)
    else:
        ssl_context = None
    app.run(host="0.0.0.0", port=options.http_port, ssl_context=ssl_context)
