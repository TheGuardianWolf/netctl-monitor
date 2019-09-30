#!/usr/bin/python3

import time
from argparse import ArgumentParser
import subprocess
import sys
import traceback
import speedtest


def network_speed():
    try:
        s = speedtest.Speedtest()
        s.get_best_server()
        return s.download()
    except speedtest.ConfigRetrievalError:
        return 0.0


def reconnect(interface):
    subprocess.run(["systemctl", "restart", "wpa_supplicant@{interface}".format(interface)])

if __name__ == "__main__":
    parser = ArgumentParser(description="Monitors wpa network connection and reconnects on fail or slow speeds")
    parser.add_argument("interface")
    parser.add_argument("interval")
    parser.add_argument("threshold")

    args = parser.parse_args()

    try:
        threshold = int(args.threshold)
        while True:
            time.sleep(args.interval)
            speed = network_speed()
            if speed < threshold:
                print("Reconnecting network due to low speeds ({} < {})".format(speed, threshold))
                reconnect(args.interface)
    except Exception as e:
        traceback.print_exc()
