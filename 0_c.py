import time
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
buffer_size = 1024 * 1024  # 1MB buffer size
s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buffer_size)
s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, buffer_size)
print("Socket buffer size set to 1MB")
print(s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))
print(s.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF))
s.connect(("192.168.1.55", 22236))
print("Connected to server")
data = s.recv(1024)
data = s.recv(1024)
print(data.decode("utf-8"))
time.sleep(10)
with open("./download_path/sample2.pdf", "rb") as f:
    data = f.read()
s.send(data)
s.close()
