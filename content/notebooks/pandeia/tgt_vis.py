# Adapted from https://github.com/spacetelescope/roman-technical-information/blob/main/data/Observatory/Visibility/test_tgt_vis2.py

'''
General note on coordinates used here:
     Calculations will be performed in Ecliptic coordinates.
    +X points to vernal equinox;
    +Z points to North ecliptic pole;
    +Y makes a right handed coordinate system.

    Rotating these axes first around +Z to align X' to the longitude of
    the line of sight, then rotating around Y' to align X'' with
    the line of sight gives a S/C local set of coordinates:
    X'' along LOS,
    Z'' towards increasing latitude,
    and
    Y'' pointing towards increasing longitude.
    Positive roll rotates around X'' according to right hand rule.

    Observatory coordinates:
    +Xobs is along boresight,
    +Zobs is normal to Solar array,
    +Yobs makes right handed sys.
     At nominal roll, Sun is in Xobs-Zobs plane, with +Zobs as close to Sun as possible.
     At zero roll offset:
    +Xobs=+X''
    +Yobs=+Y''
    +Zobs=+Z''
     Define position angle of Observatory as angle of +Yobs in degrees East of North.

    LOS = line of sight
    FOR = Field of Regard (defined by valid LOS angle with respect to the Sun)

    Inputs to this routine:
    tgt_ra,
    tgt_dec:
    coordinates of line of sight (LOS) in RA, DEC.
    hardwired below to galactic center for a test case

    Outputs from this routine (defined on exiting below) - can wrap this code as desired
    All outputs are ndarrays of length 365 (or n_samp if weekly or some other variant)
    nominal_roll,  in degrees; one value for each day of 2028.
    good_angles,  0 if not in FOR, 1 if in FOR; one value for each day of 2028.
    sunang_x - angle of Sun with respect to observatory +X axis (boresight), in degrees
    sunang_y - angle of Sun with respect to observatory +Y axis, in degrees
    sunang_z - angle of Sun with respect to observatory +Z axis (SASS normal), in degrees

    Jeff Kruk   2021 09 04

    Inputs:
    target_coordinates: SkyCoord objects
'''

import numpy as np
import sys
from astropy.coordinates import solar_system_ephemeris
from astropy.coordinates import get_body
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy import units as u
import pandas as pd
import warnings
from astropy.utils.exceptions import AstropyWarning


