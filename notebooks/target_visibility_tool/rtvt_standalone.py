"""Standalone Roman Target Visibility Tool notebook helper.

This file is generated from the RTVT development package so the accompanying
Roman notebook can run with only this local helper file plus the notebook
requirements. Keep it in the same directory as the notebook.
"""

from __future__ import annotations

import base64
import html
import io
import os
import sys
import tempfile
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

import ipywidgets as widgets
import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import BarycentricTrueEcliptic, SkyCoord, get_body
from astropy.time import Time
from astropy.utils.exceptions import AstropyWarning
from IPython.display import clear_output, display


# ---- rtvt/utils.py ----
def prepare_matplotlib_cache() -> None:
    """Point matplotlib + XDG caches at a writable temp directory.

    Several install targets (locked-down kernels, the tkinter GUI on macOS,
    binder-style notebook environments) refuse to create the default
    ``~/.matplotlib`` cache. Routing both caches through ``tempfile.gettempdir()``
    keeps every entry point happy without needing per-frontend setup.
    """
    cache_root = Path(tempfile.gettempdir()) / 'rtvt-matplotlib'
    xdg_cache_root = Path(tempfile.gettempdir()) / 'rtvt-cache'
    cache_root.mkdir(parents=True, exist_ok=True)
    xdg_cache_root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(cache_root))
    os.environ.setdefault('XDG_CACHE_HOME', str(xdg_cache_root))

def figure_to_png_bytes(fig, dpi: int=150, close: bool=False) -> bytes:
    """Render a matplotlib figure to PNG bytes, optionally closing the figure."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight')
    if close:
        import matplotlib.pyplot as plt
        plt.close(fig)
    return buffer.getvalue()

def quantity_series_to_deg(series: pd.Series) -> np.ndarray:
    """Convert a pandas Series of astropy Quantities or floats to a float ndarray in degrees."""
    return np.array([value.to_value(u.deg) if hasattr(value, 'to_value') else float(value) for value in series.to_numpy()], dtype=float)

# ---- rtvt/analysis.py ----
@dataclass
class VisibilityResult:
    """Single-target view of a `VisibilityCalculator` run."""
    target: SkyCoord
    label: str
    table: pd.DataFrame
    sampled_times: Time
    sampling_days: float
    coordinate_system: str = 'equatorial'

def find_observable_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return contiguous True runs in ``mask`` as ``(start_index, length)`` tuples."""
    mask = np.asarray(mask, dtype=bool)
    if not np.any(mask):
        return []
    padded = np.concatenate(([False], mask, [False]))
    diffs = np.diff(padded.astype(int))
    starts = np.where(diffs == 1)[0]
    ends = np.where(diffs == -1)[0]
    return list(zip(starts.tolist(), (ends - starts).tolist()))

def summarize_windows(result: VisibilityResult) -> pd.DataFrame:
    """Return a DataFrame of observable windows with start/end/duration/roll bookends."""
    good = result.table['good_angles'].astype(bool).to_numpy()
    columns = ['window_start', 'window_end', 'duration_days', 'nominal_roll_start', 'nominal_roll_end']
    if not np.any(good):
        return pd.DataFrame(columns=columns)
    rolls = quantity_series_to_deg(result.table['nominal_roll'])
    rows = []
    for (start, length) in find_observable_runs(good):
        end_exclusive = start + length
        last = end_exclusive - 1
        rows.append({'window_start': result.sampled_times[start].isot, 'window_end': result.sampled_times[last].isot, 'duration_days': length * result.sampling_days, 'nominal_roll_start': rolls[start], 'nominal_roll_end': rolls[last]})
    return pd.DataFrame(rows)

def format_summary(result: VisibilityResult, target_name: str | None=None) -> str:
    """Render the terminal summary block (target metadata + windows table)."""
    good = result.table['good_angles'].astype(bool).to_numpy()
    windows = summarize_windows(result)
    vis_fraction = float(np.mean(good)) if len(good) else 0.0
    start = result.sampled_times[0].isot
    end = result.sampled_times[-1].isot
    title = target_name or result.label
    lines = ['Roman Target Visibility Tool', f'Target: {title}', f'RA: {result.target.ra.deg:.8f} deg', f'Dec: {result.target.dec.deg:.8f} deg', f'Galactic l: {result.target.galactic.l.deg:.8f} deg', f'Galactic b: {result.target.galactic.b.deg:.8f} deg', f'Input coordinate system: {result.coordinate_system}', f'Checked interval: {start} to {end}', f'Sampling cadence: {result.sampling_days:g} day(s)', f'Visible samples: {int(np.sum(good))}/{len(good)} ({vis_fraction * 100:.1f}%)', '']
    if windows.empty:
        lines.append('No observable windows found.')
    else:
        lines.append('Observable windows:')
        lines.append(windows.to_string(index=False))
    return '\n'.join(lines)

def check_cvz_status(df: pd.DataFrame, max_sep_deg: float=126.0, good_angle_threshold: float=0.99) -> tuple[bool, float, str]:
    """Notebook CVZ heuristic: target is in CVZ if visible most of the year.

    Returns ``(is_cvz, visible_fraction, info_string)``. A target qualifies when
    visibility fraction meets ``good_angle_threshold``, or when the Sun-target
    separation is always strictly above ``max_sep_deg``.
    """
    good = df['good_angles'].astype(bool).values
    vis_frac = float(np.mean(good))
    separation = quantity_series_to_deg(df['separation'])
    always_above_max = bool(np.all(separation > max_sep_deg))
    mostly_good = vis_frac >= good_angle_threshold
    is_cvz = always_above_max or mostly_good
    if always_above_max:
        info_str = f'IN CVZ: Sun-target separation always > {max_sep_deg} deg'
    elif mostly_good:
        info_str = f'IN CVZ: Good visibility {vis_frac * 100:.1f}% of the year (>={good_angle_threshold * 100:.0f}%)'
    else:
        info_str = f'NOT in CVZ: Good visibility only {vis_frac * 100:.1f}% of the year'
    return (is_cvz, vis_frac, info_str)

# ---- rtvt/coords.py ----
_COORDINATE_SYSTEM_ALIASES = {'equatorial': 'equatorial', 'eq': 'equatorial', 'icrs': 'equatorial', 'radec': 'equatorial', 'ra/dec': 'equatorial', 'galactic': 'galactic', 'gal': 'galactic', 'lb': 'galactic', 'l/b': 'galactic', 'ecliptic': 'ecliptic', 'ecl': 'ecliptic', 'eliptic': 'ecliptic', 'elliptic': 'ecliptic'}

def normalize_coordinate_system(value: str) -> str:
    """Resolve an input coord-system label to a supported display coordinate system."""
    normalized = str(value).strip().lower()
    if normalized not in _COORDINATE_SYSTEM_ALIASES:
        raise ValueError("coordinate_system must be 'equatorial', 'galactic', or 'ecliptic'")
    return _COORDINATE_SYSTEM_ALIASES[normalized]

def coordinate_labels(coordinate_system: str) -> tuple[str, str, str]:
    """Return ``(lon_label, lat_label, frame_title)`` for the resolved coord system."""
    coordinate_system = normalize_coordinate_system(coordinate_system)
    if coordinate_system == 'galactic':
        return ('l', 'b', 'Galactic')
    if coordinate_system == 'ecliptic':
        return ('Ecl lon', 'Ecl lat', 'Ecliptic')
    return ('RA', 'Dec', 'Equatorial')

def skycoord_from_lon_lat(lon_deg: float, lat_deg: float, coordinate_system: str) -> SkyCoord:
    """Build a SkyCoord from decimal-degree lon/lat in the requested frame."""
    coordinate_system = normalize_coordinate_system(coordinate_system)
    if coordinate_system == 'galactic':
        return SkyCoord(l=lon_deg * u.deg, b=lat_deg * u.deg, frame='galactic')
    if coordinate_system == 'ecliptic':
        return SkyCoord(lon=lon_deg * u.deg, lat=lat_deg * u.deg, frame=BarycentricTrueEcliptic())
    return SkyCoord(ra=lon_deg * u.deg, dec=lat_deg * u.deg, frame='icrs')

