from typing import List, Union, Dict, Callable, Tuple, Optional
from hyperclass.data.manager import dataManager
from hyperclass.gui.labels import labelsManager, Marker
from scipy.spatial import distance
from typing import List, Tuple, Optional, Dict
from hyperclass.gui.tasks import taskRunner, Task
import numpy as np
from functools import partial
from hyperclass.learn.manager import LearningModel, Cluster

class GraphLearningModel(LearningModel):

    def __init__(self, **kwargs ):
        LearningModel.__init__(self, "graph",  **kwargs )

    def fit( self, X: np.ndarray, y: np.ndarray, **kwargs ):
        labelsManager.spread( "neighbors", 100 )
        print(f"Fitting model, X shape: {X.shape}), y shape: {y.shape})")

    def predict( self, X: np.ndarray, **kwargs ) -> np.ndarray:
        return labelsManager.classification

graphLearningModel = GraphLearningModel()


