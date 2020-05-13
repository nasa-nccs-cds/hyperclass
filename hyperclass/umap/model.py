import umap, time, pickle, os, math, locale
from typing import List, Union, Tuple, Optional, Dict
from warnings import warn
from scipy.optimize import curve_fit
from sklearn.utils import check_random_state, check_array
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import normalize
from sklearn.neighbors import KDTree
import numpy as np
import scipy.sparse
import scipy.sparse.csgraph
import numba
import umap.distances as dist
import umap.sparse as sparse
from umap.utils import ts, csr_unique
from umap.spectral import spectral_layout
from umap.layouts import optimize_layout_euclidean, optimize_layout_generic
from pynndescent import NNDescent
from pynndescent.distances import named_distances as pynn_named_distances
from pynndescent.sparse import sparse_named_distances as pynn_sparse_named_distances

locale.setlocale(locale.LC_NUMERIC, "C")
INT32_MIN = np.iinfo(np.int32).min + 1
INT32_MAX = np.iinfo(np.int32).max - 1
SMOOTH_K_TOLERANCE = 1e-5
MIN_K_DIST_SCALE = 1e-3
NPY_INFINITY = np.inf



def nearest_neighbors(
        X,
        n_neighbors,
        metric,
        metric_kwds,
        random_state,
        low_memory=False,
        verbose=False,
):
    """Compute the ``n_neighbors`` nearest points for each data point in ``X``
    under ``metric``. This may be exact, but more likely is approximated via
    nearest neighbor descent.

    Parameters
    ----------
    X: array of shape (n_samples, n_features)
        The input data to compute the k-neighbor graph of.

    n_neighbors: int
        The number of nearest neighbors to compute for each sample in ``X``.

    metric: string or callable
        The metric to use for the computation.

    metric_kwds: dict
        Any arguments to pass to the metric computation function.

    random_state: np.random state
        The random state to use for approximate NN computations.

    low_memory: bool (optional, default False)
        Whether to pursue lower memory NNdescent.

    verbose: bool (optional, default False)
        Whether to print status data during the computation.

    Returns
    -------
    knn_indices: array of shape (n_samples, n_neighbors)
        The indices on the ``n_neighbors`` closest points in the dataset.

    knn_dists: array of shape (n_samples, n_neighbors)
        The distances to the ``n_neighbors`` closest points in the dataset.

    rp_forest: list of trees
        The random projection forest used for searching (if used, None otherwise)
    """


    n_trees = 5 + int(round((X.shape[0]) ** 0.5 / 20.0))
    n_iters = max(5, int(round(np.log2(X.shape[0]))))

    nnd = NNDescent(
        X,
        n_neighbors=n_neighbors,
        metric=metric,
        metric_kwds=metric_kwds,
        random_state=random_state,
        n_trees=n_trees,
        n_iters=n_iters,
        max_candidates=60,
        low_memory=low_memory,
        verbose=verbose,
    )
    knn_indices, knn_dists = nnd.neighbor_graph
    rp_forest = nnd

    return knn_indices, knn_dists, rp_forest

def compute_membership_strengths(  knn_indices, knn_dists, sigmas, rhos):
    """Construct the membership strength data for the 1-skeleton of each local
    fuzzy simplicial set -- this is formed as a sparse matrix where each row is
    a local fuzzy simplicial set, with a membership strength for the
    1-simplex to each other data point.

    Parameters
    ----------
    knn_indices: array of shape (n_samples, n_neighbors)
        The indices on the ``n_neighbors`` closest points in the dataset.

    knn_dists: array of shape (n_samples, n_neighbors)
        The distances to the ``n_neighbors`` closest points in the dataset.

    sigmas: array of shape(n_samples)
        The normalization factor derived from the metric tensor approximation.

    rhos: array of shape(n_samples)
        The local connectivity adjustment.

    Returns
    -------
    rows: array of shape (n_samples * n_neighbors)
        Row data for the resulting sparse matrix (coo format)

    cols: array of shape (n_samples * n_neighbors)
        Column data for the resulting sparse matrix (coo format)

    vals: array of shape (n_samples * n_neighbors)
        Entries for the resulting sparse matrix (coo format)
    """
    n_samples = knn_indices.shape[0]
    n_neighbors = knn_indices.shape[1]

    rows = np.zeros(knn_indices.size, dtype=np.int32)
    cols = np.zeros(knn_indices.size, dtype=np.int32)
    vals = np.zeros(knn_indices.size, dtype=np.float32)

    for i in range(n_samples):
        for j in range(n_neighbors):
            if knn_indices[i, j] == -1:
                continue  # We didn't get the full knn for i
            if knn_indices[i, j] == i:
                val = 0.0
            elif knn_dists[i, j] - rhos[i] <= 0.0 or sigmas[i] == 0.0:
                val = 1.0
            else:
                val = np.exp(-((knn_dists[i, j] - rhos[i]) / (sigmas[i])))

            rows[i * n_neighbors + j] = i
            cols[i * n_neighbors + j] = knn_indices[i, j]
            vals[i * n_neighbors + j] = val

    return rows, cols, vals

