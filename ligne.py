"""Arret automatique du robot apres chaque trajet de un metre."""

import math
import sys

from ev_app import EvApp
from ev_app_client_api import fermer_client, gen_ev_externe
from param import (
    APP_CTRL_ROBOT,
    APP_LIGNE,
    DISTANCE_LIGNE_CM,
    DISTANCE_PAR_TRANSITION_CM,
    IP_CTRL_ROBOT,
    MSG_INIT,
    MSG_POSITION,
)


class Ligne(EvApp):
    def __init__(
        self,
        port_no=APP_LIGNE,
        ip_robot=IP_CTRL_ROBOT,
        envoyer=gen_ev_externe,
        afficher=print,
        **app_options,
    ):
        super().__init__(port_no, **app_options)
        self.ip_robot = ip_robot
        self._envoyer = envoyer
        self._afficher = afficher
        self.distance_parcourue = 0.0
        self._point_precedent = None
        self._attend_position_initiale = True

        self._demander_initialisation()

    @staticmethod
    def lire_position(evenement):
        donnees = evenement.split()
        if len(donnees) != 5:
            raise ValueError(
                "MSG_POSITION doit contenir exactement cinq valeurs"
            )

        try:
            valeurs = tuple(float(donnee) for donnee in donnees)
        except (TypeError, ValueError) as erreur:
            raise ValueError(
                "MSG_POSITION ne contient pas de nombres"
            ) from erreur

        if not all(math.isfinite(valeur) for valeur in valeurs):
            raise ValueError("MSG_POSITION ne contient pas de nombres finis")
        return valeurs

    def _demander_initialisation(self):
        self.distance_parcourue = 0.0
        self._point_precedent = None
        self._attend_position_initiale = True
        try:
            self._envoyer(
                self.ip_robot,
                APP_CTRL_ROBOT,
                MSG_INIT,
            )
        except OSError as erreur:
            print(f"MSG_INIT n'est pas transmis au robot: {erreur}")

    def _accepter_position_initiale(self, x, y):
        distance_origine = math.hypot(x, y)
        if distance_origine > DISTANCE_PAR_TRANSITION_CM:
            return False

        self._point_precedent = (x, y)
        self._attend_position_initiale = False
        self._afficher("Nouvelle ligne: position initiale.")
        return True

    def _ajouter_position(self, x, y):
        point = (x, y)
        x_precedent, y_precedent = self._point_precedent
        self.distance_parcourue += math.hypot(
            point[0] - x_precedent,
            point[1] - y_precedent,
        )
        self._point_precedent = point

        if self.distance_parcourue < DISTANCE_LIGNE_CM:
            return

        self._afficher(
            f"Distance atteinte: {self.distance_parcourue:.2f} cm. "
            "Robot arrete et odometrie reinitialisee."
        )
        self._demander_initialisation()

    def dispatch_event(self, evenement):
        if evenement is None:
            return
        if evenement.type != MSG_POSITION:
            print(f"Message inconnu ignore: {evenement.type}")
            return

        try:
            _vg, _vd, x, y, _angle = self.lire_position(evenement)
        except ValueError as erreur:
            print(f"MSG_POSITION invalide ignore: {erreur}")
            return

        if self._attend_position_initiale:
            self._accepter_position_initiale(x, y)
            return
        self._ajouter_position(x, y)

    def quitter(self):
        self._demander_initialisation()
        print("Programme ligne arrete; reinitialiser.")


def main():
    ip_robot = sys.argv[1] if len(sys.argv) > 1 else IP_CTRL_ROBOT
    ligne = Ligne(ip_robot=ip_robot)
    print(
        f"Programme ligne en ecoute sur le port {APP_LIGNE}; "
        f"robot a {ip_robot}:{APP_CTRL_ROBOT}."
    )
    try:
        ligne.run()
    finally:
        fermer_client()


if __name__ == "__main__":
    main()
