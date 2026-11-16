from astropy.coordinates import SkyCoord
from astropy.stats import sigma_clipped_stats
from astropy.table import Table
import astropy.units as u
import galsim
from galsim.roman import collecting_area
import numpy as np
import roman_datamodels as rdm
from scipy.optimize import curve_fit
import synphot as syn
import stpsf

from profile_workflows import profile_resources


PIXEL_SCALE = 0.11


def get_data():
    image_url = (
        "https://s3.amazonaws.com/stpubdata/roman/nexus/"
        "soc_simulations/tutorial_data/"
        "r0003201001001001004_0001_wfi01_f106_cal.asdf"
    )
    catalog_url = (
        "https://s3.amazonaws.com/stpubdata/roman/nexus/"
        "soc_simulations/tutorial_data/full_catalog.ecsv"
    )

    with rdm.open(image_url) as dm:
        catalog = Table.read(catalog_url)

        coords = SkyCoord(
            ra=catalog["ra"] * u.deg,
            dec=catalog["dec"] * u.deg,
        )
        x, y = dm.meta.wcs.world_to_pixel(coords)

        catalog["x"] = x
        catalog["y"] = y

        mag_ab = -2.5 * np.log10(catalog["F106"])
        bright = (
            (mag_ab > 17)
            & (mag_ab < 21)
            & (catalog["type"] == "SER")
        )

        padding = 10
        ny, nx = dm.data.shape
        inchip = (
            (x > padding)
            & (x < nx - padding)
            & (y > padding)
            & (y < ny - padding)
        )

        gal_tab = catalog[bright & inchip]

        # Materialize independent arrays before closing the ASDF file.
        data = np.array(dm.data, copy=True)
        err = np.array(dm.err, copy=True)

    _, med_bkg, _ = sigma_clipped_stats(data)
    data -= med_bkg

    return data, err, gal_tab