def display_lon_lat(coord: SkyCoord, coordinate_system: str) -> tuple[float, float]:
    """Project a SkyCoord to the display lon/lat (degrees) for the requested frame."""
    coordinate_system = normalize_coordinate_system(coordinate_system)
    if coordinate_system == 'galactic':
        gal = coord.galactic
        return (float(gal.l.deg), float(gal.b.deg))
    if coordinate_system == 'ecliptic':
        ecl = coord.transform_to(BarycentricTrueEcliptic())
        return (float(ecl.lon.deg), float(ecl.lat.deg))
    icrs = coord.icrs
    return (float(icrs.ra.deg), float(icrs.dec.deg))

def format_display_coordinate(lon_deg: float, lat_deg: float, coordinate_system: str, precision: int=1) -> str:
    """Format a lon/lat pair in the selected display coordinate system."""
    (lon_label, lat_label, _) = coordinate_labels(coordinate_system)
    return f'{lon_label}={lon_deg:.{precision}f}, {lat_label}={lat_deg:.{precision}f}'

def parse_target(ra: str, dec: str, coordinate_system: str='equatorial') -> SkyCoord:
    """Parse CLI/GUI-style string inputs into a SkyCoord.

    Equatorial RA accepts decimal degrees or sexagesimal hour-angle strings
    (``"06:00:00"``, ``"6h0m0s"``); Dec is parsed as decimal degrees.
    Galactic inputs are decimal-degree ``l`` and ``b``. Ecliptic inputs are
    decimal-degree ecliptic longitude and latitude.
    """
    coordinate_system = normalize_coordinate_system(coordinate_system)
    if coordinate_system == 'galactic':
        return SkyCoord(l=float(ra) * u.deg, b=float(dec) * u.deg, frame='galactic')
    if coordinate_system == 'ecliptic':
        return SkyCoord(lon=float(ra) * u.deg, lat=float(dec) * u.deg, frame=BarycentricTrueEcliptic())
    ra_unit = u.hourangle if _looks_sexagesimal_ra(ra) else u.deg
    return SkyCoord(ra, dec, unit=(ra_unit, u.deg), frame='icrs')

def _looks_sexagesimal_ra(value: str) -> bool:
    lowered = value.lower()
    return ':' in value or 'h' in lowered or 'm' in lowered or ('s' in lowered)

# ---- rtvt/visibility.py ----
def normalize_start_time(start_time: Time | str | None) -> Time | None:
    """Coerce ``None`` / ISO string / ``Time`` into an astropy ``Time`` or ``None``."""
    if start_time is None:
        return None
    if isinstance(start_time, Time):
        return start_time
    if isinstance(start_time, str):
        if 'T' in start_time:
            return Time(start_time, format='isot', scale='utc')
        return Time(f'{start_time}T00:00:00.0', format='isot', scale='utc')
    raise TypeError('start_time must be None, an astropy Time, or an ISO date string')

def sampled_times_for_interval(start_time: Time | str | None=None, duration_days: float=365.0, sampling_days: float=1.0) -> Time:
    """Build the array of sample times used by the visibility computation."""
    t_start = normalize_start_time(start_time)
    if t_start is None:
        t_start = Time(['2024-01-01T00:00:00.0'], format='isot', scale='utc')
    if sampling_days > duration_days:
        raise ValueError('sampling interval cannot exceed total duration')
    return t_start + np.arange(0.0, duration_days, sampling_days) * u.d

class VisibilityCalculator:
    """Compute Roman field-of-regard visibility for one or more fixed targets."""

    def __init__(self, targets_coordinates, fileout=None, report=False, interval_sampling_days=None, interval_start_time=None, interval_duration_days=None):
        if isinstance(targets_coordinates, list):
            targets = targets_coordinates
        else:
            targets = [targets_coordinates]
        self.targets_coordinates = [coords.icrs for coords in targets]
        self.target_labels = self._make_unique_target_labels(self.targets_coordinates)
        self.fileout = fileout
        self.report = report
        self.interval = {'sampling_days': interval_sampling_days, 'start_time': interval_start_time, 'duration_days': interval_duration_days}
        self.sampled_times = sampled_times_for_interval(start_time=interval_start_time, duration_days=365.0 if interval_duration_days is None else interval_duration_days, sampling_days=1.0 if interval_sampling_days is None else interval_sampling_days)
        self.sun_coord = get_body('Sun', self.sampled_times)
        self.min_sun_angle = (90.0 - 36.0) * u.deg
        self.max_sun_angle = (90.0 + 36.0) * u.deg
        self.df_results = self.initialize_dataframe()

    def compute_and_display(self):
        self.get_good_angles()
        self.get_roll_pa_sunang()
        if self.report:
            self.printout(self.get_preamble())
            self.printout(self.df_results.to_string())

    def initialize_dataframe(self):
        radec_string = self.target_labels
        time_string = [self.format_time(time) for time in self.sampled_times]
        index_levels = [radec_string, time_string]
        index_names = ['(RA, Dec)', 'DOY']
        multi_index = pd.MultiIndex.from_product(index_levels, names=index_names)
        column_names = ['Sun_RA', 'Sun_Dec', 'separation', 'good_angles', 'nominal_roll', 'pa_obs_y', 'pa_fpa_local_x', 'pa_fpa_local_y', 'sunang_x', 'sunang_y', 'sunang_z']
        return pd.DataFrame(index=multi_index, columns=column_names).reindex(radec_string, level=0)

    def _make_unique_target_labels(self, targets_coordinates):
        labels = ['({}, {})'.format(coords.ra.to_string(u.hour), coords.dec.to_string(u.degree, alwayssign=True)) for coords in targets_coordinates]
        counts = {}
        for label in labels:
            counts[label] = counts.get(label, 0) + 1
        seen = {}
        unique_labels = []
        for label in labels:
            seen[label] = seen.get(label, 0) + 1
            if counts[label] == 1:
                unique_labels.append(label)
            else:
                unique_labels.append(f'{label} #{seen[label]}')
        return unique_labels

    def format_time(self, time_object):
        """Convert an astropy ``Time`` to the ``YYYY-DOY.fraction`` index string."""
        datetime = time_object.datetime
        decimal_hours = datetime.hour + datetime.minute / 60.0 + datetime.second / 3600
        return datetime.strftime('%Y') + '-' + datetime.strftime('%j') + '.' + '{:7.5f}'.format(decimal_hours / 24)[2:]

    def printout(self, text):
        if self.fileout is not None:
            try:
                with open(self.fileout, 'w') as ofile:
                    print(text, file=ofile)
            except Exception as e:
                print(f'Error writing to file: {e}', file=sys.stderr)
                print(text)
        else:
            print(text)

    def get_preamble(self):
        preamble = 'Xang, Yang, Zang are angles of Sun vector in Observatory coordinate frame \n'
        preamble += 'X is the boresight, valid angles are 54-126 degrees \n'
        preamble += 'Z is normal to solar array, as close to zero as the pitch allows (<36 at nominal roll when pitch is OK) \n'
        preamble += 'Y is perpendicular to X-Z plane; Yang should always be 90 at nominal roll \n'
        return preamble

    def get_good_angles(self):
        for (i, target_coordinates) in enumerate(self.targets_coordinates):
            target_label = self.target_labels[i]
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', AstropyWarning)
                sun_angle = self.sun_coord.separation(target_coordinates)
                good_angles = (sun_angle >= self.min_sun_angle) & (sun_angle <= self.max_sun_angle)
            self.df_results.loc[pd.IndexSlice[target_label, :], 'good_angles'] = good_angles
            self.df_results.loc[pd.IndexSlice[target_label, :], 'separation'] = sun_angle
            self.df_results.loc[pd.IndexSlice[target_label, :], 'Sun_RA'] = self.sun_coord.ra
            self.df_results.loc[pd.IndexSlice[target_label, :], 'Sun_Dec'] = self.sun_coord.dec

    def get_roll_pa_sunang(self):
        for (i, target_coordinates) in enumerate(self.targets_coordinates):
            target_label = self.target_labels[i]
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
            arg1 = sin_ra_t * cc_s - cos_ra_t * sc_s
            arg2 = cos_dec_t * sin_dec_s - sin_dec_t * (cos_ra_t * cc_s + sin_ra_t * sc_s)
            phi = np.arctan2(arg1, arg2)
            sinr = np.sin(phi)
            cosr = np.cos(phi)
            z_sun1 = (sinr * sin_ra_t - cosr * cs_t) * cc_s
            z_sun2 = (-sinr * cos_ra_t - cosr * ss_t) * sc_s
            z_sun3 = cosr * cos_dec_t * sin_dec_s
            z_sun = z_sun1 + z_sun2 + z_sun3
            sunang_z = np.arccos(z_sun) * 180.0 / np.pi
            phi = np.where(z_sun < 0.0, phi + np.pi, phi)
            nominal_roll = phi * 180.0 / np.pi
            nominal_roll = np.where(nominal_roll >= 0.0, nominal_roll, nominal_roll + 360.0)
            pa_obs_y = nominal_roll - 90.0
            pa_fpa_local_x = nominal_roll - 30.0
            pa_fpa_local_y = nominal_roll - 120.0
            pa_obs_y = np.where(pa_obs_y >= 0.0, pa_obs_y, pa_obs_y + 360.0)
            pa_fpa_local_x = np.where(pa_fpa_local_x >= 0.0, pa_fpa_local_x, pa_fpa_local_x + 360.0)
            pa_fpa_local_y = np.where(pa_fpa_local_y >= 0.0, pa_fpa_local_y, pa_fpa_local_y + 360.0)
            x_sun = cc_t * cc_s + sc_t * sc_s + sin_dec_t * sin_dec_s
            sunang_x = np.arccos(x_sun) * 180.0 / np.pi
            sinr = np.sin(phi)
            cosr = np.cos(phi)
            y_sun1 = (-cosr * sin_ra_t - sinr * cs_t) * cc_s
            y_sun2 = (cosr * cos_ra_t - sinr * ss_t) * sc_s
            y_sun3 = sinr * cos_dec_t * sin_dec_s
            y_sun = y_sun1 + y_sun2 + y_sun3
            sunang_y = np.arccos(y_sun) * 180.0 / np.pi
            self.df_results.loc[pd.IndexSlice[target_label, :], 'nominal_roll'] = nominal_roll
            self.df_results.loc[pd.IndexSlice[target_label, :], 'pa_obs_y'] = pa_obs_y
            self.df_results.loc[pd.IndexSlice[target_label, :], 'pa_fpa_local_x'] = pa_fpa_local_x
            self.df_results.loc[pd.IndexSlice[target_label, :], 'pa_fpa_local_y'] = pa_fpa_local_y
            self.df_results.loc[pd.IndexSlice[target_label, :], 'sunang_x'] = sunang_x
            self.df_results.loc[pd.IndexSlice[target_label, :], 'sunang_y'] = sunang_y
            self.df_results.loc[pd.IndexSlice[target_label, :], 'sunang_z'] = sunang_z

