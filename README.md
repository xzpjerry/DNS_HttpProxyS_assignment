# DNS_HttpProxyS_assignment
A DNS and HTTP Proxy server from scratch, using low level socket programming in Python.


## A multi-threaded web proxy.
This web proxy can only handle GET request for now.
### File Structure
```
.
├── Cache
│   ├── [Some_cached_website_elements]
├── my_proxyServer.py
```
### Usage: python3 my_proxyServer.py [server_ip_address] [server_listening_port_number]
#### Example: 
````
python3 my_proxyServer.py 0.0.0.0 8080

# To test it, simply open a browser to access http://localhost:8080/www.google.com or http://[server_ip_address]:8080/www.google.com
````

## A web server at www.yourlastname.432.(In this case, www.xie.432.)
### File structure

```
.
├── ZONES
│   └── sample.json <===> A sample zone file including xie.432 DNS records
├── my_dns.py
```
### USage: python3 my_dns.py [server_ip_address] [server_listening_port_number]