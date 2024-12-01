import struct
import select
from socket import socket


class PeerCommunicator:
    def __init__(self, socket: socket, timeout=5):
        self.socket = socket
        self.timeout = timeout  # Timeout for operations in seconds

    def _wait_for_data(self):
        ready, _, _ = select.select([self.socket], [], [], self.timeout)
        if not ready:
            raise TimeoutError("Timeout waiting for data from peer")

    def validate_handshake(self, peer_handshake, expected_info_hash, expected_peer_id):
        if len(peer_handshake) != 68:
            print("Invalid handshake length. Received:", len(peer_handshake))
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

    def send_handshake(self, id: str, infohash: str):
        pstrlen = struct.pack("B", 19)
        pstr = b"BitTorrent protocol"
        reserved = b"\x00" * 8
        infohash_as_bytes = bytes.fromhex(infohash)
        peer_id = id.encode("utf-8")
        handshake = pstrlen + pstr + reserved + infohash_as_bytes + peer_id

        self.socket.send(handshake)

    def receive_handshake(self):
        self._wait_for_data()
        peer_handshake = self.socket.recv(68)
        return peer_handshake

    def _send_message(self, message_id, payload=None):
        if payload:
            length = len(payload) + 1
            message = (
                struct.pack(">I", length) + struct.pack(">B", message_id) + payload
            )
        else:
            length = 1
            message = struct.pack(">I", length) + struct.pack(">B", message_id)
        self.socket.send(message)

    def _receive_message(self):
        self._wait_for_data()
        length_bytes = self.socket.recv(4)
        if not length_bytes:
            raise ConnectionError("Peer disconnected")
        length = struct.unpack(">I", length_bytes)[0]
        message_id = struct.unpack(">B", self.socket.recv(1))[0]
        payload = self.socket.recv(length - 1) if length > 1 else b""
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
        self._wait_for_data()
        message_id, _ = self._receive_message()
        return message_id

    def receive_have(self):
        self._wait_for_data()
        _, payload = self._receive_message()
        piece_index = struct.unpack(">I", payload)[0]
        return piece_index

    def receive_bitfield(self) -> bytes:
        self._wait_for_data()
        _, payload = self._receive_message()
        return payload

    def receive_request(self):
        self._wait_for_data()
        _, payload = self._receive_message()
        if payload == b"":
            return None
        piece_index = struct.unpack(">I", payload)[0]
        return piece_index

    def receive_piece(self):
        self._wait_for_data()
        _, payload = self._receive_message()
        piece_index = struct.unpack(">I", payload[:4])[0]
        piece_data = payload[4:]
        return piece_index, piece_data

    def receive_choke(self):
        self._wait_for_data()
        return self.receive_message_type() == 0

    def receive_unchoke(self):
        self._wait_for_data()
        return self.receive_message_type() == 1

    def receive_interested(self):
        self._wait_for_data()
        return self.receive_message_type() == 2

    def receive_not_interested(self):
        self._wait_for_data()
        return self.receive_message_type() == 3
