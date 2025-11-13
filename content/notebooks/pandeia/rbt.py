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
from pathlib import Path

import healpy
import numpy as np
from scipy.interpolate import interp1d

from astropy.coordinates import SkyCoord
from astropy import units as u

__version__ = "no_version_info"

import tgt_vis


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
        self.remote_dir = "https://archive.stsci.edu/missions/roman/simulations/straylight/sl_cache/"
        self.cache_version = "2025.9"

        # Static refdata (still read from local repo files)
        self.local_path = Path(__file__).parent / "refdata"
        self.wave_file = "std_spectrum_wavelengths.txt"
        self.thermal_file = "thermal_curve_roman_rryan_v1.0.csv"

        # Healpix details used by cache partitioning
        self.nside = 128

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
        healpix_idx = healpy.pixelfunc.ang2pix(self.nside, ra, dec, nest=False, lonlat=True)
        healpix_str_pad = str(healpix_idx).zfill(6)
        return f"{healpix_str_pad[0:4]}/sl_pix_{healpix_str_pad}.bin"

    def read_static_data(self):
        """Load static wavelength grid and thermal curve from refdata."""
        abs_wave_array = np.loadtxt(self.local_path / self.wave_file)
        thermal = np.transpose(np.genfromtxt(self.local_path / self.thermal_file, delimiter=","))
        thermal_wave_array = thermal[0]
        thermal_flux = thermal[1]
        return abs_wave_array, thermal_wave_array, thermal_flux

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
        calendar = np.where(date_map >= 0)[0]
        if verbose:
            print("Valid days in file:", calendar.size, "of", len(date_map))

        # Apply Roman sun-angle constraint using tgt_vis (visibility mask)
        target = SkyCoord(self.ra * u.degree, self.dec * u.degree, frame="icrs")
        c = tgt_vis.compute_visibility(
            target, report=True, fileout="vis_debug.txt",
            interval_sampling_days=1, interval_start_time=None, interval_duration_days=366,
        )
        c.get_good_angles()
        good_indices = np.where(c.df_results["good_angles"].values)[0]  # day-of-year indices (0..365)

        # Keep only days that are both in the file and visible
        calendar = calendar[np.isin(calendar, good_indices)]

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

        # Apply NIRCam-informed modification to total and components
        for dd in range(Ndays):
            if dd == 0:
                mod_wave_array, mod_total_bg_first = self.modify_background(total_bg[dd])
                mod_total_bg = np.zeros((Ndays, len(mod_total_bg_first)))
                mod_total_bg[dd] = mod_total_bg_first
            else:
                _, mod_total_bg[dd] = self.modify_background(total_bg[dd])

        mod_zodi_bgs_int = np.zeros((Ndays, self.sl_thermal_nwave))
        for dd in range(Ndays):
            _, mod_zodi_bgs_int[dd] = self.modify_background(zodi_bgs_int[dd])
        _, mod_nonzodi_flux = self.modify_background(nonzodi_bg_int)

        return {
            "calendar": np.array(calendar),      # day-of-year indices that survived visibility gating
            "ra": ra,
            "dec": dec,
            "pos": pos,
            "wave_array": self.thermal_wave_array,
            "nonzodi_bg": mod_nonzodi_flux,
            "thermal_bg": self.thermal_bg,
            "zodi_bg": mod_zodi_bgs_int,
            "total_bg": mod_total_bg,
        }

    # ---------- Spectral modification / interpolation ----------

    def modify_background(self, bg_flux):
        """
        E. Han's modification to incorporate NIRCam measurements.
        Returns (modified_wavelength_grid, modified_flux_interpolated_to_thermal_grid).
        """
        bg_wvl_to_mod = self.thermal_wave_array
        bg_flux_to_mod = copy.deepcopy(bg_flux)

        # Smooth the hard 0.5 μm cutoff to 0.4–0.5 μm
        first_pass = np.where((bg_wvl_to_mod >= 0.4) & (bg_wvl_to_mod <= 0.5))[0]
        if first_pass.size > 1:
            bg_flux_to_mod[first_pass] = np.interp(
                bg_wvl_to_mod[first_pass],
                [bg_wvl_to_mod[first_pass[0]], bg_wvl_to_mod[first_pass[-1]]],
                [bg_flux_to_mod[first_pass[0]], bg_flux_to_mod[first_pass[-1]]],
            )

        # NIRCam pivot wavelengths and ratios (technical report)
        pivot_wvl = [0.705, 0.902, 1.154, 1.501]
        measured_bg_ratio = [0.656, 0.680, 0.819, 0.982]

        bg_model = np.interp(pivot_wvl, bg_wvl_to_mod, bg_flux_to_mod)
        measured_bg_nircam = np.array(measured_bg_ratio) * bg_model

        # Quadratic fit of ratio for extrapolation 0.41–0.624 μm
        fit = np.polyfit(pivot_wvl, measured_bg_ratio, 2)
        wvl_fix_indices = np.where((bg_wvl_to_mod >= 0.41) & (bg_wvl_to_mod <= 0.624))[0]
        bg_wvl_to_fix = bg_wvl_to_mod[wvl_fix_indices]
        solution = fit[0] * bg_wvl_to_fix**2 + fit[1] * bg_wvl_to_fix + fit[2]
        bg_flux_polyfit = solution * bg_flux_to_mod[wvl_fix_indices]

        original_blue = np.where(bg_wvl_to_mod <= 0.41)[0]
        original_red = np.where(bg_wvl_to_mod >= 1.668)[0]

        bg_wvl_mod = np.concatenate((
            bg_wvl_to_mod[original_blue],
            bg_wvl_to_fix,
            np.array(pivot_wvl),
            bg_wvl_to_mod[original_red]
        ))
        bg_flux_mod = np.concatenate((
            bg_flux_to_mod[original_blue],
            bg_flux_polyfit,
            measured_bg_nircam,
            bg_flux_to_mod[original_red]
        ))

        # Interpolate back to the thermal grid
        bg_flux_mod_interp = self.interpolate_spec(
            bg_wvl_mod, bg_flux_mod, self.thermal_wave_array, fill=0.0
        )
        return bg_wvl_mod, bg_flux_mod_interp

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

    # ---------- Optional writers (no plotting) ----------

    def write_bathtub(self, bathtub_file='background_versus_day.txt'):
        """Write bathtub (total vs. day) to a text file."""
        with open(bathtub_file, 'w') as f:
            header_text = [
                f"# Output of roman_backgrounds version {__version__}\n",
                f"# background cache version {self.cache_version}\n",
                "\n",
                f"# for RA={self.ra}, DEC={self.dec} at wavelength={self.wavelength} micron\n",
                "# Columns:\n",
                "# - Calendar day (Jan1=0)\n",
                "# - Total background (MJy/sr)\n",
            ]
            f.writelines(header_text)
            for i, calendar_day in enumerate(self.bkg_data['calendar']):
                f.write(f"{calendar_day}    {self.bathtub['total_thiswave'][i]:5.4f}\n")

    def write_background(self, background_file='background.txt', thisday=None):
        """Write full background spectrum (and components) for a given calendar day."""
        calendar = self.bkg_data['calendar']
        if thisday in calendar:
            thisday_index = np.where(thisday == calendar)[0][0]
        else:
            print(f"The input calendar day {thisday} is not available")
            return

        with open(background_file, 'w') as f:
            header_text = [
                f"# Output of Roman_backgrounds version {__version__}\n",
                f"# background cache version {self.cache_version}\n",
                "\n",
                f"# for RA={self.ra}, DEC={self.dec} On calendar day {thisday}\n",
                "# Columns:\n",
                "# - Wavelength [micron]\n",
                "# - Total background (MJy/sr)\n",
                "# - In-field zodiacal light (MJy/sr)\n",
                "# - In-field galactic light (MJy/sr)\n",
                "# - Thermal self-emission (MJy/sr)\n",
            ]
            f.writelines(header_text)

            for i, wavelength in enumerate(self.bkg_data['wave_array']):
                f.write(
                    f"{wavelength:f}    "
                    f"{self.bkg_data['total_bg'][thisday_index][i]:5.4f}    "
                    f"{self.bkg_data['zodi_bg'][thisday_index][i]:5.4f}    "
                    f"{self.bkg_data['nonzodi_bg'][i]:5.4f}    "
                    f"{self.bkg_data['thermal_bg'][i]:5.4f}\n"
                )


# ------------ Convenience wrapper (no plotting) ------------

def get_background(
    ra, dec, wavelength, thresh=1.1, thisday=None,
    write_background=False, write_bathtub=False,
    background_file='background.txt', bathtub_file='background_versus_day.txt'
):
    """
    Create a `background` instance and (optionally) write text outputs.
    """
    bkg = background(ra, dec, wavelength, thresh=thresh)
    calendar = bkg.bkg_data["calendar"]

    print("These coordinates are observable by Roman",
          len(calendar), "days per year.")
    print("For", bkg.bathtub["good_days"], "of those days, the background is <",
          thresh, "× minimum at wavelength", wavelength, "μm")

    if write_background and thisday is not None:
        bkg.write_background(thisday=thisday, background_file=background_file)
    if write_bathtub:
        bkg.write_bathtub(bathtub_file=bathtub_file)

    return bkg
