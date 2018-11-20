from socket import *
import time
import re
import sys
import os

tcpSerPort = 80
server_ip = '127.0.0.1'
if len(sys.argv) != 3:
	print(sys.argv)
	print("Usage: python3 this.py server_ip port_num")
else:
	server_ip = sys.argv[1]
	tcpSerPort = int(sys.argv[2])
print("Will use the deafule setting with port number %d and server_ip is %s" %(tcpSerPort, server_ip))

BUFFER_SIZE = 4096
FILE_FOLDER = "File/"
THIS_SERVER_IP_PORT_NUM = '127.0.0.1:%d' % tcpSerPort

# Using regular expression to parse certain fields from the request and response
# print(precompile_str)
httpres = re.compile(r'HTTP\/[1-9]\.[0-9] (?P<RESCODE>[0-9][0-9][0-9])[.|\s|\S]*Date\:\s(?P<DATE>[.|\s|\S]*GMT)\s[.|\s|\S]*')
http_request_rule_for_normal_GET = re.compile(r'[.|\s|\S]*GET \/(?P<GET>[a-z|A-Z|\.]*)[.|\s|\S]*')


with socket(AF_INET, SOCK_STREAM) as tcpSerSock:
	# Prepare a server socket
	tcpSerSock.bind((server_ip, tcpSerPort))
	# Listen to at most 5 connection at a time
	tcpSerSock.listen(5)

	while True:
		print("Ready to serve.")
		tcpCLISock, addr = tcpSerSock.accept()
		print("Reveived a connection from ", addr)
		message = tcpCLISock.recv(BUFFER_SIZE)
		message = message.decode()
		# print(message)

		requested_item = None
		hostn = None
		
		tmp_match = http_request_rule_for_normal_GET.match(message)
		if tmp_match:
			requested_item = tmp_match.group('GET')
		
		print(requested_item)
		try:
			buffer_lines = None
			with open(FILE_FOLDER+requested_item, "r") as f:
				buffer_lines = f.readlines()
			response_header = b"HTTP/1.1 200 OK\r\n"
			response_header += b"Content-Type: text/html\r\n"
			response_header += b"Content-Disposition: attachment\r\n"
			response_header += ("Content-Length: %d\r\n" % os.path.getsize(FILE_FOLDER+requested_item)).encode()
			response_header += b"\n\n"
			print(response_header)

			response_body = b""
			for line in buffer_lines:
				print(line)
				response_body += (line.encode())
			response_body += b"\n\n"
			tcpCLISock.sendall(response_header+response_body)
		except FileNotFoundError as e:
			print("No such file")
			tcpCLISock.sendall(b"HTTP/1.1 404 Not Found\n\n")

		except Exception as e:
			print(e)
			tcpCLISock.sendall(b"HTTP/1.1 404 Not Found\n\n")
		finally:
			tcpCLISock.close()


