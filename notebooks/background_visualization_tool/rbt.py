"""
Roman background model (data-only, URL-based).

This module loads and prepares background data for Roman observations
directly from the STScI-hosted straylight cache.

All plotting is handled elsewhere. This file
intentionally contains **no plotting code**.
"""

import io
import copy
import urllib.request
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import healpy
import numpy as np
from scipy.interpolate import interp1d

#from astropy.coordinates import SkyCoord
#from astropy import units as u

__version__ = "no_version_info"

#import tgt_vis

try:
    from notebook_data_dependencies import get_remote_data
except ModuleNotFoundError as exc:
    if exc.name != "notebook_data_dependencies":
        raise
    # A full repository checkout can use the shared helper without installing
    # the repository package or adding a copy/symlink to this notebook folder.
    helper_path = Path(__file__).resolve().parents[2] / "shared" / "notebook_data_dependencies.py"
    if not helper_path.is_file():
        raise ModuleNotFoundError(
            "RBVT needs the repository's shared/notebook_data_dependencies.py. "
            "Clone the full roman_notebooks repository, or install its helper "
            "package with 'pip install -e /path/to/roman_notebooks' and set "
            "ROMAN_REFDATA_MANIFEST to that release's refdata_dependencies.yaml."
        ) from exc
    helper_spec = spec_from_file_location("_rbvt_data_dependencies", helper_path)
    helper_module = module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper_module)
    get_remote_data = helper_module.get_remote_data

_CACHE = get_remote_data("roman_straylight_cache")
_HEALPIX = get_remote_data("healpix")


def validate_reference_data(wave_path=None, thermal_path=None):
    """Read and validate the spectral grids before starting the Bokeh app."""
    refdata = Path(__file__).parent / "refdata"
    wave_path = Path(wave_path) if wave_path is not None else refdata / get_remote_data("wave_file")
    thermal_path = Path(thermal_path) if thermal_path is not None else refdata / get_remote_data("thermal_file")

    def read_table(path):
        try:
            return np.loadtxt(path, delimiter="," if path == thermal_path else None, ndmin=2)
        except (OSError, ValueError) as exc:
            raise ValueError(
                f"Cannot read reference file {path}. Restore the refdata files "
                "from the same repository release as this notebook."
            ) from exc

    wave = read_table(wave_path)
    thermal = read_table(thermal_path)
    for path, table, columns in [(wave_path, wave, 1), (thermal_path, thermal, 2)]:
        if (table.shape[1] != columns or table.shape[0] < 2
                or not np.isfinite(table).all()
                or not np.all(np.diff(table[:, 0]) > 0)):
            raise ValueError(
                f"Invalid reference file {path}: expected at least two rows, "
                f"{columns} numeric column(s), finite values, and strictly "
                "increasing wavelengths. Restore the refdata files from the "
                "same repository release as this notebook."
            )
    return wave[:, 0], thermal[:, 0], thermal[:, 1]


