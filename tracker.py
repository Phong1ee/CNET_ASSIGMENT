import socket

# from threading import Thread
from aiohttp import web
import bencodepy


class Tracker:
    def __init__(self):
        # List of swarms (dict):
        #    {info_hash: str,
        #     peers[]: {seeder, peer_id, ip, port}})
        self.swarms = {}

    def _print_swarm(self):
        for swarm in self.swarms:
            print(f"info_hash: {swarm['info_hash']}")
            for peer in swarm["peers"]:
                print(f"    peer_id: {peer['peer_id']}")
                print(f"    ip: {peer['ip']}")
                print(f"    port: {peer['port']}")
                print(f"    seeder: {peer['seeder']}")

    # def _update_swarms(self, info_hash, peer_id, ip, port, is_seeder, event):
    #     # Remove peer from swarm if event is "stopped"
    #     if event == "stopped":
    #         print("there are swarms:", self.swarms)
    #         for swarm in self.swarms:
    #             print(f"Checking swarm {swarm['info_hash']}")
    #             for i, peer in enumerate(swarm["peers"]):
    #                 if peer["ip"] == ip:
    #                     swarm["peers"].pop(i)
    #                     print(f"Peer {peer_id} has left the swarm {swarm['info_hash']}")
    #                     if not swarm["peers"]:
    #                         print(f"Swarm {swarm['info_hash']} is empty, removing it")
    #                         self.swarms.remove(swarm)
    #                     break
    #
    #     for swarm in self.swarms:
    #         if swarm["info_hash"] == info_hash:
    #             for i, peer in enumerate(swarm["peers"]):
    #                 if peer["ip"] == ip:
    #                     # Update peer information, including peer_id and seeder status
    #                     print(f"Updating new Peer_ID for {ip}")
    #                     swarm["peers"][i]["peer_id"] = peer_id
    #                     swarm["peers"][i]["seeder"] = is_seeder
    #                     return
    #
    #             # If the peer doesn't exist, add it to the swarm
    #             swarm["peers"].append(
    #                 {"peer_id": peer_id, "ip": ip, "port": port, "seeder": is_seeder}
    #             )
    #             return
    #
    #     # If the swarm doesn't exist, create a new one
    #     self.swarms.append(
    #         {
    #             "info_hash": info_hash,
    #             "peers": [
    #                 {"peer_id": peer_id, "ip": ip, "port": port, "seeder": is_seeder}
    #             ],
    #         }
    #     )

    # def _prepare_response_params(
    #     self, info_hash: str, numwant: int, peer_id: str, ip: str, port: int, is_seeder: int, event: str
    # ):
    #     """Prepare the response parameters for the announce request.
    #     Args:
    #         info_hash (str): The info hash of the torrent
    #         numwant (int): Number of peers to return
    #         peer_id (str): The peer ID of the client
    #         ip (str): The IP address of the client
    #         port (int): The port of the client
    #         is_seeder (int): 1 if the client is a seeder, 0 otherwise
    #         event (str): The event type of the announce request
    #     Returns:
    #         The response parameters encoded in bencode format
    #     """
    #     if is_seeder:
    #         return bencodepy.encode({"interval": 1800})
    #
    #     if
    #         return bencodepy.encode({"failure reason": "Missing required parameters"})
    #
    #     response = {"interval": 1800, "complete": 0, "incomplete": 0, "peers": []}
    #
    #     for swarm in self.swarms:
    #         # Check if the info_hash matches
    #         if swarm["info_hash"] == info_hash:
    #             found_numwant = False
    #
    #             # Iterate through the peers in the swarm
    #             for peer in swarm["peers"]:
    #                 # Skip the peer if it's the same as the client
    #                 if peer["peer_id"] == peer_id or (
    #                     peer["ip"] == ip and peer["port"] == port
    #                 ):
    #                     continue
    #
    #                 # Add the peer to the response
    #                 response["peers"].append(peer)
    #                 if peer["seeder"]:
    #                     response["complete"] += 1
    #                 else:
    #                     response["incomplete"] += 1
    #                 if len(response["peers"]) == numwant:
    #                     found_numwant = True
    #                     break
    #
    #             if found_numwant:
    #                 break
    #
    #     return bencodepy.encode(response)

    async def announce(self, request):
        info_hash = request.query.get("info_hash")
        peer_id = request.query.get("peer_id")
        ip = request.query.get("ip")
        port = int(request.query.get("port"))
        left = int(request.query.get("left"))
        event = request.query.get("event")
        numwant = int(request.query.get("numwant", 50))

        is_seeder = left == 0
        peer_info = {"peer_id": peer_id, "ip": ip, "port": port}

        if info_hash not in self.swarms:
            self.swarms[info_hash] = {"peers": [], "complete": 0, "incomplete": 0}

        swarm = self.swarms[info_hash]

        if event == "stopped":
            swarm["peers"].remove(peer_info)
            if is_seeder:
                swarm["complete"] -= 1
            else:
                swarm["incomplete"] -= 1
            if not swarm["peers"]:
                del self.swarms[info_hash]
        else:
            swarm["peers"].append(peer_info)
            if is_seeder:
                swarm["complete"] += 1
            else:
                swarm["incomplete"] += 1

        response = {
            "interval": 1800,
            "complete": swarm["complete"],
            "incomplete": swarm["incomplete"],
            "peers": [],
        }

        # Don't include the client in the response
        for peer in swarm["peers"]:
            if peer != peer_info:
                response["peers"].append(peer)
                if len(response["peers"]) >= numwant:
                    break

        return web.Response(body=bencodepy.encode(response), content_type="text/plain")


def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    tracker = Tracker()

    app = web.Application()
    app.router.add_get("/announce", tracker.announce)
    hostip = get_host_default_interface_ip()
    port = 22236
    print("Listening on: {}:{}".format(hostip, port))
    web.run_app(app, host=hostip, port=port)