# ---- rtvt/sky_grid.py ----
_SKY_GRID_CACHE: dict = {}

def compute_all_sky_visibility_grid(ra_grid: np.ndarray | None=None, dec_grid: np.ndarray | None=None, grid_step_deg: float=10, start_time: Time | str | None=None, duration_days: float=365, sampling_days: float=1, coordinate_system: str='equatorial') -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute the visibility fraction over a coarse all-sky grid.

    If ``ra_grid`` / ``dec_grid`` are omitted, a ``grid_step_deg``-spaced grid
    is used. Returned arrays are ``(lon_grid_deg, lat_grid_deg, vis_frac_2d)``;
    ``vis_frac_2d`` has shape ``(len(lat_grid), len(lon_grid))``.
    """
    coordinate_system = normalize_coordinate_system(coordinate_system)
    if ra_grid is None:
        ra_grid = np.arange(0, 360, grid_step_deg)
    if dec_grid is None:
        dec_grid = np.arange(-90, 91, grid_step_deg)
    (ra_mesh, dec_mesh) = np.meshgrid(ra_grid, dec_grid)
    ra_flat = ra_mesh.ravel()
    dec_flat = dec_mesh.ravel()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', AstropyWarning)
        sky_points = skycoord_from_lon_lat(ra_flat, dec_flat, coordinate_system).icrs
        sampled_times = sampled_times_for_interval(start_time=start_time, duration_days=duration_days, sampling_days=sampling_days)
        sun_coord = get_body('Sun', sampled_times)
        separation = sun_coord[:, np.newaxis].separation(sky_points[np.newaxis, :])
    good_angles = (separation >= 54 * u.deg) & (separation <= 126 * u.deg)
    vis_frac = np.mean(good_angles, axis=0)
    return (np.asarray(ra_grid), np.asarray(dec_grid), vis_frac.reshape(ra_mesh.shape))

def get_cached_all_sky_visibility_grid(grid_step_deg: float=10, start_time: Time | str | None=None, duration_days: float=365, sampling_days: float=1, coordinate_system: str='equatorial') -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Process-local cache of `compute_all_sky_visibility_grid` keyed on its inputs."""
    coordinate_system = normalize_coordinate_system(coordinate_system)
    t0 = normalize_start_time(start_time)
    start_key = 'default' if t0 is None else t0.isot
    key = (coordinate_system, float(grid_step_deg), start_key, float(duration_days), float(sampling_days))
    if key not in _SKY_GRID_CACHE:
        _SKY_GRID_CACHE[key] = compute_all_sky_visibility_grid(grid_step_deg=grid_step_deg, start_time=t0, duration_days=duration_days, sampling_days=sampling_days, coordinate_system=coordinate_system)
    return _SKY_GRID_CACHE[key]

# ---- rtvt/visualization/sky.py ----
def make_all_sky_mollweide(ra_grid_deg: np.ndarray, dec_grid_deg: np.ndarray, vis_frac_2d: np.ndarray, *, coordinate_system: str='equatorial', test_targets: Iterable | None=None):
    """Render a Mollweide projection of the visibility fraction over the sky.

    Returns ``(fig, ax, pcm)``. The caller is responsible for displaying,
    closing, or wiring up click handlers — this function only builds the
    figure. ``test_targets`` are optional SkyCoord-like objects drawn as
    preview markers.
    """
    import matplotlib.pyplot as plt
    (_, _, coordinate_title) = coordinate_labels(coordinate_system)
    ra_shifted = np.where(ra_grid_deg > 180, ra_grid_deg - 360, ra_grid_deg)
    sort_idx = np.argsort(ra_shifted)
    ra_sorted_deg = ra_shifted[sort_idx]
    vis_frac_sorted = vis_frac_2d[:, sort_idx]
    ra_plot = np.deg2rad(ra_sorted_deg)
    dec_plot = np.deg2rad(dec_grid_deg)
    (ra_plot_mesh, dec_plot_mesh) = np.meshgrid(ra_plot, dec_plot)
    with plt.ioff():
        (fig, ax) = plt.subplots(figsize=(12, 6), subplot_kw=dict(projection='mollweide'))
    if hasattr(fig.canvas, 'toolbar_position'):
        fig.canvas.toolbar_position = 'bottom'
    pcm = ax.pcolormesh(ra_plot_mesh, dec_plot_mesh, vis_frac_sorted, cmap='RdYlGn', shading='auto', vmin=0, vmax=1)
    cbar = fig.colorbar(pcm, ax=ax, orientation='horizontal', pad=0.05, shrink=0.7)
    cbar.set_label('Visibility Fraction (of year)')
    if test_targets:
        for tgt in test_targets:
            (tgt_lon, tgt_lat) = display_lon_lat(tgt, coordinate_system)
            tgt_ra_plot = np.deg2rad(tgt_lon - 360 if tgt_lon > 180 else tgt_lon)
            tgt_dec_plot = np.deg2rad(tgt_lat)
            ax.plot(tgt_ra_plot, tgt_dec_plot, marker='x', linestyle='None', color='#222222', markersize=8, markeredgewidth=1.5, alpha=0.75)
    ax.set_title(f'All-Sky Visibility Fraction ({coordinate_title}) -- Click to Select Targets', fontsize=12, pad=20)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return (fig, ax, pcm)

