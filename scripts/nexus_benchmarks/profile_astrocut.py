"""Profile Astrocut image cutouts for representative Nexus workloads.

The cases create random sky coordinates over a Roman WFI image and measure
cutouts at two sizes. Results are workload-specific; see the benchmark article
linked from this directory's README for resource-planning context.
"""

import warnings
from copy import deepcopy

import astropy.units as u
import numpy as np
from astrocut import ASDFCutout
from astropy.coordinates import SkyCoord
from astropy.utils.exceptions import AstropyDeprecationWarning
import roman_datamodels as rdm

from profile_workflows import profile_resources

# Ignore warnings from the 'astropy.wcs' module
# When creating cutouts -> WARNING: Polynomial distortion is not implemented.
warnings.filterwarnings('ignore', module='astropy.wcs')

# Ignore AstropyDeprecationWarning
# When creating cutouts -> WARNING: AstropyDeprecationWarning: The class
# "Fits" has been renamed to "FITS" in version 7.0.
# The old name is deprecated and may be removed in a future version. Use
# FITS instead. [astropy.units.format]
warnings.filterwarnings('ignore', category=AstropyDeprecationWarning)


def get_wcs(asdf_file):
    """Return the world-coordinate system from an ASDF image."""
    dm = rdm.open(asdf_file)
    wcs = dm.meta.wcs

    return wcs


def cutouts(n_cutouts=100, cutout_size=100):
    """Profile creation of random cutouts from a calibrated WFI image.

    Args:
        n_cutouts: Number of random sky positions to sample.
        cutout_size: Width and height of each cutout in pixels.

    Returns:
        The result and resource metrics returned by ``profile_resources``.
    """

    asdf_file = (
        'https://s3.amazonaws.com/stpubdata/roman/nexus/'
        'soc_simulations/tutorial_data/'
        'r0003201001001001004_0001_wfi02_f106_cal.asdf'
    )
    gwcs = get_wcs(asdf_file)

    rng = np.random.default_rng()
    x = rng.uniform(low=50, high=4000, size=n_cutouts)
    y = rng.uniform(low=50, high=4000, size=n_cutouts)
    ra, dec = gwcs(x, y)
    cdt = SkyCoord(ra, dec, unit='deg', frame='icrs')

    @profile_resources()
    def perform_calc(cdt, cutout_size=cutout_size):
        """Create cutouts for the selected coordinates."""
        ac = ASDFCutout(asdf_file, cdt, cutout_size)

    result = perform_calc(cdt, cutout_size=cutout_size)

    return result


def case1():
    """Profile 100 cutouts, each 100 pixels wide."""
    result = cutouts(n_cutouts=100, cutout_size=100)
    return result


def case2():
    """Profile 100 cutouts, each 10 pixels wide."""
    result = cutouts(n_cutouts=100, cutout_size=10)
    return result
