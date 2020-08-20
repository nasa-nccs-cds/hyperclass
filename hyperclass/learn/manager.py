import xarray as xa
import time, traceback, abc
import numpy as np
from hyperclass.gui.labels import labelsManager, Marker
from functools import partial
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from hyperclass.gui.events import EventClient, EventMode
from typing import List, Tuple, Optional, Dict
from hyperclass.data.manager import dataManager
from hyperclass.data.spatial.tile import Tile, Block
from hyperclass.gui.tasks import taskRunner, Task

MID = "mahal"

class Cluster:

    def __init__(self, cid, **kwargs):
        self.cid = cid
        self.members = []
        self.metrics = {}

    def addMember(self, example: np.ndarray ):
        self.members.append( example )
        self.metrics = {}

    @property
    def mean(self):
        if "mean" not in self.metrics.keys():
            hs = np.vstack( self.members )
            self.metrics["mean"] = hs.mean(0)
        return self.metrics["mean"]

    @property
    def std(self):
        if "std" not in self.metrics.keys():
            hs = np.vstack( self.members )
            self.metrics["std"] = hs.std(0)
        return self.metrics["std"]

    @property
    def cov(self):
        if "cov" not in self.metrics.keys():
            hs = np.vstack( self.members )
            self.metrics["cov"] = np.cov(hs)
        return self.metrics["cov"]

class LearningManager(QObject,EventClient):

    def __init__(self,  **kwargs ):
        QObject.__init__(self)
        self._models: Dict[str,LearningModel] = {}

    def addModel(self, mid: str, model: "LearningModel" ):
        self._models[ mid ] = model

    def activate(self):
        self.activate_event_listening()

    @property
    def model(self):
        return self._models[ MID ]

    def learn_classification( self, block: Block, labels: xa.DataArray, **kwargs  ):
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

    def apply_classification( self, block: Block, **kwargs ):
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
            block: Block = event.get('data',None)
            labels1: xa.DataArray = event.get('labels',None)
            if (block is not None) and (labels1 is not None):
                self.learn_classification( block, labels1  )
        elif self.event_match(event, 'classify', "apply" ):
            block: Block = event.get('data')
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
        learningManager.addModel( name, self )

    @property
    def score(self) -> Optional[np.ndarray]:
        return self._score

    @abc.abstractmethod
    def learn_classification( self, block: Block, labels: xa.DataArray, **kwargs  ):
        raise Exception( "abstract method LearningModel.learn_classification called")

    @abc.abstractmethod
    def apply_classification( self, block: Block, **kwargs ):
        raise Exception( "abstract method LearningModel.apply_classification called")

learningManager = LearningManager()

