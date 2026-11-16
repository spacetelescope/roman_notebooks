from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.stats import SigmaClip, sigma_clipped_stats
import astropy.units as u
import numpy as np
from photutils.aperture import CircularAperture, CircularAnnulus, aperture_photometry, ApertureStats
from photutils.detection import DAOStarFinder
from photutils.psf import ImagePSF, PSFPhotometry
import roman_datamodels as rdm
import os
import s3fs
import stpsf

from profile_workflows import profile_resources


def source_detection(image, fwhm=0.791, background_sigma=3.0, threshold_sigma=5.0):

    dm = rdm.open(image)

    @profile_resources()
    def perform_calc(image, fwhm, background_sigma, threshold_sigma):

        data = image.data
        mask = image.dq
        _, median, std = sigma_clipped_stats(data, sigma=3.0)
        
        finder = DAOStarFinder(
            fwhm=fwhm,
            threshold=threshold_sigma * std,
        )
        
        sources = finder(data - median, mask=mask)

        return sources

    sources, result = perform_calc(dm, fwhm, background_sigma, threshold_sigma)
    
    return sources, result


def forced_aperture_photometry(image, catalog, radius=3.0):

    dm = rdm.open(image)
    cat = Table.read(catalog)

    x, y = dm.meta.wcs.invert(cat['ra'], cat['dec'])
    cat['x'] = x
    cat['y'] = y
    mask = np.isfinite(x) & np.isfinite(y)

    stars = cat[mask & (cat["type"] == "PSF")]
    star_positions = [(x, y) for x, y in zip(stars['x'].data, stars['y'].data)]

    @profile_resources()
    def perform_calc(dm, positions, radius=3.0):
    
        star_apertures = CircularAperture(positions=positions, r=radius)
        star_bkg_apertures = CircularAnnulus(positions=positions, r_in=20, r_out=25)

        columns = ('id', 'x_centroid', 'y_centroid', 'median', 'std')
        sigclip = SigmaClip(sigma=3.0, maxiters=5)
        star_bkg = ApertureStats(dm.data, star_bkg_apertures, sigma_clip=sigclip, mask=dm.dq.astype(np.bool))
        tab = star_bkg.to_table(columns=columns)

        return tab

    tab, results = perform_calc(dm, star_positions, radius=radius)
    
    return tab, results
    

def forced_psf_photometry(image, catalog, fit_shape=(9, 9), fov_pixels=21):
    with rdm.open(image) as dm:
        cat = Table.read(catalog)
        coords = SkyCoord(ra=cat["ra"] * u.deg, dec=cat["dec"] * u.deg)
        x, y = dm.meta.wcs.world_to_pixel(coords)
        cat["x"] = x
        cat["y"] = y

        valid = np.isfinite(x) & np.isfinite(y) & (cat["type"] == "PSF")
        stars = cat[valid]
        if len(stars) == 0:
            raise ValueError("The catalog contains no on-detector PSF sources.")

        positions = Table()
        positions["x_0"] = np.asarray(stars["x"], dtype=float)
        positions["y_0"] = np.asarray(stars["y"], dtype=float)

        data = np.array(dm.data, dtype=float, copy=True)
        error = np.array(dm.err, dtype=float, copy=True)
        mask = np.asarray(dm.dq, dtype=bool) | ~np.isfinite(data) | ~np.isfinite(error)
        _, median, _ = sigma_clipped_stats(data, mask=mask)
        data -= median

        # A local positive-pixel sum is a reasonable starting amplitude; the
        # fitter determines the final flux from the PSF model.
        radius = max(fit_shape) // 2
        initial_flux = []
        for xpos, ypos in zip(positions["x_0"], positions["y_0"]):
            xc = int(np.rint(xpos))
            yc = int(np.rint(ypos))
            xmin, xmax = max(0, xc - radius), min(data.shape[1], xc + radius + 1)
            ymin, ymax = max(0, yc - radius), min(data.shape[0], yc + radius + 1)
            stamp = data[ymin:ymax, xmin:xmax]
            stamp_mask = mask[ymin:ymax, xmin:xmax]
            usable = stamp[~stamp_mask]
            initial_flux.append(max(float(np.sum(usable)), np.finfo(float).eps))
        positions["flux"] = initial_flux

        wfi = stpsf.WFI()
        wfi.filter = "F106"
        psf_hdul = wfi.calc_psf(fov_pixels=fov_pixels)
        psf_data = np.array(psf_hdul["DET_SAMP"].data, dtype=float, copy=True)

        if psf_data.ndim != 2 or min(psf_data.shape) < 4:
            raise ValueError("STPSF returned an invalid detector-sampled PSF.")
        if not np.all(np.isfinite(psf_data)) or psf_data.sum() <= 0:
            raise ValueError("STPSF returned a non-finite or zero-sum PSF.")

        psf_data /= psf_data.sum()
        psf_model = ImagePSF(psf_data)

        @profile_resources()
        def perform_calc(data, error, mask, positions, psf_model):
            psf_photometry = PSFPhotometry(
                psf_model,
                fit_shape=fit_shape,
            )
            return psf_photometry(
                data,
                error=error,
                mask=mask,
                init_params=positions,
            )

        results, metrics = perform_calc(data, error, mask, positions, psf_model)

    return results, metrics



def case1():
    """
    Source Detection, 10k stars
    """

    sources, results = source_detection('photometry_10k_cal.asdf', threshold_sigma=10.0)
    print(f'Found {len(sources)} out of 10,000 ({len(sources)/10_000:.1%}) sources')

    return results


def case2():
    """
    Source Detection, 1k stars
    """

    sources, results = source_detection('photometry_1k_cal.asdf', threshold_sigma=10.0)
    print(f'Found {len(sources)} out of 1,000 ({len(sources)/1_000:.1%}) sources')

    return results


def case3():
    """
    Aperture Photometry, 10k stars
    """

    photometry, results = forced_aperture_photometry('photometry_10k_cal.asdf', 'photometry_10k_catalog.ecsv')

    return results


def case4():
    """
    Aperture Photometry, 1k stars
    """

    photometry, results = forced_aperture_photometry('photometry_1k_cal.asdf', 'photometry_1k_catalog.ecsv')

    return results


def case5():
    """
    PSF Photometry, 10k stars
    """

    photometry, results = forced_psf_photometry(
        "photometry_10k_cal.asdf",
        "photometry_10k_catalog.ecsv",
    )

    return results


def case6():
    """
    PSF Photometry, 1k stars
    """

    photometry, results = forced_psf_photometry(
        "photometry_1k_cal.asdf",
        "photometry_1k_catalog.ecsv",
    )

    return results

    