@numba.njit(
    locals={
        "psum": numba.types.float32,
        "lo": numba.types.float32,
        "mid": numba.types.float32,
        "hi": numba.types.float32,
    },
    fastmath=True,
)  # benchmarking `parallel=True` shows it to *decrease* performance
def smooth_knn_dist( distances, k, n_iter=64, local_connectivity=1.0, bandwidth=1.0):
    """Compute a continuous version of the distance to the kth nearest
    neighbor. That is, this is similar to knn-distance but allows continuous
    k values rather than requiring an integral k. In essence we are simply
    computing the distance such that the cardinality of fuzzy set we generate
    is k.

    Parameters
    ----------
    distances: array of shape (n_samples, n_neighbors)
        Distances to nearest neighbors for each samples. Each row should be a
        sorted list of distances to a given samples nearest neighbors.

    k: float
        The number of nearest neighbors to approximate for.

    n_iter: int (optional, default 64)
        We need to binary search for the correct distance value. This is the
        max number of iterations to use in such a search.

    local_connectivity: int (optional, default 1)
        The local connectivity required -- i.e. the number of nearest
        neighbors that should be assumed to be connected at a local level.
        The higher this value the more connected the manifold becomes
        locally. In practice this should be not more than the local intrinsic
        dimension of the manifold.

    bandwidth: float (optional, default 1)
        The target bandwidth of the kernel, larger values will produce
        larger return values.

    Returns
    -------
    knn_dist: array of shape (n_samples,)
        The distance to kth nearest neighbor, as suitably approximated.

    nn_dist: array of shape (n_samples,)
        The distance to the 1st nearest neighbor for each point.
    """
    target = np.log2(k) * bandwidth
    rho = np.zeros(distances.shape[0], dtype=np.float32)
    result = np.zeros(distances.shape[0], dtype=np.float32)

    mean_distances = np.mean(distances)

    for i in range(distances.shape[0]):
        lo = 0.0
        hi = NPY_INFINITY
        mid = 1.0

        # TODO: This is very inefficient, but will do for now. FIXME
        ith_distances = distances[i]
        non_zero_dists = ith_distances[ith_distances > 0.0]
        if non_zero_dists.shape[0] >= local_connectivity:
            index = int(np.floor(local_connectivity))
            interpolation = local_connectivity - index
            if index > 0:
                rho[i] = non_zero_dists[index - 1]
                if interpolation > SMOOTH_K_TOLERANCE:
                    rho[i] += interpolation * (
                            non_zero_dists[index] - non_zero_dists[index - 1]
                    )
            else:
                rho[i] = interpolation * non_zero_dists[0]
        elif non_zero_dists.shape[0] > 0:
            rho[i] = np.max(non_zero_dists)

        for n in range(n_iter):

            psum = 0.0
            for j in range(1, distances.shape[1]):
                d = distances[i, j] - rho[i]
                if d > 0:
                    psum += np.exp(-(d / mid))
                else:
                    psum += 1.0

            if np.fabs(psum - target) < SMOOTH_K_TOLERANCE:
                break

            if psum > target:
                hi = mid
                mid = (lo + hi) / 2.0
            else:
                lo = mid
                if hi == NPY_INFINITY:
                    mid *= 2
                else:
                    mid = (lo + hi) / 2.0

        result[i] = mid

        # TODO: This is very inefficient, but will do for now. FIXME
        if rho[i] > 0.0:
            mean_ith_distances = np.mean(ith_distances)
            if result[i] < MIN_K_DIST_SCALE * mean_ith_distances:
                result[i] = MIN_K_DIST_SCALE * mean_ith_distances
        else:
            if result[i] < MIN_K_DIST_SCALE * mean_distances:
                result[i] = MIN_K_DIST_SCALE * mean_distances

    return result, rho

