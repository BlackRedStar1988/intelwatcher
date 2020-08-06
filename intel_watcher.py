import argparse
import sys
import requests
import time
import timeit
import json
import logging
import coloredlogs

from concurrent.futures.thread import ThreadPoolExecutor
from rich.progress import Progress
from rich import print

from util.ingress import IntelMap, MapTiles
from util.config import Config
from util.queries import Queries
from util.get_cookie import mechanize_cookie, selenium_cookie

def maybe_byte(name):
    try:
        return name.decode()
    except:
        return name

def update_wp(wp_type, points):
    updated = 0
    log.info(f"Found {len(points)} {wp_type}s")
    for wp in points:
        portal_details = scraper.get_portal_details(wp[0])
        if portal_details is not None:
            try:
                pname = maybe_byte(portal_details.get("result")[portal_name])
                queries.update_point(wp_type, pname, maybe_byte(portal_details.get("result")[portal_url]), wp[0])
                updated += 1
                log.info(f"Updated {wp_type} {pname}")
            except Exception as e:
                log.error(f"Could not update {wp_type} {wp[0]}")
                log.exception(e)
        else:
            log.info(f"Couldn't get Portal info for {wp_type} {wp[0]}")
            
    log.info(f"Updated {updated} {wp_type}s")
    log.info("")

def scrape_tile(tile, scraper, progress, task, tiles_data):
    iitc_xtile = int(tile[0])
    iitc_ytile = int(tile[1])
    iitc_tile_name  = f"15_{iitc_xtile}_{iitc_ytile}_0_8_100"

    tries = 0
    progress.update(task, advance=1)
    while tries < 3:
        try:
            t_data = scraper.get_entities([iitc_tile_name])
            tiles_data.append(t_data["result"]["map"])
            tries = 3
        except Exception as e:
            tries += 1
            print(f"[#676b70]Tile {iitc_tile_name} didn't load correctly - Retry {tries}/3 ({e})")

def scrape_all():
    bbox = list(config.bbox.split(';'))
    tiles_list = []
    for cord in bbox:
        bbox_cord = list(map(float, cord.split(',')))
        bbox_cord.append(15)
        mTiles = MapTiles(bbox_cord)
        tiles_list.append(mTiles.getTiles())

    for index, tiles in enumerate(tiles_list):
        area = index + 1
        total_tiles = len(tiles)
        portals = []
        tiles_data = []

        log.info("")
        log.warning(f"Getting area #{area}")
        log.info(f"Total tiles to scrape: {total_tiles}")
        with Progress() as progress:
            task = progress.add_task("Scraping Portals", total=total_tiles)
            with ThreadPoolExecutor(max_workers=config.workers) as executor: 
                for tile in tiles:
                    executor.submit(scrape_tile, tile, scraper, progress, task, tiles_data)

        try:
            for tile_data in tiles_data:
                for value in tile_data.values():
                    for entry in value["gameEntities"]:
                        if entry[2][0] == "p":
                            p_id = entry[0]
                            p_lat = entry[2][2]/1e6
                            p_lon = entry[2][3]/1e6
                            p_name = maybe_byte(entry[2][8])
                            p_img = maybe_byte(entry[2][7])
                            portals.append([p_id, p_lat, p_lon, p_name, p_img])
        except Exception as e:
            log.info("Something went wrong while parsing Portals")
            log.exception(e)

        log.info(f"Found {len(portals)} Portals")
        queries = Queries(config)
        updated_portals = 0
        with Progress() as progress:
            task = progress.add_task("Updating DB", total=len(portals))
            for p_id, lat, lon, p_name, p_img in portals:
                updated_ts = int(time.time())
                try:
                    queries.update_portal(p_id, p_name, p_img, lat, lon, updated_ts)
                    updated_portals += 1
                except Exception as e:
                    log.error(f"Failed putting Portal {p_name} ({p_id}) in your DB")
                    log.exception(e)
                progress.update(task, advance=1)

        queries.close()
        if updated_portals == len(portals):
            log.success("Put all Portals in your DB.")
        else:
            log.critical(f"Only put {updated_portals} in your DB")
        time.sleep(config.areasleep)

def send_cookie_webhook(text):
    if config.cookie_wh:
        data = {
            "username": "Cookie Alarm",
            "avatar_url": "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/apple/237/cookie_1f36a.png",
            "content": config.cookie_text,
            "embeds": [{
                "description": f":cookie: {text}",
                "color": 16073282
            }]
        }
        result = requests.post(config.wh_url, json=data)
        log.info(f"Webhook response: {result.status_code}")

if __name__ == "__main__":
    portal_name = 8
    portal_url = 7

    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--update", action='store_true', help="Updates all Gyms and Stops using Portal info")
    parser.add_argument("-c", "--config", default="config.ini", help="Config file to use")
    parser.add_argument("-w", "--workers", default=0, help="Workers")
    parser.add_argument("-d", "--debug", action='store_true', help="Run the script in debug mode")
    args = parser.parse_args()

    # LOG STUFF
    success_level = 25
    if args.debug:
        log_level = "DEBUG"
    else:
        log_level = "INFO"

    log = logging.getLogger(__name__)
    logging.addLevelName(success_level, "SUCCESS")
    def success(self, message, *args, **kws):
        self._log(success_level, message, args, **kws) 
    logging.Logger.success = success
    coloredlogs.DEFAULT_LEVEL_STYLES["debug"] = {"color": "blue"}
    coloredlogs.install(level=log_level, logger=log, fmt="%(message)s")

    log.info("Initializing...")

    config_path = args.config

    config = Config(config_path)

    scraper = IntelMap(config.cookie)

    if not scraper.getCookieStatus():
        log.error("Oops! Looks like you have a problem with your cookie.")
        cookie_get_success = False
        if config.enable_cookie_getting:
            log.info("Trying to get a new one")
            while not cookie_get_success:
                try:
                    if config.cookie_getting_module == "mechanize":
                            config.cookie = mechanize_cookie(config, log)
                            cookie_get_success = True

                    elif config.cookie_getting_module == "selenium":
                            config.cookie = selenium_cookie(config, log)
                            cookie_get_success = True
                except Exception as e:
                    log.error("Error while trying to get a Cookie - sending a webhook, sleeping 1 hour and trying again")
                    log.exception(e)
                    send_cookie_webhook("Got an error while trying to get a new cookie - Please check logs. Retrying in 1 hour.")
                    time.sleep(3600)
            scraper.login(config.cookie)
        else:
            send_cookie_webhook("Your Intel Cookie probably ran out! Please get a new one or check your account.")
            sys.exit(1)
    else:
        log.success("Cookie works!")

    log.success("Got everything. Starting to scrape now.")

    if args.update:
        queries = Queries(config)
        gyms = queries.get_empty_gyms()
        stops = queries.get_empty_stops()
        update_wp("Gym", gyms)
        update_wp("Stop", stops)
        queries.close()
        sys.exit()

    if int(args.workers) > 0:
        config.workers = int(args.workers)

    start = timeit.default_timer()
    scrape_all()
    stop = timeit.default_timer()
    log.success(f"Total runtime: {round(stop - start, 1)} seconds")
