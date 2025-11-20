"""
This is a module to predict the background levels for Roman observations,
for use in Roman proposal planning.

Bulk of the code is inherited from the JBT and some modifications were made to work for Roman.  

It accesses a precompiled background cache prepared by STScI, to do the following:
- Plot the background versus calendar day.
- Compute the number of days per year that a target is observable at low background,
  for a given wavelength and a selectable threshold.

Software is provided as-is, with no warranty. Use the latest versions of APT and ETC to confirm
the observability of any Roman targets.

"""

import os
import healpy
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

from astropy.coordinates import SkyCoord
from astropy import units as u

import copy
import pdb
import urllib
import io

__version__ = "no_version_info"


class background():
    '''
    Main background class. It is initialized with all background data for a specific
    position (RA, DEC). The wavelength at which the bathtub curve is calculated
    can be updated as needed.

    Parameters
    ----------
    ra: float
        Right ascension in decimal degrees
    dec: float
        Declination in decimal degrees
    wavelength: float
        Wavelength at which the bathtub curve is calculated, in micron
    thresh: float
        the background threshold, relative to the minimum.  Default=1.1, which corresponds to <5% above the minimum background noise.
        Note that the actual noise difference will be even smaller, as there are often other significant sources of noise than just the
        background (source shot noise, detector noise, etc.).

    Attributes
    ----------
    bkg_data: dict
        Contains all the data for the background for the input (RA,DEC) position
    bathtub:
        Contains the (RA,DEC) background information as a function of calendar day, interpolated at wavelength
    '''
    def __init__(self, ra, dec, wavelength, thresh=1.1):
        # global attributes
        self.cache_dir = 'https://archive.stsci.edu/missions/roman/simulations/straylight/sl_cache/' 
        self.cache_version = 'R2025.9'    # Corresponding Pandeia release when the cache was generated
        self.local_path = os.path.join(os.path.dirname(__file__), 'refdata')
        self.wave_file = 'std_spectrum_wavelengths.txt'  # The wavelength grid of the background cache
        self.thermal_file = 'thermal_curve_roman_rryan_v1.0.csv'  # The constant (not time variable) thermal self-emission curve
        self.nside = 128  # Healpy parameter, from generate_backgroundmodel_cache.c .
        self.abs_wave_array, self.thermal_wave_array, self.thermal_bg = self.read_static_data()
        self.sl_abs_nwave = self.abs_wave_array.size  # Size of the absolute wavelength array
        self.sl_thermal_nwave = self.thermal_wave_array.size

        # input parameters
        self.ra = ra
        self.dec = dec
        self.wavelength = wavelength
        self.thresh = thresh

        # Load variable content
        self.cache_file = self.myfile_from_healpix(ra, dec)
        self.bkg_data = self.read_bkg_data(self.cache_file)

        # Interpolate bathtub curve and package it
        self.make_bathtub(wavelength)

    def myfile_from_healpix(self, ra, dec):
        # old versions of healpy don't have lonlat
        healpix = healpy.pixelfunc.ang2pix(self.nside, ra, dec, nest=False, lonlat=True)
        # we have to pad with 0s up to 6 characters to the left to match the file name convention
        healpix_str_pad = str(healpix).zfill(6)
        file = healpix_str_pad[0:4] + "/sl_pix_" + healpix_str_pad + ".bin"
        return file

    def read_static_data(self):
        """Read static data from backgrounds package

        Parameters
        ----------
        None

        Returns
        -------
        wave_array : np.array
            Wavelength data
        thermal_flux : np.array
            Thermal flux data
        """
        # Standard wavelength array.
        abs_wave_file = os.path.join(self.local_path, self.wave_file)
        abs_wave_array = np.loadtxt(abs_wave_file)

        thermal = np.transpose(np.genfromtxt(os.path.join(self.local_path, self.thermal_file), delimiter=','))
        thermal_wave_array = thermal[0]
        thermal_flux = thermal[1]

        return abs_wave_array, thermal_wave_array, thermal_flux

    def read_bkg_data(self, cache_file, verbose=False):
        """
        Method for reading one Roman background file, and parsing it.

        Schema of each binary file in the cache:
        ----------------------------------------
        JRR verified the schema against the source code, generate_stray_light_with_threads.c.
        The cache uses a Healpix RING tesselation, with NSIDE=128.  Every point on the sky
        (tesselated tile) corresponds to one binary file, whose name includes its healpix
        pixel number, in a directory corresponding to the first 4 digits of the healpix number.

        - double RA
        - double DEC
        - double pos[3]
        - double nonzodi_bg[SL_ABS_NWAVE]
        - int[366] date_map  : This maps dates to indices.  NOTE: There are 366 days, not 365!
        - for each day in FOR:
            - double zodi_bg[SL_ABS_NWAVE]
            - double stray_light_bg[SL_ABS_NWAVE]

        parameters
        ----------
        cache_file: string

        attributes
        ----------

        """

        # Read the background file via http
        sbet_file = urllib.request.urlopen(self.cache_dir + cache_file)
        sbet_data = io.BytesIO(sbet_file.read())


        # Unpack the constant first part
        if verbose:
            print("File has", len(sbet_data), "bytes, which is", len(sbet_data) / 8., "doubles")

        # These parts are adopted and modified from 
        # https://github.com/spacetelescope/pandeia/blob/master/engine/pandeia/engine/helpers/background/multimission/accessor_funcs.py
        nonzodi_pix_dtype = np.dtype(
            [
                ('pix_ra', 'f8'),
                ('pix_dec', 'f8'),
                ('upos', [('x', 'f8'), ('y', 'f8'), ('z', 'f8')]),
                ('nonzodi_bg', ('f8', self.sl_abs_nwave)),
                ('iday_index', ('i4', 366))
            ]
        )

        zodi_sl_dtype = np.dtype(
            [
                ('zodi_bg', ('f8', self.sl_abs_nwave)),
                ('stray_light_bg', ('f8', self.sl_abs_nwave))   # Stray light doesn't exist for Roman and within the cache, they are marked as -1
            ]
        )

        nonzodi_bg = np.frombuffer(sbet_data.getbuffer(), dtype=nonzodi_pix_dtype, count=1, offset=0)
        offset = nonzodi_pix_dtype.itemsize

        ra = nonzodi_bg['pix_ra']
        dec = nonzodi_bg['pix_dec']
        pos = nonzodi_bg['upos']
        nonzodi_bg_flux = nonzodi_bg['nonzodi_bg'][0]
        
        date_map = nonzodi_bg['iday_index'][0]  #the calendar dates - the dates go from 0 to 365 days.
        if verbose:
            print("Out of", len(date_map), "days, these many are legal:", np.sum(date_map >= 0))

        calendar = np.where(date_map >= 0)[0]

        Ndays = len(calendar)
        if verbose:
            print(len(date_map), Ndays)

        # Unpack the time-variable part
        zodi_sl_bgs = np.frombuffer(sbet_data.getbuffer(), dtype=zodi_sl_dtype, offset=offset)


        # Need to interpolate the background cache into the thermal background wavelength scale
        zodi_bgs_int = np.zeros((Ndays, self.sl_thermal_nwave))
        for dd in range(0, int(Ndays)):
            # zodi_sl_bgs[dd][0]: the zodi part
            # zodi_sl_bgs[dd][1]: the stray light part
            zodi_bgs_int[dd] = self.interpolate_spec(self.abs_wave_array, zodi_sl_bgs[dd][0], self.thermal_wave_array, fill=0.0)
        nonzodi_bg_int = self.interpolate_spec(self.abs_wave_array, nonzodi_bg_flux, self.thermal_wave_array, fill=0.0)

        # Expand static background components to the same shape as zodi_bg
        total_bg = np.tile(nonzodi_bg_int + self.thermal_bg, (Ndays, 1)) + zodi_bgs_int


        # This is the additional step that is introduced as a temporary fix to make the cache work for the full Roman wavelength range. 
        # Below will be removed when the new Roman cache comes with full Roman wavelength 
        # Applying the fix to the individual components except for the thermal
        mod_zodi_bgs_int = np.zeros((Ndays, self.sl_thermal_nwave))
        mod_total_bg = copy.deepcopy(total_bg)
        for dd in range(0, int(Ndays)):
            mod_zodi_wvl, mod_zodi_flux = self.modify_background(zodi_bgs_int[dd])
            mod_zodi_bgs_int[dd] = mod_zodi_flux    
            mod_total_wvl, mod_total_bg[dd] = self.modify_background(total_bg[dd])
        mod_nonzodi_wvl, mod_nonzodi_flux = self.modify_background(nonzodi_bg_int)
        
        ############
        
        # pack everything up as a dict
        # return {'calendar': calendar, 'ra': ra, 'dec': dec, 'pos': pos, 'wave_array': self.thermal_wave_array, 'nonzodi_bg': nonzodi_bg_int,
        #         'thermal_bg': self.thermal_bg, 'zodi_bg': zodi_bgs_int, 'total_bg': total_bg}
        return {'calendar': calendar, 'ra': ra, 'dec': dec, 'pos': pos, 'wave_array': self.thermal_wave_array, 'nonzodi_bg': mod_nonzodi_flux,
                'thermal_bg': self.thermal_bg, 'zodi_bg': mod_zodi_bgs_int, 'total_bg': mod_total_bg}


    # E. Han's modification to incorporate NIRCam measurements
    def modify_background(self, bg_flux):

        # Make deep copies of the original model and keep it untouched
        bg_wvl_original = copy.deepcopy(self.thermal_wave_array)
        bg_flux_original = copy.deepcopy(bg_flux)

        bg_wvl_to_mod = self.thermal_wave_array
        bg_flux_to_mod = bg_flux

        # Make a first pass to the original cache to have a continuous decrease in flux from 0.5 micron to 0.4
        # rather than an abrupt drop of flux to 0 at 0.5 micron
        # 0 flux in the original cache means no empirical data
        first_pass = np.where((bg_wvl_to_mod >= 0.4) & (bg_wvl_to_mod <= 0.5))[0]
        bg_flux_to_mod[first_pass] = np.interp(bg_wvl_to_mod[first_pass], [bg_wvl_to_mod[first_pass[0]], bg_wvl_to_mod[first_pass[-1]]], [bg_flux_to_mod[first_pass[0]], bg_flux_to_mod[first_pass[-1]]])


        return bg_wvl_to_mod, bg_flux_to_mod #bg_flux_mod_interp


    def make_bathtub(self, wavelength):
        """
        This method interpolates a bathtub curve at a given wavelength.
        It also uses the threshold fraction ("thresh") above the minimum background, to calculate number of good days.

        parameters
        ----------
        wavelength: float

        """

        self.wavelength = wavelength
        wave_array = self.bkg_data['wave_array']

        # Use linear interpolation to provide the background at any wavelength
        total_thiswave = (interp1d(wave_array, self.bkg_data['total_bg'], bounds_error=True))(wavelength)
        zodi_thiswave = (interp1d(wave_array, self.bkg_data['zodi_bg'], bounds_error=True))(wavelength)
        thermal_thiswave = (interp1d(wave_array, self.bkg_data['thermal_bg'], bounds_error=True))(wavelength)
        nonzodi_thiswave = (interp1d(wave_array, self.bkg_data['nonzodi_bg'], bounds_error=True))(wavelength)

        themin = np.min(total_thiswave)
        good_days = int(np.sum(total_thiswave < themin * self.thresh) * 1.0)

        self.bathtub = {'wavelength': wavelength, 'themin': themin, 'good_days': good_days,
                        'total_thiswave': total_thiswave, 'zodi_thiswave': zodi_thiswave,
                        'thermal_thiswave': thermal_thiswave, 'nonzodi_thiswave': nonzodi_thiswave}

    def interpolate_spec(self, wave, specin, new_wave, fill=np.nan):
        """Interpolate spectral data

        Parameters
        ----------
        wave : np.array

        specin : np.array

        new_wave : np.array

        fill : obj

        Returns
        -------
        new_spec : np.array
            Interpolated spectrum
        """
        # With these settings, writes NaN to extrapolated regions
        f = interp1d(wave, specin, bounds_error=False, fill_value=fill)
        new_spec = f(new_wave)
        return new_spec

    def plot_background(self, fontsize=16, xrange=(0.6, 3), yrange=(1e-4, 1e4), thisday=None):
        """Plot background data

        Parameters
        ----------
        fontsize : int
            Fontsize for axes and titles
        xrange : tuple
            minimum and maximum range for x axis
        yrange : tuple
            minimum and maximum value for y axis
        thisday : int
            The day of the year to plot
        """
        wave_array = self.bkg_data['wave_array']
        calendar = self.bkg_data['calendar']

        if thisday in calendar:
            thisday_index = np.where(thisday == calendar)[0][0]
        else:
            print("The input calendar day {}".format(thisday) + " is not available")
            return

        plt.plot(wave_array, self.bkg_data['nonzodi_bg'], label="ISM")
        plt.plot(wave_array, self.bkg_data['zodi_bg'][thisday_index, :], label="Zodi")
        plt.plot(wave_array, self.bkg_data['thermal_bg'], label="Thermal")
        plt.plot(wave_array, self.bkg_data['total_bg'][thisday_index, :], label="Total", color='black', lw=3)
        plt.xlim(xrange)
        plt.ylim(yrange)

        plt.xlabel("wavelength (micron)", fontsize=fontsize)
        plt.ylabel("Equivalent in-field radiance (MJy/sr)", fontsize=fontsize)
        plt.title("Background for calendar day " + str(thisday))
        plt.legend()
        plt.yscale('log')
        plt.show()

    def plot_bathtub(self, showthresh=True, showplot=False, showsubbkgs=False, showannotate=True, title=False, label=False):
        """Create background bathtub plot.

        Parameters
        ----------
        showthresh : bool

        showplot : bool

        showsubbkgs : bool

        showannotate : bool

        title : bool

        label : bool
        """
        bathtub = self.bathtub  # local link

        if not label:
            label = "Total " + str(bathtub['wavelength']) + " micron"

        calendar = self.bkg_data['calendar']
        plt.scatter(calendar, bathtub['total_thiswave'], s=20, label=label)
        plt.xlabel("Day of the year", fontsize=12)
        plt.xlim(0, 366)

        if showannotate:
            annotation = (
                str(bathtub["good_days"])
                + " good days out of "
                + str(calendar.size)
                + " days observable, for threshold "
                + str(self.thresh)
            )

            plt.title(annotation)
            plt.ylabel("bkg at " + str(bathtub['wavelength']) + " um (MJy/sr)", fontsize=12)
        else:
            plt.ylabel("bkg (MJy/SR)", fontsize=20)

        if showsubbkgs:
            plt.scatter(calendar, bathtub['zodi_thiswave'], s=20, label="Zodiacal")
            plt.scatter(calendar, bathtub['nonzodi_thiswave'] * np.ones_like(calendar), s=20, label="ISM+CIB")
            plt.scatter(calendar, bathtub['thermal_thiswave'] * np.ones_like(calendar), s=20, label="Thermal")
            plt.legend(fontsize=10, frameon=False, labelspacing=0)
            plt.grid()
            plt.locator_params(axis='x', nbins=10)
            plt.locator_params(axis='y', nbins=10)

        if showthresh:
            percentiles = (bathtub['themin'], bathtub['themin'] * self.thresh)
            plt.hlines(percentiles, 0, 365, color='black')

        if title:
            plt.title(title)

        plt.show()

    def write_bathtub(self, bathtub_file='background_versus_day.txt'):
        """Write out bathtub distribution data

        Parameters
        ----------
        bathtub_file : str
            Output text file name
        """
        f = open(bathtub_file, 'w')
        header_text = ["# Output of roman_backgrounds version " + str(__version__) + "\n",
                       "# background cache version " + str(self.cache_version) + '\n',
                       "\n"
                       "# for RA=" + str(self.ra) + ", DEC=" + str(self.dec) + " at wavelength=" + str(self.wavelength) + " micron \n",
                       "# Columns: \n",
                       "# - Calendar day (Jan1=0) \n",
                       "# - Total background (MJy/sr)\n"]
        for line in header_text:
            f.write(line)

        for i, calendar_day in enumerate(self.bkg_data['calendar']):
            f.write('{0}    {1:5.4f}'.format(calendar_day, self.bathtub['total_thiswave'][i]) + '\n')

        f.close()

    def write_background(self, background_file='background.txt', thisday=None):
        """Write out backgrounds data to text file.

        background_file : str
            Output text file name
        """
        calendar = self.bkg_data['calendar']

        if thisday in calendar:
            thisday_index = np.where(thisday == calendar)[0][0]
        else:
            print("The input calendar day {}".format(thisday) + " is not available")
            return

        f = open(background_file, 'w')
        header_text = ["# Output of Roman_backgrounds version " + str(__version__) + "\n",
                       "# background cache version " + str(self.cache_version) + '\n',
                       "\n"
                       "# for RA=" + str(self.ra) + ", DEC=" + str(self.dec) + " On calendar day " + str(thisday) + "\n",
                       "# Columns: \n",
                       "# - Wavelength [micron] \n",
                       "# - Total background (MJy/sr)\n",
                       "# - In-field zodiacal light (MJy/sr)\n",
                       "# - In-field galactic light (MJy/sr)\n",
                       "# - Thermal self-emission (MJy/sr)\n"]
        for line in header_text:
            f.write(line)

        for i, wavelength in enumerate(self.bkg_data['wave_array']):
            f.write('{0:f}    {1:5.4f}    {2:5.4f}    {3:5.4f}    {4:5.4f}'.format(wavelength,
                    self.bkg_data['total_bg'][thisday_index][i], self.bkg_data['zodi_bg'][thisday_index][i], self.bkg_data['nonzodi_bg'][i],
                    self.bkg_data['thermal_bg'][i]) + '\n')

        f.close()