def fuzzy_simplicial_set(
        shape,
        n_neighbors,
        random_state,
        metric,
        metric_kwds={},
        knn_indices=None,
        knn_dists=None,
        angular=False,
        set_op_mix_ratio=1.0,
        local_connectivity=1.0,
        apply_set_operations=True,
        verbose=False,
):
    """Given a set of data X, a neighborhood size, and a measure of distance
    compute the fuzzy simplicial set (here represented as a fuzzy graph in
    the form of a sparse matrix) associated to the data. This is done by
    locally approximating geodesic distance at each point, creating a fuzzy
    simplicial set for each such point, and then combining all the local
    fuzzy simplicial sets into a global one via a fuzzy union.

    Parameters
    ----------
    shape: array shape (n_samples, n_features)
        The data to be modelled as a fuzzy simplicial set.

    n_neighbors: int
        The number of neighbors to use to approximate geodesic distance.
        Larger numbers induce more global estimates of the manifold that can
        miss finer detail, while smaller values will focus on fine manifold
        structure to the detriment of the larger picture.

    random_state: numpy RandomState or equivalent
        A state capable being used as a numpy random state.

    metric: string or function (optional, default 'euclidean')
        The metric to use to compute distances in high dimensional space.
        If a string is passed it must match a valid predefined metric. If
        a general metric is required a function that takes two 1d arrays and
        returns a float can be provided. For performance purposes it is
        required that this be a numba jit'd function. Valid string metrics
        include:
            * euclidean (or l2)
            * manhattan (or l1)
            * cityblock
            * braycurtis
            * canberra
            * chebyshev
            * correlation
            * cosine
            * dice
            * hamming
            * jaccard
            * kulsinski
            * ll_dirichlet
            * mahalanobis
            * matching
            * minkowski
            * rogerstanimoto
            * russellrao
            * seuclidean
            * sokalmichener
            * sokalsneath
            * sqeuclidean
            * yule
            * wminkowski

        Metrics that take arguments (such as minkowski, mahalanobis etc.)
        can have arguments passed via the metric_kwds dictionary. At this
        time care must be taken and dictionary elements must be ordered
        appropriately; this will hopefully be fixed in the future.

    metric_kwds: dict (optional, default {})
        Arguments to pass on to the metric, such as the ``p`` value for
        Minkowski distance.

    knn_indices: array of shape (n_samples, n_neighbors) (optional)
        If the k-nearest neighbors of each point has already been calculated
        you can pass them in here to save computation time. This should be
        an array with the indices of the k-nearest neighbors as a row for
        each data point.

    knn_dists: array of shape (n_samples, n_neighbors) (optional)
        If the k-nearest neighbors of each point has already been calculated
        you can pass them in here to save computation time. This should be
        an array with the distances of the k-nearest neighbors as a row for
        each data point.

    angular: bool (optional, default False)
        Whether to use angular/cosine distance for the random projection
        forest for seeding NN-descent to determine approximate nearest
        neighbors.

    set_op_mix_ratio: float (optional, default 1.0)
        Interpolate between (fuzzy) union and intersection as the set operation
        used to combine local fuzzy simplicial sets to obtain a global fuzzy
        simplicial sets. Both fuzzy set operations use the product t-norm.
        The value of this parameter should be between 0.0 and 1.0; a value of
        1.0 will use a pure fuzzy union, while 0.0 will use a pure fuzzy
        intersection.

    local_connectivity: int (optional, default 1)
        The local connectivity required -- i.e. the number of nearest
        neighbors that should be assumed to be connected at a local level.
        The higher this value the more connected the manifold becomes
        locally. In practice this should be not more than the local intrinsic
        dimension of the manifold.

    verbose: bool (optional, default False)
        Whether to report information on the current progress of the algorithm.

    Returns
    -------
    fuzzy_simplicial_set: coo_matrix
        A fuzzy simplicial set represented as a sparse matrix. The (i,
        j) entry of the matrix represents the membership strength of the
        1-simplex between the ith and jth sample points.
    """

    knn_dists = knn_dists.astype(np.float32)

    sigmas, rhos = smooth_knn_dist(
        knn_dists, float(n_neighbors), local_connectivity=float(local_connectivity),
    )

    rows, cols, vals = compute_membership_strengths(
        knn_indices, knn_dists, sigmas, rhos
    )

    result = scipy.sparse.coo_matrix(
        (vals, (rows, cols)), shape=( shape[0], shape[0] )
    )
    result.eliminate_zeros()

    if apply_set_operations:
        transpose = result.transpose()

        prod_matrix = result.multiply(transpose)

        result = (
                set_op_mix_ratio * (result + transpose - prod_matrix)
                + (1.0 - set_op_mix_ratio) * prod_matrix
        )

    result.eliminate_zeros()

    return result, sigmas, rhos

