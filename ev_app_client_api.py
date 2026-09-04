import socket
import struct

TAILLE_MSG = 256
TAILLE_MSG_TOT = TAILLE_MSG + 4
MSG_PACK_FORMAT = f"!I {TAILLE_MSG}s"

client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def gen_ev_externe(ip_addr, port_no, ev_ty, *args, sock=None):
    try:
        ev_ty = int(ev_ty)
    except (TypeError, ValueError) as erreur:
        raise ValueError(f"Le type de message doit etre un entier: {ev_ty}") from erreur

    donnees = ";".join(str(donnee) for donnee in args).encode("utf-8")
    if len(donnees) > TAILLE_MSG:
        raise ValueError(f"Le message depasse {TAILLE_MSG} octets")

    message = struct.pack(MSG_PACK_FORMAT, ev_ty, donnees)
    (sock or client_sock).sendto(message, (ip_addr, int(port_no)))


def fermer_client():
    if client_sock.fileno() != -1:
        client_sock.close()
