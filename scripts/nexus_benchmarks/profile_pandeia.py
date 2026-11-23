"""Profile representative Roman WFI exposure calculations with Pandeia.

The functions calculate signal-to-noise ratios or exposure counts for sampled
source magnitudes. Measurements depend on the input assumptions and compute
configuration.
"""

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
    """Calculate signal-to-noise ratios across a range of magnitudes.

    Parameters
    ----------
    filt : str
        Name of Roman WFI filter
    nexp : int
        Number of exposures
    bracket : tuple
        Inclusive magnitude range to test; defaults to (18, 30).

    Returns
    -------
    mag_range : numpy.ndarray
        Magnitudes used to compute signal-to-noise ratios.
    computed_snrs : list
        Signal-to-noise ratios returned by Pandeia.
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
    """Interpolate the magnitude that yields a requested signal-to-noise ratio.

    Parameters
    ----------
    mag_range : array-like
        Magnitudes used to calculate the sampled signal-to-noise ratios.
    computed_snrs : array-like
        Pandeia signal-to-noise ratios corresponding to ``mag_range``.
    sntarget : float
        Requested signal-to-noise ratio.

    Returns:
        The interpolated magnitude for ``sntarget``.
    """
    interpolator = interpolate.interp1d(computed_snrs, mag_range)
    mag = interpolator(sntarget)

    return mag


def _nexp2sn_(nexp, calc, sntarget):
    """Return squared signal-to-noise error for an exposure-count estimate.

    Parameters
    ----------
    nexp : float
        Candidate exposure count supplied to the optimizer.
    calc : dict
        Pandeia calculation configuration, updated in place.
    sntarget : float
        Requested signal-to-noise ratio.

    Returns:
        Squared difference between the requested and calculated ratios.
    """
    calc['configuration']['detector']['nexp'] = int(nexp)
    etc = perform_calculation(calc)['scalar']

    return (sntarget - etc['sn'])**2


def compute_nexp(filt, sn, mag, bracket=(1, 1000), xtol=0.1):
    """Estimate the exposure count needed for a target signal-to-noise ratio.

    Parameters
    ----------
    filt : str
        Name of Roman WFI filter
    sn : float
        Required S/N
    mag : float
        AB Magnitude of source
    bracket : tuple, default (1, 1000)
        Bounds for the exposure-count search.
    xtol : float, default 0.1
        Absolute tolerance passed to the minimizer.

    Returns
    -------
    nexp : int
        Estimated exposure count.
    report : dict
        Pandeia report for the selected exposure count.
    exptime : float
        Total exposure time in the report.
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
        # For more details on the minimize_scalar function, refer to
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize_scalar.html
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
    """Profile Pandeia for a randomly sampled WFI exposure setup."""

    rng = np.random.default_rng()
    mags = rng.normal(25, 3, nsamples)
    for m in mags:
        # Creating a default calculation using Roman's WFI with an imaing mode
        calc = build_default_calc('roman', 'wfi', 'imaging')
        # Setting the filter to F129
        calc['configuration']['instrument']['filter'] = 'f158'
        # Taking three exposures of multi-accum sequence
        calc['configuration']['detector']['nexp'] = 3
        # Truncate after 6 resultant
        calc['configuration']['detector']['nresultants'] = 7
        calc['scene'][0]['spectrum']['normalization']['norm_flux'] = m
        calc['scene'][0]['spectrum']['normalization'][
            'norm_fluxunit'] = 'abmag'

        @profile_resources()
        def run_calc():
            """Run Pandeia for the currently configured magnitude."""
            report = perform_calculation(calc)

    return run_calc()


def case2(nsamples):
    """Profile magnitude interpolation across sampled targets and exposures."""

    rng = np.random.default_rng()
    SN = rng.normal(5, 1, nsamples)
    NEXP = rng.integers(8, high=12, size=nsamples)

    @profile_resources()
    def perform_calc():
        """Calculate and interpolate magnitudes for all sampled cases."""
        for i in range(nsamples):
            mag_range, computed_snrs = compute_mag('f158', NEXP[i])
            mag = _mag2sn_(mag_range, computed_snrs, SN[i])

    return perform_calc()


def case3(nsamples):
    """Profile exposure-count estimates for sampled signal and magnitudes."""

    rng = np.random.default_rng()
    SN = rng.normal(5, 1, 100)
    MAG = rng.normal(23.84, 3, size=100)

    @profile_resources()
    def perform_calc():
        """Estimate exposure counts for all requested samples."""
        for i in range(nsamples):
            nexp, etc, exptime = compute_nexp('f158', SN[i], MAG[i])

    return perform_calc()
