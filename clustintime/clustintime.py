#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clustintime is a python3 library meant to apply clustering algorithms over spatio-temporal fMRI data

It supports ``.nii.gz`` files as well as ``.txt`` files.

It requires python 3.6 or above, as well as the modules:
    - `numpy`
    - `matplotlib`
    - `pandas`
"""


import clustintime.Clustering as clus

# Libraries
import numpy as np
import clustintime.Processing as proc
import clustintime.Visualization as vis
import sys
from nilearn.input_data import NiftiMasker
from nilearn.masking import apply_mask
from clustintime.cli.run_clime import _get_parser



def clustintime(
    data_file,
    mask_file,
    component = 'whole',
    timings_file = None,
    correlation = 'standard',
    processing=None,
    window_size=1,
    near=1,
    thr=95,
    contrast=1,
    TR=0.5,
    affinity = 'euclidean',
    linkage = 'ward',
    algorithm="infomap",
    thr_infomap=90,
    n_clusters=7,
    eps = 0.3,
    damping = 0.5,
    algorithm_dbscan = 'auto',
    save_maps=False,
    saving_dir=".",
    prefix="",
    seed=0,
    Dyn = False
):
    """
    Run main workflow of clustintime.

    Estimates the functional connectivity of the data, processes the data and performs the clustering analysis,
    It returns summary on screen as well as the graphs corresponding to the data, the processing and the results.


    Parameters
    ----------
    data_file : str or path
        Fullpath to the data to be analyzed.
    mask_file : str or path
        Fullpath to the corresponding mask.
    component : str, optional
        Desired component of the signal to analyze, the options are `whole`, `positive`, `negative`.
        The default is `whole`.
    timings_file : str or path, optional
        path to `.txt` files containing timings of the analyzed task.
        The default is `None`
    correlation : str, optional
        Desired type of correlation, the options are `standard`, `window`
        The default is `standard`
    processing : str, optional
        Desired type of processing, the options are `None`, `double`, `thr`, `RSS`, `window`.
        The default is `None`.
    window_size : int, optional
        Window size for the `window` correlation option.
        The default is 1.
    near : int, optional
        Nearby time-points to select when performing `RSS` processing.
        The default is 1.
    thr : int, optional
        Threshold percentile for the `thr` processing.
        The default is 95.
    contrast : float, optional
        Range of values for the correlation matrixes.
        The default is 1.
    TR : float, optional
        TR of the data.
        The default is 0.5.
    algorithm : str, optional
        Desired clustering algorithm for the analysis, the options are `infomap` and `KMeans`.
        The default is "infomap".
    thr_infomap : int, optional
        Threshold percentile to binarize the matrix in the infomap algorithm.
        The default is 90.
    n_clusters : int, optional
        Desired number of groups for the K Means algorithm.
        The default is 7.
    save_maps : bool, optional
        Boolean that indicates whether the results must be saved or not.
        The default is False.
    saving_dir : str or path, optional
        Fullpath to the saving directory.
        The default is ".".
    prefix: str, optional
        Prefix for the saved outcomes
    Dyn : bool, optional
        Generate a DyNeuSR graph. Default is `False`

    Returns
    -------
    None.

    """

    masker = NiftiMasker(mask_img=mask_file)
    masker.fit(data_file)

    print("Applying mask ...")
    print(" ")

    data = apply_mask(data_file, mask_file)  # apply mask to the fitted signal
    print("Mask applied!")
    
    if component == 'negative':
        data[data>0] = 0
    elif component == 'positive':
        data[data<0] = 0

    
    # Create data
    if timings_file != None:
        # Load timings
        # 1D files are a txt file with the times in which the events occur. They are divided by TR
        task = {}
        if type(timings_file) == str:
            timings_file = [timings_file]
        for i in range(len(timings_file)):
            task[i] = np.loadtxt(timings_file[i])

    else:
        task = []
    if correlation == 'standard':
        corr_map = np.nan_to_num(np.corrcoef(data))
    else:
         corr_map = np.nan_to_num(proc.correlation_with_window(data, window_size)  )
    
    nscans = corr_map.shape[0]
    indexes = range(corr_map.shape[0])

    if processing != None:
        corr_map, indexes = proc.preprocess(
            corr_map = corr_map,
            analysis = processing,
            near = near,
            thr = thr,
            contrast = contrast,
            task = task,
            TR = TR
        )

    if algorithm == "infomap":
        corr_map_2 = corr_map.copy()
        corr_map, labels = clus.Info_Map(
            corr_map,
            indexes,
            thr_infomap,
            nscans=nscans,
            task=task,
            TR=TR,
            saving_dir=saving_dir,
            prefix=prefix,
        )
        vis.plot_two_matrixes(
            corr_map_2, corr_map, "Original correlation map", "Binary correlation map",task = task,  saving_dir = saving_dir, prefix = f'{prefix}_orig_binary',TR= TR ,contrast = contrast
        )
    elif algorithm == "KMeans":
        labels = clus.K_Means(
            corr_map=corr_map,
            indexes=indexes,
            nscans=nscans,
            n_clusters=n_clusters,
            TR=TR,
            task=task,
            saving_dir=saving_dir,
            prefix=prefix,
            seed = seed
        )
    elif algorithm == 'Agglomerative':
        labels = clus.Agglomerative_Clustering(
            corr_map=corr_map,
            indexes=indexes,
            nscans=nscans,
            n_clusters=n_clusters,
            affinity = affinity,
            linkage = linkage,
            TR=TR,
            task=task,
            saving_dir=saving_dir,
            prefix=prefix
        )
    elif algorithm == 'Affinity':
        labels = clus.Affinity_Propagation(
            corr_map=corr_map,
            indexes=indexes,
            nscans=nscans,
            damping=damping,
            TR=TR,
            task=task,
            saving_dir=saving_dir,
            prefix=prefix
        )
    elif algorithm == 'Mean':
        labels = clus.Mean_Shift(
            corr_map=corr_map,
            indexes=indexes,
            nscans=nscans,
            TR=TR,
            task=task,
            saving_dir=saving_dir,
            prefix=prefix
        )
    elif algorithm == "Louvain":
        corr_map_2 = corr_map.copy()
        corr_map, labels = clus.Louvain(
            corr_map,
            indexes,
            thr_infomap,
            nscans=nscans,
            task=task,
            TR=TR,
            saving_dir=saving_dir,
            prefix=prefix,
        )
        vis.plot_two_matrixes(
            corr_map_2, corr_map, "Original correlation map", "Binary correlation map",task = task, saving_dir = saving_dir, prefix = f'{prefix}_orig_binary', TR= TR ,contrast = contrast
        )
    elif algorithm == "Greedy":
        corr_map_2 = corr_map.copy()
        corr_map, labels = clus.Louvain(
            corr_map,
            indexes,
            thr_infomap,
            nscans=nscans,
            task=task,
            TR=TR,
            saving_dir=saving_dir,
            prefix=prefix,
        )
        vis.plot_two_matrixes(
            corr_map_2, corr_map, "Original correlation map", "Binary correlation map",task = task,saving_dir = saving_dir, prefix = f'{prefix}_orig_binary',  TR= TR ,contrast = contrast
        )
    elif algorithm == 'DBSCAN':
        labels = clus.dbscan(
            corr_map=corr_map,
            indexes=indexes,
            nscans=nscans,
            eps=eps,
            metric = affinity,
            algorithm = algorithm_dbscan,
            TR=TR,
            task=task,
            saving_dir=saving_dir,
            prefix=prefix
        )
    elif algorithm == 'OPTICS':
        labels = clus.optics(
            corr_map=corr_map,
            indexes=indexes,
            nscans=nscans,
            algorithm = algorithm_dbscan,
            TR=TR,
            task=task,
            saving_dir=saving_dir,
            prefix=prefix
        )

    if save_maps:
        clus.generate_maps(labels, saving_dir, data, masker, prefix)
    
    if Dyn:
        vis.Dyn(corr_map, labels, output_file=f"{saving_dir}/dyneusr_{prefix}.html")

def _main(argv = None):
    print(sys.argv)
    options = _get_parser().parse_args(argv)
    clustintime(**vars(options))
    if __name__ == '__main__':
        _main(sys.argv[1:])