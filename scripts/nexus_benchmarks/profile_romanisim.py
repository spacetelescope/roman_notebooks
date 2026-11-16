import asdf
from astropy.coordinates import SkyCoord, SkyOffsetFrame
from astropy.time import Time
from astropy.table import Table, vstack
from astropy import units as u
import copy
import galsim
import numpy as np
import os
import roman_datamodels as rdm
from romanisim import catalog, log, persistence, ris_make_utils as ris, image as risim
from romanisim.models import parameters, bandpass, wcs  
from romanisim.image import inject_sources_into_l2
import crds
import stpsf

from profile_workflows import profile_resources


def get_coords(ra, dec, orient, sca):

    wficen_rsim = parameters.v2v3_wficen

    # Get distortion file for this SCA
    meta = {
        'ROMAN.META.INSTRUMENT.NAME': 'WFI',
        'ROMAN.META.INSTRUMENT.DETECTOR': f'WFI{sca:02d}',
        'ROMAN.META.INSTRUMENT.OPTICAL_ELEMENT': 'F158',
        'ROMAN.META.EXPOSURE.TYPE': 'WFI_IMAGE',
        'ROMAN.META.EXPOSURE.START_TIME': '2029-10-31 00:00:00'
    }
    
    ref_files = crds.getreferences(meta, reftypes=['distortion'], observatory='roman')
    dist = rdm.open(ref_files['distortion'])
    dist_mod = dist.coordinate_distortion_transform
    sca_v2, sca_v3 = dist_mod.offset_10.value, dist_mod.offset_11.value
    
    # Transform to the WFI and SCA centers.
    v1 = SkyCoord(ra, dec, unit='deg', frame='icrs')
    vframe = v1.skyoffset_frame(rotation=orient * u.degree)
    wfi_sky = SkyCoord(*wficen_rsim, unit='arcsec', frame=vframe).transform_to('icrs')
    sca_sky = SkyCoord(sca_v2, sca_v3, unit='arcsec', frame=vframe).transform_to('icrs')

    return wfi_sky.ra.degree, wfi_sky.dec.degree, sca_sky.ra.degree, sca_sky.dec.degree


def generate_catalog(n_stars=500, n_galaxies=500, seed=4642, ra=270.94, dec=-0.2, radius=0.06, 
                     faint_mag=22, half_light_radius=0.3, optical_element=['F106']):
    """
    By default, generate a catalog of sources within a circle roughly the size of a WFI detector.
    """

    galaxy_cat = catalog.make_galaxies(SkyCoord(ra, dec, unit='deg'), n_galaxies, radius=radius, index=0.4, faintmag=faint_mag,
                                       hlr_at_faintmag=half_light_radius, bandpasses=optical_element, rng=None, seed=seed)

    star_cat = catalog.make_stars(SkyCoord(ra, dec, unit='deg'), n_stars, radius=radius, index=5/3., faintmag=faint_mag, 
                                  truncation_radius=None, bandpasses=optical_element, rng=None, seed=seed)

    full_cat = vstack([galaxy_cat, star_cat])

    return full_cat


@profile_resources()
def run_romanisim(catalog, ra=270.94, dec=-0.2, sca=1, optical_element='F106',
                  ma_table_number=1049, level=2, seed=5346):
    """
    MA Table suggestions:
        1049 = IM_66_6_V2
        1018 = IM_294_16
    """

    # Set reference files to None for CRDS
    for k in parameters.reference_data:
        parameters.reference_data[k] = None

    # Set Galsim RNG object
    rng = galsim.UniformDeviate(seed)

    # Set default persistence information
    persist = persistence.Persistence()

    # Set metadata
    metadata = ris.set_metadata(date='2029-10-31T00:00:00', bandpass=optical_element, sca=sca,
                                ma_table_number=ma_table_number, usecrds=True)

    # Update the WCS info
    wcs.fill_in_parameters(metadata, SkyCoord(ra, dec, unit='deg', frame='icrs'),
                           boresight=False, pa_aper=0.0)

    # Run the simulation using metadata value without saving any files
    im, extras = risim.simulate(metadata, catalog, usecrds=True,
                                psftype='stpsf', level=level,
                                persistence=persist, rng=rng
                                )

    return im


