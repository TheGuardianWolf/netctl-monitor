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
        speed = s.download()
        return speed
    except speedtest.ConfigRetrievalError:
        return 0.0


def reconnect(interface):
    return subprocess.check_output(["systemctl", "restart", "wpa_supplicant@{}".format(interface)])

if __name__ == "__main__":
    parser = ArgumentParser(description="Monitors wpa network connection and reconnects on fail or slow speeds")
    parser.add_argument("interface")
    parser.add_argument("interval")
    parser.add_argument("threshold")

    args = parser.parse_args()

    try:
        interface = args.interface
        interval = int(args.interval)
        threshold = int(args.threshold)
        while True:
            time.sleep(interval)
            speed = network_speed()
            print(threshold)
            print(speed)
            if speed < threshold:
                print("Reconnecting network due to low speeds ({} < {})".format(speed, threshold))
                print(reconnect(interface))
    except Exception as e:
        traceback.print_exc()
