import numpy as np
import asdf
from astropy.io import fits
import gwcs
import warnings
from astropy.modeling.models import (
    Shift, Polynomial2D, Pix2Sky_TAN, RotateNative2Celestial, Mapping)
from astropy import wcs as fits_wcs
import astropy.units as u
import astropy.coordinates
from gwcs import coordinate_frames as cf
import astropy.time
import pandas as pd
import s3fs
from astropy.table import Table
from pathlib import Path


def wcs_from_fits_header(header):
    """Convert a FITS WCS to a GWCS.

    This function reads SIP coefficients from a FITS WCS and implements
    the corresponding gWCS WCS.
    Copied from romanisim/wcs.py

    Parameters
    ----------
    header : astropy.io.fits.header.Header
        FITS header

    Returns
    -------
    wcs : gwcs.wcs.WCS
        gwcs WCS corresponding to header
    """

    # NOTE: this function ignores table distortions

    def coeffs_to_poly(mat, degree):
        pol = Polynomial2D(degree=degree)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                if 0 < i + j <= degree:
                    setattr(pol, f'c{i}_{j}', mat[i, j])
        return pol

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', fits_wcs.FITSFixedWarning)
        w = fits_wcs.WCS(header)
    ny, nx = header['NAXIS2'] + 1, header['NAXIS1'] + 1
    x0, y0 = w.wcs.crpix

    cd = w.wcs.piximg_matrix

    cfx, cfy = np.dot(cd, [w.sip.a.ravel(), w.sip.b.ravel()])
    a = np.reshape(cfx, w.sip.a.shape)
    b = np.reshape(cfy, w.sip.b.shape)
    a[1, 0] = cd[0, 0]
    a[0, 1] = cd[0, 1]
    b[1, 0] = cd[1, 0]
    b[0, 1] = cd[1, 1]

    polx = coeffs_to_poly(a, w.sip.a_order)
    poly = coeffs_to_poly(b, w.sip.b_order)

    # construct GWCS:
    det2sky = (
        (Shift(-x0) & Shift(-y0)) | Mapping((0, 1, 0, 1)) | (polx & poly)
        | Pix2Sky_TAN() | RotateNative2Celestial(*w.wcs.crval, header['LONPOLE'])
    )

    detector_frame = cf.Frame2D(name="detector", axes_names=("x", "y"),
                                unit=(u.pix, u.pix))
    sky_frame = cf.CelestialFrame(
        reference_frame=getattr(astropy.coordinates, w.wcs.radesys).__call__(),
        name=w.wcs.radesys,
        unit=(u.deg, u.deg)
    )
    pipeline = [(detector_frame, det2sky), (sky_frame, None)]
    gw = gwcs.WCS(pipeline)
    gw.bounding_box = ((-0.5, nx - 0.5), (-0.5, ny - 0.5))

    return gw


