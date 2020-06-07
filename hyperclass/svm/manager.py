from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from typing import List, Union, Dict, Callable, Tuple, Optional
from sklearn.svm import LinearSVC
from hyperclass.gui.tasks import taskRunner, Task
import abc, time
import numpy as np

class SVC:
    __metaclass__ = abc.ABCMeta

    def __init__(self, **kwargs):
        self._score: Optional[np.ndarray] = None

    @abc.abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray): pass

    @abc.abstractmethod
    def predict( self, X: np.ndarray ) -> np.ndarray: pass

    @property
    def score(self) -> Optional[np.ndarray]:
        return self._score

    @property
    @abc.abstractmethod
    def decision_function(self) -> Callable: pass

    @classmethod
    def instance(cls, type: str, **kwargs ):
        if type == "SVCL": return SVCL( **kwargs )
        raise Exception( f"Unknown SVC type: {type}")


class SVCL(SVC):

    def __init__(self, **kwargs ):
        SVC.__init__(self, **kwargs )
        tol = kwargs.pop( 'tol', 1e-5 )
        self.svc = make_pipeline( StandardScaler(), LinearSVC( tol=tol, dual=False, fit_intercept=False, **kwargs ) )

    def fit( self, X: np.ndarray, y: np.ndarray ) -> Optional[np.ndarray]:
        t0 = time.time()
        if not ( y > 0 ).count():
            Task.taskNotAvailable( "Workflow violation", "Must spread some labels before learning the classification" )
            return None
        print(f"Running SVC fit, X shape: {X.shape}), y shape: {y.shape})")
        self.svc.fit( X, y )
        self._score = self.decision_function(X)
        print(f"Completed SVC fit, in {time.time()-t0} secs")
        return self._score

#        self._support_vector_indices = np.where( (2 * y - 1) * self._score <= 1 )[0]    # For binary classifier
#        self._support_vectors = X[ self.support_vector_indices ]

    def predict( self, X: np.ndarray ) -> np.ndarray:
        return self.svc.predict( X )

    @property
    def decision_function(self) -> Callable:
        return self.svc.decision_function

