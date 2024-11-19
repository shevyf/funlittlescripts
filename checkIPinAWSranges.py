#!/usr/bin/python3

import ipaddress
import json
import urllib.request
import sys
import argparse
import datetime
import os

IP_RANGE_URL = 'https://ip-ranges.amazonaws.com/ip-ranges.json'

# test IP addresses - two valid, two not valid, one IPv6
IP_LIST = ['34.253.29.245','151.101.194.217','16.163.220.0','172.0.0.1','2001:0db8:85a3:0000:0000:8a2e:0370:7334']

# Get IP ranges for AWS services, and return just the list of prefixes
# TODO: store locally instead of fetching every time. Can we use if-modified-since to see if file has changed?
def get_ip_ranges(endpoint: str):
    with urllib.request.urlopen(endpoint) as url:
        ranges_dict = json.load(url)
        return ranges_dict["prefixes"]

def check_ip(ipaddr: str, prefixes: dict) -> list:
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
        for prefix in prefixes:
            # all values are listed twice, once as 'AMAZON' and once as a specific service name. Only display the specific service.
            if (prefix["service"] != "AMAZON" and ip in ipaddress.ip_network(prefix["ip_prefix"])):
                output.append('*** IP ' +str(ip)+ ' FOUND in region: ' + prefix["region"] + ' service type: '+ prefix["service"] + ' ***')
    if not output:
        output.append(str(ip)+ ' not found in any prefix')
    return output

def check_ip_list(iplist: list) -> list:
    prefixes = get_ip_ranges(IP_RANGE_URL)
    results = []
    for ipaddr in iplist:
        results.extend(check_ip(ipaddr, prefixes))
    return results

def fileToList(filepath: str) -> list:
    with open(filepath) as f:
        lines = f.read().splitlines()
    return lines

def resolve_domain(domain: str) -> list:
    import socket
    results = socket.getaddrinfo(domain, None)
    ipv4_addresses = set()
    for result in results:
        family, _, _, _, sockaddr = result
        if family == socket.AF_INET:
            ipv4_addresses.add(sockaddr[0])
    return list(ipv4_addresses)

# TODO: make sort optional; output to file as CSV; accept list of domains
if __name__=='__main__':
    parser = argparse.ArgumentParser(
                    prog='Check IP in Ranges',
                    description='Checks IPv4 addresses against the ip ranges for New Relic public Locations for synthetics',
                    epilog='Use either an IP address or the test flag')
    parser.add_argument('addresses', metavar='IP', type=str, nargs='*',
                    help='A series of IP addresses to check')
    parser.add_argument('-f', '--file', help='specify filepath to get addresses from a file')
    parser.add_argument('-t', '--test', action='store_true', help='Run using a list of provided test IP addresses')
    parser.add_argument('-d', '--domain', help='specify a domain name to resolve and check ipv4 address')

    args = parser.parse_args()

    if not (args.addresses or args.test or args.file or args.domain):
        parser.print_help()
    else:
        print('Checking...')
        final_results = []

        if args.test:
            final_results.extend(check_ip_list(IP_LIST))

        if args.file:
            ips_from_file = fileToList(args.file)
            final_results.extend(check_ip_list(ips_from_file))

        if args.addresses:
            final_results.extend(check_ip_list(args.addresses))

        if args.domain:
            resolved_ips = resolve_domain(args.domain)
            final_results.extend(check_ip_list(resolved_ips))

        final_results.sort()
        print('\n'.join(final_results))
        print('Done')
