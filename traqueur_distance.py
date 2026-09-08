from moteur import ETAT_AVANT, ETAT_ARRIERE
from param import DISTANCE_TRANSITION

class TraqueurDistance:
    def __init__(self, moteur, encRot):
        self._activations = 0

        def on_change():
            etat = moteur.etat()
            if (etat = ETAT_AVANT):
                self._activations += 1
            elif (etat = ETAT_ARRIERE):
                self._activations -= 1

        encRot.when_activated = on_change
        encRot.when_deactivated = on_change

    def distance(self):
        return self._activations * DISTANCE_TRANSITION
