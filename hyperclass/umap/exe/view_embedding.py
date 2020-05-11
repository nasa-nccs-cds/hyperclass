from typing import List, Union, Tuple, Optional
from hyperclass.plot.points import datashade_points, point_cloud_3d, point_cloud_vtk
import os, math, pickle

mapper_file_path = "/usr/local/web/ILAB/data/results/umap/umap.ang20170720t004130_corr_v2p9.ss-5_ti-1-1_ts-1000-1000_md-0.01_nc-3_nn-10_b-0-0.pkl"
mapper = pickle.load( open( mapper_file_path, "rb" ) )
model_data = mapper.embedding_
point_cloud_vtk(model_data)