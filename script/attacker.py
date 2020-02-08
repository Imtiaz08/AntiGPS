# -*- coding:utf-8 -*-
###
# @Author: Chris
# Created Date: 2020-01-02 21:16:28
# -----
# Last Modified: 2020-02-07 19:03:07
# Modified By: Chris
# -----
# Copyright (c) 2020
###
import os
import copy
import json
import random

import pandas as pd
from tqdm import tqdm
from loguru import logger

from script.utility import Utility


class Attacker:
    def __init__(self, datafile):
        self.datafile = datafile
        self.__loaddata()

    def __loaddata(self):
        self.dataset = {}
        with open(self.datafile, "r") as fin:
            for line in tqdm(fin.readlines()):
                data = json.loads(line)
                self.dataset[data["id"]] = data

    def random_same(self, num):
        return random.sample(list(self.dataset.values()), num)

    def random(self, num):
        pano_attack = random.sample(list(self.dataset.values()), num)
        pano_attack_random = []
        for pano in pano_attack:
            gps_correct = (pano["lat"], pano["lng"])
            gps_attack = Utility.generateGPS_random(1)[0]
            while gps_attack == gps_correct:
                gps_attack = Utility.generateGPS_random(1)[0]
            pano["lat_attack"] = gps_attack[0]
            pano["lng_attack"] = gps_attack[1]
            pano_attack_random.append(pano)
        return pano_attack_random

    def nearby(self, num):
        pass

    def driving(self, num_route, num_point, attack=True):
        logger.info(f"Generating {num_route} routes with {num_point} points")
        pano_init = random.sample(list(self.dataset.values()), num_route)
        pano_attack_driving = []
        count_miss = 0
        for pano in pano_init:
            for _ in range(5):
                route = self.generate_route(pano, num_point, attack=attack)
                if route:
                    break
            if len(route) < num_point:
                count_miss += 1
                logger.warning(f"{pano['id']} can not find a route with {num_point} points.")
            else:
                pano_attack_driving.append(route)
        if count_miss:
            pano_attack_driving.extend(self.driving(count_miss, num_point))
        return pano_attack_driving

    def generate_route(
        self, pano_init, num_point, route=[], attack=True,
    ):
        num_exist = len(route)
        pano = pano_init
        for idx in range(num_exist, num_exist + num_point):
            if not route:
                pano_nxt_id = pano["neighbor"][0]
            else:
                if len(pano["neighbor"]) == 1:
                    return route
                pano_nxt_id = random.choice(pano["neighbor"])
                while pano_nxt_id == route[idx - 1]["id"]:
                    pano_nxt_id = random.choice(pano["neighbor"])

            if attack:
                ## fraud GPS
                gps_correct = (pano["lat"], pano["lng"])
                gps_attack = Utility.generateGPS_random(1)[0]
                while gps_attack == gps_correct:
                    gps_attack = Utility.generateGPS_random(1)[0]
                pano["lat_attack"] = gps_attack[0]
                pano["lng_attack"] = gps_attack[1]
            route.append(pano)
            pano = self.dataset[pano_nxt_id]
        return route

    def read_route(self, filename):
        routesDF = pd.read_csv(filename, index_col=["route_id"])
        routes_num = int(routesDF.index[-1] + 1)
        routes = []
        for route_id in range(routes_num):
            route = []
            routeDF = routesDF.loc[route_id]
            for step in range(len(routeDF)):
                pano_id = routeDF.iloc[step]["pano_id"]
                pano = self.dataset[pano_id]
                pano["lat_attack"] = routeDF.iloc[step]["lats_attack"]
                pano["lng_attack"] = routeDF.iloc[step]["lngs_attack"]
                route.append(pano)
            routes.append(route)
        return routes


def test_generate_route():
    test = Attacker("../results/pano_text.json")
    routes = test.driving(300, 50)
    routes_dict = {"route_id": [], "pano_id": []}
    coords = {"lats": [], "lngs": [], "lats_attack": [], "lngs_attack": []}
    for idx, route in enumerate(routes):
        for pano in route:
            routes_dict["route_id"].append(idx)
            routes_dict["pano_id"].append(pano["id"])
            coords["lats"].append(pano["lat"])
            coords["lngs"].append(pano["lng"])
            coords["lats_attack"].append(pano["lat_attack"])
            coords["lngs_attack"].append(pano["lng_attack"])
    Utility.visualize_map(coords)
    routesDF = pd.DataFrame({**routes_dict, **coords})
    filename = "/home/bourne/Workstation/AntiGPS/results/routes_generate.csv"
    header = not os.path.exists(filename)
    routesDF.to_csv(filename, index=False, header=header, mode="a")


def test_generate_route_longer():
    test = Attacker("../results/pano_text.json")
    filename = "/home/bourne/Workstation/AntiGPS/results/routes_generate.csv"
    routesDF = pd.read_csv(filename, index_col=["route_id"])
    routes_num = int(routesDF.index[-1] + 1)
    routes_dict = {"route_id": [], "pano_id": []}
    routes_dist = 0
    coords = {"lats": [], "lngs": [], "lats_attack": [], "lngs_attack": []}
    for route_id in range(routes_num):
        route = []
        routeDF = routesDF.loc[route_id]
        for step in range(len(routeDF)):
            pano_id = routeDF.iloc[step]["pano_id"]
            pano = test.dataset[pano_id]
            pano["lat_attack"] = routeDF.iloc[step]["lats_attack"]
            pano["lng_attack"] = routeDF.iloc[step]["lngs_attack"]
            route.append(pano)

        route_default = copy.deepcopy(route)
        for _ in range(5):
            route = test.generate_route(route[-1], 49, route)
            if len(route) < 99:
                route = test.generate_route(route[0], 99 - len(route), route[::-1])
            if len(route) < 99:
                route = route_default
            else:
                break
        if len(route) < 99:
            logger.warning(f"route {route_id} cannot be produced")
            continue
        for pano in route:
            routes_dict["route_id"].append(route_id)
            routes_dict["pano_id"].append(pano["id"])
            coords["lats"].append(pano["lat"])
            coords["lngs"].append(pano["lng"])
            coords["lats_attack"].append(pano["lat_attack"])
            coords["lngs_attack"].append(pano["lng_attack"])

        routes_dist += Utility.distance_route(route)
    logger.info("Average route length is {}".format(routes_dist / routes_num))
    Utility.visualize_map(coords)
    routesDF = pd.DataFrame({**routes_dict, **coords})
    filename = "/home/bourne/Workstation/AntiGPS/results/routes_generate_longer.csv"
    routesDF.to_csv(filename, index=False, header=True, mode="w")


if __name__ == "__main__":
    # test = Attacker("../results/pano_text.json")
    # test_pano_attack_random = test.random(10)
    # print(test_pano_attack_random)

    test_generate_route_longer()
