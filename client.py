import socket
import time
import argparse
from threading import Thread

def new_connection(tid, host, port):
    print('Thread ID {} connecting to {}:{}'.format(tid, host, port))

    client_socket = socket.socket()
    client_socket.connect((host, port))

    # Handshake: Send "HELLO" message
    client_socket.send(b"HELLO")
    
    # Wait for server acknowledgment
    ack_msg = client_socket.recv(1024).decode()  # Receive acknowledgment
    if ack_msg == "ACK":
        print(f'Thread ID {tid} received ACK from server.')
    else:
        print(f'Thread ID {tid} did not receive ACK from server.')
    
    # Demo sleep time for fun (dummy command)
    for i in range(0, 3):
        print('Let me, ID={}: sleep in {}s'.format(tid, 3 - i))
        time.sleep(1)

    print('OK! I am ID={} done here'.format(tid))
    client_socket.close()  # Close the client socket

def connect_server(threadnum, host, port):
    # Create "threadnum" of Thread to parallel connect
    threads = [Thread(target=new_connection, args=(i, host, port)) for i in range(0, threadnum)]
    [t.start() for t in threads]

    # Wait for all threads to finish
    [t.join() for t in threads]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Client',
        description='Connect to pre-declared server',
        epilog='!!!It requires the server is running and listening!!!'
    )
    parser.add_argument('--server-ip', type=str, required=True)
    parser.add_argument('--server-port', type=int, required=True)
    parser.add_argument('--client-num', type=int, required=True)
    args = parser.parse_args()
    host = args.server_ip
    port = args.server_port
    cnum = args.client_num
    connect_server(cnum, host, port)
