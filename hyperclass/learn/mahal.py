from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from typing import List, Union, Dict, Callable, Tuple, Optional
from scipy.spatial import distance
import scipy
import xarray as xa
import time, traceback
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from hyperclass.gui.events import EventClient, EventMode
from typing import List, Tuple, Optional, Dict
from hyperclass.gui.tasks import taskRunner, Task
import numpy as np
from hyperclass.learn.manager import LearningModel, Cluster

class MahalLearningModel(LearningModel):

    def __init__(self, **kwargs ):
        LearningModel.__init__(self, "mahal",  **kwargs )
        self.norm = kwargs.get( 'norm', True )
        self._clusters: Dict[int,Cluster] = {}

    def cluster( self, cid: int ) -> Cluster:
        return self._clusters.setdefault( cid, Cluster(cid) )

    def learn_classification( self, data: xa.DataArray, labels: xa.DataArray, **kwargs  ):
        t1 = time.time()
        labels_mask = (labels > 0)
        filtered_labels: np.ndarray = labels.where(labels_mask, drop=True).values
        filtered_point_data: np.ndarray = data.where(labels_mask, drop=True).values
        print(f"Learning mapping with {filtered_labels.shape[0]} labels.")
        self.distances = self.fit( filtered_point_data, filtered_labels, **kwargs )

    def apply_classification( self, data: xa.DataArray, **kwargs ):
        prediction: np.ndarray = self.predict( data.values, **kwargs )
        return xa.DataArray( prediction, dims=['samples'], coords=dict( samples=data.coords['samples'] ) )

    def fit( self, X: np.ndarray, y: np.ndarray, **kwargs ) -> Optional[np.ndarray]:
        t0 = time.time()
        if np.count_nonzero( y > 0 ) == 0:
            Task.taskNotAvailable( "Workflow violation", "Must spread some labels before learning the classification", **kwargs )
            return None
        print(f"Running Mahal fit, X shape: {X.shape}), y shape: {y.shape})")
        for iS in range(y.size):
            self.cluster(y[iS]).addMember( X[iS] )

        distances = np.zeros( [ X.shape[0], len(self._clusters) ], dtype=np.float32 )
        for cid, cluster in self._clusters.items():
            for isample in range(X.shape[0]):
                distances[isample][cid] = distance.mahalanobis( X[isample], cluster.mean, VI=scipy.linalg.pinv(cluster.cov))

        return distances



    def predict( self, X: np.ndarray, **kwargs ) -> np.ndarray:
        print(f"Running SVC predict, X shape: {X.shape})")
        return self.svc.predict( X ).astype( int )

    @property
    def decision_function(self) -> Callable:
        return self.svc.decision_function

mahalLearningModel = MahalLearningModel()


