from spectral import *
from spectral.image import ImageArray
from spectral.algorithms.algorithms import TrainingClassSet
import numpy as np

image_file = "ang20170720t004130_corr_v2p9.1292-1208_1-1.tif"
img: ImageArray = open_image(image_file).load()


tset: TrainingClassSet = create_training_classes( )
view = imshow(img, (29, 19, 9))

# (m, c) = kmeans(img, 20, 30)
#
# view: ImageView = imshow(classes=m)
# view.show_classes()
#
# gmlc = GaussianClassifier(classes)