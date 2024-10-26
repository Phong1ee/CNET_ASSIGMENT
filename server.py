import socket
from threading import Thread

def new_connection(addr, conn):
    print(f"Receiving connection request from {addr}.")

    # Receive SYN message from client
    syn = conn.recv(1024).decode()
    if syn == "SYN":
        print(f"SYN received from {addr}.")

        conn.send(b"SYN-ACK")
        print(f"SYN-ACK sent to {addr}.")

        ack = conn.recv(1024).decode()
        if ack == "ACK":
            print(f"ACK received from {addr}.")
        else:
            print(f"ACK not received from {addr}.")
            conn.close()
    else:
        print(f"SYN not received from {addr}.")
        conn.close()

    print(f"Connection from {addr} established.")
    conn.close()  # Close connection

def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def server_program(host, port):
    serversocket = socket.socket()
    serversocket.bind((host, port))
    
    serversocket.listen(10)
    print(f"Server listening on: {host}:{port}")
    
    while True:
        conn, addr = serversocket.accept()
        nconn = Thread(target=new_connection, args=(addr, conn))
        nconn.start()

if __name__ == "__main__":
    hostip = get_host_default_interface_ip()
    port = 22236
    print("Listening on: {}:{}".format(hostip, port))
    server_program(hostip, port)
