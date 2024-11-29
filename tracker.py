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
        for info_hash, swarm in self.swarms.items():
            print(f"Swarm for {info_hash}")
            print(f"  Complete: {swarm['complete']}")
            print(f"  Incomplete: {swarm['incomplete']}")
            for peer in swarm["peers"]:
                print(f"    Peer: {peer['peer_id']} ({peer['ip']}:{peer['port']})")
            print()

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
            peer_exist = False
            # modify the peer info if it already exists
            for peer in swarm["peers"]:
                if peer["ip"] == ip and peer["port"] == port:
                    peer["peer_id"] = peer_id
                    peer_exist = True
                    break
            if not peer_exist:
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

        print("Responding to peer", peer_id)
        print("Response:", response)
        self._print_swarm()
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