@numba.njit()
def fast_intersection( rows, cols, values, target, unknown_dist=1.0, far_dist=5.0):
    """Under the assumption of categorical distance for the intersecting
    simplicial set perform a fast intersection.

    Parameters
    ----------
    rows: array
        An array of the row of each non-zero in the sparse matrix
        representation.

    cols: array
        An array of the column of each non-zero in the sparse matrix
        representation.

    values: array
        An array of the value of each non-zero in the sparse matrix
        representation.

    target: array of shape (n_samples)
        The categorical labels to use in the intersection.

    unknown_dist: float (optional, default 1.0)
        The distance an unknown label (-1) is assumed to be from any point.

    far_dist float (optional, default 5.0)
        The distance between unmatched labels.

    Returns
    -------
    None
    """
    for nz in range(rows.shape[0]):
        i = rows[nz]
        j = cols[nz]
        if (target[i] == -1) or (target[j] == -1):
            values[nz] *= np.exp(-unknown_dist)
        elif target[i] != target[j]:
            values[nz] *= np.exp(-far_dist)

    return

@numba.jit()
def fast_metric_intersection(
        rows, cols, values, discrete_space, metric, metric_args, scale
):
    """Under the assumption of categorical distance for the intersecting
    simplicial set perform a fast intersection.

    Parameters
    ----------
    rows: array
        An array of the row of each non-zero in the sparse matrix
        representation.

    cols: array
        An array of the column of each non-zero in the sparse matrix
        representation.

    values: array of shape
        An array of the values of each non-zero in the sparse matrix
        representation.

    discrete_space: array of shape (n_samples, n_features)
        The vectors of categorical labels to use in the intersection.

    metric: numba function
        The function used to calculate distance over the target array.

    scale: float
        A scaling to apply to the metric.

    Returns
    -------
    None
    """
    for nz in range(rows.shape[0]):
        i = rows[nz]
        j = cols[nz]
        dist = metric(discrete_space[i], discrete_space[j], *metric_args)
        values[nz] *= np.exp(-(scale * dist))

    return

@numba.njit()
def reprocess_row( probabilities, k=15, n_iters=32):
    target = np.log2(k)

    lo = 0.0
    hi = NPY_INFINITY
    mid = 1.0

    for n in range(n_iters):

        psum = 0.0
        for j in range(probabilities.shape[0]):
            psum += pow(probabilities[j], mid)

        if np.fabs(psum - target) < SMOOTH_K_TOLERANCE:
            break

        if psum < target:
            hi = mid
            mid = (lo + hi) / 2.0
        else:
            lo = mid
            if hi == NPY_INFINITY:
                mid *= 2
            else:
                mid = (lo + hi) / 2.0

    return np.power(probabilities, mid)

@numba.njit()
def reset_local_metrics( simplicial_set_indptr, simplicial_set_data):
    for i in range(simplicial_set_indptr.shape[0] - 1):
        simplicial_set_data[
        simplicial_set_indptr[i]: simplicial_set_indptr[i + 1]
        ] = reprocess_row(
            simplicial_set_data[simplicial_set_indptr[i]: simplicial_set_indptr[i + 1]]
        )
    return

def reset_local_connectivity( simplicial_set, reset_local_metric=False):
    """Reset the local connectivity requirement -- each data sample should
    have complete confidence in at least one 1-simplex in the simplicial set.
    We can enforce this by locally rescaling confidences, and then remerging the
    different local simplicial sets together.

    Parameters
    ----------
    simplicial_set: sparse matrix
        The simplicial set for which to recalculate with respect to local
        connectivity.

    Returns
    -------
    simplicial_set: sparse_matrix
        The recalculated simplicial set, now with the local connectivity
        assumption restored.
    """
    simplicial_set = normalize(simplicial_set, norm="max")
    if reset_local_metric:
        simplicial_set = simplicial_set.tocsr()
        reset_local_metrics(simplicial_set.indptr, simplicial_set.data)
        simplicial_set = simplicial_set.tocoo()
    transpose = simplicial_set.transpose()
    prod_matrix = simplicial_set.multiply(transpose)
    simplicial_set = simplicial_set + transpose - prod_matrix
    simplicial_set.eliminate_zeros()

    return simplicial_set

