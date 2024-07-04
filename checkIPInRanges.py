#!/usr/bin/python3

import ipaddress
import json
import urllib.request
import sys
import argparse
import datetime
import os


IP_RANGE_URL = 'https://s3.amazonaws.com/nr-synthetics-assets/nat-ip-dnsname/production/ip-ranges.json'
HORDE_US = ['162.247.240.0/22','152.38.128.0/19']
HORDE_EU = ['185.221.84.0/22','212.32.0.0/20']

# test IP addresses - two valid, two not valid, one IPv6
IP_LIST = ['45.202.178.0','3.38.229.128','16.163.220.0','172.0.0.1','2001:0db8:85a3:0000:0000:8a2e:0370:7334']

# Get public location IP ranges for New Relic Synthetics
# TODO: find a way to update Horde IPs automatically instead of hard coding
def get_ip_ranges(endpoint: str):
    with urllib.request.urlopen(endpoint) as url:
        ranges_dict = json.load(url)
        ranges_dict["Horde US"] = HORDE_US
        ranges_dict["Horde EU"] = HORDE_EU
        return ranges_dict


def check_ip(ipaddr: str, ranges: dict):
    output = []
    try:
        ip = ipaddress.ip_address(ipaddr)
    except ValueError:
        output.append('ERROR: '+ipaddr+' is not a valid IP address')
        return output
    if ip.version == 6:
        output.append('ERROR: '+ipaddr+' IPv6 addresses are not valid')
        return output
    if not output:
        for location in ranges:
            found = 0
            for cidr in ranges[location]:
                if ip in ipaddress.ip_network(cidr):
                    found += 1
            if found:
                output.append('*** IP ' +str(ip)+ ' FOUND in location: ' + location + ' ***')
    if not output:
        output.append(str(ip)+ ' not found in any location')
    return output
    # if found_in:
    #     print('*** IP ' +str(ip)+ ' FOUND in locations: ' + ', '.join(found_in) + ' ***')
    # else:
    #     print('IP ' +str(ip)+ ' not found in any location')


def check_ip_list(iplist: list):
    ranges = get_ip_ranges(IP_RANGE_URL)
    results = []
    for ipaddr in iplist:
        results.extend(check_ip(ipaddr, ranges))
    return results


if __name__=='__main__':
    parser = argparse.ArgumentParser(
                    prog='Check IP in Ranges',
                    description='Checks IPv4 addresses against the ip ranges for New Relic public Locations for synthetics',
                    epilog='Use either an IP address or the test flag')
    parser.add_argument('addresses', metavar='IP', type=str, nargs='*',
                    help='A series of IP addresses to check')
    parser.add_argument('-t', '--test', action='store_true', help='Run using a list of provided test IP addresses')

    args = parser.parse_args()

    if not (args.addresses or args.test):
        parser.print_help()
    else:
        print('Checking...')
        final_results = []
        if args.test:
            final_results.extend(check_ip_list(IP_LIST))
        final_results.extend(check_ip_list(args.addresses))
        final_results.sort()
        print('\n'.join(final_results))
        print('Done')
