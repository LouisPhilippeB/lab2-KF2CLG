"""Controle des moteurs et odometrie du robot."""

import math
import sys
import threading
import time

from ev_app import EvApp
from ev_app_client_api import gen_ev_externe
from moteur import Moteur
from param import (
    APP_CTRL_ROBOT,
    APP_LIGNE,
    APP_TRACEUR,
    DISTANCE_PAR_TRANSITION_CM,
    ENCODEUR_DROIT_GPIO,
    ENCODEUR_GAUCHE_GPIO,
    INTERVALLE_ODOMETRIE,
    IP_LIGNE,
    IP_TRACEUR,
    LARGEUR_ROBOT_CM,
    MOTEUR_DROIT_IN1,
    MOTEUR_DROIT_IN2,
    MOTEUR_DROIT_PWM,
    MOTEUR_GAUCHE_IN1,
    MOTEUR_GAUCHE_IN2,
    MOTEUR_GAUCHE_PWM,
    MSG_ARRETER,
    MSG_AVANCER,
    MSG_INIT,
    MSG_PIVOTER_D,
    MSG_PIVOTER_G,
    MSG_POSITION,
    MSG_RECULER,
    VITESSE_MAX,
    VITESSE_MIN,
)
from robot import Robot


class CtrlRobot(EvApp):
    TMO = INTERVALLE_ODOMETRIE

    def __init__(
        self,
        port_no,
        robot,
        encodeur_gauche,
        encodeur_droit,
        destinations_position=None,
        envoyer=gen_ev_externe,
        horloge=time.perf_counter,
        **app_options,
    ):
        app_options.setdefault("tmo", self.TMO)
        super().__init__(port_no, **app_options)
        self.robot = robot
        self.encodeur_gauche = encodeur_gauche
        self.encodeur_droit = encodeur_droit
        self._envoyer = envoyer
        self._horloge = horloge
        self._destinations_position = tuple(
            destinations_position
            if destinations_position is not None
            else (
                (IP_TRACEUR, APP_TRACEUR),
                (IP_LIGNE, APP_LIGNE),
            )
        )
        self._verrou_compteurs = threading.Lock()

        self.x = 0.0
        self.y = 0.0
        self.angle = 0.0
        self.vitesse_gauche = 0.0
        self.vitesse_droite = 0.0
        self._compteur_gauche = 0
        self._compteur_droit = 0
        self._sens_gauche = 0
        self._sens_droit = 0
        self._dernier_calcul = self._horloge()

        self._actions = {
            MSG_AVANCER: (self.robot.avancer, 1, 1),
            MSG_RECULER: (self.robot.reculer, -1, -1),
            MSG_PIVOTER_G: (self.robot.pivoter_gauche, -1, 1),
            MSG_PIVOTER_D: (self.robot.pivoter_droite, 1, -1),
        }

        self.encodeur_gauche.when_activated = self._transition_gauche
        self.encodeur_gauche.when_deactivated = self._transition_gauche
        self.encodeur_droit.when_activated = self._transition_droite
        self.encodeur_droit.when_deactivated = self._transition_droite

    @staticmethod
    def lire_vitesse(evenement):
        donnees = evenement.split()
        if not donnees or donnees[0] == "":
            raise ValueError("Vitesse manquante")
        vitesse = float(donnees[0])
        return max(VITESSE_MIN, min(VITESSE_MAX, vitesse))

    def _transition_gauche(self, _encodeur=None):
        with self._verrou_compteurs:
            self._compteur_gauche += self._sens_gauche

    def _transition_droite(self, _encodeur=None):
        with self._verrou_compteurs:
            self._compteur_droit += self._sens_droit

    def _definir_sens(self, sens_gauche, sens_droit):
        with self._verrou_compteurs:
            self._sens_gauche = sens_gauche
            self._sens_droit = sens_droit

    def initialiser_odometrie(self):
        """Arrete le robot et remet les compteurs et la pose a zero."""
        self.robot.arreter()
        with self._verrou_compteurs:
            self._compteur_gauche = 0
            self._compteur_droit = 0
            self._sens_gauche = 0
            self._sens_droit = 0

        self.x = 0.0
        self.y = 0.0
        self.angle = 0.0
        self.vitesse_gauche = 0.0
        self.vitesse_droite = 0.0
        self._dernier_calcul = self._horloge()
        self._transmettre_position()

    def _lire_deplacements_roues(self):
        with self._verrou_compteurs:
            transitions_gauche = self._compteur_gauche
            transitions_droite = self._compteur_droit
            self._compteur_gauche = 0
            self._compteur_droit = 0

        distance_gauche = transitions_gauche * DISTANCE_PAR_TRANSITION_CM
        distance_droite = transitions_droite * DISTANCE_PAR_TRANSITION_CM
        return distance_gauche, distance_droite

    def _transmettre_position(self):
        donnees = (
            round(self.vitesse_gauche, 4),
            round(self.vitesse_droite, 4),
            round(self.x, 4),
            round(self.y, 4),
            round(math.degrees(self.angle), 4),
        )
        for ip_addr, port_no in self._destinations_position:
            try:
                self._envoyer(ip_addr, port_no, MSG_POSITION, *donnees)
            except OSError as erreur:
                print(
                    "MSG_POSITION non transmis a "
                    f"{ip_addr}:{port_no}: {erreur}"
                )

    def actualiser_odometrie(self, maintenant=None):
        maintenant = self._horloge() if maintenant is None else maintenant
        duree = maintenant - self._dernier_calcul
        if duree < INTERVALLE_ODOMETRIE:
            return False

        distance_gauche, distance_droite = self._lire_deplacements_roues()
        self.vitesse_gauche = distance_gauche / duree
        self.vitesse_droite = distance_droite / duree

        distance = (distance_droite + distance_gauche) / 2.0
        variation_angle = ( distance_droite - distance_gauche ) / LARGEUR_ROBOT_CM
        angle_milieu = self.angle + variation_angle / 2.0
        self.x += math.cos(angle_milieu) * distance
        self.y += math.sin(angle_milieu) * distance
        self.angle += variation_angle
        self._dernier_calcul = maintenant
        self._transmettre_position()
        return True

    def _traiter_commande(self, evenement):
        if evenement.type == MSG_INIT:
            self.initialiser_odometrie()
            return

        if evenement.type == MSG_ARRETER:
            self.robot.arreter()
            self._definir_sens(0, 0)
            return

        action = self._actions.get(evenement.type)
        if action is None:
            print(f"Message inconnu ignore: {evenement.type}")
            return

        mouvement, sens_gauche, sens_droit = action
        try:
            mouvement(self.lire_vitesse(evenement))
            self._definir_sens(sens_gauche, sens_droit)
        except ValueError as erreur:
            self.robot.arreter()
            self._definir_sens(0, 0)
            print(f"Commande invalide, robot arrete: {erreur}")

    def dispatch_event(self, evenement):
        if evenement is not None:
            self._traiter_commande(evenement)
        self.actualiser_odometrie()

    def quitter(self):
        try:
            self.robot.fermer()
        finally:
            self.encodeur_gauche.close()
            self.encodeur_droit.close()
        print("Controleur arrete; moteurs et encodeurs desactives.")


