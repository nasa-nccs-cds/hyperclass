from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from typing import List, Union, Dict, Callable, Tuple, Optional
from sklearn.svm import LinearSVC
from hyperclass.gui.events import EventClient, EventMode
from PyQt5.QtCore import QObject

from hyperclass.gui.tasks import taskRunner, Task
import abc, time
import numpy as np

class Exemplar:

    def __init__(self, cid, **kwargs):
        self.cid = cid
        self.examples = []
        self._ave = None

    def addExample(self, example: np.ndarray ):
        self.examples.append( example )
        self._ave = None

    def ave(self):
        if self._ave is None:
            hs = np.hstack( self.examples )
            self._ave = hs.mean(0)
        return self._ave

class DictionaryLearning:

    def __init__(self, **kwargs):
        self._class_exemplars = {}

    def fit(self, X: np.ndarray, y: np.ndarray):
        t0 = time.time()
        if np.count_nonzero( y > 0 ) == 0:
            Task.taskNotAvailable( "Workflow violation", "Must spread some labels before learning the classification" )
            return None
        for iS in y.size:
            self.add_example( y[iS], X[iS] )

    def predict( self, X: np.ndarray ) -> np.ndarray:
        for iC, exemplar in self.getExemplars():
            np.apply_along_axis( exemplar.match, 0, X )

    def exemplar( self, cid: int ):
        return self._class_exemplars.setdefault( cid, Exemplar(cid) )

    def add_example( self, cid: int, example: np.ndarray ):
        self.exemplar( cid ).addExample( example )




