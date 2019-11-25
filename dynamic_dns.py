#!/usr/bin/env python3.6

import json,ipaddress,boto3,sys
from datetime import datetime 
from subprocess import Popen, PIPE

'''
Dynamic DNS
===========

python 3 script to check public dns, local machine's public ip, and update 
route 53 if there is a difference between the two. 
'''


def aws_file_handler(batch_file, read=True, ipv4_address=""):
    # Parse value from last written value
    with open(batch_file, "r") as file:
        aws_batch_file = json.load(file)

    # Document values from the file to see what
    # the last value that was written to route 53
    recorded_ip = aws_batch_file["Changes"][0]["ResourceRecordSet"]["ResourceRecords"][0]["Value"]
    dns_record = aws_batch_file["Changes"][0]["ResourceRecordSet"]["Name"]
    
    if read == True:    
        return (recorded_ip, dns_record)
    else:
        # update Value with new ip address
        aws_batch_file["Changes"][0]["ResourceRecordSet"]["ResourceRecords"][0]["Value"] = ipv4_address

        # create timestamp object
        dateTimeObj = datetime.now()
        timestamp = dateTimeObj.strftime("Last updated: %d-%b-%Y (%H:%M:%S.%f)")
        # write timestamp
        aws_batch_file["Comment"] = timestamp
        # generate new json file
        with open(batch_file, "w") as file:
            json.dump(aws_batch_file, file, indent=4)

        return aws_batch_file


# Discover advertised value from route 53
def advertised_ip(dns_record):
    route_53 = Popen(f"dig +short {dns_record} @1.1.1.1", shell=True, stdout=PIPE)
    route_53 = route_53.communicate()[0]

    # register the returned value
    return ipaddress.ip_address(str(route_53)[2:-3])

# Find out the current dynamic ip is of the local machine
def verify_local_machine():    
    curl_ip = Popen("curl -sk ifconfig.co", shell=True, stdout=PIPE)
    curl_ip = curl_ip.communicate()[0]

    # register current public ip address
    return ipaddress.ip_address(str(curl_ip)[2:-3])


def update_route53(batch_file,zoneid):
    session = boto3.Session(profile_name = "nullconfig")
    response = session.client("route53").change_resource_record_sets(
        HostedZoneId=zoneid,
        ChangeBatch=batch_file
    )

if __name__ == '__main__':
    zoneid = sys.argv[1]
    filename = sys.argv[2]
    
    file_out = aws_file_handler(filename)
    public_ip = advertised_ip(file_out[1])
    local_ip = verify_local_machine()

    if public_ip != local_ip:
        output_file = aws_file_handler(filename, False, str(local_ip))
        update_route53(output_file, zoneid)
    else:
        print(f"Local IP {local_ip} same as advertised IP in Route 53")


