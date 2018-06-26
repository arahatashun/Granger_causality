#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Shun Arahata
"""
Code for demonstration
"""

import sys
sys.path.append('./granger_python')
sys.path.append('../pylearn-parsimony')
import numpy as np
import matplotlib.pyplot as plt
from lassoGranger import lasso_granger
import time
from run_ilasso import solve_loop, search_optimum_lambda
from ilasso import ilasso
from igrouplasso import igrouplasso
from graph_compare import f_score
from correlation import  calc_cor, calc_each_cor
import pickle

def gen_synth(N, T, sig):
    """generate simulation data

    :param N: number of time series (a multiple of 4)
    :param T: length of the time series
    :param sig: variance of the noise process
    :return(tuple): tuple containing:

        series: times series data
        A: Kronecker tensor product
    """
    assert N % 4 == 0, "N must be a multiple of 4"
    K = np.array(
        [[0.9, 0, 0, 0], [0, 0.9, 0, 0], [0, 0, 0.9, 0], [0, 0, 0, 0.9]])
    A = np.kron(np.eye(int(N / 4)), K)
    series = np.zeros((N, T))
    series[:, 0] = np.random.randn(N)
    for t in range(T - 1):
        series[:, t + 1] = A @ series[:, t] + sig * np.random.randn(N)

    return series, A


def gen_synth_lagged(N, T, sig):
    """generate Auto-Regressive model with longer effect

    :param N: number of time series (a multiple of 4)
    :param T: length of the time series
    :param sig: variance of the noise process
    :return:(tuple): tuple containing:

        series: times series data (feature,time) shape
        A: Kronecker tensor product
    """
    assert N % 4 == 0, "N must be a multiple of 4"
    assert T > 4, "T must be larger than 4"
    K1 = np.array(
        [[0.3, 0, 0, 0], [0, 0.3, 0, 0], [0, 0, 0.3, 0], [0, 0, 0, 0.3]])
    K2 = np.array(
        [[0.3, 0, 0, 0], [0, 0.3, 0, 0], [0, 0, 0.3, 0], [0, 0, 0, 0.3]])
    K3 = np.array(
        [[0.3, 0, 0, 0], [1, 0.3, 0, 0], [1, 0, 0.3, 0], [1, 0, 0, 0.3]])
    A1 = np.kron(np.eye(int(N / 4)), K1)
    A2 = np.kron(np.eye(int(N / 4)), K2)
    A3 = np.kron(np.eye(int(N / 4)), K3)
    series = np.zeros((N, T))
    series[:, 0] = np.random.randn(N)
    series[:, 1] = A1 @ series[:, 0] + sig * np.random.randn(N)
    series[:, 2] = A1 @ series[:, 1] \
                   + A2 @ series[:, 0] + sig * np.random.randn(N)
    for t in range(T - 3):
        series[:, t + 3] = A1 @ series[:, t + 2] + A2 @ series[:, t + 1] \
                           + A3 @ series[:, t] + sig * np.random.randn(N)
    return series, [A1, A2, A3]


def gen_list_iLasso(series, times):
    """ generate list for iLasso simulation
    and timestamp is defined here.

    :param series: generated by gen_synth_lagged
    :param times:
    :return:
    """
    num_of_features = series.shape[0]
    cell_array = []
    for i in range(num_of_features):
        selected = series[i, :]
        nan_index = np.isnan(selected)
        values = selected[~nan_index]
        time = times[~nan_index]
        cell = np.array([np.copy(values).T, np.copy(time).T])
        cell_array.append(cell)
        assert cell.shape[0] == 2, "cell dimension error"

    return cell_array


def inject_nan(series, ratio):
    """ replace some Numpy array with nan

    :param series: numpy array
    :param ratio: ratio of nan = 0~1
    :return:
    """
    B = np.copy(series)
    array_shape = B.shape
    c = int((B.ravel().shape[0] * ratio))
    B.ravel()[np.random.choice(B.ravel().shape[0], c, replace=False)] = np.nan
    B.reshape(array_shape)
    assert np.count_nonzero(np.isnan(B)) == c, "error c:" + str(
        c) + "nan:" + str(np.count_nonzero(~np.isnan(B)))
    return B


