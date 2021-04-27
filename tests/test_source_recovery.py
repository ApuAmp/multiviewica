# Authors: Hugo Richard, Pierre Ablin
# License: BSD 3 clause

import pytest
import numpy as np
from multiviewica import _hungarian, permica, groupica, multiviewica


def normalize(A):
    A_ = A - np.mean(A, axis=1, keepdims=True)
    A_ = A_ / np.linalg.norm(A_, axis=1, keepdims=True)
    return A_


def amari_d(W, A):
    P = np.dot(W, A)

    def s(r):
        return np.sum(np.sum(r ** 2, axis=1) / np.max(r ** 2, axis=1) - 1)

    return (s(np.abs(P)) + s(np.abs(P.T))) / (2 * P.shape[0])


def error(M):
    order, _ = _hungarian(M)
    return 1 - M[np.arange(M.shape[0]), order]


@pytest.mark.parametrize(
    ("algo, init"),
    [
        (permica, None),
        (groupica, None),
        (multiviewica, "permica"),
        (multiviewica, "groupica"),
    ],
)
@pytest.mark.parametrize("dimension_reduction", ["pca", "srm"])
def test_ica(algo, dimension_reduction, init):
    # Test that all algo can recover the sources
    sigma = 1e-4
    n, v, p, t = 3, 10, 5, 1000
    # Generate signals
    rng = np.random.RandomState(0)
    S_true = rng.laplace(size=(p, t))
    S_true = normalize(S_true)
    A_list = rng.randn(n, v, p)
    noises = rng.randn(n, v, t)
    X = np.array([A.dot(S_true) for A in A_list])
    X += [sigma * N for A, N in zip(A_list, noises)]
    # Run ICA
    if init is None:
        K, W, S = algo(
            X,
            n_components=5,
            dimension_reduction=dimension_reduction,
            tol=1e-5,
        )
    else:
        K, W, S = algo(
            X,
            n_components=5,
            dimension_reduction=dimension_reduction,
            tol=1e-5,
            init=init,
        )
    dist = np.mean([amari_d(W[i].dot(K[i]), A_list[i]) for i in range(n)])
    S = normalize(S)
    err = np.mean(error(np.abs(S.dot(S_true.T))))
    assert dist < 0.01
    assert err < 0.01


def test_supergaussian():
    # Test with super Gaussian data
    # should only work when density in the model is super-Gaussian
    rng = np.random.RandomState()
    sigmas = rng.randn(3) * 0.01
    n, p, t = 5, 3, 1000
    S_true = rng.laplace(size=(p, t))
    S_true = normalize(S_true)
    A_list = rng.randn(n, p, p)
    noises = rng.randn(n, p, t)
    X = np.array([A.dot(S_true) for A in A_list])
    X += [A.dot(sigmas.reshape(-1, 1) * N) for A, N in zip(A_list, noises)]
    W_init = rng.randn(n, p, p)
    dist = np.mean([amari_d(W_init[i], A_list[i]) for i in range(n)])
    print(dist)

    for fun in ["quartic", "logcosh", "abs"]:
        K, W, S = multiviewica(X, init=W_init, fun=fun)
        dist = np.mean([amari_d(W[i], A_list[i]) for i in range(n)])
        S = normalize(S)
        err = np.mean(error(np.abs(S.dot(S_true.T))))
        print(fun, err, dist)
        if fun == "quartic":
            assert dist > 0.3
            assert err > 0.2
        else:
            assert dist < 0.3
            assert err < 0.1


def test_subgaussian():
    # Test with sub Gaussian data
    # should only work when density in the model is sub-Gaussian
    rng = np.random.RandomState(0)
    sigmas = rng.randn(4) * 0.01
    n, p, t = 5, 4, 1000
    S_true = rng.uniform(low=-np.sqrt(3), high=+np.sqrt(3), size=(p, t))
    S_true = np.random.randn(p, t)
    S_true = np.sign(S_true) * np.abs(S_true) ** 1
    S_true = normalize(S_true)
    A_list = rng.randn(n, p, p)
    noises = rng.randn(n, p, t)
    X = np.array([A.dot(S_true) for A in A_list])
    X += [A.dot(sigmas.reshape(-1, 1) * N) for A, N in zip(A_list, noises)]
    W_init = rng.randn(n, p, p)
    dist = np.mean([amari_d(W_init[i], A_list[i]) for i in range(n)])
    print(dist)

    for fun in ["quartic", "logcosh", "abs"]:
        K, W, S = multiviewica(X, init=W_init, fun=fun)
        dist = np.mean([amari_d(W[i], A_list[i]) for i in range(n)])
        S = normalize(S)
        err = np.mean(error(np.abs(S.dot(S_true.T))))
        print(fun, err, dist)
        # if fun == "quartic":
        #     assert dist < 0.3
        #     assert err < 0.1
        # else:
        #     assert dist > 0.3
        #     assert err > 0.2


def test_gaussian():
    # Test with super Gaussian data:
    # should only work when density in the model is super-Gaussian
    rng = np.random.RandomState(0)
    sigma = 1e-2
    n, p, t = 5, 3, 1000
    S_true = rng.randn(p, t)
    # S_true = normalize(S_true)
    A_list = rng.randn(n, p, p)
    noises = rng.randn(n, p, t)
    sigmas = rng.randn(p)
    X = np.array(
        [
            A.dot(S_true + sigma * sigmas.reshape(-1, 1) * N)
            for A, N in zip(A_list, noises)
        ]
    )
    K, W_init, S = groupica(X)

    for fun in ["quartic", "logcosh", "abs", "groupica"]:
        if fun == "groupica":
            K, W, S = groupica(X)
        else:
            K, W, S = multiviewica(X, init=W_init, fun=fun)
        dist = np.mean([amari_d(W[i], A_list[i]) for i in range(n)])
        S = normalize(S)
        S_true = normalize(S_true)
        err = np.mean(error(np.abs(S.dot(S_true.T))))
        print(dist, err, fun)