class FitsToAsdf(object):
    def __init__(self, fitspath, file_in_s3=True, lazy_load=True,
                 fsspec_kwargs={"anon": True}):
        """
        FitsToAsdf object that allows the conversion from FITS to ASDF assuming
        the same format of the Open Universe Simulations (i.e. 3 HDUs)

        Parameters:
        -----------
        fitspath (str): Path to FITS file to convert.
        file_in_s3 (bool): It enables the ability to read files in S3 buckets.
        lazy_load (bool): If `True` it skips populating self.data, self.err, and self.dq,
            reading only the fits headers.
        fsspec_kwargs (dict): Dictionary to pass along to fits.open(**fsspec_kwargs) that contains
            S3 reading settings. By default we set anonymous file retrieval.
        """
        # Initialization
        self.fitspath = fitspath
        self.file_in_s3 = file_in_s3
        self.fsspec_kwargs = fsspec_kwargs
        self.lazy_load = lazy_load
        self.data = None
        self.err = None
        self.dq = None
        self.wcs = None
        self.catalogs = None
        self.fitsheader = None
        if isinstance(self.fitspath, str):
            if self.file_in_s3:
                self.read_s3bucket(load_data=not (self.lazy_load))
            else:  # If the files are not in an S3 bucket and you have the correct path
                if not self.lazy_load:
                    f = fits.open(self.fitspath, lazy_load=self.lazy_load)
                    self.fitsheader = f[1].header.copy()
                    self.data = f[1].data.copy()
                    self.err = f[2].data.copy()
                    self.dq = f[3].data.copy()
                    f.close()
                else:
                    self.fitsheader = fits.getheader(self.fitspath, 1)
        else:
            raise NotImplementedError(
                'Expected path to FITS file. No other mode available yet.')

    def read_s3bucket(self, load_data=False):
        """
        Method to retrieve FITS data from an S3 bucket

        Parameters:
        -----------
        load_data (bool): If `True` populates the data arrays in the FitsToAsdf object.
            Otherwise, it just populates self.fitsheader.
        """
        with fits.open(self.fitspath, lazy_load=self.lazy_load,
                       fsspec_kwargs=self.fsspec_kwargs) as f:
            if load_data:
                self.fitsheader = f[1].header.copy()
                self.data = f[1].data.copy()
                self.err = f[2].data.copy()
                self.dq = f[3].data.copy()
            else:
                self.fitsheader = f[1].header.copy()

    def fitsheader_to_dict(self):
        """
        Method to convert the FITS header to a plain dictionary
        """
        if self.fitsheader is not None:
            hdr_out = {}
            for key, value in self.fitsheader.items():
                hdr_out[key] = value
            return hdr_out
        else:
            raise ValueError('self.fitsheader is empty, \
                             please load the header first')

    def build_gwcs(self):
        """
        Buld output gwcs for the ASDF file
        """
        if self.fitsheader is None:
            raise ValueError('self.fitsheader is empty!')
        else:
            self.wcs = wcs_from_fits_header(self.fitsheader)

    def fetch_catalogs(self, add_point_sources=True, add_galaxies=True, add_transients=True, use_cache=False, cache_path='ou_catalog_cache'):
        """
        Method to collect all the sources that lie within the data product.

        Parameters:
        -----------
        add_point_sources (bool): If 'True' the point source catalog will be queried to gather the point sources (e.g. stars) within the field of view.
        add_galaxies (bool): If 'True' the galaxy catalog will be queried to gather the galaxies within the field of view.
        add_transients (bool):If 'True' the transient catalog will be queried to gather the transients within the field of view.
        use_cache (bool): If 'True' the catalog files will be saved to a local path (specified by `cache_path`) to faster querying. This is only recommended when running many files on a private, non-cloud computer.
        cache_path (str): The filepath to the directory where the catalog files should be saved if `use_cache = True`.

        Attempt to collect the catalogs of stars, galaxies, and transients present in the simulated data. If not catalog exists, return None
        """
        # make sure wcs is built so we can identify which sources should be on the detector
        if self.wcs is None:
            self.build_gwcs()

        # Define filenames
        ps_general_cat_file = 'pointsource_10307.parquet'
        ps_flux_cat_file = 'pointsource_flux_10307.parquet'
        gal_cat_file = 'galaxy_10307.parquet'
        gal_flux_cat_file = 'galaxy_flux_10307.parquet'
        trans_cat_file = 'snana_10307.parquet'

        s3 = s3fs.S3FileSystem(anon=True)

        # decide if we should use a cache
        s3_path = 's3://nasa-irsa-simulations/openuniverse2024/roman/preview/roman_rubin_cats_v1.1.2_faint'
        if use_cache:
            cat_path = Path(cache_path)
            cat_path.mkdir(parents=True, exist_ok=True)
            # ensure all the files exist in the cache
            all_filenames = [ps_general_cat_file, ps_flux_cat_file, gal_cat_file, gal_flux_cat_file, trans_cat_file]
            for fn in all_filenames:
                if not (cat_path / fn).exists():
                    read_cat = pd.read_parquet(s3_path +'/'+ fn, filesystem=s3)
                    read_cat.to_parquet(path=cat_path / fn)
            cat_path = str(cat_path.resolve())
            fs = None
        else:
            cat_path = s3_path 
            fs = s3

        cat_path += '/'

        # build out the corners of the detector
        detector_corners = [self.wcs(0,0), self.wcs(0,4088), self.wcs(4088,4088), self.wcs(4088,0)]
        min_ra = min([c[0] for c in detector_corners])
        max_ra = max([c[0] for c in detector_corners])
        min_dec = min([c[1] for c in detector_corners])
        max_dec = max([c[1] for c in detector_corners])

        self.catalogs = {}

        if add_point_sources:
            ps_cat = pd.read_parquet(cat_path + ps_general_cat_file, filesystem=fs)

            # determine which sources are on the detector. Narrow down the full catalog to a smaller number as the numerical inverse takes a long time with >10k sources
            on_detector_mask = ((ps_cat['ra'] >= min_ra) & (ps_cat['ra'] <= max_ra)) & ((ps_cat['dec'] >= min_dec) & (ps_cat['dec'] <= max_dec))
            possible_ps_cat = ps_cat[on_detector_mask]
            possible_ps_xs, possible_ps_ys = self.wcs.world_to_pixel(possible_ps_cat['ra'], possible_ps_cat['dec'])

            # Trim the possible catalog to only keep sources on the detector
            good_ps_cat = possible_ps_cat[(~np.isnan(possible_ps_xs)) & (~np.isnan(possible_ps_ys))]

            # clean up the data before reading more in
            del ps_cat, possible_ps_cat, possible_ps_xs, possible_ps_ys

            # exctract the source fluxes and merge to create a single catalog
            ps_flux_cat = pd.read_parquet(cat_path + ps_flux_cat_file, filesystem=fs)
            good_ps_flux_cat = ps_flux_cat[ps_flux_cat['id'].isin(good_ps_cat['id'])]
            full_ps_cat = pd.merge(good_ps_cat, good_ps_flux_cat, on='id')

            # salt2params is an unknown type that cannot be serialized, but is also None for all values so omitting
            full_ps_cat.drop('salt2_params', axis=1, inplace=True)

            ps_table = Table.from_pandas(full_ps_cat)

            # clean up point sources
            del good_ps_cat, ps_flux_cat, good_ps_flux_cat, full_ps_cat

            self.catalogs['point_sources'] = ps_table
        else:
            self.catalogs['point_sources'] = None

        if add_galaxies:
            gal_cat = pd.read_parquet(cat_path + gal_cat_file, filesystem=fs)
            on_detector_mask = ((gal_cat['ra'] >= min_ra) & (gal_cat['ra'] <= max_ra)) & ((gal_cat['dec'] >= min_dec) & (gal_cat['dec'] <= max_dec))
            possible_gal_cat = gal_cat[on_detector_mask]
            possible_gal_xs, possible_gal_ys = self.wcs.world_to_pixel(possible_gal_cat['ra'], possible_gal_cat['dec'])

            good_gal_cat = possible_gal_cat[(~np.isnan(possible_gal_xs)) & (~np.isnan(possible_gal_ys))]

            del gal_cat, possible_gal_cat, possible_gal_xs, possible_gal_ys

            gal_flux_cat = pd.read_parquet(cat_path + gal_flux_cat_file, filesystem=fs)
            good_gal_flux_cat = gal_flux_cat[gal_flux_cat['galaxy_id'].isin(good_gal_cat['galaxy_id'])]
            full_gal_cat = pd.merge(good_gal_cat, good_gal_flux_cat, on='galaxy_id')

            del good_gal_cat, gal_flux_cat, good_gal_flux_cat

            gal_table = Table.from_pandas(full_gal_cat)

            del full_gal_cat

            self.catalogs['galaxies'] = gal_table
        else:
            self.catalogs['galaxies'] = None

        if add_transients:
            trans_cat = pd.read_parquet(cat_path + trans_cat_file, filesystem=fs)
            possible_trans_cat = trans_cat[((trans_cat['ra'] >= min_ra) & (trans_cat['ra'] <= max_ra)) & ((trans_cat['dec'] >= min_dec) & (trans_cat['dec'] <= max_dec))]
            possible_trans_xs, possible_trans_ys = self.wcs.world_to_pixel(possible_trans_cat['ra'], possible_trans_cat['dec'])

            good_trans_cat = possible_trans_cat[(~np.isnan(possible_trans_xs)) & (~np.isnan(possible_trans_ys))]

            del trans_cat, possible_trans_cat, possible_trans_xs, possible_trans_ys

            #  model_params are arrays and asdf was unhappy trying to save them so they are unpacked here. Most only contain a template index, but ~1/6th of the time they contain a full suite of model parameters.
            good_trans_cat.reset_index(drop=True, inplace=True)
            n_cat_rows = len(good_trans_cat.index)
            template_indices = np.empty(n_cat_rows) * np.nan
            salt2_x0s = np.empty(n_cat_rows) * np.nan
            salt2_x1s = np.empty(n_cat_rows) * np.nan
            salt2_cs = np.empty(n_cat_rows) * np.nan
            salt2_mBs = np.empty(n_cat_rows) * np.nan
            salt2_alphas = np.empty(n_cat_rows) * np.nan
            salt2_betas = np.empty(n_cat_rows) * np.nan
            salt2_gammaDMs = np.empty(n_cat_rows) * np.nan

            for i, row in good_trans_cat.iterrows():
                template_indices[i] = row['model_param_values'][0]
                if len(row['model_param_names']) > 1:
                    salt2_x0s[i] = row['model_param_values'][1]
                    salt2_x1s[i] = row['model_param_values'][2]
                    salt2_cs[i] = row['model_param_values'][3]
                    salt2_mBs[i] = row['model_param_values'][4]
                    salt2_alphas[i] = row['model_param_values'][5]
                    salt2_betas[i] = row['model_param_values'][6]
                    salt2_gammaDMs[i] = row['model_param_values'][7]

            good_trans_cat['model_template_index'] = template_indices
            good_trans_cat['salt2_x0s'] = salt2_x0s
            good_trans_cat['salt2_x1s'] = salt2_x1s
            good_trans_cat['salt2_cs'] = salt2_cs
            good_trans_cat['salt2_mBs'] = salt2_mBs
            good_trans_cat['salt2_alphas'] = salt2_alphas
            good_trans_cat['salt2_betas'] = salt2_betas
            good_trans_cat['salt2_gammaDMs'] = salt2_gammaDMs
            
            good_trans_cat.drop(columns=['model_param_names', 'model_param_values'], inplace=True)

            trans_table = Table.from_pandas(good_trans_cat)

            del good_trans_cat

            self.catalogs['transients'] = trans_table
        else:
            self.catalogs['transients'] = None

    def write(self, path, include_raw_header=False):
        """
        Method to write the file to disk

        Parameters:
        -----------
        path (str): Output path and filename
        include_raw_header (bool): If `True` include a copy of the raw FITS header
           as a dictionary in the ASDF file.
        """
        tree = {}
        # Fill out the data, err, dq blocks
        if self.data is None:
            self.read_s3bucket(load_data=True)
        tree['data'] = self.data
        tree['err'] = self.err
        tree['dq'] = self.dq

        # Fill out the gwcs block
        if self.wcs is None:
            self.build_gwcs()
        tree['wcs'] = self.wcs

        # check for catalogs
        if self.catalogs is None:
            self.fetch_catalogs()
        tree['catalogs'] = self.catalogs

        # Populate metadata
        if self.fitsheader is not None:
            tree['meta'] = {}
            if include_raw_header:
                tree['meta']['raw_header'] = self.fitsheader_to_dict()
            tree['meta']['telescope'] = 'ROMAN'
            tree['meta']['instrument'] = 'WFI'
            tree['meta']['optical_element'] = self.fitsheader['FILTER']
            tree['meta']['detector'] = f'SCA{self.fitsheader["SCA_NUM"]:02d}'
            tree['meta']['ra_pointing'] = self.fitsheader['RA_TARG']
            tree['meta']['dec_pointing'] = self.fitsheader['DEC_TARG']
            tree['meta']['zptmag'] = self.fitsheader['ZPTMAG']
            tree['meta']['sky_mean'] = self.fitsheader['SKY_MEAN']
            tree['meta']['pa_fpa'] = self.fitsheader['PA_FPA']
            tree['meta']['obs_date'] = astropy.time.Time(self.fitsheader['DATE-OBS'])
            tree['meta']['mjd_obs'] = astropy.time.Time(self.fitsheader['MJD-OBS'], format='mjd')   
            tree['meta']['exp_time'] = self.fitsheader['EXPTIME']
            tree['meta']['nreads'] = 1
            # Constant gain = 1 (Troxel private comm.)
            tree['meta']['gain'] = 1.0
        else:
            raise ValueError('`self.fitsheader` is empty. Please load a FITS header.')

        af = asdf.AsdfFile({'roman': tree})
        af.write_to(path)