# ---- rtvt/visualization/timeseries.py ----
def make_visibility_plot(dates: Sequence, good_mask: np.ndarray, separation_deg: np.ndarray, *, visibility_title: str, separation_title: str | None=None, color: str='#1f77b4', line_width: float=1.5, fill_color: str='blue'):
    """Build a 2-panel figure (in-FOR step + Sun-target separation) and return it.

    The caller owns the figure (closing, saving, displaying). Both panels share
    the X axis. Pass ``separation_title`` to label the lower panel; the CLI
    leaves it blank, the notebook uses a per-target string.
    """
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter, MonthLocator
    (fig, (ax_vis, ax_sep)) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    ax_vis.step(dates, np.asarray(good_mask, dtype=int), where='mid', lw=line_width, color=color)
    ax_vis.set_yticks([0, 1])
    ax_vis.set_yticklabels(['Not in FOR', 'In FOR'])
    ax_vis.set_ylim(-0.1, 1.1)
    ax_vis.set_ylabel('Visibility')
    ax_vis.set_title(visibility_title)
    ax_vis.grid(alpha=0.3)
    ax_sep.plot(dates, separation_deg, lw=line_width, color=color)
    ax_sep.axhline(54, ls='--', color='green', lw=1, label='Min (54 deg)')
    ax_sep.axhline(126, ls='--', color='orange', lw=1, label='Max (126 deg)')
    ax_sep.fill_between(dates, 54, 126, alpha=0.12, color=fill_color, label='Observable range')
    ax_sep.set_ylabel('Separation (deg)')
    ax_sep.set_xlabel('Date')
    if separation_title:
        ax_sep.set_title(separation_title)
    ax_sep.legend(fontsize=8, loc='upper right')
    ax_sep.grid(alpha=0.3)
    ax_sep.xaxis.set_major_locator(MonthLocator())
    ax_sep.xaxis.set_major_formatter(DateFormatter('%b %d'))
    for tick in ax_sep.get_xticklabels():
        tick.set_rotation(45)
    fig.tight_layout()
    return fig

def plot_visibility_result(result: VisibilityResult, target_name: str | None=None):
    """CLI-style 2-panel plot for a VisibilityResult."""
    title = target_name or result.label
    dates = [time.datetime for time in result.sampled_times]
    good = result.table['good_angles'].astype(bool).to_numpy()
    separation = quantity_series_to_deg(result.table['separation'])
    return make_visibility_plot(dates, good, separation, visibility_title=f'Roman visibility window: {title}')

# ---- rtvt/visualization/gantt.py ----
TARGET_COLOR_PALETTE = ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02', '#a6761d', '#1f78b4', '#b2df8a', '#666666']

def target_color(index: int) -> str:
    """Pick a deterministic color for the Nth selected target."""
    return TARGET_COLOR_PALETTE[index % len(TARGET_COLOR_PALETTE)]

def make_gantt_chart(selected_targets: Sequence[dict]):
    """Render a cumulative Gantt of observable windows; highlight the latest target.

    Each item in ``selected_targets`` must have keys ``dates`` (datetime sequence),
    ``good`` (boolean array, same length), ``color``, ``display_label``, and
    ``is_cvz`` (bool). Returns the matplotlib Figure.
    """
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter, MonthLocator, date2num
    with plt.ioff():
        (fig, ax) = plt.subplots(figsize=(13, 0.7 * len(selected_targets) + 1.8))
    latest_index = len(selected_targets) - 1
    for (i, item) in enumerate(selected_targets):
        if i == latest_index:
            ax.axhspan(i - 0.43, i + 0.43, color=item['color'], alpha=0.16, zorder=0)
        windows = find_observable_runs(item['good'])
        bars = []
        for (start_idx, length) in windows:
            d_start = item['dates'][start_idx]
            d_end = item['dates'][min(start_idx + length - 1, len(item['dates']) - 1)]
            width = max(date2num(d_end) - date2num(d_start), 0.5)
            bars.append((date2num(d_start), width))
        if bars:
            ax.broken_barh(bars, (i - 0.35, 0.7), facecolors=item['color'], edgecolors='black', linewidth=0.5, zorder=2)
        else:
            ax.text(0.5, i, 'No observable days', transform=ax.get_yaxis_transform(), ha='center', va='center', fontsize=8, color=item['color'])
    labels = [f"{i + 1}: {item['display_label']}" + (' [CVZ]' if item['is_cvz'] else '') for (i, item) in enumerate(selected_targets)]
    ax.set_yticks(range(len(selected_targets)))
    ax.set_yticklabels(labels, fontsize=8)
    for (tick, item) in zip(ax.get_yticklabels(), selected_targets):
        tick.set_color(item['color'])
    ax.set_ylim(-0.6, len(selected_targets) - 0.4)
    ax.xaxis.set_major_locator(MonthLocator())
    ax.xaxis.set_major_formatter(DateFormatter('%b %d'))
    for tick in ax.get_xticklabels():
        tick.set_rotation(45)
    ax.set_xlabel('Date')
    ax.set_title('Selected-target Visibility Windows (Gantt; latest target highlighted)')
    ax.grid(axis='x', alpha=0.3)
    fig.tight_layout()
    return fig

def make_separation_comparison(selected_targets: Sequence[dict]):
    """Render the multi-target Sun-target separation overlay; highlight the latest target.

    Each item must have keys ``dates``, ``separation`` (deg array, same length),
    ``color``, and ``display_label``.
    """
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter, MonthLocator
    with plt.ioff():
        (fig, ax) = plt.subplots(figsize=(13, 5.2))
    latest_index = len(selected_targets) - 1
    for (i, item) in enumerate(selected_targets):
        is_latest = i == latest_index
        label = f"{i + 1}: {item['display_label']}"
        ax.plot(item['dates'], item['separation'], lw=3.0 if is_latest else 1.3, alpha=1.0 if is_latest else 0.72, color=item['color'], label=label + (' (latest)' if is_latest else ''), zorder=4 if is_latest else 2)
    ax.axhline(54, ls='--', color='green', lw=1, label='Min (54 deg)')
    ax.axhline(126, ls='--', color='orange', lw=1, label='Max (126 deg)')
    ax.fill_between(selected_targets[-1]['dates'], 54, 126, alpha=0.12, color='gray', label='Observable range')
    ax.set_ylabel('Sun-target separation (deg)')
    ax.set_xlabel('Date')
    ax.set_title('Selected-target Sun-Target Separation Comparison')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc='center left', bbox_to_anchor=(1.01, 0.5))
    ax.xaxis.set_major_locator(MonthLocator())
    ax.xaxis.set_major_formatter(DateFormatter('%b %d'))
    for tick in ax.get_xticklabels():
        tick.set_rotation(45)
    fig.tight_layout()
    return fig

# ---- rtvt/reports.py ----
def write_csv(result: VisibilityResult, path: str) -> None:
    """Write the sampled visibility table to a CSV file, prepending the ISO timestamp column."""
    output = result.table.copy()
    output.insert(0, 'time_isot', [time.isot for time in result.sampled_times])
    output.to_csv(path, index=True)

def figure_img_html(fig, dpi: int=120, close: bool=True) -> str:
    """Encode a matplotlib figure as a self-contained inline ``<img>`` tag."""
    png = figure_to_png_bytes(fig, dpi=dpi, close=close)
    encoded = base64.b64encode(png).decode('ascii')
    return f'<img src="data:image/png;base64,{encoded}" style="max-width: 100%; height: auto;">'

def make_html_report(result: VisibilityResult, target_name: str | None=None, plot_png: bytes | None=None) -> str:
    """Build a single-target HTML report (summary + plot + windows + data table)."""
    title = target_name or result.label
    windows = summarize_windows(result)
    sampled = result.table.copy()
    sampled.insert(0, 'time_isot', [time.isot for time in result.sampled_times])
    if plot_png is None:
        prepare_matplotlib_cache()
        fig = plot_visibility_result(result, target_name=target_name)
        plot_png = figure_to_png_bytes(fig, close=True)
    plot_encoded = base64.b64encode(plot_png).decode('ascii')
    return f"""<!doctype html>\n<html>\n<head>\n  <meta charset="utf-8">\n  <title>RTVT Report - {html.escape(title)}</title>\n  <style>\n    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2933; }}\n    h1, h2 {{ color: #1e334c; }}\n    pre {{ background: #f4f6f8; padding: 14px; white-space: pre-wrap; }}\n    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}\n    th, td {{ border: 1px solid #ddd; padding: 5px; text-align: left; }}\n    th {{ background: #f4f6f8; }}\n    img {{ max-width: 100%; height: auto; }}\n  </style>\n</head>\n<body>\n  <h1>Roman Target Visibility Tool Report</h1>\n  <h2>Summary</h2>\n  <pre>{html.escape(format_summary(result, target_name=target_name))}</pre>\n  <h2>Visibility Plot</h2>\n  <img src="data:image/png;base64,{plot_encoded}">\n  <h2>Observable Windows</h2>\n  {(windows.to_html(index=False) if not windows.empty else '<p>No observable windows found.</p>')}\n  <h2>Sampled Data</h2>\n  {sampled.to_html(index=True)}\n</body>\n</html>\n"""

