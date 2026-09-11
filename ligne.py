"""Arret lorsque le robot est a un metre du debut de la ligne."""

import math

from ev_app import EvApp
from ev_app_client_api import fermer_client, gen_ev_externe
from param import (
    APP_CTRL_ROBOT,
    APP_LIGNE,
    DISTANCE_LIGNE_CM,
    DISTANCE_PAR_TRANSITION_CM,
    MSG_INIT,
    MSG_POSITION,
)


class Ligne(EvApp):
    def __init__(
        self,
        port_no=APP_LIGNE,
        envoyer=gen_ev_externe,
        afficher=print,
        **app_options,
    ):
        super().__init__(port_no, **app_options)
        self._envoyer = envoyer
        self._afficher = afficher
        self.distance_parcourue = 0.0
        self._point_initial = None
        self._attend_position_initiale = True

        self._demander_initialisation()

    @staticmethod
    def lire_position(evenement):
        donnees = evenement.split()
        if len(donnees) != 3:
            raise ValueError(
                "MSG_POSITION doit contenir x, y et l'orientation"
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
        self._point_initial = None
        self._attend_position_initiale = True
        try:
            self._envoyer(
                "127.0.0.1",
                APP_CTRL_ROBOT,
                MSG_INIT,
            )
        except OSError as erreur:
            print(f"MSG_INIT n'est pas transmis au robot: {erreur}")

    def _accepter_position_initiale(self, x, y):
        distance_origine = math.hypot(x, y)
        if distance_origine > DISTANCE_PAR_TRANSITION_CM:
            return False

        self._point_initial = (x, y)
        self._attend_position_initiale = False
        self._afficher("Nouvelle ligne: position initiale.")
        return True

    def _calculer_distance(self, x, y):
        x_initial, y_initial = self._point_initial
        self.distance_parcourue = math.hypot(
            x - x_initial,
            y - y_initial,
        )

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
            x, y, _angle = self.lire_position(evenement)
        except ValueError as erreur:
            print(f"MSG_POSITION invalide ignore: {erreur}")
            return

        if self._attend_position_initiale:
            self._accepter_position_initiale(x, y)
            return
        self._calculer_distance(x, y)

    def quitter(self):
        self._demander_initialisation()
        print("Programme ligne arrete; reinitialiser.")


def main():
    ligne = Ligne()
    print(
        f"Programme ligne en ecoute sur le port local {APP_LIGNE}."
    )
    try:
        ligne.run()
    finally:
        fermer_client()


if __name__ == "__main__":
    main()
