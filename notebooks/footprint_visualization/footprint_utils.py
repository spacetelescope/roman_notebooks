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
import warnings
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
    att_here = attitude(wfi_cen.V2Ref, wfi_cen.V3Ref, ra_cen, dec_cen, pa)
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
            elif (len(line) > 55) & (len(line) < 80):
                _list = line.split()
                if len(_list) == 5:
                   if 'Index' not in _list:
                        df2.loc[reg, _list[0], ra_ref, dec_ref, pa] = np.array(_list[1:]).astype(np.float32)
    if not reset_index:                    
        return df, df2
    else:
        return df.reset_index(), df2.reset_index()

def get_survey_maps_uri(survey_name, band, tier=None):
    """
    Utility function to retrieve the relevant pre-generated
    survey exposure-time maps

    Params:
    -------
    survey_name (str) : Survey name -- allowed options are [HLTDS, HLWAS, GBTDS, GPS]
    band (str) : Filter element of interest 
                 -- allowed options are [F062, F087, F106, F129, F146, F158, F814, F213, PRISM, GRISM]
    tier (str) : Survey tier -- only available for HLWAS and HLTDS

    Returns:
    --------
    file_name (str) : Path to pre-generated healsparse map containing the exposure time for the 
    selected survey / filter combination
    """

    allowed_surveys = ['HLTDS', 'HLWAS', 'GBTDS', 'GPS']
    allowed_bands = ['F062', 'F087', 'F106', 'F129', 'F146', 'F158', 'F184', 'F213', 'PRISM', 'GRISM']
    allowed_hlwas_tier = ['ALL', 'DEEP', 'WIDE', 'MEDIUM', 'ULTRA-DEEP', 'ULTRADEEP']
    allowed_hltds_tier = ['ALL', 'DEEP', 'WIDE']
    if survey_name.upper() not in allowed_surveys:
        raise ValueError('The requested survey is not one of the Community defined surveys')

    if band.upper() not in allowed_bands:
        raise ValueError('The requested filter element is not available on WFI')
    # GBTDS logic -- we have all optical elements with their own map but PRISM which is not used
    if survey_name.upper() == 'GBTDS':
        if band == 'PRISM':
            raise ValueError('No PRISM component available for the GBTDS')
        else:
            return f'./aux_data/map_{survey_name.upper()}_{band.upper()}.hsp'
    # GPS logic -- we have all optical elements with their own map
    elif survey_name.upper() == 'GPS':
        if band == 'F146':
            raise ValueError('No F146 component available for the GPS')
        else:
            return f'./aux_data/map_{survey_name.upper()}_{band.upper()}.hsp'
    # HLWAS logic
    # We have 4 tiers -- wide (only F158), medium (3 filters all the same + grism)
    # Deep 5 filters with the same exposure time, 1 with different + grism
    # ultra-deep 3 filters all with the same exposure time we reuse the maps
    # when possible
    elif survey_name.upper() == 'HLWAS':
        if tier is None:
            warnings.warn('No selected tier for the HLWAS, returning the sum of all tiers')
            tier = 'ALL'
        else:
            if tier.upper() not in allowed_hlwas_tier:
                raise ValueError('The requested tier name is not available, please try ALL, DEEP, \
                                  WIDE, MEDIUM, or ULTRA-DEEP')
            else:
                if tier.upper() == 'WIDE':
                    if band.upper() != 'F158':
                        raise ValueError('HLWAS-WIDE only available for F158')
                    else:
                        return f'./aux_data/map_{survey_name.upper()}-{tier.lower()}_{band.upper()}.hsp'
                elif tier.upper() == 'MEDIUM':
                    if band.upper() in ['F106', 'F129', 'F158']:
                        return f'./aux_data/map_{survey_name.upper()}-{tier.lower()}_F158.hsp'
                    elif band.upper() == 'GRISM':
                        return f'./aux_data/map_{survey_name.upper()}-{tier.lower()}_GRISM.hsp'
                    else:
                        raise ValueError(f'The requested element {band.upper()} is not available \
                                         for HLWAS-MEDIUM')
                elif tier.upper() == 'DEEP':
                    if band.upper() in ['F087', 'F106', 'F129', 'F158', 'F184', 'F213']:
                        return f'./aux_data/map_{survey_name.upper()}-{tier.lower()}_F213.hsp'
                    elif band.upper() == 'F146':
                        return f'./aux_data/map_{survey_name.upper()}-{tier.lower()}_{band.upper()}.hsp'
                    elif band.upper() == 'GRISM':
                        return f'./aux_data/map_{survey_name.upper()}-{tier.lower()}_{band.upper()}.hsp'
                    else:
                        raise ValueError(f'The requested element {band.upper()} is not available \
                                          for HLWAS-DEEP')
                elif (tier.upper() == 'ULTRADEEP') or (tier.upper() == 'ULTRA-DEEP'):
                    if tier == 'ULTRA-DEEP':
                        tier = 'ULTRADEEP'
                    if band.upper() in ['F106', 'F129', 'F158']:
                        return f'./aux_data/map_{survey_name.upper()}-{tier.lower()}_F158.hsp'
                    else:
                        raise ValueError(f'The requested element {band.upper()} is not available \
                                         for HLWAS-ULTRADEEP')
                elif tier.upper() == 'ALL':
                    if band.upper() in ['F087', 'F184', 'F213']:
                        return f'./aux_data/map_HLWAS-deep_F213.hsp'
                    elif band.upper() == 'F146':
                        return f'./aux_data/map_HLWAS-deep_F146.hsp'
                    elif band.upper() == 'F158':
                        return f'./aux_data/map_HLWAS-all_F158.hsp'
                    elif band.upper() == 'GRISM':
                        return f'./aux_data/map_HLWAS-all_GRISM.hsp'
                    elif band.upper() in ['F106', 'F129']:
                        return f'./aux_data/map_HLWAS-all_F106.hsp'
                    else:
                        raise ValueError(f'The selected element {band} is not available for HLWAS')
    
    elif survey_name.upper() == 'HLTDS':
        if tier is None:
            warnings.warn('No selected tier for HLTDS, returning sum of all tiers')
        else:
            warnings.warn('Tier separation not implemented currently for HLTDS, returning the sum of all tiers')
        if band.upper() == 'F184':
            return f'./aux_data/map_{survey_name.upper()}-deep_{band.upper()}.hsp'
        elif band.upper() == 'F062':
            return f'./aux_data/map_{survey_name.upper()}-wide_{band.upper()}.hsp'
        elif band.upper() in ['PRISM', 'F158', 'F129', 'F106', 'F087']:
            return f'./aux_data/map_{survey_name.upper()}-deep+wide_{band.upper()}.hsp'
        else:
            raise ValueError(f'The requested element {band.upper()} is not available for HLTDS')
