from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.gui.dialog import DialogBase
from typing import List, Union, Tuple, Dict
from keras.layers import *
from keras.models import *
from keras.callbacks import *
import xarray as xa
import numpy as np

class ReductionManager(QObject,EventClient):

    def __init__( self, **kwargs ):
        QObject.__init__(self)

    def gui(self, base: DialogBase ):
        methodSelector = base.createComboSelector("Method: ", ["None", "Autoencoder"], "input.reduction/method", "Autoencoder" )
        nDimSelector = base.createComboSelector("#Dimensions: ", list(range(3, 50)), "input.reduction/ndim", 35)
        ssSelector = base.createComboSelector("Subsample: ", list(range(1, 100, 2)), "input.reduction/subsample", 1)
        return base.createGroupBox("reduction", [methodSelector, nDimSelector, ssSelector])

    def reduce(self, inputs: np.ndarray, reduction_method: str, ndim: int ) -> np.ndarray:
        if reduction_method.lower() == "autoencoder": return self.autoencoder( inputs, ndim )

    def xreduce(self, inputs: xa.DataArray, reduction_method: str, ndim: int ) -> xa.DataArray:
        if reduction_method.lower() == "autoencoder":
            encoded_data = self.autoencoder( inputs.values, ndim )
            coords = {inputs.dims[0]: inputs.coords[inputs.dims[0]], inputs.dims[1]: np.arange(ndim)}
            return xa.DataArray(encoded_data, dims=inputs.dims, coords=coords, attrs=inputs.attrs)
        return inputs

    def autoencoder( self, encoder_input: np.ndarray, ndim: int ) -> np.ndarray:
        input_dims = encoder_input.shape[1]
        inputlayer = Input( shape=[input_dims] )
        activation = 'tanh'
        encoded = None
        layer_dims, x = input_dims, inputlayer
        while layer_dims > ndim:
            x = Dense(layer_dims, activation=activation)(x)
            layer_dims = layer_dims // 2
        layer_dims = ndim
        while layer_dims < input_dims:
            x = Dense(layer_dims, activation=activation)(x)
            if encoded is None: encoded = x
            layer_dims = layer_dims * 2
        decoded = Dense( input_dims, activation='sigmoid' )(x)

#        modelcheckpoint = ModelCheckpoint('xray_auto.weights', monitor='loss', verbose=1, save_best_only=True, save_weights_only=True, mode='auto', period=1)
#        earlystopping = EarlyStopping(monitor='loss', min_delta=0., patience=100, verbose=1, mode='auto')
        autoencoder = Model(inputs=[inputlayer], outputs=[decoded])
        encoder = Model(inputs=[inputlayer], outputs=[encoded])
        autoencoder.compile(loss='mse', optimizer='rmsprop')

        autoencoder.fit( encoder_input, encoder_input, epochs=1, batch_size=256, shuffle=True )
        return  encoder.predict( encoder_input )

reductionManager = ReductionManager( )
