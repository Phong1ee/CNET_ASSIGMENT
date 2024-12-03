import socket
import time

ip = "192.168.1.55"
port = 22236

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((ip, port))

server_socket.listen(5)
s, _ = server_socket.accept()
s.send(b"Hello, world!")
time.sleep(5)
s.send(b"okay after 5s")

data = s.recv(1024 * 1024)
print(data)
s.close()
