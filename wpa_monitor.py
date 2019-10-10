#!/usr/bin/python3

import time
from argparse import ArgumentParser
import subprocess
import sys
import traceback
import speedtest
import logging
from systemd import journal
from pythonping import ping
from math import inf
from threading import Thread, Lock


def network_latency(address, latency_threshold=3):
    """
    Returns average ping to an address over 5 pings in milliseconds.
    """
    try:
        responses = ping(address, timeout=latency_threshold, count=5, size=56)
        return responses.rtt_avg_ms
    except OSError:
        # unreachable, so infinite latency
        return inf


def network_speed():
    """
    Returns the speedtest result in Mbits.
    """
    try:
        s = speedtest.Speedtest()
        s.get_best_server()
        speed = s.download()
        return speed / 1000000  # Mbits conversion
    except speedtest.ConfigRetrievalError:
        return 0.0


def reconnect(interface):
    return subprocess.check_output(["systemctl", "restart", "wpa_supplicant@{}".format(interface)])


if __name__ == "__main__":
    parser = ArgumentParser(description="Monitors wpa network connection and reconnects on high latency or slow speeds")
    parser.add_argument("interface")
    parser.add_argument("ping_address", type=str,
                            help="Set the ping address")
    parser.add_argument("ping_interval", type=int,
                            help="Set how often the ping will run (in seconds) (will not run concurrently with speedtest on overlapping intervals), set -1 to disable")
    parser.add_argument("ping_threshold", type=float,
                            help="Set the highest mean latency before a reconnect is triggered (in ms)")
    parser.add_argument("speed_tests_per_ping_test", type=int,
                            help="Set after how many ping tests a speed test will run (will not run concurrently with ping on overlapping intervals), set -1 to disable. If ping tests are disabled, this will run in place of a ping test after the set interval.")
    parser.add_argument("speed_threshold", type=float,
                            help="Set the lowest speed before a reconnect is triggered (in Mbits)")

    args = parser.parse_args()

    logger = logging.getLogger('wpa_monitor_journal')
    logger.addHandler(journal.JournalHandler())
    logger.setLevel(logging.INFO)
    logger.info("Monitoring connection on {}, pinging {} per {} seconds, speedtesting after {} intervals. Network will reset if latency is above {} ms or speed is below {} Mbits/s".format(
        args.interface, args.ping_address, args.ping_interval,
        args.speed_tests_per_ping_test, args.ping_threshold, args.speed_threshold))

    lock = Lock()

    def run_speedtest():
        try:
            with lock:
                logger.info("Speedtest interval passed, testing...")
                speed = network_speed()
                logger.info("Network speed reported as {} Mbits/s".format(speed))
                if speed < args.speed_threshold:
                    logger.info("Reconnecting network due to low speeds ({} < {})".format(speed, args.speed_threshold))
                    cmd = reconnect(args.interface)
                    logger.info("Reconnection output: {}".format(cmd))
        except TimeoutError:
            logger.warning("Speed test tried to run but was blocked.")
        except Exception as e:
            logger.error(traceback.format_exc())

    def run_ping():
        try:
            with lock:
                logger.info("Ping interval passed, testing...")
                latency = network_latency(args.ping_address, args.ping_threshold * 2)
                logger.info("Network latency reported as {} ms".format(latency))
                if latency < args.ping_threshold:
                    logger.info("Reconnecting network due to high latency ({} > {})".format(latency, args.ping_threshold))
                    cmd = reconnect(args.interface)
                    logger.info("Reconnection output: {}".format(cmd))
        except TimeoutError:
            logger.warning("Ping test tried to run but was blocked.")
        except Exception as e:
            logger.error(traceback.format_exc())

    try:
        i = 0
        j = args.speed_tests_per_ping_test

        while True:
            time.sleep(args.ping_interval)

            if (i % j) == j:
                target = run_speedtest
            else:
                target = run_ping

            i += 1
            t = Thread(target=target, daemon=True)
            t.start()
    except Exception as e:
        logger.error(traceback.format_exc())