def discrete_metric_simplicial_set_intersection(
        simplicial_set,
        discrete_space,
        unknown_dist=1.0,
        far_dist=5.0,
        metric=None,
        metric_kws={},
        metric_scale=1.0,
):
    """Combine a fuzzy simplicial set with another fuzzy simplicial set
    generated from discrete metric data using discrete distances. The target
    data is assumed to be categorical label data (a vector of labels),
    and this will update the fuzzy simplicial set to respect that label data.

    TODO: optional category cardinality based weighting of distance

    Parameters
    ----------
    simplicial_set: sparse matrix
        The input fuzzy simplicial set.

    discrete_space: array of shape (n_samples)
        The categorical labels to use in the intersection.

    unknown_dist: float (optional, default 1.0)
        The distance an unknown label (-1) is assumed to be from any point.

    far_dist: float (optional, default 5.0)
        The distance between unmatched labels.

    metric: str (optional, default None)
        If not None, then use this metric to determine the
        distance between values.

    metric_scale: float (optional, default 1.0)
        If using a custom metric scale the distance values by
        this value -- this controls the weighting of the
        intersection. Larger values weight more toward target.

    Returns
    -------
    simplicial_set: sparse matrix
        The resulting intersected fuzzy simplicial set.
    """
    simplicial_set = simplicial_set.tocoo()

    if metric is not None:
        # We presume target is now a 2d array, with each row being a
        # vector of target info
        if metric in dist.named_distances:
            metric_func = dist.named_distances[metric]
        else:
            raise ValueError("Discrete intersection metric is not recognized")

        fast_metric_intersection(
            simplicial_set.row,
            simplicial_set.col,
            simplicial_set.data,
            discrete_space,
            metric_func,
            tuple(metric_kws.values()),
            metric_scale,
        )
    else:
        fast_intersection(
            simplicial_set.row,
            simplicial_set.col,
            simplicial_set.data,
            discrete_space,
            unknown_dist,
            far_dist,
        )

    simplicial_set.eliminate_zeros()

    return reset_local_connectivity(simplicial_set)

def general_simplicial_set_intersection( simplicial_set1, simplicial_set2, weight):

    result = (simplicial_set1 + simplicial_set2).tocoo()
    left = simplicial_set1.tocsr()
    right = simplicial_set2.tocsr()

    sparse.general_sset_intersection(
        left.indptr,
        left.indices,
        left.data,
        right.indptr,
        right.indices,
        right.data,
        result.row,
        result.col,
        result.data,
        weight,
    )

    return result

def make_epochs_per_sample( weights, n_epochs):
    """Given a set of weights and number of epochs generate the number of
    epochs per sample for each weight.

    Parameters
    ----------
    weights: array of shape (n_1_simplices)
        The weights ofhow much we wish to sample each 1-simplex.

    n_epochs: int
        The total number of epochs we want to train for.

    Returns
    -------
    An array of number of epochs per sample, one for each 1-simplex.
    """
    result = -1.0 * np.ones(weights.shape[0], dtype=np.float64)
    n_samples = n_epochs * (weights / weights.max())
    result[n_samples > 0] = float(n_epochs) / n_samples[n_samples > 0]
    return result

