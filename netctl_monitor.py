#!/usr/bin/python3

from pythonping import ping
import time
from argparse import ArgumentParser
import subprocess
import sys
import traceback


def is_connected(address):
    try:
        responses = ping(address, timeout=10, count=2, size=56)._responses

        return max([response.success for response in responses])
    except OSError:
        return False


def try_connect(profile):
    subprocess.run(["netctl", "restart", profile])

if __name__ == "__main__":
    parser = ArgumentParser(description="Tries to reconnect to a netctl profile if pings fail")
    parser.add_argument("address")
    parser.add_argument("profile")

    args = parser.parse_args()

    try:
        while True:
            time.sleep(30)
            if not is_connected(args.address):
                try_connect(args.profile)
    except Exception as e:
        traceback.print_exc()
