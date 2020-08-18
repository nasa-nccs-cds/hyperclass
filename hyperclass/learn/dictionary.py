from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from typing import List, Union, Dict, Callable, Tuple, Optional
from sklearn.svm import LinearSVC
from hyperclass.gui.events import EventClient, EventMode
from PyQt5.QtCore import QObject

from hyperclass.gui.tasks import taskRunner, Task
import abc, time
import numpy as np

class DictionaryLearning:

    def __init__(self, **kwargs):
        self._class_exemplars = {}

    def fit(self, X: np.ndarray, y: np.ndarray):
        t0 = time.time()
        if np.count_nonzero( y > 0 ) == 0:
            Task.taskNotAvailable( "Workflow violation", "Must spread some labels before learning the classification" )
            return None
        for iS in y.size:
            self.add_exemplar( y[iS], X[iS] )
        self._class_exemplars = self._class_exemplars / y.size

    def predict( self, X: np.ndarray ) -> np.ndarray:
        pass

    def add_exemplar( self, cid: int, exemplar: np.ndarray ):
        self._class_exemplars[cid] = self._class_exemplars[cid] + exemplar if cid in self._class_exemplars.keys() else exemplar




