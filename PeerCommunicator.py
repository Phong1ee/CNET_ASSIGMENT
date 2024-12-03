import struct
import time
import select
from socket import socket


class PeerCommunicator:
    def __init__(self, socket: socket, timeout=5):
        self.socket = socket
        self.timeout = timeout

    # def _wait_for_data(self):
    #     ready, _, _ = select.select([self.socket], [], [], self.timeout)
    #     if not ready:
    #         raise TimeoutError("Timeout waiting for data from peer")

    def _wait_for_data(self):
        if self.socket.fileno() == -1:  # Check if the socket is open
            raise ConnectionError("Socket is closed.")

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
        print("PeerCommunicator: Sending request for piece", piece_index)
        self._send_message(6, struct.pack(">I", piece_index))

    # def send_piece(self, piece_index, piece_data):
    #     chunk_size = 4096
    #     divided_piece = [
    #         piece_data[i : i + chunk_size]
    #         for i in range(0, len(piece_data), chunk_size)
    #     ]
    #
    #     for i, piece_chunk in enumerate(divided_piece):
    #         is_last_chunk = 1 if i == len(divided_piece) - 1 else 0
    #         payload = (
    #             struct.pack(">I", piece_index)
    #             + struct.pack(">B", is_last_chunk)
    #             + piece_chunk
    #         )
    #         self._send_message(7, payload)
    #         time.sleep(0.005)

    def send_piece(self, piece_index, piece_data):
        block_size = 4 * 1024

        divided_piece = [
            piece_data[i : i + block_size]
            for i in range(0, len(piece_data), block_size)
        ]

        for i, piece_block in enumerate(divided_piece):
            is_last_block = 1 if i == len(divided_piece) - 1 else 0

            payload = (
                struct.pack(">I", piece_index)
                + struct.pack(">B", is_last_block)
                + piece_block
            )

            try:
                self._send_message(7, payload)
            except Exception as e:
                raise ConnectionError(f"Failed to send piece chunk: {e}")

            time.sleep(0.01)

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
        print("PeerCommunicator: Received request for piece", piece_index)
        return piece_index

    # def receive_piece(self):
    #     piece_data = b""
    #     piece_index = None
    #
    #     while True:
    #         self._wait_for_data()
    #         _, payload = self._receive_message()
    #
    #         if piece_index is None:
    #             piece_index = struct.unpack(">I", payload[:4])[0]
    #
    #         is_last_chunk = struct.unpack(">B", payload[4:5])[0]
    #         piece_data += payload[5:]
    #
    #         if is_last_chunk == 1:
    #             break
    #
    #     return piece_index, piece_data

    def receive_piece(self):
        piece_data = b""
        piece_index = None

        while True:
            try:
                _, payload = self._receive_message()
            except Exception as e:
                raise ConnectionError(f"Error receiving message: {e}")

            if len(payload) < 5:
                raise ValueError("Invalid payload length received.")

            if piece_index is None:
                piece_index = struct.unpack(">I", payload[:4])[0]

            is_last_chunk = struct.unpack(">B", payload[4:5])[
                0
            ]  # Extract last chunk flag
            piece_data += payload[5:]  # Append chunk data

            if is_last_chunk == 1:
                break  # Exit loop if this is the last chunk

        print("PeerCommunicator: received piece", piece_index)
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
