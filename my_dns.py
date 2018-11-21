from socket import *
from functools import reduce
import time
import glob, json # handle zone files
import sys

ZONE_FILE_FOLDER = "ZONES"
BUFFER_SIZE = 1024
dnsSerIP = "0.0.0.0"
dnsSerPort = 53
if len(sys.argv) != 3:
	# print(sys.argv)
	print("Usage: python3 this.py ip_address port_num")
else:
	dnsSerIP = sys.argv[1]
	dnsSerPort = int(sys.argv[2])
print("Will use the deafule setting with port number %d and ip address %s" % (dnsSerPort, dnsSerIP))

JSON_ZONE = {}
zone_files = glob.glob(ZONE_FILE_FOLDER+'/*.json')
for zone in zone_files:
	with open(zone) as f:
		data = json.load(f)
		name = data["$origin"].upper()
		JSON_ZONE[name] = data

# print(JSON_ZONE)
def get_zone(zone):
	global JSON_ZONE
	akey = zone.upper()+"."
	if akey in JSON_ZONE:
		return JSON_ZONE[akey]
	return None
print(get_zone("MYDOMAIN.COM"))

def binstr2byte(binstr):
	return int(binstr, 2).to_bytes(1, byteorder='big')
def get_flags(flags_byte):
	rflags = ''

	byte1 = flags_byte[:1]
	QR = '1'

	# Get opcode
	Opcode = ''
	for bit in range(1,5):
		Opcode += str((ord(byte1))&(1<<bit))

	# flags
	AA = '1' # Authoritative Answer
	TC = '0' # No TrunCation
	RD = '0' # No recursion
	RA = '0' # No recursion
	Z = '000'
	RCODE = '0000' # No error condition

	rflags = QR + Opcode + AA + TC + RD
	rflags2 = RA + Z + RCODE
	return binstr2byte(rflags) + binstr2byte(rflags2)
def get_domain(query): 
	# e.g. return : (['google'], 'com', b'\x00\x01') 0001 means typa a
	# bytes -> ([domain name list], label, question_type_byte)
	expected_len = query[0] # "google" 6
	accumulated_str = ''

	label = "DefaultLabel"
	domain_parts = ([], label)
	name_parts = []
	counter = 0
	type_pos_counter = 1
	for byte in query[1:]:
		type_pos_counter += 1
		# Every query ends with 0
		if byte == 0:
			if accumulated_str != '':
				domain_parts = (name_parts, accumulated_str, query[type_pos_counter:type_pos_counter+2])
			break
		if counter == expected_len:
			counter = 0
			expected_len = byte
			name_parts.append(accumulated_str)
			accumulated_str = ''
		else:
			accumulated_str += chr(byte)
			counter += 1
		
	return domain_parts

def domain_parts2records(domain_parts):
	names, label, question_type = domain_parts
	if question_type == b"\x00\x01": # a record
		# print("It's an A record request.")
		domain_label = reduce(lambda x, y: x+'.'+y, names) + '.' + label
		domain_label = domain_label
		print("Looking up", domain_label)
		possible_rslt = get_zone(domain_label)
		if possible_rslt:
			return possible_rslt['a']
	# else: aaaa record handling is not implemented
	# 	pass
	return None

# Question field
def build_question(domain_parts):
    #                                 1  1  1  1  1  1
    #   0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
    # |                                               |
    # /                     QNAME                     /
    # /                                               /
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
    # |                     QTYPE                     |
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
    # |                     QCLASS                    |
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
	rslt = b''
	domain_name_list, domain_label, question_type = domain_parts
	for name in domain_name_list:
		rslt += bytes([len(name)])
		for ch in name:
			rslt += ord(ch).to_bytes(1, byteorder='big')
	rslt += bytes([len(domain_label)])
	for ch in domain_label:
		rslt += ord(ch).to_bytes(1, byteorder='big')
	rslt += (0).to_bytes(1, byteorder='big')
	# QNAME is done

	# QTYPE + QCLASS
	rslt += question_type
	rslt += question_type

	return rslt

def build_header(data, domain_parts, possible_ans):
	# The header contains the following fields:
	#                                     1  1  1  1  1  1
	#       0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
	#     +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
	#     |                      ID                       | TID
	#     +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
	#     |QR|   Opcode  |AA|TC|RD|RA|   Z    |   RCODE   | FLG
	#     +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
	#     |                    QDCOUNT                    | 
	#     +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
	#     |                    ANCOUNT                    |
	#     +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
	#     |                    NSCOUNT                    |
	#     +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
	#     |                    ARCOUNT                    |
	#     +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
	# First two bytes of the query is the transaction ID
	transactionID = data[:2]

	# Next two bytes are the flags
	flags = data[2:4]
	FLG = get_flags(flags)
	# print(FLG)

	# Question type count
	QDCOUNT = b'\x00\x01'

	# Answer Count, parse the query first
	ANCOUNT = (0).to_bytes(2, byteorder='big')
	if possible_ans:
		# print(possible_ans)
		ANCOUNT = len(possible_ans).to_bytes(2, byteorder='big')
	# print(ANCOUNT)

	# Nameserver count
	NSCOUNT = (0).to_bytes(2, byteorder='big')

	# Additional Count
	ARCOUNT = (0).to_bytes(2, byteorder='big')
	
	return transactionID+FLG+QDCOUNT+ANCOUNT+NSCOUNT+ARCOUNT

# Record to bytes
def rec2bytes(recttl, recval, recclass = b'\x00\x01', rectype = b'\x00\x01'):
    rslt = b"\xc0\x0c" # Compression
    rslt += rectype
    rslt += recclass
    rslt += int(recttl).to_bytes(4, byteorder='big')

    # For ipv4, RDLength 4 Bytes
    rslt += bytes([0]) + bytes([4])

    # RDATA
    for ippart in recval.split('.'):
    	rslt += bytes([int(ippart)])
    return rslt
    

def build_answer(possible_ans):
	#                                 1  1  1  1  1  1
    #   0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
    # |                                               |
    # /                                               /
    # /                      NAME                     /
    # |                                               |
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
    # |                      TYPE                     |
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
    # |                     CLASS                     |
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
    # |                      TTL                      |
    # |                                               |
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
    # |                   RDLENGTH                    |
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--|
    # /                     RDATA                     /
    # /                                               /
    # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

    rslt = b''
    if possible_ans:
    	for rec in possible_ans:
    		rslt += rec2bytes(rec['ttl'], rec['ip'])
    		# print(rslt)
    return rslt

def build_response(data):
	# Message Format
	# +---------------------+
	# |        Header       |
	# +---------------------+
	# |       Question      | the question for the name server
	# +---------------------+
	# |        Answer       | RRs answering the question
	# +---------------------+
	# |      Authority      | RRs pointing toward an authority
	# +---------------------+
	# |      Additional     | RRs holding additional information
	# +---------------------+
	domain_parts = get_domain(data[12:])
	possible_ans = domain_parts2records(domain_parts)

	res_Header = build_header(data, domain_parts, possible_ans)
	res_Question =  build_question(domain_parts)
	res_Answer = build_answer(possible_ans)
	# print(res_Answer)
	
	return res_Header+res_Question+res_Answer

	

with socket(AF_INET, SOCK_DGRAM) as dnsSerSock:
	dnsSerSock.bind((dnsSerIP, dnsSerPort))
	while True:
		print("Ready to serve.")
		data, addr = dnsSerSock.recvfrom(BUFFER_SIZE)
		dnsSerSock.sendto(build_response(data), addr)