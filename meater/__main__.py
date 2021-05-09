import time
import argparse
import asyncio
import aiohttp
import logging
from . import MeaterApi

_LOGGER = logging.getLogger(__file__)


def parse_arguments():
    """Parse arguments when running API from CLI."""
    parser = argparse.ArgumentParser(description="Read data from Meater API")
    parser.add_argument("-u", "--username", help="Username", required=True)
    parser.add_argument("-p", "--password", help="Password", required=True)
    parser.add_argument(
        "-pr",
        "--probe",
        help="Query specific probe with ID or index",
        action="store_true",
    )
    parser.add_argument(
        "-l",
        "--loop",
        help="Loop API query with given interval in seconds",
        nargs="?",
        const=15,
        type=int,
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="Print debugging statements",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Be verbose",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )
    args = parser.parse_args()
    return args


async def probe_info(meater, time=0):
    """Log probe information when running API from CLI."""
    devices = await meater.get_devices()
    if len(devices) > 0:
        for device in devices:
            # print(f"{device}")
            print(
                f"{time}\t\t{device.index}\t{device.internal_temperature}\t{device.ambient_temperature}\t{device.time_updated}\t{device.cook}"
            )
    else:
        print(f"All devices are offline.")


async def async_main(args):
    """Main async method when running API from CLI."""
    session = aiohttp.ClientSession()
    meater = MeaterApi(session)
    tableheader = "TIME\t\tPROBE\tTEMP\tAMBIENT\tUPDATED\t\t\tCOOK"
    try:
        auth = await meater.authenticate(args.username, args.password)
        if auth:
            print("Logged in.")
            if args.loop:
                print(f"Looping with interval: {args.loop}")
                print(tableheader)
                time = 0
                while True:
                    await probe_info(meater, time)
                    await asyncio.sleep(args.loop)
                    time += args.loop
            else:
                print(tableheader)
                await probe_info(meater)
    except KeyboardInterrupt:
        _LOGGER.debug("User interrupt.")

    await session.close()


def main(args):
    """Wrapper method for async when running API from CLI."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_main(args))
        loop.run_until_complete(asyncio.sleep(1))
        loop.close()
    except RuntimeError:
        pass


if __name__ == "__main__":
    """Main call if API used from CLI."""
    s = time.perf_counter()
    args = parse_arguments()
    logging.basicConfig(
        format="%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s",
        level=args.loglevel,
    )

    if args.username is None or args.password is None:
        _LOGGER.error("Username and password are required.")
    else:
        try:
            main(args)
        except KeyboardInterrupt:
            _LOGGER.debug("User interrupt.")

    elapsed = time.perf_counter() - s
    print(f"{__file__} executed in {elapsed:0.2f} seconds.")
