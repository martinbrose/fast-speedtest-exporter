import subprocess
import json
import os
import logging
import datetime
from prometheus_client import make_wsgi_app, Gauge, Info
from flask import Flask
from waitress import serve
from shutil import which

app = Flask("fast-com-Speedtest-Exporter")  # Create flask app

# Setup logging values
format_string = 'level=%(levelname)s datetime=%(asctime)s %(message)s'
logging.basicConfig(encoding='utf-8',
                    level=logging.DEBUG,
                    format=format_string)

# Disable Waitress Logs
log = logging.getLogger('waitress')
log.disabled = True

# Create Metrics
client = Info('speedtest_client', 'Speedtest client information')
# server = Info('speedtest_server', 'Speedtest server used to test')
# ping = Gauge('speedtest_ping_latency_milliseconds',
#              'Speedtest current Ping in ms')
# jitter = Gauge('speedtest_jitter_latency_milliseconds',
#                'Speedtest current Jitter in ms')
download_speed = Gauge('speedtest_download_bits_per_second',
                       'Speedtest current Download Speed in bit/s')
# upload_speed = Gauge('speedtest_upload_bits_per_second',
#                      'Speedtest current Upload speed in bits/s')
up = Gauge('speedtest_up', 'Speedtest status whether the scrape worked')

# Cache metrics for how long (seconds)?
cache_seconds = int(os.environ.get('SPEEDTEST_CACHE_FOR', 0))
cache_until = datetime.datetime.fromtimestamp(0)


def bytes_to_bits(bytes_per_sec):
    return bytes_per_sec * 8


def bits_to_megabits(bits_per_sec):
    megabits = round(bits_per_sec * (10**-6), 2)
    return str(megabits) + "Mbps"

def megabits_to_bits(megabits):
    bits_per_sec = int(megabits) * (10**6)
    return str(bits_per_sec)

def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError:
        return False
    return True


def runTest():
    timeout = int(os.environ.get('SPEEDTEST_TIMEOUT', 90))

    cmd = [
        "fastcli", "--json"
    ]
    try:
        output = subprocess.check_output(cmd, timeout=timeout)
    except subprocess.CalledProcessError as e:
        output = e.output
        if not is_json(output):
            if len(output) > 0:
                logging.error('Fast CLI Error occurred that' +
                              'was not in JSON format')
            return (0, 0, 0, 0, 0)
    except subprocess.TimeoutExpired:
        logging.error('Fast CLI process took too long to complete ' +
                      'and was killed.')
        return (0, 0, 0, 0, 0)

    if is_json(output):
        data = json.loads(output)
        if "error" in data:
            # Socket error
            print('Something went wrong')
            print(data['error'])
            return (0, 0, 0, 0, 0)  # Return all data as 0
        if "version" in data:
            actual_client_city = data['client_info']['location']['city']
            actual_client_region = data['client_info']['location']['country']
            # actual_ping = data['latency_ms']['value']
            # actual_jitter = data['Jitter_ms']['value']
            download_mbps = data['download_speed']
            download = megabits_to_bits(download_mbps)
            # upload_mbps = data['90th_percentile_upload_speed']['value']
            # upload = megabits_to_bits(upload_mbps)
            # return (actual_server_city, actual_server_region, actual_ping, actual_jitter, 
                    # download_mbps, download, upload_mbps, upload, 1)
            return (actual_client_city, actual_client_region, download_mbps, download, 1)


@app.route("/metrics")
def updateResults():
    global cache_until

    if datetime.datetime.now() > cache_until:
        r_client_city, r_client_region, r_download_mbps, r_download, r_status = runTest()
        # r_server_city, r_server_region, r_ping, r_jitter, r_download_mbps, r_download, r_upload_mbps, r_upload, r_status = runTest()
        # server.info({'server_location_city': r_server_city, 'server_location_region': r_server_region})
        # jitter.set(r_jitter)
        # ping.set(r_ping)
        download_speed.set(r_download)
        # upload_speed.set(r_upload)
        up.set(r_status)
        logging.info("Client City=" + r_client_city + " Client Region=" + r_client_region +
                     " Download=" + str(r_download_mbps) + "Mbps")

        cache_until = datetime.datetime.now() + datetime.timedelta(
            seconds=cache_seconds)

    return make_wsgi_app()


@app.route("/")
def mainPage():
    return ("<h1>Welcome to fast.com-Speedtest-Exporter.</h1>" +
            "Click <a href='/metrics'>here</a> to see metrics.")


def checkForBinary():
    if which("fastcli") is None:
        logging.error("Speedtest CLI binary not found. Please install it by" +
                      " going to the official website.\n" +
                      "https://pypi.org/project/fastcli/")
        exit(1)
    speedtestVersionDialog = (subprocess.run(['fastcli', '--version'],
                              capture_output=True, text=True))


if __name__ == '__main__':
    checkForBinary()
    PORT = os.getenv('SPEEDTEST_PORT', 9798)
    logging.info("Starting fast.com-Speedtest-Exporter on http://localhost:" +
                 str(PORT))
    serve(app, host='0.0.0.0', port=PORT)
