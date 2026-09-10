"""Affichage des positions recues du controleur du robot."""

import math

from ev_app import EvApp
from param import APP_TRACEUR, MSG_POSITION


class Traceur(EvApp):
    def __init__(self, port_no=APP_TRACEUR, afficher=print, **app_options):
        super().__init__(port_no, **app_options)
        self._afficher = afficher

    @staticmethod
    def lire_position(evenement):
        donnees = evenement.split()
        if len(donnees) != 5:
            raise ValueError(
                "MSG_POSITION doit contenir 5 chiffres"
            )

        try:
            valeurs = tuple(float(donnee) for donnee in donnees)
        except (TypeError, ValueError) as erreur:
            raise ValueError(
                "MSG_POSITION contient une mauvaise valeur"
            ) from erreur

        if not all(math.isfinite(valeur) for valeur in valeurs):
            raise ValueError("MSG_POSITION contient une valeur non finie")
        return valeurs

    def dispatch_event(self, evenement):
        if evenement is None:
            return
        if evenement.type != MSG_POSITION:
            print(f"Message inconnu ignore: {evenement.type}")
            return

        try:
            vg, vd, x, y, angle_degres = self.lire_position(evenement)
        except ValueError as erreur:
            print(f"MSG_POSITION invalide ignore: {erreur}")
            return

        self._afficher(
            "POSITION | "
            f"vg={vg:8.3f} cm/s | "
            f"vd={vd:8.3f} cm/s | "
            f"x={x:8.3f} cm | "
            f"y={y:8.3f} cm | "
            f"angle={angle_degres:8.3f} deg"
        )

    def quitter(self):
        print("Traceur arrete.")


def main():
    traceur = Traceur()
    print(f"Traceur en ecoute sur le port {APP_TRACEUR}.")
    traceur.run()


if __name__ == "__main__":
    main()