def write_report(result: VisibilityResult, path: str, target_name: str | None=None) -> None:
    """Write the single-target HTML report to ``path``."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(make_html_report(result, target_name=target_name), encoding='utf-8')


prepare_matplotlib_cache()
import matplotlib.pyplot as plt

# ---- rtvt/notebook.py ----
SUN_ANGLE_MIN_DEG = 54.0

SUN_ANGLE_MAX_DEG = 126.0

TARGET_NAME_ALIASES = {'andromeda': 'M31', 'andromeda galaxy': 'M31'}

LOCAL_TARGET_COORDS = {'m31': ('M31', 10.6847083, 41.26875)}

def _dataframe_doy_to_datetime(df) -> 'pd.DatetimeIndex':
    import pandas as pd
    return pd.to_datetime(df.index.astype(str), format='%Y-%j.%f')

def _resolve_target_name(target_name: str) -> dict:
    cleaned_name = ' '.join(str(target_name).strip().split())
    if not cleaned_name:
        raise ValueError('Enter a target name first.')
    lookup_name = TARGET_NAME_ALIASES.get(cleaned_name.casefold(), cleaned_name)
    local_target = LOCAL_TARGET_COORDS.get(lookup_name.casefold())
    if local_target is not None:
        (resolved_name, ra_deg, dec_deg) = local_target
        return {'input_name': cleaned_name, 'lookup_name': resolved_name, 'coord': SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame='icrs')}
    sky = SkyCoord.from_name(lookup_name).icrs
    return {'input_name': cleaned_name, 'lookup_name': lookup_name, 'coord': sky}

def _target_name_display_label(resolved_target: dict) -> str:
    input_name = resolved_target['input_name']
    lookup_name = resolved_target['lookup_name']
    if input_name.casefold() == lookup_name.casefold():
        return input_name
    return f'{input_name} ({lookup_name})'

def launch_interactive_sky_gantt(ra_grid=None, dec_grid=None, vis_frac_2d=None, test_targets=None, grid_step_deg=10, start_time='2027-01-01', duration_days=365, sampling_days=1, good_angle_threshold=0.99, coordinate_system='equatorial'):
    """Launch the Mollweide picker plus cumulative Gantt + separation comparison.

    If ``ra_grid``, ``dec_grid``, and ``vis_frac_2d`` are all supplied, they
    are reused. If any are omitted, a coarse all-sky visibility map is
    computed (using the cached result when available).
    """
    coordinate_system = normalize_coordinate_system(coordinate_system)
    (lon_label, lat_label, coordinate_title) = coordinate_labels(coordinate_system)
    if ra_grid is None and dec_grid is None and (vis_frac_2d is None):
        (ra_grid, dec_grid, vis_frac_2d) = get_cached_all_sky_visibility_grid(grid_step_deg=grid_step_deg, start_time=start_time, duration_days=duration_days, sampling_days=sampling_days, coordinate_system=coordinate_system)
    elif ra_grid is None or dec_grid is None or vis_frac_2d is None:
        (ra_grid, dec_grid, vis_frac_2d) = compute_all_sky_visibility_grid(ra_grid=ra_grid, dec_grid=dec_grid, grid_step_deg=grid_step_deg, start_time=start_time, duration_days=duration_days, sampling_days=sampling_days, coordinate_system=coordinate_system)
    (fig_sky, ax_sky, _pcm) = make_all_sky_mollweide(ra_grid, dec_grid, vis_frac_2d, coordinate_system=coordinate_system, test_targets=test_targets)
    status_label = widgets.Label(value=f'Click on the sky map to select targets in {coordinate_title} coordinates.')
    plots_output = widgets.HTML()
    report_button = widgets.Button(description='Create report + CSV', button_style='success', tooltip='Write an HTML report and CSV table exports for the selected targets.', layout=widgets.Layout(width='190px'))
    report_status = widgets.HTML()
    rendered_plots = {'latest': '', 'gantt': '', 'comparison': ''}
    selected_targets: list[dict] = []
    selected_markers: list = []
    selected_number_labels: list = []
    target_name = widgets.Text(description='Name:', placeholder='Andromeda, M31, Vega', layout=widgets.Layout(width='220px'), style={'description_width': '54px'})
    name_button = widgets.Button(description='Add named target', button_style='primary', tooltip='Resolve a target name and compute its visibility.', layout=widgets.Layout(width='220px'))
    name_status = widgets.HTML()
    manual_lon = widgets.Text(description=f'{lon_label}:', placeholder='decimal degrees', layout=widgets.Layout(width='220px'), style={'description_width': '54px'})
    manual_lat = widgets.Text(description=f'{lat_label}:', placeholder='decimal degrees', layout=widgets.Layout(width='220px'), style={'description_width': '54px'})
    manual_button = widgets.Button(description='Add coordinate target', button_style='primary', tooltip='Compute visibility for the typed coordinates.', layout=widgets.Layout(width='220px'))
    manual_status = widgets.HTML()
    manual_panel = widgets.VBox([widgets.HTML("<b>Search by target name</b><br><span style='font-size: 12px; color: #666;'>Type a common object name, then add it to the map.</span>"), target_name, name_button, name_status, widgets.HTML(f"<hr style='border:0; border-top:1px solid #ddd; margin:10px 0;'><b>Exact {html.escape(coordinate_title)} coordinates</b><br><span style='font-size: 12px; color: #666;'>Enter decimal-degree coordinates, or click the map.</span>"), manual_lon, manual_lat, manual_button, manual_status], layout=widgets.Layout(width='255px', border='1px solid #d6d6d6', padding='10px', margin='0 12px 0 0'))

    def _plot_section(title, image_html):
        return f'<section style="margin-top: 14px;"><h3 style="margin: 0 0 6px 0; font-size: 16px;">{title}</h3>{image_html}</section>'

    def _update_plots_output():
        plots_output.value = '\n'.join((rendered_plots[key] for key in ('latest', 'gantt', 'comparison') if rendered_plots[key]))

    def _map_radians(lon_deg, lat_deg):
        plot_lon = lon_deg - 360.0 if lon_deg > 180.0 else lon_deg
        return (np.deg2rad(plot_lon), np.deg2rad(lat_deg))

    def _format_date(value) -> str:
        if value is None or value == '':
            return ''
        return value.strftime('%Y-%m-%d')

    def _format_float(value, precision=3) -> str:
        if value is None or value == '':
            return ''
        if not np.isfinite(value):
            return ''
        return f'{value:.{precision}f}'

    def _run_parameter_rows():
        sampled_times = sampled_times_for_interval(start_time=start_time, duration_days=duration_days, sampling_days=sampling_days)
        return [('Display coordinate system', coordinate_title), ('Input longitude label', lon_label), ('Input latitude label', lat_label), ('Interval start', sampled_times[0].isot), ('Interval end', sampled_times[-1].isot), ('Duration', f'{duration_days:g} days'), ('Sampling cadence', f'{sampling_days:g} day(s)'), ('Sample count', str(len(sampled_times))), ('All-sky grid step', f'{grid_step_deg:g} deg'), ('All-sky grid shape', f'{len(ra_grid)} longitude x {len(dec_grid)} latitude samples'), ('Allowed Sun-target separation', f'{SUN_ANGLE_MIN_DEG:g}-{SUN_ANGLE_MAX_DEG:g} deg'), ('CVZ visibility threshold', f'{good_angle_threshold * 100:.1f}%'), ('Visibility engine frame', 'ICRS target positions with ecliptic-frame roll geometry')]

    def _run_parameters_dataframe():
        import pandas as pd
        return pd.DataFrame([{'parameter': label, 'value': value} for (label, value) in _run_parameter_rows()])

    def _run_parameters_html() -> str:
        rows = _run_parameter_rows()
        rows_html = ''.join((f'<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>' for (label, value) in rows))
        return "<div style='overflow-x:auto;'><table style='border-collapse: collapse; width: 100%; font-size: 12px;'><tbody>" + rows_html + '</tbody></table></div>'

    def _target_summary_dataframe():
        import pandas as pd
        rows = []
        for (i, item) in enumerate(selected_targets, start=1):
            target_icrs = SkyCoord(ra=item['ra_deg'] * u.deg, dec=item['dec_deg'] * u.deg, frame='icrs')
            gal_l = float(target_icrs.galactic.l.deg)
            gal_b = float(target_icrs.galactic.b.deg)
            (ecl_lon, ecl_lat) = display_lon_lat(target_icrs, 'ecliptic')
            rows.append({'target_index': i, 'target': item['display_label'], 'input_system': item['coord_system'], f'{lon_label}_deg': item['coord_lon_deg'], f'{lat_label}_deg': item['coord_lat_deg'], 'ra_deg': item['ra_deg'], 'dec_deg': item['dec_deg'], 'galactic_l_deg': gal_l, 'galactic_b_deg': gal_b, 'ecliptic_lon_deg': ecl_lon, 'ecliptic_lat_deg': ecl_lat, 'visible_samples': item['visible_samples'], 'total_samples': item['total_samples'], 'visible_days': item['visible_days'], 'visible_fraction': item['vis_fraction'], 'window_count': item['window_count'], 'first_visible_date': _format_date(item['first_visible_date']), 'last_visible_date': _format_date(item['last_visible_date']), 'min_separation_deg': item['min_separation_deg'], 'max_separation_deg': item['max_separation_deg'], 'min_nominal_roll_deg': item['min_nominal_roll_deg'], 'max_nominal_roll_deg': item['max_nominal_roll_deg'], 'is_cvz': item['is_cvz']})
        return pd.DataFrame(rows)

    def _target_rows_html():
        if not selected_targets:
            return '<p>No selected targets yet.</p>'
        rows = []
        for (i, item) in enumerate(selected_targets, start=1):
            target_icrs = SkyCoord(ra=item['ra_deg'] * u.deg, dec=item['dec_deg'] * u.deg, frame='icrs')
            gal_l = float(target_icrs.galactic.l.deg)
            gal_b = float(target_icrs.galactic.b.deg)
            (ecl_lon, ecl_lat) = display_lon_lat(target_icrs, 'ecliptic')
            rows.append(f"<tr><td>{i}</td><td><span style='color:{item['color']}; font-weight: 700;'>{html.escape(item['display_label'])}</span></td><td>{html.escape(item['coord_system'])}</td><td>{item['coord_lon_deg']:.6f}</td><td>{item['coord_lat_deg']:.6f}</td><td>{item['ra_deg']:.6f}</td><td>{item['dec_deg']:.6f}</td><td>{gal_l:.6f}</td><td>{gal_b:.6f}</td><td>{ecl_lon:.6f}</td><td>{ecl_lat:.6f}</td><td>{item['visible_samples']}/{item['total_samples']}</td><td>{item['visible_days']:.3f}</td><td>{item['vis_fraction'] * 100:.1f}%</td><td>{item['window_count']}</td><td>{html.escape(_format_date(item['first_visible_date']))}</td><td>{html.escape(_format_date(item['last_visible_date']))}</td><td>{item['min_separation_deg']:.3f}</td><td>{item['max_separation_deg']:.3f}</td><td>{item['min_nominal_roll_deg']:.3f}</td><td>{item['max_nominal_roll_deg']:.3f}</td><td>{('Yes' if item['is_cvz'] else 'No')}</td></tr>")
        return f"<div style='overflow-x:auto;'><table style='border-collapse: collapse; width: 100%;'><thead><tr><th>#</th><th>Input</th><th>Input system</th><th>{html.escape(lon_label)} deg</th><th>{html.escape(lat_label)} deg</th><th>RA deg</th><th>Dec deg</th><th>Galactic l deg</th><th>Galactic b deg</th><th>Ecliptic lon deg</th><th>Ecliptic lat deg</th><th>Visible samples</th><th>Visible days</th><th>Visible fraction</th><th>Window count</th><th>First visible date</th><th>Last visible date</th><th>Min sep deg</th><th>Max sep deg</th><th>Min nominal roll deg</th><th>Max nominal roll deg</th><th>CVZ flag</th></tr></thead><tbody>" + ''.join(rows) + '</tbody></table></div><style>th,td{border:1px solid #ddd;padding:6px;text-align:left;}th{background:#f4f6f8;}</style>'

    def _observable_windows_dataframe():
        import pandas as pd
        rows = []
        for (i, item) in enumerate(selected_targets, start=1):
            windows = find_observable_runs(item['good'])
            nominal_roll = item['nominal_roll_deg']
            separation = item['separation']
            if not windows:
                rows.append({'target_index': i, 'target': item['display_label'], 'window_index': '', 'start_date': '', 'end_date': '', 'duration_days': 0.0, 'nominal_roll_start_deg': '', 'nominal_roll_end_deg': '', 'separation_start_deg': '', 'separation_end_deg': ''})
                continue
            for (window_number, (start_idx, length)) in enumerate(windows, start=1):
                end_idx = start_idx + length - 1
                rows.append({'target_index': i, 'target': item['display_label'], 'window_index': window_number, 'start_date': _format_date(item['dates'][start_idx]), 'end_date': _format_date(item['dates'][end_idx]), 'duration_days': length * sampling_days, 'nominal_roll_start_deg': nominal_roll[start_idx], 'nominal_roll_end_deg': nominal_roll[end_idx], 'separation_start_deg': separation[start_idx], 'separation_end_deg': separation[end_idx]})
        return pd.DataFrame(rows)

    def _observable_windows_html():
        if not selected_targets:
            return '<p>No selected targets yet.</p>'
        rows = []
        for (i, item) in enumerate(selected_targets, start=1):
            windows = find_observable_runs(item['good'])
            if not windows:
                rows.append(f"<tr><td>{i}</td><td>{html.escape(item['display_label'])}</td><td colspan='6'>No observable windows found.</td></tr>")
                continue
            nominal_roll = item['nominal_roll_deg']
            separation = item['separation']
            for (window_number, (start_idx, length)) in enumerate(windows, start=1):
                end_idx = start_idx + length - 1
                rows.append(f"<tr><td>{i}</td><td>{html.escape(item['display_label'])}</td><td>{window_number}</td><td>{html.escape(_format_date(item['dates'][start_idx]))}</td><td>{html.escape(_format_date(item['dates'][end_idx]))}</td><td>{length * sampling_days:.3f}</td><td>{nominal_roll[start_idx]:.3f}</td><td>{nominal_roll[end_idx]:.3f}</td><td>{separation[start_idx]:.3f}</td><td>{separation[end_idx]:.3f}</td></tr>")
        return "<div style='overflow-x:auto;'><table style='border-collapse: collapse; width: 100%;'><thead><tr><th>#</th><th>Target</th><th>Window</th><th>Start date</th><th>End date</th><th>Duration days</th><th>Nominal roll start deg</th><th>Nominal roll end deg</th><th>Separation start deg</th><th>Separation end deg</th></tr></thead><tbody>" + ''.join(rows) + '</tbody></table></div>'

    def _detailed_samples_dataframe():
        import pandas as pd
        rows = []
        for (i, item) in enumerate(selected_targets, start=1):
            table = item['table']
            sun_ra = quantity_series_to_deg(table['Sun_RA'])
            sun_dec = quantity_series_to_deg(table['Sun_Dec'])
            nominal_roll = item['nominal_roll_deg']
            pa_obs_y = quantity_series_to_deg(table['pa_obs_y'])
            pa_fpa_local_x = quantity_series_to_deg(table['pa_fpa_local_x'])
            pa_fpa_local_y = quantity_series_to_deg(table['pa_fpa_local_y'])
            sunang_x = quantity_series_to_deg(table['sunang_x'])
            sunang_y = quantity_series_to_deg(table['sunang_y'])
            sunang_z = quantity_series_to_deg(table['sunang_z'])
            for (row_idx, doy_label) in enumerate(table.index.astype(str)):
                rows.append({'target_index': i, 'target': item['display_label'], 'row_index': row_idx + 1, 'doy_index': str(doy_label), 'date_utc': _format_date(item['dates'][row_idx]), 'sun_ra_deg': sun_ra[row_idx], 'sun_dec_deg': sun_dec[row_idx], 'sun_target_separation_deg': item['separation'][row_idx], 'visible': bool(item['good'][row_idx]), 'nominal_roll_deg': nominal_roll[row_idx], 'pa_obs_y_deg': pa_obs_y[row_idx], 'pa_fpa_local_x_deg': pa_fpa_local_x[row_idx], 'pa_fpa_local_y_deg': pa_fpa_local_y[row_idx], 'sunang_x_deg': sunang_x[row_idx], 'sunang_y_deg': sunang_y[row_idx], 'sunang_z_deg': sunang_z[row_idx]})
        return pd.DataFrame(rows)

    def _detailed_sample_tables_html():
        if not selected_targets:
            return '<p>No selected targets yet.</p>'
        target_sections = []
        for (i, item) in enumerate(selected_targets, start=1):
            table = item['table']
            sun_ra = quantity_series_to_deg(table['Sun_RA'])
            sun_dec = quantity_series_to_deg(table['Sun_Dec'])
            nominal_roll = item['nominal_roll_deg']
            pa_obs_y = quantity_series_to_deg(table['pa_obs_y'])
            pa_fpa_local_x = quantity_series_to_deg(table['pa_fpa_local_x'])
            pa_fpa_local_y = quantity_series_to_deg(table['pa_fpa_local_y'])
            sunang_x = quantity_series_to_deg(table['sunang_x'])
            sunang_y = quantity_series_to_deg(table['sunang_y'])
            sunang_z = quantity_series_to_deg(table['sunang_z'])
            rows = []
            for (row_idx, doy_label) in enumerate(table.index.astype(str)):
                rows.append(f"<tr><td>{row_idx + 1}</td><td>{html.escape(str(doy_label))}</td><td>{html.escape(_format_date(item['dates'][row_idx]))}</td><td>{sun_ra[row_idx]:.6f}</td><td>{sun_dec[row_idx]:.6f}</td><td>{item['separation'][row_idx]:.6f}</td><td>{bool(item['good'][row_idx])}</td><td>{nominal_roll[row_idx]:.6f}</td><td>{pa_obs_y[row_idx]:.6f}</td><td>{pa_fpa_local_x[row_idx]:.6f}</td><td>{pa_fpa_local_y[row_idx]:.6f}</td><td>{sunang_x[row_idx]:.6f}</td><td>{sunang_y[row_idx]:.6f}</td><td>{sunang_z[row_idx]:.6f}</td></tr>")
            target_sections.append(f"<details style='margin-top: 10px;'><summary><b>Target {i}: {html.escape(item['display_label'])}</b> ({len(table)} sampled rows)</summary><div style='overflow-x:auto; max-height: 480px; overflow-y:auto;'><table style='border-collapse: collapse; width: 100%; font-size: 11px;'><thead><tr><th>#</th><th>DOY index</th><th>Date UTC</th><th>Sun RA deg</th><th>Sun Dec deg</th><th>Sun-target sep deg</th><th>Visible?</th><th>Nominal roll deg</th><th>PA obs Y deg</th><th>PA FPA local X deg</th><th>PA FPA local Y deg</th><th>Sun angle X deg</th><th>Sun angle Y deg</th><th>Sun angle Z deg</th></tr></thead><tbody>" + ''.join(rows) + '</tbody></table></div></details>')
        return ''.join(target_sections)

    def _target_tables_html(include_detailed_samples=False):
        detailed = ''
        if include_detailed_samples:
            detailed = f"<section style='margin-top: 16px;'><h3 style='margin-bottom: 6px;'>Detailed Sampled Visibility Data</h3><p style='color:#53606d;'>These collapsible tables include every sampled row and every per-sample quantity computed by the visibility calculator.</p>{_detailed_sample_tables_html()}</section>"
        return f"<section style='margin-top: 14px;'><h3 style='margin-bottom: 6px;'>Run Parameters</h3>{_run_parameters_html()}</section><section style='margin-top: 16px;'><h3 style='margin-bottom: 6px;'>Selected Target Summary</h3>{_target_rows_html()}</section><section style='margin-top: 16px;'><h3 style='margin-bottom: 6px;'>Observable Windows</h3>{_observable_windows_html()}</section>{detailed}"

    def _write_csv_tables(timestamp: str) -> Path:
        csv_dir = Path.cwd() / f'rtvt_visibility_tables_{timestamp}'
        csv_dir.mkdir(parents=True, exist_ok=True)
        _run_parameters_dataframe().to_csv(csv_dir / 'run_parameters.csv', index=False)
        _target_summary_dataframe().to_csv(csv_dir / 'selected_targets.csv', index=False)
        _observable_windows_dataframe().to_csv(csv_dir / 'observable_windows.csv', index=False)
        _detailed_samples_dataframe().to_csv(csv_dir / 'sampled_visibility.csv', index=False)
        return csv_dir

    def _create_report(_event=None):
        if not selected_targets:
            report_status.value = "<span style='color:#b00020;'>Select at least one target first.</span>"
            return
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = Path.cwd() / f'rtvt_visibility_report_{timestamp}.html'
        csv_dir = _write_csv_tables(timestamp)
        plot_sections = '\n'.join((rendered_plots[key] for key in ('latest', 'gantt', 'comparison') if rendered_plots[key]))
        sky_snapshot = _plot_section('All-Sky Selection Map', figure_img_html(fig_sky, close=False))
        report_html = f"""<!doctype html>\n<html>\n<head>\n  <meta charset="utf-8">\n  <title>RTVT Visibility Report</title>\n  <style>\n    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2933; }}\n    h1, h2, h3 {{ color: #1e334c; }}\n    .meta {{ color: #53606d; margin-bottom: 18px; }}\n    section {{ margin-top: 22px; }}\n  </style>\n</head>\n<body>\n  <h1>Roman Target Visibility Tool Report</h1>\n  <div class="meta">\n    Generated {html.escape(datetime.now().isoformat(timespec='seconds'))}<br>\n    Coordinate system: {html.escape(coordinate_title)}<br>\n    Duration: {duration_days:g} days; sampling: {sampling_days:g} day(s)\n  </div>\n  <section>\n    <h2>Tables</h2>\n    {_target_tables_html(include_detailed_samples=True)}\n  </section>\n  {sky_snapshot}\n  {plot_sections}\n</body>\n</html>\n"""
        report_path.write_text(report_html, encoding='utf-8')
        report_status.value = f'Report saved: <code>{html.escape(str(report_path))}</code><br>CSV tables saved in: <code>{html.escape(str(csv_dir))}</code>'
    report_button.on_click(_create_report)

    def _render_latest_visibility(display_label, radec_label, item):
        title_suffix = ' [CVZ]' if item['is_cvz'] else ''
        fig_v = make_visibility_plot(item['dates'], item['good'], item['separation'], visibility_title=f"Visibility Window -- {display_label}{title_suffix} (vis frac = {item['vis_fraction'] * 100:.1f}%)", separation_title=f'Sun-Target Separation -- {display_label} ({radec_label})', color=item['color'], line_width=1.8, fill_color='gray')
        rendered_plots['latest'] = _plot_section('Latest Target Visibility', figure_img_html(fig_v))
        _update_plots_output()

    def _render_selected_gantt():
        if not selected_targets:
            rendered_plots['gantt'] = ''
            rendered_plots['comparison'] = ''
            _update_plots_output()
            return
        fig_g = make_gantt_chart(selected_targets)
        rendered_plots['gantt'] = _plot_section('Selected-Target Visibility Gantt', figure_img_html(fig_g))
        _update_plots_output()
        fig_c = make_separation_comparison(selected_targets)
        rendered_plots['comparison'] = _plot_section('All-Target Sun-Target Separation Comparison', figure_img_html(fig_c))
        _update_plots_output()

    def _add_target(tgt_click, lon_deg, lat_deg, map_lon_rad, map_lat_rad, display_label=None):
        if display_label is None:
            display_label = format_display_coordinate(lon_deg, lat_deg, coordinate_system, precision=4)
        status_label.value = f'Computing visibility for {display_label}...'
        name_status.value = ''
        manual_status.value = ''
        report_status.value = ''
        t0 = normalize_start_time(start_time)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', AstropyWarning)
            vis = VisibilityCalculator(tgt_click, report=False, fileout=None, interval_sampling_days=sampling_days, interval_start_time=t0, interval_duration_days=duration_days)
            vis.compute_and_display()
        radec_label = vis.df_results.index.levels[0][0]
        df_one = vis.df_results.xs(radec_label, level=0)
        good = df_one['good_angles'].astype(bool).values
        dates_vis = _dataframe_doy_to_datetime(df_one)
        separation = quantity_series_to_deg(df_one['separation'])
        nominal_roll = quantity_series_to_deg(df_one['nominal_roll'])
        windows = find_observable_runs(good)
        first_visible_date = ''
        last_visible_date = ''
        if windows:
            first_visible_date = dates_vis[windows[0][0]]
            (last_window_start, last_window_length) = windows[-1]
            last_visible_date = dates_vis[last_window_start + last_window_length - 1]
        (is_cvz, vis_fraction, _) = check_cvz_status(df_one, good_angle_threshold=good_angle_threshold)
        target_number = len(selected_targets) + 1
        marker_color = target_color(target_number - 1)
        (marker,) = ax_sky.plot([map_lon_rad], [map_lat_rad], marker='x', linestyle='None', color=marker_color, markersize=15, markeredgewidth=3, zorder=10)
        number_label = ax_sky.text(map_lon_rad, map_lat_rad, f' {target_number}', color=marker_color, fontsize=10, fontweight='bold', ha='left', va='bottom', bbox=dict(facecolor='white', alpha=0.75, edgecolor='none', pad=1.5), zorder=11)
        selected_markers.append(marker)
        selected_number_labels.append(number_label)
        item = dict(label=radec_label, display_label=display_label, coord_system=coordinate_system, coord_lon_deg=float(lon_deg), coord_lat_deg=float(lat_deg), ra_deg=float(tgt_click.icrs.ra.deg), dec_deg=float(tgt_click.icrs.dec.deg), dates=dates_vis, good=good, separation=separation, nominal_roll_deg=nominal_roll, table=df_one.copy(), total_samples=int(len(good)), visible_samples=int(np.sum(good)), visible_days=float(np.sum(good) * sampling_days), window_count=int(len(windows)), first_visible_date=first_visible_date, last_visible_date=last_visible_date, min_separation_deg=float(np.min(separation)), max_separation_deg=float(np.max(separation)), min_nominal_roll_deg=float(np.min(nominal_roll)), max_nominal_roll_deg=float(np.max(nominal_roll)), is_cvz=bool(is_cvz), vis_fraction=float(vis_fraction), color=marker_color)
        selected_targets.append(item)
        fig_sky.canvas.draw_idle()
        _render_latest_visibility(display_label, radec_label, item)
        _render_selected_gantt()
        status_label.value = f"Selected {len(selected_targets)} target(s). Latest: {display_label} -- {radec_label} -- Vis: {vis_fraction * 100:.1f}% -- {('CVZ' if is_cvz else 'not CVZ')}"

    def _compute_manual_target(_event=None):
        try:
            lon_deg = float(manual_lon.value)
            lat_deg = float(manual_lat.value)
        except ValueError:
            manual_status.value = "<span style='color:#b00020;'>Enter numeric decimal-degree coordinates.</span>"
            return
        if not -90.0 <= lat_deg <= 90.0:
            manual_status.value = "<span style='color:#b00020;'>Latitude must be between -90 and +90 degrees.</span>"
            return
        lon_deg = lon_deg % 360.0
        (map_lon_rad, map_lat_rad) = _map_radians(lon_deg, lat_deg)
        tgt_manual = skycoord_from_lon_lat(lon_deg, lat_deg, coordinate_system)
        _add_target(tgt_manual, lon_deg, lat_deg, map_lon_rad, map_lat_rad)

    def _compute_named_target(_event=None):
        try:
            resolved = _resolve_target_name(target_name.value)
        except Exception as exc:
            name_status.value = f"<span style='color:#b00020;'>Could not resolve target name: {html.escape(str(exc))}</span>"
            return
        tgt_named = resolved['coord']
        (lon_deg, lat_deg) = display_lon_lat(tgt_named, coordinate_system)
        (map_lon_rad, map_lat_rad) = _map_radians(lon_deg, lat_deg)
        _add_target(tgt_named, lon_deg, lat_deg, map_lon_rad, map_lat_rad, display_label=_target_name_display_label(resolved))

    def on_sky_click(event):
        if event.inaxes is not ax_sky or event.xdata is None:
            return
        lon_rad = event.xdata
        lat_rad = event.ydata
        lon_deg = np.degrees(lon_rad)
        if lon_deg < 0:
            lon_deg += 360.0
        lat_deg = np.degrees(lat_rad)
        lon_deg = float(np.clip(lon_deg, 0, 360))
        lat_deg = float(np.clip(lat_deg, -90, 90))
        tgt_click = skycoord_from_lon_lat(lon_deg, lat_deg, coordinate_system)
        _add_target(tgt_click, lon_deg, lat_deg, lon_rad, lat_rad)
    name_button.on_click(_compute_named_target)
    manual_button.on_click(_compute_manual_target)
    fig_sky.canvas.mpl_connect('button_press_event', on_sky_click)
    is_widget_canvas = isinstance(fig_sky.canvas, widgets.Widget)
    if is_widget_canvas:
        fig_sky.canvas.layout = widgets.Layout(width='900px', height='520px', min_width='720px')
        fig_sky.canvas.draw_idle()
        map_child = fig_sky.canvas
        map_note = None
    else:
        map_child = widgets.Output()
        map_note = widgets.HTML("<span style='color:#b00020;'>The sky map is not using the interactive Matplotlib widget backend. Run <code>%matplotlib widget</code> before launching RTVT and make sure <code>ipympl</code> is installed in this kernel.</span>")
        with map_child:
            display(fig_sky)
    map_box_children = [manual_panel, map_child]
    map_box = widgets.HBox(map_box_children, layout=widgets.Layout(align_items='flex-start'))
    display(map_box)
    if map_note is not None:
        display(map_note)
        plt.close(fig_sky)
    display(status_label)
    display(plots_output)
    display(widgets.HBox([report_button, report_status], layout=widgets.Layout(margin='12px 0 0 0')))
    return {'fig_sky': fig_sky, 'ax_sky': ax_sky, 'status_label': status_label, 'target_name': target_name, 'name_button': name_button, 'name_status': name_status, 'manual_panel': manual_panel, 'manual_lon': manual_lon, 'manual_lat': manual_lat, 'manual_button': manual_button, 'manual_status': manual_status, 'plots_output': plots_output, 'report_button': report_button, 'report_status': report_status, 'selected_targets': selected_targets, 'selected_markers': selected_markers, 'selected_number_labels': selected_number_labels}

def launch_interactive_sky_gantt_with_controls(grid_step_deg=10, start_time='2027-01-01', duration_days=365, sampling_days=1, good_angle_threshold=0.99):
    """Wrap `launch_interactive_sky_gantt` with a coordinate-system toggle.

    Click *Launch / Refresh* after changing the coordinate system. The frame
    controls the map axes and the per-target display coordinates; the
    underlying Roman visibility math always runs in ICRS.
    """
    coordinate_selector = widgets.ToggleButtons(options=[('Equatorial (RA/Dec)', 'equatorial'), ('Galactic (l/b)', 'galactic'), ('Ecliptic (lon/lat)', 'ecliptic')], value='equatorial', description='Coords:', button_style='')
    launch_button = widgets.Button(description='Launch / Refresh', button_style='primary', tooltip='Create the visibility map with the selected coordinate system.')
    output = widgets.Output()
    state = {'viewer': None}

    def _launch(_event=None):
        with output:
            clear_output(wait=True)
            previous_viewer = state.get('viewer')
            if previous_viewer is not None:
                plt.close(previous_viewer['fig_sky'])
            print(f'Preparing {coordinate_selector.value} all-sky map...')
            state['viewer'] = launch_interactive_sky_gantt(grid_step_deg=grid_step_deg, start_time=start_time, duration_days=duration_days, sampling_days=sampling_days, good_angle_threshold=good_angle_threshold, coordinate_system=coordinate_selector.value)
    coordinate_selector.observe(_launch, names='value')
    launch_button.on_click(_launch)
    display(widgets.VBox([widgets.HBox([coordinate_selector, launch_button]), output]))
    _launch()
    return {'coordinate_selector': coordinate_selector, 'launch_button': launch_button, 'output': output, 'state': state}
