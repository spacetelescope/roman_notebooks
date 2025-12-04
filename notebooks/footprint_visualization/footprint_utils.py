import numpy as np
import matplotlib.pyplot as plt
import skyproj
import healsparse as hsp
import healpy as hp
from astropy.table import Table
import hpgeom as hpg
import pandas as pd
import pysiaf
from pysiaf.utils.rotations import attitude
rsiaf = pysiaf.Siaf('Roman')
wfi_cen = rsiaf['WFI_CEN']
sensors = [rsiaf[f'WFI{j:02d}_FULL'] for j in range(1, 19)]

def build_single_exp_map_ref(ra_ref, dec_ref, pa, v2, v3, nside_cov, nside_sparse, wgt=None, return_map=True):
    """
    Calculate the healpixels that cover a single exposure at a given pointing position.

    Params:
    -------
    ra_ref (float) : RA reference position for the pointing in degrees (typically the center of a segment).
    dec_ref (float) : Dec reference position for the pointing in degrees (typically the center of a segment).
    pa (float) : Position angle of the `WFI_CEN` aperture in degrees.
    v2 (float) : v2 angle (in arcsec) with respect to the reference position for `WFI_CEN`.
    v3 (float) : v3 angle (in arcsec) with respect to the reference position for `WFI_CEN`.
    nside_cov (int) : HEALPix Nside parameter for the coverage `healsparse` output map.
    nside_sparse (int) : HEALPix Nside parameter for the sparse `healsparse` output map.
    wgt (float) : Weight for the exposure (e.g., a useful case can be exposure time).
        If `None` the exposure will be given a weight of 1. 
    return_map (bool) : If `True` it will return a healsparse map object. If `False` it returns
        a list of HEALPix numbers at the nside_sparse resolution (with the NEST ordering).

    Returns:
    --------
    map_here (healsparse.HealSparseMap) : Healsparse map containing float64 data with nside_coverage = nside_cov, 
        and nside_sparse = nside_sparse (if return_map = True)

    or

    ipix_pass (list of ints) : List of HEALPix (with nside = nside_sparse) NEST pixels that are covered by the exposure. 
    """
    att_here = attitude(v2, v3, ra_ref, dec_ref, pa)
    ipix_pass = []
    for sensor in sensors:
        sensor.set_attitude_matrix(att_here)
        corners = sensor.corners('sky')
        pixels = hpg.query_polygon(nside_sparse,
                                   corners[0],
                                   corners[1],
                                   inclusive=True)
        ipix_pass.append(pixels)
    ipix_pass = np.unique(np.concatenate(ipix_pass).flatten())
    if return_map:
        map_here = hsp.HealSparseMap.make_empty(nside_coverage=nside_cov, nside_sparse=nside_sparse, dtype=np.float64)
        if wgt is None:
            map_here.update_values_pix(ipix_pass, 1.0)
        else:
            # Assuming the same weight for the full FOV
            map_here.update_values_pix(ipix_pass, 1.0*wgt)
        return map_here
    else:
        return ipix_pass


def build_single_exp_map_cen(ra_cen, dec_cen, pa, wgt, nside_cov=64, nside_sparse=4096*4):
    """
    Calculate the healpixels that cover a single exposure at a given pointing position.

    Params:
    -------
    ra_cen (float) : RA position for the `WFI_CEN` aperture (in degrees).
    dec_cen (float) : Dec position for the `WFI_CEN` aperture (in degrees).
    pa (float): Position angle for the `WFI_CEN` aperture (in degrees).
    wgt (float) : Weight for the exposure (e.g., a useful case can be exposure time).
    nside_cov (int) : HEALPix Nside parameter for the coverage `healsparse` output map.
    nside_sparse (int) : HEALPix Nside parameter for the sparse `healsparse` output map.

    Returns:
    --------
    map_in (healsparse.HealSparseMap) : Healsparse map containing float64 data with nside_coverage = nside_cov, 
        and nside_sparse = nside_sparse.
    """
    map_in=hsp.HealSparseMap.make_empty(nside_cov, nside_sparse, np.float64)
    att_here = attitude(0, 0, ra_cen, dec_cen, pa)
    ipix_pass = []
    for sensor in sensors:
        sensor.set_attitude_matrix(att_here)
        corners = sensor.corners('sky')
        pixels = hpg.query_polygon(nside_sparse,
                                   corners[0],
                                   corners[1],
                                   inclusive=True)
        map_in.update_values_pix(pixels, 1.0*wgt)
    return map_in