def case1():
    """
    1,000 galaxies, L1
    """
    
    wra, wdec, sra, sdec = get_coords(270.94, -0.2, 60, 1)
    catalog = generate_catalog(n_stars=0, n_galaxies=1_000, ra=sra, dec=sdec)
    _, results = run_romanisim(catalog, ra=wra, dec=wdec, sca=1, level=1)

    return results


def case2():
    """
    1,000 galaxies, L2
    """
    
    wra, wdec, sra, sdec = get_coords(270.94, -0.2, 60, 1)
    catalog = generate_catalog(n_stars=0, n_galaxies=1_000, ra=sra, dec=sdec)
    _, results = run_romanisim(catalog, ra=wra, dec=wdec, sca=1, level=2)

    return results


def case3(save=False):
    """
    1,000 stars, L1
    """

    wra, wdec, sra, sdec = get_coords(270.94, -0.2, 60, 1)
    catalog = generate_catalog(n_stars=1_000, n_galaxies=0, ra=sra, dec=sdec)
    im, results = run_romanisim(catalog, ra=wra, dec=wdec, sca=1, level=1)

    # Optional save for photometry example
    if save:
        filename = 'photometry_case2_uncal.asdf'
        im.meta.filename = filename
        af = asdf.AsdfFile()
        af.tree = {'roman': im}
        af.write_to(filename)

        catalog.write('photometry_case2_catalog.ecsv')

    return results


def case4(save=False):
    """
    1,000 stars, L2
    """

    wra, wdec, sra, sdec = get_coords(270.94, -0.2, 60, 1)
    catalog = generate_catalog(n_stars=1_000, n_galaxies=0, ra=sra, dec=sdec)
    _, results = run_romanisim(catalog, ra=wra, dec=wdec, sca=1, level=2)

    # Optional save for photometry example
    if save:
        filename = 'photometry_1k_cal.asdf'
        im.meta.filename = filename
        af = asdf.AsdfFile()
        af.tree = {'roman': im}
        af.write_to(filename)

        catalog.write('photometry_1k_catalog.ecsv')

    return results


def case5():
    """
    500 stars + 500 galaxies, L1
    """

    wra, wdec, sra, sdec = get_coords(270.94, -0.2, 60, 1)
    catalog = generate_catalog(n_stars=500, n_galaxies=500, ra=sra, dec=sdec)
    _, results = run_romanisim(catalog, ra=wra, dec=wdec, sca=1, level=1)

    return results


def case6():
    """
    500 stars + 500 galaxies, L2
    """

    wra, wdec, sra, sdec = get_coords(270.94, -0.2, 60, 1)
    catalog = generate_catalog(n_stars=500, n_galaxies=500, ra=sra, dec=sdec)
    _, results = run_romanisim(catalog, ra=wra, dec=wdec, sca=1, level=2)

    return results


def case7(save=False):
    """
    10,000 stars, L1
    """

    wra, wdec, sra, sdec = get_coords(270.94, -0.2, 60, 1)
    catalog = generate_catalog(n_stars=10_000, n_galaxies=0, ra=sra, dec=sdec)
    im, results = run_romanisim(catalog, ra=wra, dec=wdec, sca=1, level=1)

    if save:
        filename = 'photometry_10k_uncal.asdf'
        im.meta.filename = filename
        af = asdf.AsdfFile()
        af.tree = {'roman': im}
        af.write_to(filename)

        catalog.write('photometry_10k_catalog.ecsv')

    return results


def case8(save=False):
    """
    """
    
    wra, wdec, sra, sdec = get_coords(270.94, -0.2, 60, 1)
    catalog = generate_catalog(n_stars=1_000, n_galaxies=0, ra=sra, dec=sdec)
    im, results = run_romanisim(catalog, ra=wra, dec=wdec, sca=1, level=1, ma_table_number=1018)

    if save:
        filename = 'elp_case3_uncal.asdf'
        im.meta.filename = filename
        af = asdf.AsdfFile()
        af.tree = {'roman': im}
        af.write_to(filename)

    return results