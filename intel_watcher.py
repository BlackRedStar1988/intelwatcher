import argparse
import sys
import requests
import time
import timeit
import json

from pymysql import connect
from concurrent.futures.thread import ThreadPoolExecutor
from rich.progress import Progress

from util.ingress import IntelMap, MapTiles
from util.config import Config
from util.queries import create_queries
from util.get_cookie import mechanize_cookie, selenium_cookie

tiles_data = []

def connect_db(config):
    mydb = connect(host = config.db_host, user = config.db_user, password = config.db_password, database = config.db_name_scan, port = config.db_port, autocommit = True)
    cursor = mydb.cursor()
    queries = create_queries(config, cursor)

    return queries

def update_wp(wp_type, points):
    updated = 0
    print(f"Found {len(points)} {wp_type}s")
    for wp in points:
        portal_details = scraper.get_portal_details(wp[0])
        if portal_details is not None:
            try:
                queries.update_point(wp_type, portal_details.get("result")[portal_name], portal_details.get("result")[portal_url], wp[0])
                updated += 1
                print(f"Updated {wp_type} {portal_details.get('result')[portal_name]}")
            except Exception as e:
                print(f"Could not update {wp_type} {wp[0]}")
                print(e)
        else:
            print(f"Couldn't get Portal info for {wp_type} {wp[0]}")
            
    print(f"Updated {updated} {wp_type}s")
    print("")

def scrape_tile(tile, scraper, progress, task):
    iitc_xtile = int(tile[0])
    iitc_ytile = int(tile[1])
    iitc_tile_name  = f"15_{iitc_xtile}_{iitc_ytile}_0_8_100"

    tries = 0
    progress.update(task, advance=1)
    while tries < 3:
        try:
            t_data = scraper.get_entities([iitc_tile_name])
            """for tiled in t_data.get("result", {})["map"].values():
                if not "error" in tiled["gameEntities"]:
                    for entry in tiled["gameEntities"]:
                        if entry[2][0] == "p":"""
            tiles_data.append(t_data["result"]["map"])
            tries = 3
        except Exception as e:
            tries += 1
            print(f"Error with tile {iitc_tile_name} - Retry {tries}/3")
            print(e)

def scrape_all():
    bbox = list(config.bbox.split(';'))
    tiles = []
    for cord in bbox:
        bbox_cord = list(map(float, cord.split(',')))
        bbox_cord.append(15)
        mTiles = MapTiles(bbox_cord)
        tiles = tiles + mTiles.getTiles()
    total_tiles = len(tiles)
    print(f"Total tiles to scrape: {total_tiles}")

    portals = []
    with Progress() as progress:
        task = progress.add_task("Scraping Portals", total=total_tiles)
        with ThreadPoolExecutor(max_workers=config.workers) as executor: 
            for tile in tiles:
                executor.submit(scrape_tile, tile, scraper, progress, task)
    #print(tiles_data)
    try:
        for tile_data in tiles_data:
            for value in tile_data.values():
                for entry in value["gameEntities"]:
                    if entry[2][0] == "p":
                        p_id = entry[0]
                        p_lat = entry[2][2]/1e6
                        p_lon = entry[2][3]/1e6
                        p_name = entry[2][8]
                        p_img = entry[2][7]
                        portals.append([p_id, p_lat, p_lon, p_name, p_img])
    except Exception as e:
        print("Something went wrong while parsing Portals")
        print(e)
    print(f"Total amount of Portals: {len(portals)}")
    queries = connect_db(config)
    updated_portals = 0
    with Progress() as progress:
        task = progress.add_task("Updating DB", total=len(portals))
        for p_id, lat, lon, p_name, p_img in portals:
            updated_ts = int(time.time())
            try:
                queries.update_portal(p_id, p_name, p_img, lat, lon, updated_ts)
                updated_portals += 1
            except Exception as e:
                print(f"Failed putting Portal {p_name} ({p_id}) in your DB")
                print(e)
            progress.update(task, advance=1)

    print(f"Done. Put {updated_portals} Portals in your DB.")

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
        print(result)

if __name__ == "__main__":
    print("Initializing...")
    portal_name = 8
    portal_url = 7

    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--update", action='store_true', help="Updates all Gyms and Stops using Portal info")
    parser.add_argument("-c", "--config", default="config.ini", help="Config file to use")
    parser.add_argument("-w", "--workers", default=0, help="Workers")
    args = parser.parse_args()
    config_path = args.config

    config = Config(config_path)
    

    scraper = IntelMap(config.cookie)

    if not scraper.getCookieStatus():
        cookie_get_success = False
        if config.enable_cookie_getting:
            print("Trying to get a new one")
            while not cookie_get_success:
                try:
                    if config.cookie_getting_module == "mechanize":
                            config.cookie = mechanize_cookie(config)
                            cookie_get_success = True

                    elif config.cookie_getting_module == "selenium":
                            config.cookie = selenium_cookie(config)
                            cookie_get_success = True
                except Exception as e:
                    print("Error while trying to get a Cookie - sending a webhook, sleeping 1 hour and trying again")
                    print(e)
                    send_cookie_webhook("Got an Error while trying to get a new cookie - Please check logs. Retrying in 1 hour.")
                    time.sleep(3600)
            scraper.login(config.cookie)
        else:
            send_cookie_webhook("Your Intel Cookie probably ran out! Please get a new one or check your account.")
            sys.exit(1)
    else:
        print("Cookie works!")

    print("Got everything. Starting to scrape now.")

    if args.update:
        queries = connect_db(config)
        gyms = queries.get_empty_gyms()
        stops = queries.get_empty_stops()
        update_wp("Gym", gyms)
        update_wp("Stop", stops)
        sys.exit()

    if int(args.workers) > 0:
        config.workers = int(args.workers)

    start = timeit.default_timer()
    scrape_all()
    stop = timeit.default_timer()
    print(f"Total runtime: {round(stop - start, 1)} seconds")