class compute_visibility():

    def __init__(self, targets_coordinates, fileout=None, report=False, interval_sampling_days=None, interval_start_time=None, interval_duration_days=None):

        if isinstance(targets_coordinates, list):
            self.targets_coordinates = targets_coordinates
        else:
            self.targets_coordinates = [targets_coordinates]

        self.fileout = fileout
        self.report = report
        self.interval = {'sampling_days': interval_sampling_days,
                         'start_time': interval_start_time,
                         'duration_days': interval_duration_days}
        self.sampled_times = self.set_sampled_times(self.interval)
        self.sun_coord = get_body('Sun', self.sampled_times)  # get coordinate object for the Sun for each day of the year
        self.min_sun_angle = (90. - 36.) * u.deg
        self.max_sun_angle = (90. + 36.) * u.deg
        self.df_results = self.initialize_dataframe()

    def compute_and_display(self):
        self.get_good_angles()
        self.get_roll_pa_sunang()
        if self.report:
            self.printout(self.get_preamble())
            self.printout(self.df_results.to_string())

    def initialize_dataframe(self):
        radec_string = ['({}, {})'.format(coords.ra.to_string(u.hour), coords.dec.to_string(u.degree, alwayssign=True)) for coords in self.targets_coordinates]
        time_string = [self.format_time(time) for time in self.sampled_times]
        index_levels = [radec_string, time_string]
        index_names = ['(RA, Dec)', 'DOY']
        multi_index = pd.MultiIndex.from_product(index_levels, names=index_names)
        column_names = ['Sun_RA', 'Sun_Dec', 'separation', 'good_angles', 'nominal_roll', 'pa_obs_y', 'pa_fpa_local_x', 'pa_fpa_local_y', 'sunang_x', 'sunang_y', 'sunang_z']

        # The reindexing of dataframe below is necessary due to this pandas bug:
        # https://stackoverflow.com/questions/71837659/trying-to-sort-multiindex-index-using-categorical-index/73766126#73766126

        return (pd.DataFrame(index=multi_index, columns=column_names)).reindex(radec_string, level=0)

    def format_time(self, time_object):
        """Converts a datetime object's time to DOY.ddddd """
        datetime = time_object.datetime
        decimal_hours = datetime.hour + datetime.minute / 60. + datetime.second / 3600
        return datetime.strftime("%Y") + '-' + datetime.strftime("%j") + '.' + '{:7.5f}'.format(decimal_hours / 24)[2:]

    def printout(self, text):
        if self.fileout is not None:
            try:
                with open(self.fileout, 'w') as ofile:
                    print(text, file=ofile)
            except Exception as e:
                print(f"Error writing to file: {e}", file=sys.stderr)
                print(text)  # Fallback to stdout if file writing fails
        else:
            print(text)

    def get_preamble(self):
        preamble = "Xang, Yang, Zang are angles of Sun vector in Observatory coordinate frame \n"
        preamble += "X is the boresight, valid angles are 54-126 degrees \n"
        preamble += "Z is normal to solar array, as close to zero as the pitch allows (<36 at nominal roll when pitch is OK) \n"
        preamble += "Y is perpendicular to X-Z plane; Yang should always be 90 at nominal roll \n"

        return preamble

    def set_sampled_times(self, interval):
        '''
        define the array of Time object at which the visitbility will be sampled.
        If a date is in the future, this will generate a 'dubious date' warning message
        the reason is that it is unknown how many leap seconds will be needed in the future.
        the results will still be valid
        '''

        if interval['start_time'] is None:
            t_start_str = ['2024-01-01T00:00:00.0']
            t_start = Time(t_start_str, format='isot', scale='utc')
        elif isinstance(interval['start_time'], Time) is False:
            if isinstance(interval['start_time'], str):
                t_start = Time(interval['start_time'], format='isot', scale='utc')
            else:
                print('Start time needs to be a astropy.Time object or a string')
                assert False
        else:
            t_start = interval['start_time']

        if interval['duration_days'] is None:
            t_end = 365.
        else:
            t_end = interval['duration_days']

        if interval['sampling_days'] is None:
            t_step = 1.
        else:
            t_step = interval['sampling_days']

        if t_step > t_end:
            print('sampling interval cannot exceeed total duration')
            assert False

        return t_start+np.arange(0., t_end, t_step) * u.d

    def get_good_angles(self):
        for i, target_coordinates in enumerate(self.targets_coordinates):

            with warnings.catch_warnings():
                warnings.simplefilter('ignore', AstropyWarning)
                sun_angle = self.sun_coord.separation(target_coordinates)
                good_angles = (sun_angle >= self.min_sun_angle) & (sun_angle <= self.max_sun_angle)
            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'good_angles'] = good_angles
            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'separation'] = sun_angle
            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'Sun_RA'] = self.sun_coord.ra
            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'Sun_Dec'] = self.sun_coord.dec

    def get_roll_pa_sunang(self):

        for i, target_coordinates in enumerate(self.targets_coordinates):

            # begin roll angle calculations
            cos_ra_t = np.cos(target_coordinates.ra.radian)
            cos_dec_t = np.cos(target_coordinates.dec.radian)
            sin_ra_t = np.sin(target_coordinates.ra.radian)
            sin_dec_t = np.sin(target_coordinates.dec.radian)
            cos_ra_s = np.cos(self.sun_coord.ra.radian)
            cos_dec_s = np.cos(self.sun_coord.dec.radian)
            sin_ra_s = np.sin(self.sun_coord.ra.radian)
            sin_dec_s = np.sin(self.sun_coord.dec.radian)

            cc_s = cos_ra_s * cos_dec_s
            sc_s = sin_ra_s * cos_dec_s
            cs_s = cos_ra_s * sin_dec_s
            ss_s = sin_ra_s * sin_dec_s

            cc_t = cos_ra_t * cos_dec_t
            sc_t = sin_ra_t * cos_dec_t
            cs_t = cos_ra_t * sin_dec_t
            ss_t = sin_ra_t * sin_dec_t

            # rotation matrix to convert a vector in celestial coordinates to body-frame coordinates,
            # for the S/C frame aligned to point X towards RA=a, DEC=d, and roll about X of r:
            # for reference only
            #  /                  cosd cosa,					  cosd sina,	     sind \
            #  | -cosr sina -sinr sind cosa,	 cosr cosa - sinr sind sina,	sinr cosd |
            #  \ sinr sina - cosr sind cosa,	-sinr cosa - cosr sind sina,	cosr cosd /
            #
            # roll is defined by rotating Sun vector into body frame, then minimizing the Z component

            arg1 = sin_ra_t * cc_s - cos_ra_t * sc_s
            arg2 = cos_dec_t * sin_dec_s - sin_dec_t * (cos_ra_t * cc_s + sin_ra_t * sc_s)
            phi = np.arctan2(arg1, arg2)

            # there are two solutions - check that resulting vector has positive Z component
            sinr = np.sin(phi)
            cosr = np.cos(phi)

            # Rotate Sun vector into body frame
            # start by confirming that projection onto Z axis is positive - if not we have to change
            # roll by 180 degrees
            z_sun1 = (sinr*sin_ra_t - cosr*cs_t) * cc_s
            z_sun2 = (-sinr*cos_ra_t - cosr*ss_t) * sc_s
            z_sun3 = cosr * cos_dec_t * sin_dec_s
            z_sun = z_sun1 + z_sun2 + z_sun3
            sunang_z = np.arccos(z_sun) * 180. / np.pi

            # if (z_sun < 0.):
            #    phi = phi + np.pi
            phi = np.where(z_sun < 0., phi + np.pi, phi)

            # done with main task of this routine.

            # convert to degrees
            nominal_roll = phi * 180. / np.pi
            # wrap roll to be between 0 and 360.
            nominal_roll = np.where(nominal_roll >= 0., nominal_roll, nominal_roll + 360.)

            # define position angles (orientation East of North)
            # observatory +Y axis
            pa_obs_y = nominal_roll - 90.
            # Projected WFI focal plane local +X axis:
            pa_fpa_local_x = nominal_roll - 30.
            # Projected WFI focal plane local +Y axis:
            pa_fpa_local_y = nominal_roll - 120.
            # wrap all to be between 0, 360 degrees
            pa_obs_y = np.where(pa_obs_y >= 0., pa_obs_y, pa_obs_y + 360.)
            pa_fpa_local_x = np.where(pa_fpa_local_x >= 0., pa_fpa_local_x, pa_fpa_local_x + 360.)
            pa_fpa_local_y = np.where(pa_fpa_local_y >= 0., pa_fpa_local_y, pa_fpa_local_y + 360.)

            # cross checks
            # check on other projections of Sun vector onto body axes as a sanity check
            x_sun = (cc_t * cc_s) + (sc_t * sc_s) + (sin_dec_t * sin_dec_s)
            sunang_x = np.arccos(x_sun) * 180. / np.pi

            sinr = np.sin(phi)
            cosr = np.cos(phi)
            y_sun1 = (-cosr * sin_ra_t - sinr * cs_t) * cc_s
            y_sun2 = (cosr * cos_ra_t - sinr * ss_t) * sc_s
            y_sun3 = sinr * cos_dec_t * sin_dec_s
            y_sun = y_sun1 + y_sun2 + y_sun3
            sunang_y = np.arccos(y_sun) * 180. / np.pi

            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'nominal_roll'] = nominal_roll
            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'pa_obs_y'] = pa_obs_y
            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'pa_fpa_local_x'] = pa_fpa_local_x
            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'pa_fpa_local_y'] = pa_fpa_local_y
            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'sunang_x'] = sunang_x
            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'sunang_y'] = sunang_y
            self.df_results.loc[pd.IndexSlice[self.df_results.index.levels[0][i], :], 'sunang_z'] = sunang_z