def make_cutout(image, catalog, index, scale=4, err=False):
    size = int(
        catalog["half_light_radius"][index] * scale / PIXEL_SCALE
    ) + 1

    xmin = int(catalog["x"][index] - size // 2)
    xmax = xmin + size + 1
    ymin = int(catalog["y"][index] - size // 2)
    ymax = ymin + size + 1

    # Clip at detector edges rather than allowing negative slice indices.
    ny, nx = image.shape
    xmin = max(0, xmin)
    xmax = min(nx, xmax)
    ymin = max(0, ymin)
    ymax = min(ny, ymax)

    if xmin >= xmax or ymin >= ymax:
        raise ValueError(f"Empty cutout for catalog index {index}.")

    stamp = image[ymin:ymax, xmin:xmax]

    if err:
        return stamp.flatten()

    return galsim.Image(stamp, scale=PIXEL_SCALE)


def make_psf():
    wfi = stpsf.WFI()
    wfi.filter = "F106"
    psf = wfi.calc_psf(fov_pixels=64)

    psf_img = galsim.Image(
        psf["OVERSAMP"].data,
        scale=PIXEL_SCALE / 4,
    )
    return galsim.InterpolatedImage(psf_img, flux=1)


def convert_flux(mag):
    spec = syn.SourceSpectrum(
        syn.models.ConstFlux1D,
        amplitude=mag * u.ABmag,
    )

    eff_area = Table.read(
        "https://raw.githubusercontent.com/RomanSpaceTelescope/"
        "roman-technical-information/refs/heads/develop/"
        "roman_technical_information/data/WideFieldInstrument/"
        "Imaging/EffectiveAreas/Roman_effarea_v8_SCA01_20240301.ecsv"
    )

    band = syn.SpectralElement(
        syn.models.Empirical1D,
        points=eff_area["Wave"] * u.micron,
        lookup_table=eff_area["F106"] / 3.60767,
    )

    obs = syn.Observation(spec, band)
    waves = obs.binset

    return np.trapezoid(obs(waves), x=waves).value


def sersic_mod(cutout, psf_obj, n, hlr, influx, pa, x0, y0, q):
    ny, nx = cutout.array.shape

    ser = galsim.Sersic(n, half_light_radius=hlr, flux=influx)
    ser = ser.shear(q=q, beta=pa * galsim.degrees)
    ser = galsim.Convolve(ser, psf_obj)

    img = galsim.ImageD(nx, ny, scale=PIXEL_SCALE)
    ser.drawImage(
        image=img,
        offset=galsim.PositionD(x=x0, y=y0),
        scale=PIXEL_SCALE,
        gain=1.8,
        area=collecting_area,
    )

    return img.array.flatten()


def mean_profile_metrics(measurements):
    if not measurements:
        raise ValueError("At least one measurement is required.")

    mean_metrics = {
        key: float(np.mean([metrics[key] for metrics in measurements]))
        for key in measurements[0]
        if key != "function"
    }
    mean_metrics["function"] = measurements[0]["function"]

    return mean_metrics


def case1(n_galaxies=20):
    data, _, catalog = get_data()

    if not 1 <= n_galaxies <= len(catalog):
        raise ValueError("n_galaxies must be between 1 and len(catalog).")

    @profile_resources()
    def get_moments(data, catalog, index):
        cutout = make_cutout(data, catalog, index)
        return galsim.hsm.FindAdaptiveMom(cutout, strict=False)

    moments = []
    measurements = []

    for index in range(n_galaxies):
        shape, metrics = get_moments(data, catalog, index)
        moments.append(shape)
        measurements.append(metrics)

    return moments, mean_profile_metrics(measurements)


def case2(n_galaxies=10):
    data, err, catalog = get_data()

    if not 1 <= n_galaxies <= len(catalog):
        raise ValueError("n_galaxies must be between 1 and len(catalog).")

    psf_obj = make_psf()

    @profile_resources()
    def fit_sersic(data, err, catalog, index):
        flux = convert_flux(-2.5 * np.log10(catalog["F106"][index]))

        p0 = [
            catalog["n"][index],
            catalog["half_light_radius"][index],
            flux,
            catalog["pa"][index] % 360,
            0.0,
            0.0,
            catalog["ba"][index],
        ]

        cutout = make_cutout(data, catalog, index)
        errstamp = make_cutout(err, catalog, index, err=True)
        observed = cutout.array.flatten()

        if not np.all(np.isfinite(observed)):
            raise ValueError(
                f"Non-finite science pixels for catalog index {index}."
            )

        if not np.all(np.isfinite(errstamp) & (errstamp > 0)):
            raise ValueError(
                f"Uncertainties must be finite and positive "
                f"for catalog index {index}."
            )

        ny, nx = cutout.array.shape
        lower = [0.3, 0.01, 1e-11, 0, -nx / 2, -ny / 2, 1e-3]
        upper = [6.2, 4.0, 0.1, 360, nx / 2, ny / 2, 1]

        if not np.all(
            np.isfinite(p0)
            & (np.asarray(p0) >= lower)
            & (np.asarray(p0) <= upper)
        ):
            raise ValueError(
                f"Initial parameters are outside the fitting bounds "
                f"for catalog index {index}: {p0}"
            )

        # curve_fit receives numeric xdata; the image and PSF stay in the closure.
        def model(pixel_indices, n, hlr, influx, pa, x0, y0, q):
            return sersic_mod(
                cutout, psf_obj, n, hlr, influx, pa, x0, y0, q
            )

        pout, pcov = curve_fit(
            model,
            np.arange(observed.size),
            observed,
            sigma=errstamp,
            p0=p0,
            bounds=(lower, upper),
        )

        return pout, pcov

    results = []
    measurements = []

    for index in range(n_galaxies):
        fit, metrics = fit_sersic(data, err, catalog, index)
        results.append(fit)
        measurements.append(metrics)

    return results, mean_profile_metrics(measurements)