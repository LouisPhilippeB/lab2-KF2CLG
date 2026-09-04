"""Telecommande clavier du robot."""

import sys

from ev_app_client_api import fermer_client, gen_ev_externe
from param import (
    APP_CTRL_ROBOT,
    IP_CTRL_ROBOT,
    MSG_ARRETER,
    MSG_AVANCER,
    MSG_PIVOTER_D,
    MSG_PIVOTER_G,
    MSG_RECULER,
    PAS_VITESSE,
    VITESSE_INITIALE,
    VITESSE_MAX,
    VITESSE_MIN,
)

NOM_FENETRE = "Controle robot - clavier actif"
LARGEUR_FENETRE = 560
HAUTEUR_FENETRE = 430

NOMS_COMMANDES = {
    MSG_AVANCER: "AVANCE",
    MSG_RECULER: "RECULE",
    MSG_PIVOTER_G: "PIVOTE A GAUCHE",
    MSG_PIVOTER_D: "PIVOTE A DROITE",
}


class TelCmd:
    COMMANDES_MOUVEMENT = {
        ord("q"): MSG_PIVOTER_G,
        ord("w"): MSG_AVANCER,
        ord("e"): MSG_PIVOTER_D,
        ord("s"): MSG_RECULER,
    }

    def __init__(self, ip_robot, envoyer=gen_ev_externe):
        self.ip_robot = ip_robot
        self.vitesse = VITESSE_INITIALE
        self.derniere_commande = None
        self._envoyer = envoyer

    def envoyer_mouvement(self, type_message):
        self._envoyer(
            self.ip_robot,
            APP_CTRL_ROBOT,
            type_message,
            self.vitesse,
        )
        self.derniere_commande = type_message

    def arreter(self):
        self._envoyer(self.ip_robot, APP_CTRL_ROBOT, MSG_ARRETER)
        self.derniere_commande = None

    def modifier_vitesse(self, variation):
        nouvelle_vitesse = self.vitesse + variation
        self.vitesse = round(
            max(VITESSE_MIN, min(VITESSE_MAX, nouvelle_vitesse)),
            2,
        )
        print(f"Vitesse: {self.vitesse:.2f} m/s")
        if self.derniere_commande is not None:
            self.envoyer_mouvement(self.derniere_commande)

    def traiter_touche(self, touche):
        if touche == -1:
            return False

        if ord("A") <= touche <= ord("Z"):
            touche = ord(chr(touche).lower())

        commande = self.COMMANDES_MOUVEMENT.get(touche)
        if commande is not None:
            self.envoyer_mouvement(commande)
        elif touche == ord(" "):
            self.arreter()
        elif touche == ord("."):
            self.modifier_vitesse(PAS_VITESSE)
        elif touche == ord(","):
            self.modifier_vitesse(-PAS_VITESSE)
        elif touche == ord("x"):
            self.arreter()
            return False
        else:
            print("Commande invalide")
        return True

    def executer(self, lire_touche, actualiser_affichage=None):
        try:
            actif = True
            while actif:
                actif = self.traiter_touche(lire_touche())
                if actif and actualiser_affichage is not None:
                    actualiser_affichage()
        except KeyboardInterrupt:
            pass
        finally:
            self.arreter()


def afficher_commandes(telecommande, cv2, np):
    image = np.full(
        (HAUTEUR_FENETRE, LARGEUR_FENETRE, 3),
        (32, 32, 32),
        dtype=np.uint8,
    )

    couleur_titre = (80, 210, 255)
    couleur_texte = (235, 235, 235)
    couleur_etat = (100, 230, 120)
    police = cv2.FONT_HERSHEY_SIMPLEX

    cv2.putText(
        image,
        "CONTROLE DU ROBOT",
        (125, 42),
        police,
        0.8,
        couleur_titre,
        2,
        cv2.LINE_AA,
    )

    commandes = (
        "W : Avancer",
        "S : Reculer",
        "Q : Pivoter a gauche",
        "E : Pivoter a droite",
        "ESPACE : Arreter",
        ". : Augmenter la vitesse",
        ", : Diminuer la vitesse",
        "X : Arreter et quitter",
    )

    for index, texte in enumerate(commandes):
        cv2.putText(
            image,
            texte,
            (55, 85 + index * 34),
            police,
            0.58,
            couleur_texte,
            1,
            cv2.LINE_AA,
        )

    etat = NOMS_COMMANDES.get(telecommande.derniere_commande, "ARRETE")
    cv2.rectangle(image, (35, 365), (525, 415), (65, 65, 65), -1)
    cv2.putText(
        image,
        f"Etat: {etat}   Vitesse: {telecommande.vitesse:.2f} m/s",
        (50, 397),
        police,
        0.58,
        couleur_etat,
        1,
        cv2.LINE_AA,
    )

    cv2.imshow(NOM_FENETRE, image)


def main():
    ip_robot = sys.argv[1] if len(sys.argv) > 1 else IP_CTRL_ROBOT

    try:
        import cv2
        import numpy as np
    except ImportError as erreur:
        raise SystemExit(
            "OpenCV et NumPy ne sont pas fonctionnels"
        ) from erreur

    telecommande = TelCmd(ip_robot)
    afficher_commandes(telecommande, cv2, np)
    print(f"Telecommande connecter a {ip_robot}:{APP_CTRL_ROBOT}.")

    try:
        telecommande.executer(
            lambda: cv2.waitKeyEx(0),
            lambda: afficher_commandes(telecommande, cv2, np),
        )
    finally:
        cv2.destroyAllWindows()
        fermer_client()


if __name__ == "__main__":
    main()
