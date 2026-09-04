import socket
import select
import struct

from ev_app_client_api import MSG_PACK_FORMAT, TAILLE_MSG_TOT

HOST_IP = "0.0.0.0"


class EvDesc:
    def __init__(self, type_message, donnee):
        try:
            self.type = int(type_message)
        except (TypeError, ValueError) as erreur:
            raise ValueError(
                f"Le type de message doit etre un entier: {type_message}"
            ) from erreur
        self.donnee = donnee

    def __repr__(self):
        return f"{self.type}::{self.donnee}"

    def split(self):
        return self.donnee.split(";")


class EvApp:
    def __init__(self, port_no=8999, tmo=0.5, host_ip=HOST_IP):
        self._termine = False
        self.tmo = tmo
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setblocking(False)
        self.udp_sock.bind((host_ip, port_no))

    def dispatch_event(self, ev):
        print(ev)

    def quitter_app(self):
        self._termine = True

    def quitter(self):
        pass

    def run(self):
        try:
            while not self._termine:
                readable, _, _ = select.select([self.udp_sock], [], [], self.tmo)
                if not readable:
                    continue

                message, _ = self.udp_sock.recvfrom(TAILLE_MSG_TOT)
                try:
                    type_message, donnees = struct.unpack(MSG_PACK_FORMAT, message)
                except struct.error:
                    print("Message UDP invalide ignore")
                    continue

                evenement = EvDesc(
                    type_message,
                    donnees.decode("utf-8").rstrip("\x00"),
                )
                self.dispatch_event(evenement)
        except KeyboardInterrupt:
            pass
        finally:
            self._termine = True
            self.quitter()
            self.udp_sock.close()