def build_single_exp_compact(inp, **kwargs):
    """
    Calculate the healpixels that cover a single exposure at a given pointing position.

    Params:
    -------
    inp (tuple) : Tuple containing
        ra_cen (float) : RA position for the `WFI_CEN` aperture (in degrees).
        dec_cen (float) : Dec position for the `WFI_CEN` aperture (in degrees).
        pa (float): Position angle for the `WFI_CEN` aperture (in degrees).
        wgt (float) : Weight for the exposure (e.g., a useful case can be exposure time).
    
    Returns:
    --------
    map_in (healsparse.HealSparseMap) : Healsparse map containing float64 data with nside_coverage = nside_cov, 
        and nside_sparse = nside_sparse.
    """
    ra_cen, dec_cen, pa, wgt = inp
    return build_single_exp_map_cen(ra_cen, dec_cen, pa, wgt, **kwargs)

def read_pointings_file(filename, reset_index=True):
    """
    Function to read an APT pointings file.

    Params:
    -------
    filename (str) : Path to pointings file
    reset_index (bool) : If `True` it resets the output DataFrames indices (useful for data-filtering). 
        If `False` it returns DataFrames with Step, Observation, Tile, Exposure; 
        and `Region`, `Index`, `ra_ref`, `dec_ref`, and `PA` as indices, respectively.

    Returns:
    --------
    df, df2 (tuple of pandas.DataFrame): DataFrames containing the description of Survey Steps 
        and Observations (df), and Region targets (df2).
    """
    
    names = 'Tile  Exposure            V2            V3  Dither_X  Dither_Y  Subpixel_X  Subpixel_Y       dDist        Tile_X        Tile_Y       Total_X       Total_Y'.split()          
    #print(names)
    df = pd.DataFrame(columns=['Step', 'Observation']+names)
    df = df.set_index(['Step','Observation','Tile','Exposure'])
    df2 = pd.DataFrame(columns=['Region', 'Index', 'RA', 'Dec', 'V2', 'V3', 'ra_ref', 'dec_ref', 'PA'])
    df2 = df2.set_index(['Region', 'Index', 'ra_ref', 'dec_ref', 'PA'])
    obs = None
    vis = None
    step = None
    reg = None
    ra_ref = None
    dec_ref = None
    pa = None
    with open(filename) as fp:
        for line in fp:
            if 'Survey Step' in line:
                step = int(line.split()[-1])
                #print('Survey Step', step)
            elif 'Observation' in line:
                obs = int(line.split()[-1])
                #print('Obs', obs)
            elif 'Region Target' in line:
                reg = line.split(':')[-1][1:]
                #print('Region', reg)
            elif 'Reference Position:' in line:
                ll = line.split(':')[-1][1:]
                ra_ref, dec_ref = ll.split(',')
                ra_ref = float(ra_ref)
                dec_ref = float(dec_ref)
            elif 'Planned Orient:' in line:
                ll = line.split(':')[-1][1:]
                pa = float(ll.split()[0])
            elif len(line) > 115:
                if 'Tile' in line:
                    continue
                else:
                    _list = line.split()
                    if len(_list) == 13:
                        #print(step, obs, _list[0], _list[1], _list[2:])
                        df.loc[step, obs, _list[0], _list[1]] = np.array(_list[2:]).astype(np.float32)
            elif (len(line) >55) & (len(line) < 80):
                _list = line.split()
                if len(_list) == 5:
                   if 'Index' not in _list:
                        df2.loc[reg, _list[0], ra_ref, dec_ref, pa] = np.array(_list[1:]).astype(np.float32)
    if not reset_index:                    
        return df, df2
    else:
        return df.reset_index(), df2.reset_index()