def main():
    # generate synthetic data set
    N = 20  # number of   print("tp",true_positive)
    T = 100  # length of time series
    sig = 0.2
    series, A = gen_synth(N, T, sig)
    # Run Lasso-Granger
    alpha = 1e-2
    L = 1  # only one lag for analysis
    cause = np.zeros((N, N))
    for i in range(N):
        index = [i] + list(range(i)) + list(range(i + 1, N))
        cause_tmp = lasso_granger(series[index, :], L, alpha)
        index = list(range(1, i + 1)) + [0] + list(range(i + 1, N))
        cause[i, :] = cause_tmp[index]

    # plot
    fig, axs = plt.subplots(1, 2)
    ax1 = axs[0]
    ax2 = axs[1]
    ax1.spy(A)
    ax1.set_title('Ground Truth')
    ax2.spy(cause, 0.4)
    ax2.set_title('Inferred Causality')
    plt.show()


def test_ilasso():
    N = 20
    T = 1000
    lag_len = 3
    sig = 0.1
    series, A_array = gen_synth_lagged(N, T, sig)
    # Run Lasso-Granger
    alpha = 1e-2
    series = inject_nan(series, 0.1)
    cell_array = gen_list_iLasso(series, np.arange(series.shape[1]))
    optimum_lamba = search_optimum_lambda(cell_array, 1e-1, 3)
    cause,*_= solve_loop(cell_array, optimum_lamba, lag_len, cv = False, group = False)
    fig, axs = plt.subplots(3, 2)
    for i in range(lag_len):
        ax1 = axs[i,0]
        ax2 = axs[i,1]
        ax1.spy(A_array[i])
        ax1.set_title('Ground Truth')
        ax2.matshow(cause[:, :, 2 - i], cmap=plt.cm.Blues)
        ax2.set_title('Inferred Causality')
    plt.show()


def comp_group():
    """compare group lasso and non group lasso"""
    N = 20
    T = 1000
    lag_len = 3
    sig = 0.1
    series, A_array = gen_synth_lagged(N, T, sig)
    # Run Lasso-Granger
    alpha = 1e-2
    alpha_group = 1e-1
    series = inject_nan(series, 0.1)
    cell_array = gen_list_iLasso(series, np.arange(series.shape[1]))
    cause,*_= solve_loop(cell_array, alpha, lag_len, cv = False, group = False)
    group_cause,*_ = solve_loop(cell_array, alpha_group, lag_len, cv = False, group = True)
    fig, axs = plt.subplots(lag_len, 3)
    for i in range(3):
        ax1 = axs[i,0]
        ax1.spy(A_array[i])
        ax1.set_title('Ground Truth')
    for i in range(lag_len):
        ax2 = axs[i,1]
        cause[:, :, lag_len -1 - i][cause[:, :, lag_len - 1 - i] > 0.1] = 1
        cause[:, :, lag_len -1 - i][cause[:, :, lag_len - 1 - i] < 1] = 0
        ax2.matshow(cause[:, :, lag_len - 1  - i], cmap=plt.cm.Blues)
        ax2.set_title('GLG Causality')
        ax3 = axs[i, 2]
        group_cause[:, :, lag_len - 1 - i][group_cause[:, :, lag_len - 1 - i] > 0.1] = 1
        group_cause[:, :, lag_len - 1 - i][group_cause[:, :, lag_len - 1 - i] < 1] = 0
        ax3.matshow(group_cause[:, :, lag_len - 1 - i], cmap=plt.cm.Blues)
        ax3.set_title('HGLG Causality')
    plt.show()

def comp_correlation():
    N = 4
    T = 1000
    sig = 0.01
    series, A_array = gen_synth(N, T, sig)
    normed = series - series.mean(axis=1, keepdims=True)/ series.std(axis=1, keepdims=True)
    cell_array = gen_list_iLasso(normed, np.arange(normed.shape[1]))
    calc_cor(cell_array)
    ans = np.corrcoef(series)
    print(ans)

if __name__ == '__main__':
    test_ilasso()