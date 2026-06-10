import socket
import requests
from ip2geotools.databases.noncommercial import DbIpCity
from geopy.distance import distance


def get_details(ip):
    res = DbIpCity.get(ip, api_key="free")
    country = res.country
    city = res.city

    if city is not None:
        return city, country
    
    else:
        city = "none"
        country = "none"
        return city, country