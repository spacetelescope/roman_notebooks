from pandeia.engine.calc_utils import build_default_calc
from pandeia.engine.perform_calculation import perform_calculation
from scipy.optimize import minimize_scalar
from scipy import interpolate
from textwrap import wrap

# General imports
import json
import numpy as np
from astropy.io import fits

# Profiling imports
from profile_workflows import profile_resources


FILTER = 'f129'


def compute_mag(filt, nexp, bracket=(18, 30)):
    """
    Method to compute the S/N from a range of magnitudes and a fixed number of exposures

    Parameters
    ----------
    filt : str
        Name of Roman WFI filter
    nexp : int
        Number of exposures
    bracket : tuple
        Range of magnitudes to test. default: (18, 30)

    Returns
    -------
    mag_range : float
        An array of magnitudes used to compute the SNRs
    computed_snrs: float
        An array of computed SNRs from Pandeia calculations
    """

    # Set up default Roman observation
    calc = build_default_calc('roman', 'wfi', 'imaging')

    # Modify defaults to place a source with an AB magnitude
    calc['scene'][0]['spectrum']['normalization']['norm_fluxunit'] = 'abmag'
    calc['scene'][0]['spectrum']['normalization']['norm_waveunit'] = 'um'
    
    # Set number of exposures and filter
    calc['configuration']['detector']['nexp'] = nexp
    calc['configuration']['instrument']['filter'] = filt

    # Create an array of magnitudes range of interest
    mag_range = np.arange(bracket[0], bracket[1] + 1, 1)
    # Create empty lists to save the computations
    computed_snrs = []
    # Compute the SNRs for a given magnitude
    for m in range(len(mag_range)):
        mag = mag_range[m]
        calc['scene'][0]['spectrum']['normalization']['norm_flux'] = mag
        report = perform_calculation(calc)
        computed_snrs.append(report['scalar']['sn'])

    return mag_range, computed_snrs


def _mag2sn_(mag_range, computed_snrs, sntarget):
    """
    Calculate a magnitude given a desired SNR by interpolating (computed_snrs, mag_range) from compute_mag
    
    Parameters
    ----------
    mag_range: float
        An array of magnitudes used in calculating a range of SNRs in compute_mag
    computed_snrs: float
        An array of computed SNR given the mag_range using Pandeia calculation object
    sntarget: float
        Required S/N
    """
    interpolator = interpolate.interp1d(computed_snrs, mag_range)
    mag = interpolator(sntarget)

    return mag


def _nexp2sn_(nexp, calc, sntarget):
    """
    Optimize a S/N ratio given a number of exposures. This is a helper function
    used as an argument for scipy's minimize_scalar() as used in compute_mag().
    
    Parameters
    ----------
    nexp : int
        The number of exposures used in an iteration of minimize_scalar()
    calc : 
        A Pandeia calculation object
    sntarget : 
        Required S/N from the matching argument of compute_mag()
    """
    calc['configuration']['detector']['nexp'] = int(nexp)
    etc = perform_calculation(calc)['scalar']
    
    return (sntarget - etc['sn'])**2


def compute_nexp(filt, sn, mag, bracket=(1, 1000), xtol=0.1):
    """
    Method to compute the number of exposures from S/N and magnitude

    Parameters
    ----------
    filt : str
        Name of Roman WFI filter
    sn : float
        Required S/N
    mag : float
        AB Magnitude of source
    bracket : tuple, default (1, 1000)
        Range of magnitudes to test
    xtold: float, default 0.1
        Target tolerance for minimizer

    Returns
    -------
    nexp : float
        Optimal number of exposures for specified S/N and magnitude
    report: dict
        Pandeia dictionary with optimal parameters
    exptime: float
        Exposure time for optimal observation
    """
    # Set up default Roman observation
    calc = build_default_calc('roman', 'wfi', 'imaging')

    # Modify defaults to place a source with an AB magnitude
    calc['scene'][0]['spectrum']['normalization']['norm_flux'] = mag
    calc['scene'][0]['spectrum']['normalization']['norm_fluxunit'] = 'abmag'
    calc['scene'][0]['spectrum']['normalization']['norm_waveunit'] = 'um'

    # Set filter
    calc['configuration']['instrument']['filter'] = filt

    # Check that the minimum of 1 exposure has a S/N lower than requested,
    # otherwise there is no sense in attempting to minimize nexp.
    calc['configuration']['detector']['nexp'] = 1
    calc['configuration']['detector']['nresultants'] = 6
    report = perform_calculation(calc)

    if report['scalar']['sn'] > sn:
        nexp = 1
    else:
        res = minimize_scalar(_nexp2sn_, bracket=bracket, bounds=bracket,
                              args=(calc, sn), method='bounded',
                              options={'xatol': xtol})

        # Take the optimization result and set it to nexp
        # 'x' is the solution array in the optimization result object
        # For more details on the minimize_scalar function, refer to https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize_scalar.html
        nexp = int(res['x'])
        calc['configuration']['detector']['nexp'] = nexp
        report = perform_calculation(calc)

        # this generally returns a S/N less than the required amount.
        # let's ensure that we get *AT LEAST* the required S/N for 2 reasons:
        # 1) better to err on the side of caution
        # 2) make code consistent with the above if clause
        if report['scalar']['sn'] < sn:
            nexp += 1
            # Re-calculate
            calc['configuration']['detector']['nexp'] = nexp
            report = perform_calculation(calc)

    exptime = report['scalar']['total_exposure_time']

    return nexp, report, exptime


def case1(nsamples):

    rng = np.random.default_rng()
    mags = rng.normal(25, 3, nsamples)
    for m in mags:
        # Creating a default calculation using Roman's WFI with an imaing mode
        calc = build_default_calc('roman', 'wfi', 'imaging')
        calc['configuration']['instrument']['filter'] = 'f158'  # Setting the filter to F129
        calc['configuration']['detector']['nexp'] = 3  # Taking three exposures of multi-accum sequence
        calc['configuration']['detector']['nresultants'] = 7  # Truncate after 6 resultant
        calc['scene'][0]['spectrum']['normalization']['norm_flux'] = m
        calc['scene'][0]['spectrum']['normalization']['norm_fluxunit'] = 'abmag'
        
        @profile_resources()
        def run_calc():
            report = perform_calculation(calc)

    return run_calc() 

    
def case2(nsamples):

    rng = np.random.default_rng()
    SN = rng.normal(5, 1, nsamples)
    NEXP = rng.integers(8, high=12, size=nsamples)

    @profile_resources()
    def perform_calc():
        for i in range(nsamples):
            mag_range, computed_snrs = compute_mag('f158', NEXP[i])
            mag = _mag2sn_(mag_range, computed_snrs, SN[i])

    return perform_calc()


def case3(nsamples):

    rng = np.random.default_rng()
    SN = rng.normal(5, 1, 100)
    MAG = rng.normal(23.84, 3, size=100)

    @profile_resources()
    def perform_calc():
        for i in range(nsamples):
            nexp, etc, exptime = compute_nexp('f158', SN[i], MAG[i])

    return perform_calc()