def simplicial_set_embedding(
        data,
        graph,
        n_components,
        initial_alpha,
        a,
        b,
        gamma,
        negative_sample_rate,
        n_epochs,
        init,
        random_state,
        metric,
        metric_kwds,
        output_metric=dist.named_distances_with_gradients["euclidean"],
        output_metric_kwds={},
        euclidean_output=True,
        parallel=False,
        verbose=False,
):
    """Perform a fuzzy simplicial set embedding, using a specified
    initialisation method and then minimizing the fuzzy set cross entropy
    between the 1-skeletons of the high and low dimensional fuzzy simplicial
    sets.

    Parameters
    ----------
    data: array of shape (n_samples, n_features)
        The source data to be embedded by UMAP.

    graph: sparse matrix
        The 1-skeleton of the high dimensional fuzzy simplicial set as
        represented by a graph for which we require a sparse matrix for the
        (weighted) adjacency matrix.

    n_components: int
        The dimensionality of the euclidean space into which to embed the data.

    initial_alpha: float
        Initial learning rate for the SGD.

    a: float
        Parameter of differentiable approximation of right adjoint functor

    b: float
        Parameter of differentiable approximation of right adjoint functor

    gamma: float
        Weight to apply to negative samples.

    negative_sample_rate: int (optional, default 5)
        The number of negative samples to select per positive sample
        in the optimization process. Increasing this value will result
        in greater repulsive force being applied, greater optimization
        cost, but slightly more accuracy.

    n_epochs: int (optional, default 0)
        The number of training epochs to be used in optimizing the
        low dimensional embedding. Larger values result in more accurate
        embeddings. If 0 is specified a value will be selected based on
        the size of the input dataset (200 for large datasets, 500 for small).

    init: string
        How to initialize the low dimensional embedding. Options are:
            * 'spectral': use a spectral embedding of the fuzzy 1-skeleton
            * 'random': assign initial embedding positions at random.
            * A numpy array of initial embedding positions.

    random_state: numpy RandomState or equivalent
        A state capable being used as a numpy random state.

    metric: string or callable
        The metric used to measure distance in high dimensional space; used if
        multiple connected components need to be layed out.

    metric_kwds: dict
        Key word arguments to be passed to the metric function; used if
        multiple connected components need to be layed out.

    output_metric: function
        Function returning the distance between two points in embedding space and
        the gradient of the distance wrt the first argument.

    output_metric_kwds: dict
        Key word arguments to be passed to the output_metric function.

    euclidean_output: bool
        Whether to use the faster code specialised for euclidean output metrics

    parallel: bool (optional, default False)
        Whether to run the computation using numba parallel.
        Running in parallel is non-deterministic, and is not used
        if a random seed has been set, to ensure reproducibility.

    verbose: bool (optional, default False)
        Whether to report information on the current progress of the algorithm.

    Returns
    -------
    embedding: array of shape (n_samples, n_components)
        The optimized of ``graph`` into an ``n_components`` dimensional
        euclidean space.
    """
    graph = graph.tocoo()
    graph.sum_duplicates()
    n_vertices = graph.shape[1]

    if n_epochs <= 0:
        # For smaller datasets we can use more epochs
        if graph.shape[0] <= 10000:
            n_epochs = 500
        else:
            n_epochs = 200

    graph.data[graph.data < (graph.data.max() / float(n_epochs))] = 0.0
    graph.eliminate_zeros()

    if isinstance(init, str) and init == "random":
        embedding = random_state.uniform(
            low=-10.0, high=10.0, size=(graph.shape[0], n_components)
        ).astype(np.float32)
    elif isinstance(init, str) and init == "spectral":
        # We add a little noise to avoid local minima for optimization to come
        initialisation = spectral_layout(
            data,
            graph,
            n_components,
            random_state,
            metric=metric,
            metric_kwds=metric_kwds,
        )
        expansion = 10.0 / np.abs(initialisation).max()
        embedding = (initialisation * expansion).astype(
            np.float32
        ) + random_state.normal(
            scale=0.0001, size=[graph.shape[0], n_components]
        ).astype(
            np.float32
        )
    else:
        init_data = np.array(init)
        if len(init_data.shape) == 2:
            if np.unique(init_data, axis=0).shape[0] < init_data.shape[0]:
                tree = KDTree(init_data)
                dist, ind = tree.query(init_data, k=2)
                nndist = np.mean(dist[:, 1])
                embedding = init_data + random_state.normal(
                    scale=0.001 * nndist, size=init_data.shape
                ).astype(np.float32)
            else:
                embedding = init_data

    epochs_per_sample = make_epochs_per_sample(graph.data, n_epochs)

    head = graph.row
    tail = graph.col
    weight = graph.data

    rng_state = random_state.randint(INT32_MIN, INT32_MAX, 3).astype(np.int64)

    embedding = (
            10.0
            * (embedding - np.min(embedding, 0))
            / (np.max(embedding, 0) - np.min(embedding, 0))
    ).astype(np.float32, order="C")

    if euclidean_output:
        embedding = optimize_layout_euclidean(
            embedding,
            embedding,
            head,
            tail,
            n_epochs,
            n_vertices,
            epochs_per_sample,
            a,
            b,
            rng_state,
            gamma,
            initial_alpha,
            negative_sample_rate,
            parallel=parallel,
            verbose=verbose,
        )
    else:
        embedding = optimize_layout_generic(
            embedding,
            embedding,
            head,
            tail,
            n_epochs,
            n_vertices,
            epochs_per_sample,
            a,
            b,
            rng_state,
            gamma,
            initial_alpha,
            negative_sample_rate,
            output_metric,
            tuple(output_metric_kwds.values()),
            verbose=verbose,
        )

    return embedding

