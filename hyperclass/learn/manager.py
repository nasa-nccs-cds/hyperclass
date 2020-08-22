import xarray as xa
import time, traceback, abc
import numpy as np
import scipy

from hyperclass.gui.dialog import DialogBase
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from hyperclass.gui.events import EventClient, EventMode
from typing import List, Tuple, Optional, Dict
from hyperclass.gui.tasks import taskRunner, Task

class Cluster:

    def __init__(self, cid, **kwargs):
        self.cid = cid
        self._members = []
        self.metrics = {}

    def addMember(self, example: np.ndarray ):
        self._members.append( example )
        self.metrics = {}

    @property
    def members(self) -> np.ndarray:
        return np.vstack(self._members)

    @property
    def mean(self):
        if "mean" not in self.metrics.keys():
            self.metrics["mean"] = self.members.mean(0)
        return self.metrics["mean"]

    @property
    def std(self):
        if "std" not in self.metrics.keys():
            self.metrics["std"] = self.members.std(0)
        return self.metrics["std"]

    @property
    def cov(self):
        if "cov" not in self.metrics.keys():
            self.metrics["cov"] = np.cov( self.members.transpose() )
        return self.metrics["cov"]

    @property
    def cor(self):
        if "cor" not in self.metrics.keys():
            self.metrics["cor"] = np.corrcoef( self.members.transpose() )
        return self.metrics["cor"]

    @property
    def icov(self):
        if "icov" not in self.metrics.keys():
            self.metrics["icov"] = scipy.linalg.pinv(self.cov)
        return self.metrics["icov"]

    @property
    def icor(self):
        if "icor" not in self.metrics.keys():
            self.metrics["icor"] = scipy.linalg.pinv(self.cor)
        return self.metrics["icor"]

class LearningManager(QObject,EventClient):

    def __init__(self,  **kwargs ):
        QObject.__init__(self)
        self._models: Dict[str,LearningModel] = {}

    @property
    def mids(self):
        return [ m.mid for m in self._models.values() ]

    def addModel(self, mid: str, model: "LearningModel" ):
        self._models[ mid ] = model

    def activate(self):
        self.activate_event_listening()

    def config_gui(self, base: DialogBase):
        mids = self.mids
        model = base.createComboSelector( "Model: ", mids, "dev/model", "cluster" )
        distanceMetric = base.createComboSelector("Distance.Metric: ", ["mahal","euclid"], "dev/distance/metric", "mahal")
        distanceMethod = base.createComboSelector("Distance.Method: ", ["centroid","nearest"], "dev/distance/method", "centroid")
        return base.createGroupBox("dev", [model, distanceMetric, distanceMethod ] )

    @property
    def model(self) -> "LearningModel":
        from hyperclass.data.manager import dataManager
        mid = dataManager.config.value("dev/model")
        model: LearningModel = self._models[ mid ]
        return model

    def learn_classification( self, block, labels: xa.DataArray, **kwargs  ):
        from hyperclass.data.manager import dataManager
        from hyperclass.umap.manager import umapManager
        embed = kwargs.get( 'embed', False )
        ndim = kwargs.get( 'ndim', dataManager.config.value("svm/ndim") )
        nepochs = kwargs.pop('nepochs', int( dataManager.config.value("umap/nepochs") ) )
        args = dict( nepochs = nepochs, **kwargs )
        try:
            embedding, labels = umapManager.supervised( block, labels, ndim, **args ) if embed else block.getPointData( **kwargs ), labels
            if embedding is not None:
                self.model.learn_classification( embedding, labels, **kwargs  )
        except Exception as err:
            Task.showErrorMessage( f"learn_classification error: {err}")
            traceback.print_exc( 50 )

    def apply_classification( self, block, **kwargs ):
        from hyperclass.umap.manager import umapManager
        embed = kwargs.get('embed', False)
        sample_labels = None
        try:
            embedding: Optional[xa.DataArray] = umapManager.apply( block, **kwargs ) if embed else block.getPointData( **kwargs )
            if embedding is not None:
                sample_labels = self.model.apply_classification( embedding, **kwargs  )
                umapManager.set_point_colors(labels=sample_labels, **kwargs)
        except Exception as err:
            Task.showErrorMessage( f"learn_classification error: {err}")
            traceback.print_exc( 50 )
        return sample_labels

    def processEvent( self, event: Dict ):
        super().processEvent(event)
        if self.event_match( event, 'classify', "learn" ):
            block = event.get('data',None)
            labels1: xa.DataArray = event.get('labels',None)
            if (block is not None) and (labels1 is not None):
                self.learn_classification( block, labels1  )
        elif self.event_match(event, 'classify', "apply" ):
            block = event.get('data')
            if (block is not None):
                sample_labels = self.apply_classification( block )
                event = dict( event='plot', type='classification', labels=sample_labels )
                self.submitEvent( event, EventMode.Gui )

class LearningModel:
    __metaclass__ = abc.ABCMeta

    def __init__(self, name: str,  **kwargs ):
        self.mid =  name
        self._score: Optional[np.ndarray] = None
        self.config = kwargs
        self._keys = []
        learningManager.addModel( name, self )

    def setKeys(self, keys: List[str] ):
        self._keys = keys

    @property
    def score(self) -> Optional[np.ndarray]:
        return self._score

    def learn_classification( self, data: xa.DataArray, labels: xa.DataArray, **kwargs  ):
        t1 = time.time()
        labels_mask = (labels > 0)
        filtered_labels: np.ndarray = labels.where(labels_mask, drop=True).astype(np.int32).values
        filtered_point_data: np.ndarray = data.where(labels_mask, drop=True).values
        if np.count_nonzero( filtered_labels > 0 ) == 0:
            Task.taskNotAvailable( "Workflow violation", "Must label some points before learning the classification", **kwargs )
            return None
        self.fit( filtered_point_data, filtered_labels, **kwargs )
        print(f"Learned mapping with {filtered_labels.shape[0]} labels in {time.time()-t1} sec.")

    @abc.abstractmethod
    def fit(self, data: np.ndarray, labels: np.ndarray, **kwargs):
        raise Exception( "abstract method LearningModel.fit called")

    def apply_classification( self, data: xa.DataArray, **kwargs ):
        t1 = time.time()
        prediction: np.ndarray = self.predict( data.values, **kwargs )
        print(f"Applied classication with input shape {data.shape[0]} in {time.time() - t1} sec.")
        return xa.DataArray( prediction, dims=['samples'], coords=dict( samples=data.coords['samples'] ) )

    @abc.abstractmethod
    def predict( self, data: np.ndarray, **kwargs ):
        raise Exception( "abstract method LearningModel.predict called")

learningManager = LearningManager()