def creer_controleur(
    port_no=APP_CTRL_ROBOT,
    ip_traceur=IP_TRACEUR,
    ip_ligne=IP_LIGNE,
):
    try:
        from gpiozero import (
            DigitalInputDevice,
            DigitalOutputDevice,
            PWMOutputDevice,
        )
    except ImportError as erreur:
        raise SystemExit(
            "gpiozero est necessaire: "
        ) from erreur

    moteur_gauche = Moteur(
        PWMOutputDevice(MOTEUR_GAUCHE_PWM),
        DigitalOutputDevice(MOTEUR_GAUCHE_IN1),
        DigitalOutputDevice(MOTEUR_GAUCHE_IN2),
    )
    moteur_droit = Moteur(
        PWMOutputDevice(MOTEUR_DROIT_PWM),
        DigitalOutputDevice(MOTEUR_DROIT_IN1),
        DigitalOutputDevice(MOTEUR_DROIT_IN2),
    )
    robot = Robot(moteur_gauche, moteur_droit)
    encodeur_gauche = DigitalInputDevice(
        ENCODEUR_GAUCHE_GPIO,
        pull_up=False,
    )
    encodeur_droit = DigitalInputDevice(
        ENCODEUR_DROIT_GPIO,
        pull_up=False,
    )
    return CtrlRobot(
        port_no,
        robot,
        encodeur_gauche,
        encodeur_droit,
        destinations_position=(
            (ip_traceur, APP_TRACEUR),
            (ip_ligne, APP_LIGNE),
        ),
    )


def main():
    ip_traceur = sys.argv[1] if len(sys.argv) > 1 else IP_TRACEUR
    ip_ligne = sys.argv[2] if len(sys.argv) > 2 else ip_traceur
    controleur = creer_controleur(
        ip_traceur=ip_traceur,
        ip_ligne=ip_ligne,
    )
    print(f"Controleur du robot en ecoute sur le port {APP_CTRL_ROBOT}.")
    print(
        "Positions transmises a "
        f"{ip_traceur}:{APP_TRACEUR} et {ip_ligne}:{APP_LIGNE}."
    )
    controleur.run()


if __name__ == "__main__":
    main()
