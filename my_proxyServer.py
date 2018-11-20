from socket import *
import time
import re
import sys

tcpSerPort = 80
server_ip = '127.0.0.1'
if len(sys.argv) != 3:
	print(sys.argv)
	print("Usage: python3 this.py server_ip port_num")
else:
	server_ip = sys.argv[1]
	tcpSerPort = int(sys.argv[2])
print("Will use the deafule setting with port number %d and server_ip is %s" %(tcpSerPort, server_ip))

# In reality, I should write a parser to get the following info from the original request
PROXY_UA = b"Proxy-Connection: keep-alive\r\n"
PROXY_UA += b"Upgrade-Insecure-Requests: 1\r\n"
PROXY_UA += b"User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36\r\n"
PROXY_UA += b"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\r\n"
PROXY_UA += b"DNT: 1\r\n"
PROXY_UA += b"Accept-Encoding: gzip, deflate, sdch\n\n"
BUFFER_SIZE = 4096
CACHE_FOLDER = "Cache/"
THIS_SERVER_IP_PORT_NUM = '127.0.0.1:%d' % tcpSerPort

# Using regular expression to parse certain fields from the request and response
precompile_str = r"[.|\s|\S]*GET \/(?P<GET>[a-z|A-Z|\.]*)[.|\s|\S]*Referer[.|\s|\S]*%d\/(?P<HOSTN>[a-z|A-Z|\.]*)[.|\s|\S]*" % tcpSerPort
# print(precompile_str)
httpres = re.compile(r'HTTP\/[1-9]\.[0-9] (?P<RESCODE>[0-9][0-9][0-9])[.|\s|\S]*Date\:\s(?P<DATE>[.|\s|\S]*GMT)\s[.|\s|\S]*')
http_request_rule_for_referring_GET = re.compile(precompile_str)
http_request_rule_for_normal_GET = re.compile(r'[.|\s|\S]*GET \/(?P<GET>[a-z|A-Z|\.]*)[.|\s|\S]*')

# A helper function to receive a large amount of data from a socket connection
def recvall(sock, timeout=2):
	global BUFFER_SIZE
	sock.setblocking(0)

	total_data = []
	begin = time.time()
	sill = begin + timeout
	abs_sill = sill + timeout

	while True:
		now = time.time()
		if total_data and now > sill:
			break
		elif now > abs_sill:
			break

		try:
			part = sock.recv(BUFFER_SIZE)
			if part:
				total_data.append(part)
				begin = time.time()
				sill = begin + timeout
				abs_sill = sill + timeout
			else:
				time.sleep(0.1)
		# except Exception as e:
		# 	print(e)
		except:
			# we might hit the server's request limitation
			pass
	return b''.join(total_data)

def update_requested_item(hostn, requested_item, check_header_first=False, with_date=None):
	hostn_without_www = hostn.replace("www.","",1)
	proxy_request = b""

	if requested_item == hostn:
		proxy_request += b"GET http://"+hostn.encode()+b"/\r\n"
	else:
		proxy_request += b"GET http://"+hostn.encode()+b'/'+requested_item.encode()+b"\r\n"

	proxy_request += b"Host: " + hostn.encode() + b"\r\n"
	global PROXY_UA
	proxy_request += PROXY_UA

	if check_header_first and with_date:
		proxy_request += ("If-Modified-Since: " + with_date).encode()

	# print(proxy_request)
	answer = None

	with socket(AF_INET, SOCK_STREAM) as local_socket:
		local_socket.connect((hostn_without_www, 80))
		local_socket.send(proxy_request)
		answer = recvall(local_socket)

	if answer:
		# print(answer)
		src = answer.decode('ISO-8859-1')
		# print(src)
		attemp_match = httpres.match(src)
		if attemp_match:
			if attemp_match.group("RESCODE") == "304":
				print("The requested_item in the Cache is still the latest version.")
				answer = None
		else: 
			answer = b"HTTP/1.1 200 OK\r\n" + answer
	else:
		answer = b"HTTP/1.1 404 Not Found\n\n"
	# print("******Getting answer from the original server******")	
	# print(answer)
	# print("******Response was printed******")
	return answer

def send_back_answer_to(tcpCLISock, answer, save=True):
	tcpCLISock.sendall(answer)
	if save:
		try:
			with open(CACHE_FOLDER+hostn+requested_item, "wb", BUFFER_SIZE) as attemp_save_file:
				# print("About to send a(n) %s object to the client" % type(answer))
				attemp_save_file.write(answer)
		except IOError:
			print("Make sure you have the permission to write the file")

def get_cache_date(lines):
	for line in lines:
		# print(line)
		if b"Date: " in line:
			line = line.decode('ISO-8859-1')
			return line.split("Date:")[1].split("\r\n")[0]
	return None

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
			hostn = requested_item
			tmp_match = http_request_rule_for_referring_GET.match(message)
			if tmp_match:
				hostn = tmp_match.group('HOSTN')
		
		# print(requested_item, hostn)

		try:
			buffer_lines = None
			with open(CACHE_FOLDER+hostn+requested_item, "rb") as f:
				buffer_lines = f.readlines()

			Cache_date = get_cache_date(buffer_lines)
			if Cache_date:
				print("The cache was updated on", Cache_date)
				is_the_latest = update_requested_item(hostn, requested_item, check_header_first=True, with_date=Cache_date)
				if is_the_latest == None:
					# no need to update
					for line in buffer_lines:
						tcpCLISock.sendall(line)
				else:
					new_item = update_requested_item(hostn, requested_item)
					send_back_answer_to(tcpCLISock, new_item)
			else:
				# some website doesn't have the Date field in the response filed, then I will get the latest version of it
				print("Cannot read the date field from the cached object")
				new_item = update_requested_item(hostn, requested_item)
				send_back_answer_to(tcpCLISock, new_item)
		except FileNotFoundError as e:
			
			answer = update_requested_item(hostn, requested_item)
			send_back_answer_to(tcpCLISock, answer)

		except Exception as e:
			print(e)
		finally:
			tcpCLISock.close()