@numba.njit()
def init_transform( indices, weights, embedding):
    """Given indices and weights and an original embeddings
    initialize the positions of new points relative to the
    indices and weights (of their neighbors in the source data).

    Parameters
    ----------
    indices: array of shape (n_new_samples, n_neighbors)
        The indices of the neighbors of each new sample

    weights: array of shape (n_new_samples, n_neighbors)
        The membership strengths of associated 1-simplices
        for each of the new samples.

    embedding: array of shape (n_samples, dim)
        The original embedding of the source data.

    Returns
    -------
    new_embedding: array of shape (n_new_samples, dim)
        An initial embedding of the new sample points.
    """
    result = np.zeros((indices.shape[0], embedding.shape[1]), dtype=np.float32)

    for i in range(indices.shape[0]):
        for j in range(indices.shape[1]):
            for d in range(embedding.shape[1]):
                result[i, d] += weights[i, j] * embedding[indices[i, j], d]

    return result

def find_ab_params( spread, min_dist):
    """Fit a, b params for the differentiable curve used in lower
    dimensional fuzzy simplicial complex construction. We want the
    smooth curve (from a pre-defined family with simple gradient) that
    best matches an offset exponential decay.
    """

    def curve(x, a, b):
        return 1.0 / (1.0 + a * x ** (2 * b))

    xv = np.linspace(0, spread * 3, 300)
    yv = np.zeros(xv.shape)
    yv[xv < min_dist] = 1.0
    yv[xv >= min_dist] = np.exp(-(xv[xv >= min_dist] - min_dist) / spread)
    params, covar = curve_fit(curve, xv, yv)
    return params[0], params[1]

