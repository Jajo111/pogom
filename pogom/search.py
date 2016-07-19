#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import json
import struct
import logging
import requests
import time


from pgoapi import PGoApi
from pgoapi.utilities import f2i, h2f, get_cellid, encode, get_pos_by_name

log = logging.getLogger(__name__)

TIMESTAMP = "\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000"
REQ_SLEEP = 1


def send_map_request(api, position):
    api.set_position( *position )
    api.get_map_objects(latitude=f2i(position[0]), 
                        longitude=f2i(position[1]), 
                        since_timestamp_ms=TIMESTAMP, 
                        cell_id=get_cellid(position[0], position[1]))
    return api.call()
    
def parse_map(map_dict):
    try:
        for cell in map_dict['responses']['GET_MAP_OBJECTS']['map_cells']:
            if not 'wild_pokemons' in cell:
                continue
            
            for pokemon in cell['wild_pokemons']:
                log.info( json.dumps(pokemon, indent=2) )
    except Exception as e:
        log.warn("Error while parsing dictionary: {}".format(e))

def generate_location_steps(initial_location, num_steps):
    pos, x, y, dx, dy = 1, 0, 0, 0, -1

    while -num_steps / 2 < x <= num_steps / 2 and -num_steps / 2 < y <= num_steps / 2:
        yield (x * 0.0025 + initial_location[0], y * 0.0025 + initial_location[1], 0)
            
        if x == y or x < 0 and x == -y or x > 0 and x == 1 - y:
            dx, dy = -dy, dx

        x, y = x + dx, y + dy


def search(args):
    position = get_pos_by_name(args.location)
    log.info('Parsed location is: {:.4f}/{:.4f}/{:.4f} (lat/lng/alt)'.
             format(*position))

    num_steps = args.step_limit
    
    api = PGoApi()
    api.set_position( *position )
    
    log.info("Attempting login.")

    while not api.login(args.auth_service, args.username, args.password):
        log.info("Login failed. Trying again.")
        time.sleep(REQ_SLEEP)
            
    log.info("Login successful.")
   
    i = 1
    for step_location in generate_location_steps(position, num_steps):
        log.info("Scanning step {:d} of {:d}.".format(i, num_steps**2))
        
        response_dict = send_map_request(api, step_location)
        while not response_dict:
            log.info("Map Download failed. Trying again.")
            response_dict = send_map_request(api, step_location)
            time.sleep(REQ_SLEEP)
            
        parse_map(response_dict)
        
        log.info("Completed {:5.2f}% of scan.".format(float(i) / num_steps**2 * 100))
        i += 1
        time.sleep(REQ_SLEEP)
