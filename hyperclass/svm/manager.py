from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from typing import List, Union, Dict, Callable, Tuple, Optional
from sklearn.svm import LinearSVC
import abc
import numpy as np

class SVC:
    __metaclass__ = abc.ABCMeta

    def __init__(self, **kwargs):
        self._support_vector_indices: np.ndarray = None
        self._support_vectors: np.ndarray = None

    @abc.abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray): pass

    @abc.abstractmethod
    def predict( self, X: np.ndarray ) -> np.ndarray: pass

    @property
    def support_vectors(self) -> np.ndarray:
        return self._support_vectors

    @property
    def support_vector_indices(self) -> np.ndarray:
        return self._support_vector_indices

    @abc.abstractmethod
    @property
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
        self._support_vector_indices:  np.ndarray = None
        self._support_vectors:  np.ndarray = None

    def fit( self, X: np.ndarray, y: np.ndarray ):
        self.svc.fit( X, y )
        self._support_vector_indices = np.where( (2 * y - 1) * self.decision_function(X) <= 1 )[0]
        self._support_vectors = X[ self.support_vector_indices ]

    def predict( self, X: np.ndarray ) -> np.ndarray:
        return self.svc.predict( X )

    @property
    def decision_function(self) -> Callable:
        return self.svc.decision_function