class Embedding(umap.UMAP):

    def build_model(self, shape: List[int], nnd: NNDescent, y: np.ndarray=None ):
        """Fit graph into an embedded space.

        Optionally use y for supervised dimension reduction.

        Parameters
        ----------

        y : array, shape (n_samples)
            A target array for supervised dimension reduction. How this is
            handled is determined by parameters UMAP was instantiated with.
            The relevant attributes are ``target_metric`` and
            ``target_metric_kwds``.
        """

        # Handle all the optional arguments, setting default
        if self.a is None or self.b is None:
            self._a, self._b = self.find_ab_params(self.spread, self.min_dist)
        else:
            self._a = self.a
            self._b = self.b

        if isinstance(self.init, np.ndarray):
            init = check_array(self.init, dtype=np.float32, accept_sparse=False)
        else:
            init = self.init

        self._initial_alpha = self.learning_rate

        self._validate_parameters()

        if self.verbose:
            print(str(self))

        # Check if we should unique the data
        # We've already ensured that we aren't in the precomputed case
        if self.unique:
            # check if the matrix is dense
            if self._sparse_data:
                # Call a sparse unique function
                index, inverse, counts = csr_unique(X)
            else:
                index, inverse, counts = np.unique(
                    X,
                    return_index=True,
                    return_inverse=True,
                    return_counts=True,
                    axis=0,
                )[1:4]
            if self.verbose:
                print(
                    "Unique=True -> Number of data points reduced from ",
                    X.shape[0],
                    " to ",
                    X[index].shape[0],
                )
                most_common = np.argmax(counts)
                print(
                    "Most common duplicate is",
                    index[most_common],
                    " with a count of ",
                    counts[most_common],
                )
        # If we aren't asking for unique use the full index.
        # This will save special cases later.
        else:
            index = list(range(X.shape[0]))
            inverse = list(range(X.shape[0]))

        # Error check n_neighbors based on data size
        if X[index].shape[0] <= self.n_neighbors:
            if X[index].shape[0] == 1:
                self.embedding_ = np.zeros(
                    (1, self.n_components)
                )  # needed to sklearn comparability
                return self

            warn(
                "n_neighbors is larger than the dataset size; truncating to "
                "X.shape[0] - 1"
            )
            self._n_neighbors = X[index].shape[0] - 1
        else:
            self._n_neighbors = self.n_neighbors

        # Note: unless it causes issues for setting 'index', could move this to
        # initial sparsity check above
        if self._sparse_data and not X.has_sorted_indices:
            X.sort_indices()

        random_state = check_random_state(self.random_state)

        if self.verbose:
            print("Construct fuzzy simplicial set")


        # Standard case
        self._small_data = False
        # pass string identifier if pynndescent also defines distance metric

        if self._sparse_data and self.metric in pynn_sparse_named_distances:
            nn_metric = self.metric
        elif not self._sparse_data and self.metric in pynn_named_distances:
            nn_metric = self.metric
        else:
            nn_metric = self._input_distance_func

        (self._knn_indices, self._knn_dists, self._rp_forest) = self.nearest_neighbors(
            X[index],
            self._n_neighbors,
            nn_metric,
            self._metric_kwds,
            self.angular_rp_forest,
            random_state,
            self.low_memory,
            use_pynndescent=True,
            verbose=self.verbose,
        )

        self.graph_, self._sigmas, self._rhos = self.fuzzy_simplicial_set(
            X[index],
            self.n_neighbors,
            random_state,
            nn_metric,
            self._metric_kwds,
            self._knn_indices,
            self._knn_dists,
            self.angular_rp_forest,
            self.set_op_mix_ratio,
            self.local_connectivity,
            True,
            self.verbose,
        )


        # Currently not checking if any duplicate points have differing labels
        # Might be worth throwing a warning...
        if y is not None:
            len_X = len(X) if not self._sparse_data else X.shape[0]
            if len_X != len(y):
                raise ValueError(
                    "Length of x = {len_x}, length of y = {len_y}, while it must be equal.".format(
                        len_x=len_X, len_y=len(y)
                    )
                )
            y_ = check_array(y, ensure_2d=False)[index]
            if self.target_metric == "categorical":
                if self.target_weight < 1.0:
                    far_dist = 2.5 * (1.0 / (1.0 - self.target_weight))
                else:
                    far_dist = 1.0e12
                self.graph_ = self.discrete_metric_simplicial_set_intersection(
                    self.graph_, y_, far_dist=far_dist
                )
            elif self.target_metric in dist.DISCRETE_METRICS:
                if self.target_weight < 1.0:
                    scale = 2.5 * (1.0 / (1.0 - self.target_weight))
                else:
                    scale = 1.0e12
                # self.graph_ = discrete_metric_simplicial_set_intersection(
                #     self.graph_,
                #     y_,
                #     metric=self.target_metric,
                #     metric_kws=self.target_metric_kwds,
                #     metric_scale=scale
                # )

                metric_kws = dist.get_discrete_params(y_, self.target_metric)

                self.graph_ = self.discrete_metric_simplicial_set_intersection(
                    self.graph_,
                    y_,
                    metric=self.target_metric,
                    metric_kws=metric_kws,
                    metric_scale=scale,
                )
            else:
                if len(y_.shape) == 1:
                    y_ = y_.reshape(-1, 1)
                if self.target_n_neighbors == -1:
                    target_n_neighbors = self._n_neighbors
                else:
                    target_n_neighbors = self.target_n_neighbors

                # Handle the small case as precomputed as before
                if y.shape[0] < 4096:
                    try:
                        ydmat = pairwise_distances(
                            y_, metric=self.target_metric, **self._target_metric_kwds
                        )
                    except (TypeError, ValueError):
                        ydmat = dist.pairwise_special_metric(
                            y_,
                            metric=self.target_metric,
                            kwds=self._target_metric_kwds,
                        )

                    target_graph, target_sigmas, target_rhos = self.fuzzy_simplicial_set(
                        ydmat,
                        target_n_neighbors,
                        random_state,
                        "precomputed",
                        self._target_metric_kwds,
                        None,
                        None,
                        False,
                        1.0,
                        1.0,
                        False,
                    )
                else:
                    # Standard case
                    target_graph, target_sigmas, target_rhos = self.fuzzy_simplicial_set(
                        y_,
                        target_n_neighbors,
                        random_state,
                        self.target_metric,
                        self._target_metric_kwds,
                        None,
                        None,
                        False,
                        1.0,
                        1.0,
                        False,
                    )
                # product = self.graph_.multiply(target_graph)
                # # self.graph_ = 0.99 * product + 0.01 * (self.graph_ +
                # #                                        target_graph -
                # #                                        product)
                # self.graph_ = product
                self.graph_ = self.general_simplicial_set_intersection(
                    self.graph_, target_graph, self.target_weight
                )
                self.graph_ = self.reset_local_connectivity(self.graph_)

        if self.n_epochs is None:
            n_epochs = 0
        else:
            n_epochs = self.n_epochs

        if self.verbose:
            print(ts(), "Construct embedding")

        self.embedding_ = self.simplicial_set_embedding(
            self._raw_data[index],  # JH why raw data?
            self.graph_,
            self.n_components,
            self._initial_alpha,
            self._a,
            self._b,
            self.repulsion_strength,
            self.negative_sample_rate,
            n_epochs,
            init,
            random_state,
            self._input_distance_func,
            self._metric_kwds,
            self._output_distance_func,
            self._output_metric_kwds,
            self.output_metric in ("euclidean", "l2"),
            self.random_state is None,
            self.verbose,
        )[inverse]

        if self.verbose:
            print(ts() + " Finished embedding")


        return self