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


# TODO: would like to make this more efficient
# TODO: when a domain was passed, this should be included in the output.
def check_ip(ipaddr: str, prefixes: dict):
    total_aws = 0
    total_non_aws = 0
    total_errors = 0
    output = []
    try:
        ip = ipaddress.ip_address(ipaddr)
    except ValueError:
        output.append('ERROR: '+ipaddr+' is not a valid IP address')
        total_errors += 1
    if ip.version == 6:
        output.append('ERROR: '+ipaddr+' IPv6 addresses are not valid')
        total_errors += 1
    if not output:
        for prefix in prefixes:
            # all values are listed twice, once as 'AMAZON' and once as a specific service name. Only display the specific service.
            if (prefix["service"] != "AMAZON" and ip in ipaddress.ip_network(prefix["ip_prefix"])):
                total_aws += 1
                output.append('*** IP ' +str(ip)+ ' FOUND in region: ' + prefix["region"] + ' service type: '+ prefix["service"] + ' ***')
    if not output:
        output.append(str(ip)+ ' not found in any prefix')
        total_non_aws += 1
    return {"details":output, "total_aws":total_aws, "total_non_aws":total_non_aws, "total_errors":total_errors}


# Core function
def check_ip_list(iplist: list, final_results):
    prefixes = get_ip_ranges(IP_RANGE_URL)

    for ipaddr in iplist:
        result = check_ip(ipaddr, prefixes)
        final_results.add_result(result)


def fileToList(filepath: str) -> list:
    """take an input file which consists of one IP address per line, read and create a list"""
    with open(filepath) as f:
        lines = f.read().splitlines()
    return lines


# TODO: make an accompanying function to take a list of domains
def resolve_domain(domain: str) -> list:
    """Resolve a domain, and return a list of IP addresses"""
    import socket

    results = socket.getaddrinfo(domain, None)
    ipv4_addresses = set()
    for result in results:
        family, _, _, _, sockaddr = result
        if family == socket.AF_INET:
            ipv4_addresses.add(sockaddr[0])
    return list(ipv4_addresses)

# previous attempt used a global value; this consolidates the handling of counts into one class.
# TODO: move formatting of results into this class; would be a good place to handle CSV generation as well.
class FinalResult:
    details = []
    total_aws_ips = 0
    total_non_aws_ips = 0
    total_errors = 0

    def add_details(self, details: list):
        self.details.extend(details)

    def sort_details(self):
        self.details.sort()

    def add_aws(self, total_aws):
        self.total_aws_ips += total_aws

    def add_non_aws( self, total_non_aws):
        self.total_non_aws_ips += total_non_aws

    def add_errors(self, total_errors):
        self.total_errors += total_errors

    def add_result(self, result):
        self.add_details(result["details"])
        self.add_aws(result["total_aws"])
        self.add_non_aws(result["total_non_aws"])
        self.add_errors(result["total_errors"])

    def print_final_results(self, sort_details=True):
        if sort_details:
            self.sort_details()
        print('\n'.join(self.details))
        print('Total AWS IPs: ', self.total_aws_ips)
        print('Total non-AWS IPs: ', self.total_non_aws_ips)
        print('Total uncheckable IPs: ', self.total_errors)


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
        final_results = FinalResult()

        if args.test:
            check_ip_list(IP_LIST, final_results)

        if args.file:
            ips_from_file = fileToList(args.file)
            check_ip_list(ips_from_file, final_results)

        if args.addresses:
            check_ip_list(args.addresses, final_results)

        if args.domain:
            resolved_ips = resolve_domain(args.domain)
            check_ip_list(resolved_ips, final_results)

        final_results.print_final_results()

        print('Done')

