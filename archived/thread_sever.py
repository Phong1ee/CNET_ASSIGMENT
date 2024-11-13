import socket
from threading import Thread

def new_sever_incoming (addr, conn):
    print (addr)

def thread_sever (host, port):
    print("thread sever listening on: {}:{}".format(host,port))

    seversocket = socket.socket()
    seversocket.bind((host,port))

    seversocket.listen(10)
    while True:
        addr, conn = seversocket.accept()
        nconn = Thread(target = new_sever_incoming, args = (addr, conn))
        nconn.start