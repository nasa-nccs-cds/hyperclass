from typing import List, Union, Dict, Callable, Tuple, Optional
from hyperclass.data.manager import dataManager
from hyperclass.gui.labels import labelsManager, Marker
from scipy.spatial import distance
from typing import List, Tuple, Optional, Dict
from hyperclass.gui.tasks import taskRunner, Task
import numpy as np
from functools import partial
from hyperclass.learn.manager import LearningModel, Cluster

class ClusterLearningModel(LearningModel):

    def __init__(self, **kwargs ):
        LearningModel.__init__(self, "cluster",  **kwargs )
        self.metric = None
        self.method = None
        self.norm = kwargs.get( 'norm', True )
        self._clusters: Dict[int,Cluster] = {}

    def cluster( self, cid: int ) -> Cluster:
        return self._clusters.setdefault( cid, Cluster(cid) )

    def distance( self, x: np.ndarray, cluster: Cluster ):
        if self.metric == "mahal":    return self.apply_distance( x, cluster, distance.mahalanobis, cluster.icov )
        elif self.metric == "euclid": return self.apply_distance( x, cluster, distance.euclidean )
        else: return None

    def apply_distance(self, x: np.ndarray, cluster: Cluster, metricFn: Callable, *args ):
        if self.method == "nearest":
            distances: np.ndarray = np.apply_along_axis( partial( metricFn, x ), 1, cluster.members, *args )
            return distances.min()
        else:
            return  metricFn( x, cluster.mean, *args )

    def fit( self, X: np.ndarray, y: np.ndarray, **kwargs ):
        self.metric = dataManager.config.value("dev/distance/metric")
        self.method = dataManager.config.value("dev/distance/method")
        print(f"Fitting model, X shape: {X.shape}), y shape: {y.shape}), metric = {self.metric}, method = {self.method}")
        for iS in range(y.size):
            self.cluster(y[iS]).addMember( X[iS] )

    def predict( self, X: np.ndarray, **kwargs ) -> np.ndarray:
        assert self.metric is not None, "Must learn a mapping before you can apply it"
        distances = np.full( [ labelsManager.nLabels, X.shape[0] ], np.inf, dtype=np.float32 )
        for cid, cluster in self._clusters.items():
            distances[cid] = np.apply_along_axis( self.distance, 1, X, cluster )
        prediction = distances.argmin(axis=0)
        return prediction

clusterLearningModel = ClusterLearningModel()