def get_background(ra, dec, wavelength, thresh=1.1, plot_background=True, plot_bathtub=True, thisday=None,
                   showsubbkgs=False, write_background=True, write_bathtub=True, background_file='background.txt',
                   bathtub_file='background_versus_day.txt'):
    """
    This is the main method, which serves as a wrapper to get the background data and create plots and outputs with one command.

    Parameters
    ----------
    ra: float
        Right ascension in decimal degrees
    dec: float
        Declination in decimal degrees
    wavelength: float
        Wavelength at which the bathtub curve is calculated, in micron
    thresh: float
        the background threshold, relative to the minimum.  Default=1.1, which corresponds to <5% above the minimum background noise.
        Note that the actual noise difference will be even smaller, as there are often other significant sources of noise than just the
        background (source shot noise, detector noise, etc.).
    plot_background: bool
        whether to plot the background spectrum (and its components) for this day.
    thisday: int
        calendar day to use for plot_spec.  If not given, will use the average of visible calendar days.
    plot_days: bool
        whether to show the plot of background at wavelength_input versus calendar days
    showsubbkgs: bool
        whether to show the components of the background in the bathtub plot.
    write_bathtub: bool
        whether to print the background levels that are plotted in plot_days to an output file
    outfile:     output filename

    """

    bkg = background(ra, dec, wavelength, thresh=thresh)
    calendar = bkg.bkg_data['calendar']

    print("These coordinates are observable by Roman", len(bkg.bkg_data['calendar']), "days per year.")
    print("For", bkg.bathtub['good_days'], "of those days, the background is <", thresh, "times the minimum, at wavelength", wavelength, "micron")

    # Figure out which day to use for the single-day background
    if thisday not in calendar:
        ndays = calendar.size
        if ndays > 0:
            thisday_input = thisday
            thisday = calendar[int(ndays / 2)]  # plot the middle of the available dates in the calendar
            print("Warning: The input calendar day {}".format(thisday_input) + " is not available, assuming the middle day: {} instead".format(thisday))
        else:
            print("No valid days")
            return

    if plot_background:
        bkg.plot_background(thisday=thisday)

    if write_background:
        bkg.write_background(thisday=thisday, background_file=background_file)

    if plot_bathtub:
        bkg.plot_bathtub(showsubbkgs=showsubbkgs)

    if write_bathtub:
        bkg.write_bathtub(bathtub_file=bathtub_file)
