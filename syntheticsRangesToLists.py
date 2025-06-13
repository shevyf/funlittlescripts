#!/opt/homebrew/bin/python3

import argparse
import ipaddress
import json
import urllib.request
from datetime import datetime
import os

IP_RANGE_URL = 'https://s3.amazonaws.com/nr-synthetics-assets/nat-ip-dnsname/production/ip-ranges.json'
DIRECTORY = 'iplists'

def get_ip_ranges(endpoint: str):
    with urllib.request.urlopen(endpoint) as url:
        return json.load(url)

def write_to_list(rangelist):
    allips = []
    for cidr in rangelist:
        allips += [str(ip) for ip in ipaddress.IPv4Network(cidr)]
    return allips


def write_location(location, rangelist, directory, time):
    location = location.replace(", ","_").replace(" ","_")
    path = './'+directory+'/'+time+location.replace(" ","_").replace(",","_")+'.txt'
    ips = write_to_list(rangelist)
    with open(path, 'w+') as f:
        for ip in ips:
            f.write(ip + '\n')

def make_ip_list_files(directory=DIRECTORY):
    time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S_')
    try:
        os.mkdir(directory)
    except FileExistsError:
        pass
    allranges = get_ip_ranges(IP_RANGE_URL)
    for cidr in allranges:
        write_location(cidr, allranges[cidr], directory, time)

if __name__=='__main__':
    parser = argparse.ArgumentParser(
                    prog='Create text files containing all possible IP addresses for New Relic Synthetics Public Locations',
                    description='Create text files containing all possible IP addresses for New Relic Synthetics Public Locations',
                    epilog='specify a directory to put the files in')
    parser.add_argument('directory', nargs='?', type=str, default=DIRECTORY,
                    help='name of a directory to place the text files in.')

    args = parser.parse_args()
    make_ip_list_files(args.directory)
