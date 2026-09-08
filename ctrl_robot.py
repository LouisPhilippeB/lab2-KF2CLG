"""Serveur qui traduit les messages en mouvements du robot."""

from ev_app import EvApp
from moteur import Moteur
from enc_rot import EncRot
from param import (
    APP_CTRL_ROBOT,
    MOTEUR_DROIT_IN1,
    MOTEUR_DROIT_IN2,
    MOTEUR_DROIT_PWM,
    MOTEUR_GAUCHE_IN1,
    MOTEUR_GAUCHE_IN2,
    MOTEUR_GAUCHE_PWM,
    MSG_ARRETER,
    MSG_AVANCER,
    MSG_PIVOTER_D,
    MSG_PIVOTER_G,
    MSG_RECULER,
    VITESSE_MAX,
    VITESSE_MIN,
    ENC_ROT_GAUCHE,
    ENC_ROT_DROIT
)
from robot import Robot


class CtrlRobot(EvApp):
    def __init__(self, port_no, robot, **app_options):
        super().__init__(port_no, **app_options)
        self.robot = robot
        self._actions = {
            MSG_AVANCER: self.robot.avancer,
            MSG_RECULER: self.robot.reculer,
            MSG_PIVOTER_G: self.robot.pivoter_gauche,
            MSG_PIVOTER_D: self.robot.pivoter_droite,
        }

    @staticmethod
    def lire_vitesse(evenement):
        donnees = evenement.split()
        if not donnees or donnees[0] == "":
            raise ValueError("Vitesse manquante")
        vitesse = float(donnees[0])
        return max(VITESSE_MIN, min(VITESSE_MAX, vitesse))

    def dispatch_event(self, evenement):
        if evenement.type == MSG_ARRETER:
            self.robot.arreter()
            return

        action = self._actions.get(evenement.type)
        if action is None:
            print(f"Message inconnu ignore: {evenement.type}")
            return

        try:
            action(self.lire_vitesse(evenement))
        except ValueError as erreur:
            self.robot.arreter()
            print(f"Commande invalide, robot arrete: {erreur}")

    def quitter(self):
        self.robot.fermer()
        print("Controleur arrete; moteurs desactives.")


def creer_robot():
    try:
        from gpiozero import DigitalOutputDevice, PWMOutputDevice, DigitalInputDevice
    except ImportError as erreur:
        raise SystemExit(
            "gpiozero est requis: "
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
    enc_droit = DigitalInputDevice(ENC_ROT_DROIT)
    enc_gauche = DigitalInputDevice(ENC_ROT_GAUCHE)

    return Robot(moteur_gauche, moteur_droit, enc_droit, enc_gauche)

def main():
    controleur = CtrlRobot(APP_CTRL_ROBOT, creer_robot())
    print(f"Controleur du robot en ecoute sur le port {APP_CTRL_ROBOT}.")
    controleur.run()


if __name__ == "__main__":
    main()
