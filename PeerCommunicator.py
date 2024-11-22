import struct
from socket import socket


class PeerCommunicator:
    def __init__(self, socket: socket):
        self.socket = socket

    def validate_handshake(self, peer_handshake, expected_info_hash, expected_peer_id):
        if len(peer_handshake) != 68:
            return False

        pstrlen = struct.unpack("B", peer_handshake[0:1])[0]
        pstr = peer_handshake[1:20].decode()

        if pstrlen != 19 or pstr != "BitTorrent protocol":
            print("Invalid protocol string.")
            return False

        info_hash = peer_handshake[28:48].hex()
        peer_id = peer_handshake[48:].decode("utf-8")

        if info_hash != expected_info_hash:
            print(
                f"Info hash mismatch. Expected: {expected_info_hash}, received: {info_hash}"
            )
            return False
        if peer_id != expected_peer_id:
            print(
                f"Peer ID mismatch. Expected: {expected_peer_id}, received: {peer_id}"
            )
            return False

        return True

    def send_handshake(self, socket: socket, id: str, infohash: str):
        """Sends a handshake message to a peer.
        Args:
            socket (socket): The socket object connected to the peer.
            id (str): The ID of the sender.
            infohash (str): The infohash of the torrent.
        Returns:
            None
        """
        # Handshake
        pstrlen = struct.pack("B", 19)
        pstr = b"BitTorrent protocol"
        reserved = b"\x00" * 8
        infohash_as_bytes = bytes.fromhex(infohash)
        peer_id = id.encode("utf-8")
        handshake = pstrlen + pstr + reserved + infohash_as_bytes + peer_id

        # Send handshake
        socket.send(handshake)
        print(f"sent handshake: {handshake!r}")

    def receive_handshake(self, socket: socket):
        """Receives a handshake message from a peer
        Args:
            socket (socket): The socket object connected to the peer.
        Returns:
            infohash (str): The infohash of the torrent.
            peer_id (str): The peer ID.
        """

        # Receive handshake
        peer_handshake = socket.recv(68)
        print(f"received handshake: {peer_handshake!r}")
        infohash = peer_handshake[28:48].hex()
        peer_id = peer_handshake[48:].decode("utf-8")

        return infohash, peer_id

    def _send_message(self, message_id, payload=None):
        length = len(payload) + 1 if payload else 0
        message = struct.pack(">I", length) + struct.pack(">B", message_id) + payload
        print("sent message", message)
        self.socket.send(message)

    def _receive_message(self):
        length_bytes = self.socket.recv(4)
        if not length_bytes:
            raise ConnectionError("Peer disconnected")
        length = struct.unpack(">I", length_bytes)[0]
        message_id = struct.unpack(">B", self.socket.recv(1))[0]
        payload = self.socket.recv(length - 1)
        return message_id, payload

    def send_choke(self):
        self._send_message(0)

    def send_unchoke(self):
        self._send_message(1)

    def send_interested(self):
        self._send_message(2)

    def send_not_interested(self):
        self._send_message(3)

    def send_have(self, piece_index):
        self._send_message(4, struct.pack(">I", piece_index))

    def send_bitfield(self, bitfield):
        self._send_message(5, bitfield)

    def send_request(self, piece_index):
        self._send_message(6, struct.pack(">I", piece_index))

    def send_piece(self, piece_index, piece_data):
        self._send_message(7, struct.pack(">I", piece_index) + piece_data)

    def receive_message_type(self):
        message_id, _ = self._receive_message()
        return message_id

    def receive_have(self):
        _, payload = self._receive_message()
        piece_index = struct.unpack(">I", payload)[0]
        return piece_index

    def receive_bitfield(self):
        _, payload = self._receive_message()
        return payload

    def receive_request(self):
        _, payload = self._receive_message()
        piece_index = struct.unpack(">I", payload)[0]
        return piece_index

    def receive_piece(self):
        _, payload = self._receive_message()
        piece_index = struct.unpack(">I", payload[:4])[0]
        piece_data = payload[4:]
        return piece_index, piece_data

    def receive_choke(self):
        return self.receive_message_type() == 0

    def receive_unchoke(self):
        return self.receive_message_type() == 1

    def receive_interested(self):
        return self.receive_message_type() == 2

    def receive_not_interested(self):
        return self.receive_message_type() == 3