class background:
    """
    Main background class. Loads background data for a specific (RA, DEC)
    directly from the online cache at STScI.

    Parameters
    ----------
    ra : float
        Right ascension in decimal degrees
    dec : float
        Declination in decimal degrees
    wavelength : float
        Wavelength (micron)
    thresh : float, optional
        Background threshold (default 1.1)
    """

    def __init__(self, ra, dec, wavelength, thresh=1.1):
        # Remote source (no local caching)
        self.remote_dir = _CACHE["cache_dir"]
        self.cache_version = str(_CACHE["cache_version"])

        # Static refdata (still read from local repo files)
        self.local_path = Path(__file__).parent / "refdata"
        self.wave_file = get_remote_data("wave_file")
        self.thermal_file = get_remote_data("thermal_file")

        # Healpix details used by cache partitioning
        self.nside = int(_HEALPIX["nside"])
        ordering = str(_HEALPIX["ordering"]).upper()
        if ordering not in {"RING", "NESTED"}:
            raise ValueError("HEALPix ordering must be RING or NESTED.")
        self.nest = ordering == "NESTED"

        # Load static spectral grids / thermal background
        self.abs_wave_array, self.thermal_wave_array, self.thermal_bg = self.read_static_data()
        self.sl_abs_nwave = self.abs_wave_array.size
        self.sl_thermal_nwave = self.thermal_wave_array.size

        # Inputs
        self.ra = ra
        self.dec = dec
        self.wavelength = wavelength
        self.thresh = thresh

        # Pick the remote filename for this sky position
        self.cache_file = self.myfile_from_healpix(ra, dec)

        # Load and prepare all per-position data
        self.bkg_data = self.read_bkg_data_from_url(self.cache_file)

        # Initialize bathtub at the input wavelength
        self.make_bathtub(wavelength)

    # ---------- File / data loading ----------

    def myfile_from_healpix(self, ra, dec):
        """Map (RA, DEC) to the cache file path via healpix indexing."""
        healpix_idx = healpy.pixelfunc.ang2pix(self.nside, ra, dec, nest=self.nest, lonlat=True)
        healpix_str_pad = str(healpix_idx).zfill(6)
        return f"{healpix_str_pad[0:4]}/sl_pix_{healpix_str_pad}.bin"

    def read_static_data(self):
        """Load static wavelength grid and thermal curve from refdata."""
        return validate_reference_data(
            self.local_path / self.wave_file,
            self.local_path / self.thermal_file,
        )

    # ---------- Remote cache reading ----------

    def read_bkg_data_from_url(self, cache_file, verbose=False):
        """
        Read one Roman background file (.bin) directly from the STScI-hosted URL,
        parse it into arrays, and return the structured dict.
        """
        url = self.remote_dir.rstrip("/") + "/" + cache_file
        print(f"Loading background file from {url}")
        with urllib.request.urlopen(url) as response:
            file_data = response.read()

        buf = io.BytesIO(file_data)

        # Dtypes for cache reading
        nonzodi_pix_dtype = np.dtype(
            [
                ("pix_ra", "f8"),
                ("pix_dec", "f8"),
                ("upos", [("x", "f8"), ("y", "f8"), ("z", "f8")]),
                ("nonzodi_bg", ("f8", self.sl_abs_nwave)),
                ("iday_index", ("i4", 366)),
            ]
        )
        zodi_sl_dtype = np.dtype(
            [
                ("zodi_bg", ("f8", self.sl_abs_nwave)),
                ("stray_light_bg", ("f8", self.sl_abs_nwave)),  # unused for Roman (often -1)
            ]
        )

        # Parse directly from in-memory buffer
        nonzodi_bg = np.frombuffer(buf.getbuffer(), dtype=nonzodi_pix_dtype, count=1, offset=0)
        offset = nonzodi_pix_dtype.itemsize
        zodi_sl_bgs = np.frombuffer(buf.getbuffer(), dtype=zodi_sl_dtype, offset=offset)

        ra = nonzodi_bg["pix_ra"]
        dec = nonzodi_bg["pix_dec"]
        pos = nonzodi_bg["upos"]
        nonzodi_bg_flux = nonzodi_bg["nonzodi_bg"][0]
        date_map = nonzodi_bg["iday_index"][0]  # 366 entries: -1 for invalid, >=0 for valid mapping

        # Initial "calendar" are the day-of-year indices with data
        # (sun-angle constraints are already encoded in the cache date_map)
        calendar = np.where(date_map >= 0)[0]
        if verbose:
            print("Valid days in file:", calendar.size, "of", len(date_map))

        # Map from calendar (day-of-year) to the sequential index space in zodi_sl_bgs
        # The file packs only valid days sequentially; the mapping is via date_map
        packed_index = date_map[calendar]  # guaranteed >= 0 for valid days
        # extra safety: ensure indices are in range
        packed_index = packed_index[packed_index < len(zodi_sl_bgs)]

        # Extract zodi on the valid packed indices
        zodi_bgs_full = zodi_sl_bgs["zodi_bg"]
        zodi_bgs = zodi_bgs_full[packed_index]

        Ndays = len(packed_index)

        # Interpolate to the thermal wavelength grid
        zodi_bgs_int = np.zeros((Ndays, self.sl_thermal_nwave))
        for dd in range(Ndays):
            zodi_bgs_int[dd] = self.interpolate_spec(
                self.abs_wave_array, zodi_bgs[dd], self.thermal_wave_array, fill=0.0
            )
        nonzodi_bg_int = self.interpolate_spec(
            self.abs_wave_array, nonzodi_bg_flux, self.thermal_wave_array, fill=0.0
        )

        # Base total = static (nonzodi + thermal) + zodi(day)
        total_bg = np.tile(nonzodi_bg_int + self.thermal_bg, (Ndays, 1)) + zodi_bgs_int

        # Base total = static (nonzodi + thermal) + zodi(day)
        total_bg = np.tile(nonzodi_bg_int + self.thermal_bg, (Ndays, 1)) + zodi_bgs_int

        return {
            "calendar": np.array(calendar),      # day-of-year indices present in the cache
            "ra": ra,
            "dec": dec,
            "pos": pos,
            "wave_array": self.thermal_wave_array,
            "nonzodi_bg": nonzodi_bg_int,
            "thermal_bg": self.thermal_bg,
            "zodi_bg": zodi_bgs_int,
            "total_bg": total_bg,
        }

    # ---------- Spectral modification / interpolation ----------


    def interpolate_spec(self, wave, specin, new_wave, fill=np.nan):
        """Interpolate spectral data to a new wavelength grid."""
        f = interp1d(wave, specin, bounds_error=False, fill_value=fill)
        return f(new_wave)

    # ---------- Bathtub calculation (no plotting) ----------

    def make_bathtub(self, wavelength):
        """
        Interpolate per-day background and components at a given wavelength,
        and compute count of 'good' days below the chosen threshold.
        """
        self.wavelength = wavelength
        wave_array = self.bkg_data["wave_array"]

        total_thiswave = interp1d(wave_array, self.bkg_data["total_bg"], bounds_error=True)(wavelength)
        zodi_thiswave = interp1d(wave_array, self.bkg_data["zodi_bg"], bounds_error=True)(wavelength)
        thermal_thiswave = interp1d(wave_array, self.bkg_data["thermal_bg"], bounds_error=True)(wavelength)
        nonzodi_thiswave = interp1d(wave_array, self.bkg_data["nonzodi_bg"], bounds_error=True)(wavelength)

        themin = np.min(total_thiswave)
        good_days = int(np.sum(total_thiswave < themin * self.thresh))

        self.bathtub = {
            "wavelength": wavelength,
            "themin": themin,
            "good_days": good_days,
            "total_thiswave": total_thiswave,
            "zodi_thiswave": zodi_thiswave,
            "thermal_thiswave": thermal_thiswave,
            "nonzodi_thiswave": nonzodi_thiswave,
        }
