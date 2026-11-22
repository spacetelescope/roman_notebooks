import gc
import json
import logging
import os
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import asdf
import numpy as np
import pandas as pd
import roman_datamodels as rdm
from asdf.exceptions import AsdfPackageVersionWarning
from astropy.time import Time
from astroquery.mast import MastMissions
from bokeh.models import (
    BoxZoomTool,
    ColumnDataSource,
    CrosshairTool,
    Range1d,
    HoverTool,
)
from bokeh.core.validation import silence
from bokeh.core.validation.warnings import MISSING_RENDERERS
from bokeh.plotting import figure
from dotenv import load_dotenv
from erfa import ErfaWarning
from roman_datamodels.datamodels import DataModel


silence(MISSING_RENDERERS, True)
_MAST_LOCK = threading.RLock()  # astroquery sessions are not thread-safe
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S")
    )
    logger.addHandler(_handler)
    logger.propagate = False

warnings.filterwarnings(
    "ignore",
    message=r'ERFA function "dtf2d".*dubious year',
    category=ErfaWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"File .*was created with extension URI",
    category=AsdfPackageVersionWarning,
)


def get_mnemonic_data(
    mnemonic, start_time, end_time, env_variables=None, *, token=None
):
    """Fetch Roman engineering data as a pandas DataFrame."""
    params = {
        "mnemonic": mnemonic,
        "s_time": datetime.fromisoformat(start_time).isoformat(),
        "e_time": datetime.fromisoformat(end_time).isoformat(),
        "result_format": "csv",
    }

    if env_variables:
        load_dotenv(env_variables, override=True)
        token = os.getenv("MAST_API_TOKEN")

    headers = {"Authorization": f"token {token}"} if token else {}
    endpoint = "https://mast.stsci.edu/edp/api/v0.1/mnemonics/spa/roman/data"
    request = Request(f"{endpoint}?{urlencode(params)}", headers=headers)

    with urlopen(request, timeout=60) as response:
        return pd.read_csv(response)


def get_data(
    science_filename,
    env_variables=None,
    *,
    get_sci=False,
    get_face=False,
    get_gw=False,
    face_filename=None,
    gw_filename=None,
):
    """Search MAST once and load only the requested products."""
    if not any((get_sci, get_face, get_gw)):
        return None, None, None

    science_filename = os.path.basename(science_filename)
    mission = MastMissions(mission="roman")

    if env_variables:
        load_dotenv(env_variables, override=True)
        mission.login(token=os.getenv("MAST_API_TOKEN"))

    file_set = "_".join(science_filename.split("_")[:-1])
    search = mission.query_criteria(fileSetName=file_set)
    products = mission.get_product_list(search)
    filenames = set(products["filename"])

    def load_product(label, *, filename=None, suffix=None):
        if filename is not None:
            filename = os.path.basename(filename)
            matches = [filename] if filename in filenames else []
        else:
            matches = sorted(
                name for name in filenames if name.endswith(suffix)
            )

        if len(matches) != 1:
            raise ValueError(
                f"Expected one {label} product; found {len(matches)}: {matches}"
            )
        return rdm.open(mission.read_product(matches[0]))

    sci = load_product("science", filename=science_filename) if get_sci else None
    face = (
        load_product("FACE", filename=face_filename, suffix="_face.asdf")
        if get_face
        else None
    )
    gw = (
        load_product("GW", filename=gw_filename, suffix="_gw.asdf")
        if get_gw
        else None
    )
    return sci, face, gw


def get_face_info(face_file):
    """
    Return FACE delta, epsilon, and zeta time series in milliarcseconds.

    Delta maps to X, epsilon maps to Y, and zeta maps to roll.
    """
    face_data = face_file["face_data"]

    raw_times = face_data["centroid_times"]
    if len(raw_times) == 0 or np.all(
        getattr(raw_times, "mask", np.ma.getmaskarray(raw_times))
    ):
        return {
            "time": np.array([], dtype=object),
            **{key: np.array([], dtype=float) for key in ("delta", "epsilon", "zeta")},
        }
    times = Time(raw_times)
    good = np.asarray(
        np.ma.filled(times > Time("2000-01-01T00:00:00"), False),
        dtype=bool,
    ) & ~np.asarray(times.mask)

    radians_to_mas = (180 / np.pi) * 3_600 * 1_000

    return {
        "time": times[good].to_datetime(),
        "delta": face_data["delta"][good] * radians_to_mas,
        "epsilon": face_data["epsilon"][good] * radians_to_mas,
        "zeta": face_data["zeta"][good] * radians_to_mas,
    }


def get_sci_info(sci_file):
    """Return the science exposure start and end times."""
    exposure = sci_file.meta.exposure
    return {
        "expstart": exposure.start_time,
        "expend": exposure.end_time,
    }


def _decimate(times, columns, max_points):
    """Return sorted indices keeping each column's min and max per time bin.

    Peaks and dips stay visible while the point count is bounded. This is for
    display only; analysis uses the full data.
    """
    order = np.argsort(times)
    n = len(order)
    if max_points is None or n <= max_points:
        return order
    bins = max(1, max_points // (2 * len(columns)))
    keep = {order[0], order[-1]}
    for values in columns:
        missing = np.isnan(np.asarray(values)[order])
        boundaries = np.flatnonzero(missing[1:] != missing[:-1])
        keep.update(order[boundaries])
        keep.update(order[boundaries + 1])
    for chunk in np.array_split(order, bins):
        if not len(chunk):
            continue
        for values in columns:
            vals = np.asarray(values)[chunk]
            if np.all(np.isnan(vals)):
                continue
            keep.add(chunk[np.nanargmin(vals)])
            keep.add(chunk[np.nanargmax(vals)])
    keep = np.fromiter(keep, dtype=int)
    return keep[np.argsort(np.asarray(times)[keep], kind="stable")]


def _add_strips(p, starts, ends, label, color, alpha, level="underlay"):
    """Shade time intervals with one legend-toggleable renderer."""
    if not starts:
        return None
    return p.vstrip(
        x0="x0", x1="x1",
        source=ColumnDataSource({"x0": list(starts), "x1": list(ends)}),
        fill_color=color, fill_alpha=alpha, line_alpha=0,
        level=level, legend_label=label,
    )


def make_plot(
    sci_info, face_info, gw_info, *, width=900, height=400,
    extra_faces=(), extra_exposures=(), max_points=20_000, show_markers=False,
    zero_crossings=(),
):
    """Create the NEA plot with exposure shading and nearest-time readout.

    ``zero_crossings`` are timestamps marked as "RW Zero Crossing".
    """
    for label, value in (("width", width), ("height", height)):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, np.integer))
            or value <= 0
        ):
            raise ValueError(f"Plot {label} must be a positive integer in pixels.")
    if max_points is not None and (
        isinstance(max_points, bool)
        or not isinstance(max_points, (int, np.integer))
        or max_points < 4
    ):
        raise ValueError("max_points must be an integer >= 4, or None.")
    p = figure(
        title="NEA Plot",
        x_axis_type="datetime",
        x_axis_label="Time",
        y_axis_label="Noise Equivalent Angle (mas)",
        width=width,
        height=height,
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )

    # One source per coordinate keeps the model count constant and allows
    # asynchronous samples. NaN rows break lines between acquisitions/BAD data.
    all_faces = (face_info, *extra_faces)
    total = sum(len(data["time"]) for data in all_faces)
    columns = {
        key: {"time": [], "delta": [], "epsilon": [], "num_stars": []}
        for key in ("delta", "epsilon")
    }
    for data in all_faces:
        if not len(data["time"]):
            continue
        # Split the point budget across FACE files by their share of samples.
        budget = (
            None if max_points is None or total <= max_points
            else max(10, int(max_points * len(data["time"]) / total))
        )
        times = np.asarray(data["time"], dtype="datetime64[ns]")
        for key, parts in columns.items():
            sample_mask = np.asarray(
                data.get(f"{key}_samples", np.ones(len(times), dtype=bool))
            )
            indices = np.flatnonzero(sample_mask)
            if not len(indices):
                continue
            selected = _decimate(
                times[indices], [np.asarray(data[key])[indices]], budget
            )
            order = indices[selected]
            if parts["time"]:
                parts["time"].append(np.array([times[order[0]]]))
                parts["delta"].append(np.array([np.nan]))
                parts["epsilon"].append(np.array([np.nan]))
                parts["num_stars"].append(np.array([np.nan]))
            parts["time"].append(times[order])
            for column in ("delta", "epsilon"):
                parts[column].append(np.asarray(data[column], dtype=float)[order])
            stars = data.get("num_stars")
            parts["num_stars"].append(
                np.full(len(order), np.nan) if stars is None
                else np.asarray(stars, dtype=float)[order]
            )
    hover_lines = []
    for key, label, color in [
        ("delta", "Delta", "navy"),
        ("epsilon", "Epsilon", "orange"),
    ]:
        source = ColumnDataSource({
            column: (
                np.concatenate(parts) if parts
                else np.array(
                    [], dtype="datetime64[ns]" if column == "time" else float
                )
            )
            for column, parts in columns[key].items()
        })
        line = p.line(
            "time", key, source=source, legend_label=label, color=color,
            line_width=2,
        )
        hover_lines.append(line)
        # Markers are off by default; they dominate browser redraw time.
        if show_markers:
            p.scatter(
                "time", key, source=source, legend_label=label,
                color=color, size=2,
            )
    p.add_tools(
        HoverTool(
            renderers=hover_lines,
            mode="vline",
            line_policy="nearest",
            tooltips=[
                ("Time (UTC)", "@time{%F %T.%3N}"),
                ("Delta (mas)", "@delta{0.000}"),
                ("Epsilon (mas)", "@epsilon{0.000}"),
                ("N stars used", "@num_stars{0}"),
            ],
            formatters={"@time": "datetime"},
        ),
        CrosshairTool(dimensions="height", line_color="gray", line_alpha=0.7),
    )

    starts, ends = [], []
    for exposure_info in (sci_info, *extra_exposures):
        starts.append(Time(exposure_info["expstart"]).utc.to_datetime())
        ends.append(Time(exposure_info["expend"]).utc.to_datetime())
    _add_strips(p, starts, ends, "Exposure", "purple", 0.4)

    if len(zero_crossings):
        crossings = p.vspan(
            x="time",
            source=ColumnDataSource({
                "time": np.asarray(zero_crossings, dtype="datetime64[ns]"),
                "label": ["RW Zero Crossing"] * len(zero_crossings),
            }),
            line_color="crimson", line_width=2, line_dash="dashed",
            legend_label="RW Zero Crossing",
        )
        p.add_tools(HoverTool(
            renderers=[crossings], line_policy="interp",
            tooltips=[("Event", "@label"), ("Time (UTC)", "@time{%F %T.%3N}")],
            formatters={"@time": "datetime"},
        ))

    p.legend.click_policy = "hide"
    p.add_layout(p.legend[0], "right")
    p.xaxis.axis_label_text_font_style = "normal"
    p.yaxis.axis_label_text_font_style = "normal"

    return p


def _get_mode_data(face_info, env_variables=None, mode_csv=None):
    """Read a local mode CSV or query MAST, retaining all original columns."""
    if len(face_info["time"]) == 0:
        raise ValueError("No valid FACE timestamps are available.")

    if mode_csv is not None:
        from pathlib import Path

        modes = pd.read_csv(Path(mode_csv).expanduser())
        missing = {"ObsTime", "EUValue"} - set(modes.columns)
        if missing:
            raise ValueError(
                f"Mode CSV is missing required columns: {', '.join(sorted(missing))}"
            )
        if modes.empty:
            raise ValueError("Mode CSV contains no observations.")
        return modes

    plot_start = pd.to_datetime(min(face_info["time"]), utc=True)
    plot_end = pd.to_datetime(max(face_info["time"]), utc=True)
    return get_mnemonic_data(
        "SCF_AC_SDR_MODE",
        plot_start.tz_localize(None).isoformat(),
        plot_end.tz_localize(None).isoformat(),
        env_variables=env_variables,
    )


MODE_COLORS = {
    "IH": ("Inertial Hold", "green", 0.08),
    "SETTLE": ("Settle", "orange", 0.15),
    "SLEW": ("Slew", "red", 0.15),
}


def _add_mode_strips(p, intervals):
    """Add one shading renderer per mode for {mode: [(start, end), ...]}."""
    # The "image" level renders below "underlay", keeping exposures on top.
    for mode, (label, color, alpha) in MODE_COLORS.items():
        spans = intervals.get(mode, [])
        _add_strips(
            p, [start for start, _ in spans], [end for _, end in spans],
            label, color, alpha, level="image",
        )


def add_mode_shading(
    p, sci_info, face_info, env_variables=None, *, mode_data=None,
    intervals=None,
):
    """
    Shade attitude modes and return seconds from IH to exposure start.

    Returns None if the beginning of inertial hold cannot be determined from
    the queried observations. Supplied mode_data is not modified. If an
    ``intervals`` dict is given, mode spans are appended to it instead of
    being drawn, so several FACE ranges can share one renderer per mode.
    """
    if len(face_info["time"]) == 0:
        raise ValueError("No valid FACE timestamps are available.")
    plot_start = pd.to_datetime(min(face_info["time"]), utc=True)
    plot_end = pd.to_datetime(max(face_info["time"]), utc=True)
    modes = (
        _get_mode_data(face_info, env_variables)
        if mode_data is None else mode_data
    )
    if modes.empty:
        warnings.warn("No attitude-mode data was returned for the plot range.")
        return None

    modes = modes[["ObsTime", "EUValue"]].copy()
    modes["ObsTime"] = pd.to_datetime(
        modes["ObsTime"], utc=True, errors="raise"
    )
    if modes["ObsTime"].isna().any() or modes["EUValue"].isna().any():
        raise ValueError("Attitude-mode data contains missing times or values.")

    modes["EUValue"] = modes["EUValue"].astype(str).str.strip()
    modes = modes.sort_values("ObsTime").drop_duplicates()
    if modes["ObsTime"].duplicated().any():
        raise ValueError("Conflicting attitude modes have the same timestamp.")
    modes = modes.reset_index(drop=True)

    draw = intervals is None
    if draw:
        intervals = {}
    # Assume each observed mode persists until the next observation.
    for i, row in modes.iterrows():
        mode = row["EUValue"]
        if mode not in MODE_COLORS:
            continue

        start = max(row["ObsTime"], plot_start)
        next_time = (
            modes.loc[i + 1, "ObsTime"]
            if i + 1 < len(modes)
            else plot_end
        )
        end = min(next_time, plot_end)
        if start >= end:
            continue
        intervals.setdefault(mode, []).append((
            start.tz_localize(None).to_pydatetime(),
            end.tz_localize(None).to_pydatetime(),
        ))
    if draw:
        _add_mode_strips(p, intervals)

    if sci_info is None:
        return None

    exposure_start = pd.to_datetime(
        Time(sci_info["expstart"]).utc.to_datetime(),
        utc=True,
    )
    if not plot_start <= exposure_start <= plot_end:
        warnings.warn("Exposure start is outside the queried mode-data range.")
        return None

    at_exposure = modes.index[modes["ObsTime"] <= exposure_start]
    if len(at_exposure) == 0:
        warnings.warn("No attitude mode is known at exposure start.")
        return None

    i = at_exposure[-1]
    if modes.loc[i, "EUValue"] != "IH":
        warnings.warn("The mode at exposure start is not inertial hold.")
        return None

    while i > 0 and modes.loc[i - 1, "EUValue"] == "IH":
        i -= 1

    if i == 0:
        warnings.warn(
            "Inertial hold was already active at the first returned sample; "
            "its actual start time is unknown."
        )
        return None

    return round(
        float((exposure_start - modes.loc[i, "ObsTime"]).total_seconds()), 3
    )


def prepare_file(value):
    """Return (model, get_file, filename) for a file input."""
    if value is None:
        return None, False, None

    if isinstance(value, str):
        if not os.path.exists(value):
            return None, True, value
        model = rdm.open(value)
    elif isinstance(value, asdf.AsdfFile):
        model = rdm.open(value)
    elif isinstance(value, DataModel):
        model = value
    else:
        raise TypeError(
            f"Expected a string, AsdfFile, or DataModel; got {type(value)}"
        )

    return model, False, model.meta.filename


def _load_guiding_files(
    sci_file, face_file=None, gw_file=None, env_variables=None
):
    """Resolve local/model inputs with at most one MAST product search."""
    if sci_file is None:
        raise ValueError("A science file or filename is required.")

    sci_file, get_sci, sci_filename = prepare_file(sci_file)
    face_file, get_face, face_filename = prepare_file(face_file)
    gw_file, get_gw, gw_filename = prepare_file(gw_file)

    # Omitted companion files are retrieved using the science filename.
    get_face = get_face or face_file is None
    get_gw = get_gw or gw_file is None

    if any((get_sci, get_face, get_gw)):
        if not sci_filename:
            raise ValueError(
                "The science model needs a filename for the MAST search."
            )

        remote_sci, remote_face, remote_gw = get_data(
            sci_filename,
            env_variables,
            get_sci=get_sci,
            get_face=get_face,
            get_gw=get_gw,
            face_filename=face_filename,
            gw_filename=gw_filename,
        )
        if get_sci:
            sci_file = remote_sci
        if get_face:
            face_file = remote_face
        if get_gw:
            gw_file = remote_gw

    return sci_file, face_file, gw_file


def _validate_visit_id(visit_id):
    if (
        not isinstance(visit_id, str)
        or not visit_id.strip()
        or not visit_id.strip().isascii()
        or not visit_id.strip().isdigit()
    ):
        raise ValueError("Enter the numeric visit ID as a string, without 'r' or a filename.")
    return visit_id.strip()


def _parse_visit_ids(value):
    """Validate, normalize, and deduplicate comma-separated visit IDs."""
    if not isinstance(value, str):
        raise ValueError("Enter one or more numeric visit IDs.")
    return list(dict.fromkeys(
        _validate_visit_id(part) for part in value.split(",")
    ))


def _timing_visit_ids(payload):
    """Extract visit IDs in file order from a single- or multi-visit export."""
    if not isinstance(payload, dict):
        raise ValueError("Timing JSON must be an object.")
    entries = payload["visits"] if "visits" in payload else [payload]
    if not isinstance(entries, list) or not entries:
        raise ValueError("Timing JSON must contain at least one visit.")
    ids = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each timing visit must be an object.")
        visit_id = _validate_visit_id(entry.get("visit_id"))
        if visit_id in ids:
            raise ValueError(f"Timing JSON contains duplicate visit ID {visit_id}.")
        ids.append(visit_id)
    return ids


def _optional_int(value):
    """Return an int, or None for missing/masked/non-numeric values."""
    if value is None or np.ma.is_masked(value) or pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_visit_data(visit_id, env_variables=None, *, timing_json=None):
    """Return (visit start, exposures) from MAST metadata; never read products."""
    from astropy.table import vstack

    visit_id = _validate_visit_id(visit_id)
    if timing_json is not None:
        from pathlib import Path

        logger.info("Reading visit timing JSON: %s", timing_json)
        with Path(timing_json).expanduser().open() as stream:
            return _validate_timing(json.load(stream), visit_id)
    mission = MastMissions(mission="roman")
    if env_variables:
        load_dotenv(env_variables, override=True)
        mission.login(token=os.getenv("MAST_API_TOKEN"))

    logger.info("Querying MAST for exposures in visit %s...", visit_id)
    pages = []
    limit = 1000
    offset = 0
    while True:
        page = mission.query_criteria(
            visit_id=visit_id,
            select_cols=[
                "visit_start_time", "exposure_start_time", "exposure_end_time",
                "ma_table_number", "ma_table_name", "optical_element",
            ],
            limit=limit,
            offset=offset,
            detector="WFI01",
        )
        if len(page):
            pages.append(page)
        if len(page) < limit:
            break
        offset += len(page)
    if not pages:
        raise ValueError(f"No MAST observations found for visit {visit_id}.")
    search = vstack(pages) if len(pages) > 1 else pages[0]
    required = {
        "fileSetName", "visit_start_time", "exposure_start_time", "exposure_end_time"
    }
    missing = required - set(search.colnames)
    if missing:
        raise ValueError(f"MAST visit results lack columns: {', '.join(sorted(missing))}")

    exposures = {}
    visit_starts = []
    skipped = 0
    for row in search:
        value = row["visit_start_time"]
        if not np.ma.is_masked(value) and not pd.isna(value) and str(value).strip():
            visit_starts.append(pd.to_datetime(value, utc=True, errors="raise"))
        name, start, end = (row[col] for col in (
            "fileSetName", "exposure_start_time", "exposure_end_time"
        ))
        if any(np.ma.is_masked(value) or pd.isna(value) or str(value).strip() == ""
               for value in (name, start, end)):
            skipped += 1
            continue
        start = pd.to_datetime(start, utc=True, errors="raise")
        end = pd.to_datetime(end, utc=True, errors="raise")
        if end < start:
            raise ValueError(f"Exposure {name} ends before it starts.")
        name = str(name)
        record = {
            "name": name, "expstart": start, "expend": end,
            "ma_table_number": _optional_int(
                row["ma_table_number"] if "ma_table_number" in search.colnames else None
            ),
            "ma_table_name": _optional_text(row, search, "ma_table_name"),
            "optical_element": _optional_text(row, search, "optical_element"),
        }
        if name in exposures and exposures[name] != record:
            raise ValueError(f"Conflicting exposure times for {name}.")
        exposures[name] = record
    if skipped:
        warnings.warn(f"Skipped {skipped} MAST rows with missing exposure metadata.")
    if not exposures:
        raise ValueError(f"No valid science exposure times found for visit {visit_id}.")
    exposures = sorted(exposures.values(), key=lambda item: (item["expstart"], item["name"]))
    logger.info("Found %d exposures in visit %s.", len(exposures), visit_id)
    if not visit_starts or any(pd.isna(value) for value in visit_starts):
        raise ValueError(f"No valid visit_start_time found for visit {visit_id}.")
    visit_start = min(visit_starts)
    if visit_start > exposures[0]["expstart"]:
        raise ValueError("Visit start is after the first exposure start.")
    return visit_start, exposures


def _optional_text(row, table, column):
    """Return a MAST cell as a stripped string, or None if absent or masked."""
    if column not in table.colnames:
        return None
    value = row[column]
    if np.ma.is_masked(value) or pd.isna(value) or not str(value).strip():
        return None
    return str(value).strip()


def _validate_timing(payload, visit_id):
    """Validate the shared timing import/export format; all times are UTC."""
    if isinstance(payload, dict) and "visits" in payload:
        entries = payload["visits"]
        matches = [
            item for item in entries
            if isinstance(item, dict) and item.get("visit_id") == visit_id
        ] if isinstance(entries, list) else []
        if len(matches) != 1:
            raise ValueError(
                "Timing JSON must contain exactly one entry matching the visit ID."
            )
        payload = matches[0]

    if not isinstance(payload, dict) or payload.get("visit_id") != visit_id:
        raise ValueError("Timing JSON must contain the matching string visit_id.")
    if (
        not isinstance(payload.get("visit_start_time"), str)
        or not payload["visit_start_time"].strip()
        or not isinstance(payload.get("exposures"), list)
    ):
        raise ValueError("Timing JSON requires visit_start_time and an exposures list.")
    start = pd.to_datetime(payload["visit_start_time"], utc=True, errors="raise")
    if not isinstance(start, pd.Timestamp) or pd.isna(start):
        raise ValueError("Invalid visit_start_time.")
    exposures = []
    names = set()
    for item in payload["exposures"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
            raise ValueError("Each exposure needs a nonempty name.")
        name = item["name"]
        if name in names:
            raise ValueError(f"Duplicate exposure name: {name}")
        names.add(name)
        times = []
        for key in ("exposure_start_time", "exposure_end_time"):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Exposure {name} requires {key}.")
            stamp = pd.to_datetime(value, utc=True, errors="raise")
            if pd.isna(stamp):
                raise ValueError(f"Exposure {name}: invalid {key}.")
            times.append(stamp)
        expstart, expend = times
        if expstart < start or expend < expstart:
            raise ValueError(f"Exposure {name}: invalid start/end relative to visit start.")
        ma_table_number = item.get("ma_table_number")
        if ma_table_number is not None and _optional_int(ma_table_number) is None:
            raise ValueError(f"Exposure {name}: invalid ma_table_number.")
        exposures.append({
            "name": name, "expstart": expstart, "expend": expend,
            "ma_table_number": _optional_int(ma_table_number),
            "ma_table_name": item.get("ma_table_name"),
            "optical_element": item.get("optical_element"),
            "guide_stars": item.get("guide_stars"),
        })
        guide_stars = exposures[-1]["guide_stars"]
        if guide_stars is not None and (
            not isinstance(guide_stars, dict)
            or any(
                not isinstance(detector, str) or not isinstance(star, str)
                for detector, star in guide_stars.items()
            )
        ):
            raise ValueError(f"Exposure {name}: invalid guide_stars mapping.")
    if not exposures:
        raise ValueError("Timing JSON requires at least one exposure.")
    return start, sorted(exposures, key=lambda item: (item["expstart"], item["name"]))


def visit_timing_data(visit_id, start, exposures):
    """Return JSON-serializable visit timing, with explicit UTC timestamps."""
    payload = {
        "visit_id": _validate_visit_id(visit_id),
        "visit_start_time": pd.to_datetime(start, utc=True).isoformat(),
        "exposures": [
            {
                "name": item["name"],
                "exposure_start_time": pd.to_datetime(item["expstart"], utc=True).isoformat(),
                "exposure_end_time": pd.to_datetime(item["expend"], utc=True).isoformat(),
                **(
                    {"ma_table_number": item["ma_table_number"]}
                    if item.get("ma_table_number") is not None else {}
                ),
                **{
                    key: item[key] for key in ("ma_table_name", "optical_element", "guide_stars")
                    if item.get(key) is not None
                },
            }
            for item in exposures
        ],
    }
    _validate_timing(payload, visit_id)
    return payload


def _telemetry_end(exposures):
    return max(item["expend"] for item in exposures) + pd.Timedelta(seconds=20)


FACE_ESTIMATES = (
    "WFIF_FAC_DELTA", "WFIF_FAC_EPSILON", "WFIF_FAC_ZETA",
    "WFIF_FAC_DELTA_VAR_P", "WFIF_FAC_EPSILON_VAR_P", "WFIF_FAC_ZETA_VAR_P",
)
TELEMETRY_MNEMONICS = (
    "SCF_AC_SDR_MODE", "SCF_AC_SDR_HGASCIMOVESTATE",
    *(
        f"WFIF_FAC_OPD{detector:02d}_{suffix}"
        for detector in range(1, 19)
        for suffix in ("H_COORD", "V_COORD", "GW_H_CENTER", "GW_V_CENTER")
    ),
    "WFIF_FAC_ATT_SOL_QUALITY",
    *FACE_ESTIMATES,
    "WFIF_FAC_OP_PHASE_SOL",
    "SCF_AC_SDR_NUMWHLSNEARZERO", "WFIF_FAC_NUM_STARS",
)
# Older saved CSVs lack these; they load as all-null columns.
OPTIONAL_MNEMONICS = ("SCF_AC_SDR_NUMWHLSNEARZERO", "WFIF_FAC_NUM_STARS")


def _parse_times(values):
    times = pd.to_datetime(values, utc=True, errors="raise", format="mixed")
    if times.isna().any():
        raise ValueError("Telemetry contains missing ObsTime values.")
    return times.astype("datetime64[ns, UTC]")


def _effective_quality(data):
    # This state is used only for rejection; the stored columns stay sparse.
    return data["WFIF_FAC_ATT_SOL_QUALITY"].ffill().astype("string")


def _reject_bad_face(data):
    """Null FACE values during BAD quality; count them in ``bad_face_rejected``.

    The per-row count is saved with the telemetry so that a replayed CSV (whose
    values were already nulled) still reports the original number.
    """
    bad = _effective_quality(data).str.contains("BAD", na=False)
    rejected = pd.Series(0, index=data.index, dtype="int64")
    rejected.loc[bad] = data.loc[bad, list(FACE_ESTIMATES)].notna().sum(axis=1)
    count = int(rejected.sum())
    if count:
        logger.info("Rejecting %d FACE estimate/variance values with BAD quality.", count)
        data.loc[bad, list(FACE_ESTIMATES)] = np.nan
    if "bad_face_rejected" in data:
        rejected = rejected + pd.to_numeric(
            data["bad_face_rejected"], errors="coerce"
        ).fillna(0).astype("int64")
    data["bad_face_rejected"] = rejected
    return data


def _normalize_telemetry(data, visit_id, start, end):
    data = data.copy()
    for column in OPTIONAL_MNEMONICS:
        if column not in data.columns:
            logger.warning("Telemetry lacks %s; treating it as all-null.", column)
            data[column] = np.nan
    missing = {"ObsTime", *TELEMETRY_MNEMONICS} - set(data.columns)
    if missing:
        raise ValueError(
            f"Telemetry lacks required columns: {', '.join(sorted(missing))}"
        )
    if data.empty:
        raise ValueError("Telemetry contains no observations.")
    data = data.copy()
    if "visit_id" in data:
        ids = data["visit_id"].astype("string")
        if ids.isna().any() or not ids.eq(visit_id).all():
            raise ValueError("Telemetry CSV belongs to a different visit.")
    data["ObsTime"] = _parse_times(data["ObsTime"])
    data = data.sort_values("ObsTime").reset_index(drop=True)
    if data["ObsTime"].duplicated().any():
        raise ValueError("Telemetry contains duplicate ObsTime rows.")
    in_range = data["ObsTime"].between(start, end)
    if not in_range.any():
        raise ValueError("Telemetry has no observations within this visit's time range.")
    if not in_range.all():
        logger.warning("Discarding %d telemetry rows outside this visit.", int((~in_range).sum()))
        data = data.loc[in_range].reset_index(drop=True)
    for column in TELEMETRY_MNEMONICS:
        if column not in (
            "SCF_AC_SDR_MODE", "SCF_AC_SDR_HGASCIMOVESTATE",
            "WFIF_FAC_ATT_SOL_QUALITY", "WFIF_FAC_OP_PHASE_SOL",
        ):
            data[column] = pd.to_numeric(data[column], errors="raise")
        else:
            data[column] = data[column].astype("string")
    data["visit_id"] = visit_id
    if data["WFIF_FAC_ATT_SOL_QUALITY"].isna().all():
        logger.warning("No quality flags available; BAD FACE rejection cannot be applied.")
    data = _reject_bad_face(data)
    data["ObsTime"] = data["ObsTime"].dt.tz_localize(None)
    return data


def get_telemetry_data(
    visit_id, start, end, env_variables=None, *, telemetry_csv=None
):
    """Return one sparse, wide DataFrame; CSV input bypasses all EDB queries.

    Times in the returned DataFrame are timezone-naive UTC. FACE estimates
    remain in native radians (variances in radians squared). BAD quality
    rejects FACE estimates/variances only; flags and other telemetry remain.
    """
    from pathlib import Path

    visit_id = _validate_visit_id(visit_id)
    start, end = pd.to_datetime([start, end], utc=True)
    if pd.isna(start) or pd.isna(end) or end < start:
        raise ValueError("Telemetry query needs a valid start/end time range.")
    if telemetry_csv is not None:
        logger.info("Reading telemetry CSV: %s", telemetry_csv)
        data = pd.read_csv(
            Path(telemetry_csv).expanduser(), dtype={"visit_id": "string"}
        )
        if "visit_id" in data:
            if data["visit_id"].isna().any():
                raise ValueError("Telemetry CSV contains rows with missing visit_id.")
            data = data.loc[data["visit_id"].eq(visit_id)]
            if data.empty:
                raise ValueError(f"Telemetry CSV has no rows for visit {visit_id}.")
        return _normalize_telemetry(data, visit_id, start, end)

    token = None
    if env_variables:
        load_dotenv(env_variables, override=True)
        token = os.getenv("MAST_API_TOKEN")

    logger.info(
        "Querying %d mnemonics from %s to %s (UTC)...",
        len(TELEMETRY_MNEMONICS), start.isoformat(), end.isoformat(),
    )
    columns = {}
    empty_mnemonics = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(
                get_mnemonic_data, mnemonic,
                start.tz_localize(None).isoformat(),
                end.tz_localize(None).isoformat(), token=token,
            ): mnemonic
            for mnemonic in TELEMETRY_MNEMONICS
        }
        for i, future in enumerate(as_completed(futures), 1):
            mnemonic = futures[future]
            try:
                samples = future.result()
            except Exception as exc:
                raise RuntimeError(f"Engineering query failed for {mnemonic}.") from exc
            if not {"ObsTime", "EUValue"} <= set(samples.columns):
                raise ValueError(f"{mnemonic}: response lacks ObsTime or EUValue.")
            samples = samples[["ObsTime", "EUValue"]].copy()
            samples["ObsTime"] = _parse_times(samples["ObsTime"])
            samples = samples.drop_duplicates()
            if samples["ObsTime"].duplicated().any():
                raise ValueError(f"{mnemonic}: conflicting values at the same ObsTime.")
            if samples.empty:
                empty_mnemonics.append(mnemonic)
            columns[mnemonic] = samples.set_index("ObsTime")["EUValue"]
            logger.debug(
                "Fetched mnemonic %d/%d: %s (%d rows)",
                i, len(TELEMETRY_MNEMONICS), mnemonic, len(samples),
            )

    if empty_mnemonics:
        logger.warning(
            "%d/%d mnemonics returned no observations; their columns will be null.",
            len(empty_mnemonics), len(TELEMETRY_MNEMONICS),
        )
    logger.info("Collating telemetry by exact ObsTime (outer join)...")
    data = pd.concat(
        [columns[mnemonic].rename(mnemonic) for mnemonic in TELEMETRY_MNEMONICS],
        axis=1, sort=True,
    ).rename_axis("ObsTime").reset_index()
    logger.info("Merged %d unique telemetry timestamps.", len(data))
    return _normalize_telemetry(data, visit_id, start, end)


def _mode_blocks(telemetry, start, end):
    modes = telemetry.loc[
        telemetry["SCF_AC_SDR_MODE"].notna(), ["ObsTime", "SCF_AC_SDR_MODE"]
    ].copy()
    if modes.empty:
        raise ValueError("No SCF_AC_SDR_MODE samples are available for this visit.")
    modes["ObsTime"] = pd.to_datetime(modes["ObsTime"], utc=True)
    modes["mode"] = modes["SCF_AC_SDR_MODE"].astype(str).str.strip()
    modes = modes.loc[modes["mode"].ne(modes["mode"].shift())].reset_index(drop=True)
    blocks = []
    for i, row in modes.iterrows():
        block_end = modes.loc[i + 1, "ObsTime"] if i + 1 < len(modes) else end
        block_start = max(start, row["ObsTime"])
        if block_start < block_end:
            blocks.append({
                "mode": row["mode"], "start": block_start, "end": block_end,
                "known_start": i > 0,
            })
    return blocks


def guiding_tool(
    visit_id, env_variables=None,
    *, return_telemetry=False, width=900, height=400, telemetry_csv=None,
    max_points=20_000, show_markers=False, timing_json=None,
):
    """Return (plot, IH results), optionally also the full telemetry DataFrame.

    Requires a numeric visit ID string. Queries MAST metadata only, then EDB
    telemetry or a saved wide CSV, through 20 seconds after the last exposure.
    Optional timing_json bypasses MAST metadata. Results include every exposure;
    subsequent exposures within the same contiguous IH interval get zero delay.
    """
    visit_id = _validate_visit_id(visit_id)
    start, exposures = get_visit_data(visit_id, env_variables, timing_json=timing_json)
    end = _telemetry_end(exposures)
    telemetry = get_telemetry_data(
        visit_id, start, end, env_variables, telemetry_csv=telemetry_csv
    )
    plot, result = _make_visit_plot(
        visit_id, start, exposures, telemetry, width=width, height=height,
        max_points=max_points, show_markers=show_markers,
    )
    if return_telemetry:
        return plot, result, telemetry
    return plot, result


def get_batch_telemetry(
    visit_ids, env_variables=None, *, return_metadata=False,
    telemetry_csv=None, timing_json=None,
):
    """Load comma-separated visits without plotting; return telemetry and IH.

    Duplicate visits are processed once in input order. A failure identifies
    the visit and aborts the batch, rather than exporting incomplete results.
    """
    visits = _parse_visit_ids(visit_ids)
    if telemetry_csv is not None and len(visits) > 1:
        from pathlib import Path
        columns = pd.read_csv(Path(telemetry_csv).expanduser(), nrows=0).columns
        if "visit_id" not in columns:
            raise ValueError("Batch telemetry CSV must contain a visit_id column.")
    frames, tables, metadata = [], [], {}
    for i, visit_id in enumerate(visits, 1):
        logger.info("Loading visit %d/%d: %s", i, len(visits), visit_id)
        try:
            start, exposures = get_visit_data(
                visit_id, env_variables, timing_json=timing_json
            )
            data = get_telemetry_data(
                visit_id, start, _telemetry_end(exposures), env_variables,
                telemetry_csv=telemetry_csv,
            )
            table = get_ih_results(start, exposures, data)
        except Exception as exc:
            raise RuntimeError(f"Batch failed for visit {visit_id}.") from exc
        frames.append(data.assign(visit_id=visit_id))
        tables.append(table.assign(visit_id=visit_id))
        metadata[visit_id] = (visit_id, start, exposures)
    logger.info("Batch ready: %d visits; no plots generated.", len(visits))
    result = (pd.concat(frames, ignore_index=True), pd.concat(tables, ignore_index=True))
    return (*result, metadata) if return_metadata else result


NEA_PRE_SETTLE_SECONDS = 20
NEA_EXPOSURE_MARGIN_SECONDS = 10


def nea_window(blocks, start, end, exposure=None):
    """Return the (start, end) UTC timestamps shown in the NEA plot.

    A single exposure gets 10 s before and after. The whole visit starts
    20 s before the first contiguous SETTLE block (or at the visit start if
    there is none, and never before the visit start) and ends at ``end``.
    """
    if exposure is not None:
        margin = pd.Timedelta(seconds=NEA_EXPOSURE_MARGIN_SECONDS)
        return exposure["expstart"] - margin, exposure["expend"] + margin
    settle = next((b for b in blocks if b["mode"] == "SETTLE"), None)
    if settle is None:
        return start, end
    return (
        max(start, settle["start"] - pd.Timedelta(seconds=NEA_PRE_SETTLE_SECONDS)),
        end,
    )


def _make_visit_plot(
    visit_id, start, exposures, telemetry, *, width=900, height=400,
    max_points=20_000, show_markers=False, exposure=None,
):
    """Build the NEA plot from already loaded visit data.

    Pass one of ``exposures`` as ``exposure`` to zoom to that exposure.
    """
    end = _telemetry_end(exposures)
    blocks = _mode_blocks(telemetry, start, end)
    win_start, win_end = nea_window(blocks, start, end, exposure)
    win_start_n = win_start.tz_localize(None)
    win_end_n = win_end.tz_localize(None)
    in_window = telemetry["ObsTime"].between(win_start_n, win_end_n).to_numpy()
    if not in_window.any():
        raise ValueError("No telemetry is available in the NEA plot time range.")
    full_telemetry = telemetry
    telemetry = telemetry.loc[in_window].reset_index(drop=True)
    bad = _effective_quality(telemetry).str.contains("BAD", na=False).to_numpy(dtype=bool)
    face_info = {"time": telemetry["ObsTime"].to_numpy(dtype="datetime64[ns]")}
    for key in ("delta", "epsilon"):
        values = telemetry[f"WFIF_FAC_{key.upper()}"].to_numpy(dtype=float)
        if not np.isfinite(values).any():
            raise ValueError(f"No valid {key} FACE telemetry is available.")
        face_info[key] = values * ((180 / np.pi) * 3_600 * 1_000)
        face_info[f"{key}_samples"] = np.isfinite(values) | bad
    if "WFIF_FAC_NUM_STARS" in telemetry:
        # Hold the last reported star count so every plotted sample has one.
        face_info["num_stars"] = (
            pd.to_numeric(telemetry["WFIF_FAC_NUM_STARS"], errors="coerce")
            .ffill().to_numpy(dtype=float)
        )
    zero = pd.to_numeric(telemetry["SCF_AC_SDR_NUMWHLSNEARZERO"], errors="coerce")
    zero_times = telemetry.loc[zero.gt(0).fillna(False), "ObsTime"].to_numpy(
        dtype="datetime64[ns]"
    )
    logger.info("Plotting FACE telemetry and exposure/mode intervals...")
    shown = [
        item for item in exposures
        if item["expend"] >= win_start and item["expstart"] <= win_end
    ] or list(exposures)
    plot = make_plot(
        shown[0], face_info, None, width=width, height=height,
        extra_exposures=shown[1:], max_points=max_points,
        show_markers=show_markers, zero_crossings=zero_times,
    )
    plot.title.text = (
        f"NEA Plot - {visit_id}"
        + (f" - {exposure['name']}" if exposure is not None else "")
    )
    plot.x_range.start = win_start_n.to_pydatetime()
    plot.x_range.end = win_end_n.to_pydatetime()
    intervals = {}
    for block in blocks:
        if block["mode"] in MODE_COLORS:
            intervals.setdefault(block["mode"], []).append((
                block["start"].tz_localize(None).to_pydatetime(),
                block["end"].tz_localize(None).to_pydatetime(),
            ))
    _add_mode_strips(plot, intervals)
    result = get_ih_results(start, exposures, full_telemetry)
    logger.info("NEA plot and IH results ready for visit %s.", visit_id)
    return plot, result


def get_ih_results(start, exposures, telemetry):
    """One row per exposure; only the first exposure per IH block has a delay."""
    if telemetry["SCF_AC_SDR_MODE"].notna().any():
        blocks = _mode_blocks(telemetry, start, _telemetry_end(exposures))
    else:
        logger.warning("No mode samples available; IH times are unavailable.")
        blocks = []
    seen = set()
    results = []
    for item in sorted(exposures, key=lambda item: (item["expstart"], item["name"])):
        match = next((
            (i, block) for i, block in enumerate(blocks)
            if block["mode"] == "IH"
            and block["start"] <= item["expstart"] < block["end"]
        ), None)
        block = match[1] if match else None
        seconds = None
        if match:
            i = match[0]
            if i in seen:
                seconds = 0.0
            elif block["known_start"]:
                seconds = round((item["expstart"] - block["start"]).total_seconds(), 3)
            seen.add(i)
        results.append({
            "ih_start": (
                block["start"].tz_localize(None)
                if block and block["known_start"] else pd.NaT
            ),
            "ih_end": block["end"].tz_localize(None) if block else pd.NaT,
            "exposure": item["name"],
            "exposure_start": item["expstart"].tz_localize(None),
            "exposure_end": item["expend"].tz_localize(None),
            "ih_seconds": seconds,
        })
    return pd.DataFrame(results)


JITTER_SOURCES = ("FACE", *(f"WFI{number:02d}" for number in range(1, 19)))


def get_jitter_data(telemetry, source="FACE", *, units="mas"):
    """Return UTC time and horizontal/vertical jitter coordinates.

    At source sample times use the most recent values, never future values.
    FACE returns epsilon/delta in mas, resetting alignment across BAD quality.
    For detectors, the epsilon/delta columns contain X/Y, in pixels or mas,
    retaining the absolute window-center offsets.
    """
    if source not in JITTER_SOURCES:
        raise ValueError(f"Unknown jitter source: {source!r}.")
    if units not in ("mas", "pixels"):
        raise ValueError("Jitter units must be 'mas' or 'pixels'.")
    if source == "FACE" and units != "mas":
        raise ValueError("FACE jitter is only available in mas.")
    if source == "FACE":
        columns = ["WFIF_FAC_DELTA", "WFIF_FAC_EPSILON"]
        required = ["ObsTime", *columns, "WFIF_FAC_ATT_SOL_QUALITY"]
    else:
        prefix = f"WFIF_FAC_OPD{source[-2:]}_"
        columns = [prefix + suffix for suffix in (
            "H_COORD", "V_COORD", "GW_H_CENTER", "GW_V_CENTER"
        )]
        required = ["ObsTime", *columns]
    missing = set(required) - set(telemetry.columns)
    if missing:
        raise ValueError(
            f"{source}: missing telemetry columns: {', '.join(sorted(missing))}"
        )
    data = telemetry[required].copy()
    data["ObsTime"] = _parse_times(data["ObsTime"]).dt.tz_localize(None)
    data = data.sort_values("ObsTime").reset_index(drop=True)
    if data["ObsTime"].duplicated().any():
        raise ValueError("Telemetry contains duplicate ObsTime rows.")
    numeric = data[columns].apply(pd.to_numeric, errors="raise")
    sampled = numeric.notna().any(axis=1)
    if source == "FACE":
        bad = _effective_quality(data).str.contains("BAD", na=False)
        numeric.loc[bad, :] = np.nan
        # Never reuse a pre-BAD coordinate after the quality recovers.
        groups = bad.ne(bad.shift(fill_value=False)).cumsum()
        aligned = numeric.groupby(groups).ffill()
        aligned.loc[bad, :] = np.nan
        factor = (180 / np.pi) * 3_600 * 1_000
        delta = aligned[columns[0]] * factor
        epsilon = aligned[columns[1]] * factor
    else:
        aligned = numeric.ffill()
        factor = 110 if units == "mas" else 1
        epsilon = factor * (aligned[columns[0]] + aligned[columns[2]])
        delta = -factor * (aligned[columns[1]] + aligned[columns[3]])
    result = pd.DataFrame({
        "time": data["ObsTime"], "delta": delta, "epsilon": epsilon,
    })
    valid = sampled & np.isfinite(delta) & np.isfinite(epsilon)
    result = result.loc[valid].reset_index(drop=True)
    if result.empty:
        raise ValueError(f"{source}: no valid paired jitter samples are available.")
    return result


def _fit_jitter_gaussian(points, x="epsilon", y="delta"):
    """Fit a bivariate Gaussian by maximum likelihood to paired samples.

    Coordinates follow the plot axes (``x`` horizontal, ``y`` vertical); the
    returned angle is counterclockwise from +x toward +y.
    """
    coordinates = points[[x, y]].to_numpy(dtype=float)
    if len(coordinates) < 3:
        raise ValueError("at least three samples are required")
    center = coordinates.mean(axis=0)
    residuals = coordinates - center
    covariance = residuals.T @ residuals / len(coordinates)
    values, vectors = np.linalg.eigh(covariance)
    if values[-1] <= 0 or values[0] <= values[-1] * 1e-12:
        raise ValueError("samples do not span two dimensions")
    minor, major = np.sqrt(values)
    direction = vectors[:, -1]
    angle = np.arctan2(direction[1], direction[0]) % np.pi
    # A circular Gaussian has no uniquely defined major-axis direction.
    position_angle = (
        None if np.isclose(values[0], values[1], rtol=1e-10, atol=0)
        else np.degrees(angle)
    )
    return center, major, minor, angle, position_angle


RESULTANT_COLOR = "cyan"


def make_jitter_plot(
    telemetry, sources=("FACE",), *, exposure, width=900, height=400,
    max_points=20_000, resultant=None, title="Jitter Plot", units="mas",
):
    """Return a single-exposure jitter scatter with top/right histograms.

    FACE plots epsilon versus delta in mas; detectors plot X versus Y in
    ``units`` ("mas" or "pixels"). FACE and detectors cannot be mixed.
    ``exposure`` (required) is a dict
    with ``expstart``/``expend`` (and optionally ``name``). Each source is
    centered on its own mean within the exposure, after latest-value
    alignment against visit history, so samples never use future values.

    ``resultant`` optionally holds ``start``/``end`` times (and ``index``) as
    from :func:`resultant_intervals`; samples inside that interval are drawn
    in cyan. Histograms and the Gaussian fit use all exposure samples; only
    the scatter is thinned to ``max_points`` per source and group, keeping
    extrema. The 1-sigma ellipse has semi-axes sqrt(covariance eigenvalues)
    and its position angle is counterclockwise from the positive horizontal
    axis toward the positive vertical axis,
    modulo 180 degrees. A 2-D Gaussian contains 39.3% within this ellipse.
    """
    from bokeh.layouts import gridplot
    from bokeh.palettes import Category20

    for label, value in (("width", width), ("height", height)):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, np.integer))
            or value <= 0
        ):
            raise ValueError(f"Plot {label} must be a positive integer in pixels.")
    if max_points is not None and (
        isinstance(max_points, bool)
        or not isinstance(max_points, (int, np.integer))
        or max_points < 4
    ):
        raise ValueError("max_points must be an integer >= 4, or None.")
    if isinstance(sources, str):
        sources = (sources,)
    sources = tuple(dict.fromkeys(sources))
    if not sources:
        raise ValueError("Select FACE or at least one detector for the jitter plot.")
    if "FACE" in sources and len(sources) > 1:
        raise ValueError("FACE and detector jitter cannot be plotted together.")
    if units not in ("mas", "pixels") or (sources == ("FACE",) and units != "mas"):
        raise ValueError("Select mas for FACE, or mas/pixels for detectors.")
    if exposure is None:
        raise ValueError("Select an exposure for the jitter plot.")
    x_label, y_label = ("Epsilon", "Delta") if sources == ("FACE",) else ("X", "Y")
    start, end = pd.to_datetime(
        [exposure["expstart"], exposure["expend"]], utc=True
    ).tz_localize(None)
    if pd.isna(start) or pd.isna(end) or end < start:
        raise ValueError("Exposure needs a valid start/stop time range.")
    highlight = None
    if resultant is not None:
        highlight = tuple(
            pd.to_datetime([resultant["start"], resultant["end"]], utc=True)
            .tz_localize(None)
        )
    plot = figure(
        title=title, name="jitter_scatter",
        x_axis_label=f"{x_label} - mean {x_label} ({units})",
        y_axis_label=f"{y_label} - mean {y_label} ({units})",
        width=width, height=height, match_aspect=True,
        tools="pan,wheel_zoom,reset,save",
    )
    plot.add_tools(BoxZoomTool(match_aspect=True))
    renderers = []
    highlight_renderers = []
    full_points = {}
    for source in sources:
        points = get_jitter_data(telemetry, source, units=units)
        points = points.loc[points["time"].between(start, end)].copy()
        if points.empty:
            raise ValueError(f"{source}: no valid jitter samples in this exposure.")
        for coordinate in ("delta", "epsilon"):
            points[coordinate] -= points[coordinate].mean()
        points["exposure"] = exposure.get("name", "Exposure")
        full_points[source] = points
        inside = (
            points["time"].between(*highlight).to_numpy()
            if highlight is not None else np.zeros(len(points), dtype=bool)
        )

        def shown_data(subset, source=source):
            order = _decimate(
                subset["time"].to_numpy(),
                [subset["delta"].to_numpy(), subset["epsilon"].to_numpy()],
                max_points,
            )
            shown = subset.iloc[order]
            return ColumnDataSource({
                "time": shown["time"].to_numpy(dtype="datetime64[ns]"),
                "delta": shown["delta"].to_numpy(dtype=float),
                "epsilon": shown["epsilon"].to_numpy(dtype=float),
                "source": [source] * len(shown),
                "exposure": shown["exposure"].to_numpy(),
            })

        data = shown_data(points.loc[~inside])
        logger.info(
            "Plotting jitter for %s: %d paired samples (%d highlighted).",
            source, len(points), int(inside.sum()),
        )
        color = Category20[20][JITTER_SOURCES.index(source)]
        try:
            center, major, minor, angle, position_angle = _fit_jitter_gaussian(points)
        except ValueError as exc:
            logger.warning("%s: Gaussian fit unavailable: %s.", source, exc)
            label = f"{source}: Gaussian fit unavailable ({exc})"
            ellipse = None
        else:
            angle_label = (
                "undefined" if position_angle is None else f"{position_angle:.2f} deg"
            )
            label = f"{source}: a={major:.3f} {units}, b={minor:.3f} {units}, PA={angle_label}"
            phase = np.linspace(0, 2 * np.pi, 201)
            x = (
                center[0] + major * np.cos(phase) * np.cos(angle)
                - minor * np.sin(phase) * np.sin(angle)
            )
            y = (
                center[1] + major * np.cos(phase) * np.sin(angle)
                + minor * np.sin(phase) * np.cos(angle)
            )
            ellipse = plot.line(x, y, color=color, line_width=2)
        renderer = plot.scatter(
            "epsilon", "delta", source=data, legend_label=label,
            size=3, alpha=0.5, color=color,
        )
        if ellipse is not None:
            renderer.js_link("visible", ellipse, "visible")
        renderers.append(renderer)
        if inside.any():
            marked = plot.scatter(
                "epsilon", "delta", source=shown_data(points.loc[inside]),
                size=5, alpha=0.9, color=RESULTANT_COLOR, line_color="black",
                line_width=0.5,
            )
            renderer.js_link("visible", marked, "visible")
            highlight_renderers.append(marked)
    if highlight is not None:
        label = (
            f"Resultant {resultant['index']}" if "index" in resultant else "Resultant"
        )
        if not highlight_renderers:
            label += " (no jitter samples)"
        # A legend-only proxy keeps the legend entry even when no samples match.
        plot.scatter(
            [np.nan], [np.nan], size=6, color=RESULTANT_COLOR, line_color="black",
            line_width=0.5, legend_label=label,
        )
    plot.add_tools(HoverTool(
        renderers=renderers + highlight_renderers,
        tooltips=[
            ("Source", "@source"), ("Time (UTC)", "@time{%F %T.%3N}"),
            ("Exposure", "@exposure"),
            (f"{x_label} ({units})", "@epsilon{0.000}"),
            (f"{y_label} ({units})", "@delta{0.000}"),
        ],
        formatters={"@time": "datetime"},
    ))
    # Center on (0, 0) and show +/-3 sigma of the widest axis, ignoring outliers.
    sigma = max(
        float(np.nanstd(p[c].to_numpy())) for p in full_points.values()
        for c in ("epsilon", "delta")
    )
    half = 3 * sigma if np.isfinite(sigma) and sigma > 0 else 1.0
    short = min(width, height)
    plot.x_range = Range1d(-half * width / short, half * width / short)
    plot.y_range = Range1d(-half * height / short, half * height / short)
    plot.legend.click_policy = "hide"
    plot.legend.title = f"1-sigma Gaussian; PA from +{x_label} toward +{y_label} (CCW)"
    plot.xaxis.axis_label_text_font_style = "normal"
    plot.yaxis.axis_label_text_font_style = "normal"
    top = figure(
        name="jitter_x_histogram", width=width, height=150,
        x_range=plot.x_range, y_axis_label="Count", tools="", toolbar_location=None,
    )
    right = figure(
        name="jitter_y_histogram", width=180, height=height,
        y_range=plot.y_range, x_axis_label="Count", tools="", toolbar_location=None,
    )
    top.xaxis.visible = False
    right.yaxis.visible = False
    # Epsilon is horizontal (top histogram); Delta is vertical (right).
    for coordinate, marginal in (("epsilon", top), ("delta", right)):
        edges = np.histogram_bin_edges(
            np.concatenate([p[coordinate].to_numpy() for p in full_points.values()]),
            bins=40,
        )
        for source, renderer in zip(sources, renderers):
            counts, _ = np.histogram(full_points[source][coordinate], bins=edges)
            color = Category20[20][JITTER_SOURCES.index(source)]
            data = ColumnDataSource({
                "bin_start": edges[:-1], "bin_end": edges[1:],
                "count": counts, "source": [source] * len(counts),
            })
            if coordinate == "epsilon":
                bars = marginal.quad(
                    left="bin_start", right="bin_end", bottom=0, top="count",
                    source=data,
                    fill_color=color, fill_alpha=0.35, line_color=color,
                )
            else:
                bars = marginal.quad(
                    bottom="bin_start", top="bin_end", left=0, right="count",
                    source=data,
                    fill_color=color, fill_alpha=0.35, line_color=color,
                )
            marginal.add_tools(HoverTool(
                renderers=[bars],
                tooltips=[
                    ("Source", "@source"),
                    (f"{x_label if coordinate == 'epsilon' else y_label} bin ({units})",
                     "@bin_start{0.000} to @bin_end{0.000}"),
                    ("Count", "@count{0}"),
                ],
            ))
            renderer.js_link("visible", bars, "visible")
    return gridplot([[top, None], [plot, right]], toolbar_location="below")


def first_slew_seconds(telemetry, start, end):
    """Return info on the first contiguous SLEW mode block, or None.

    Telemetry starts at the visit start, so a slew in progress at the first
    sample counts from there. ``completed`` is False if the data end while
    still slewing, making the duration only a lower bound.
    """
    if not telemetry["SCF_AC_SDR_MODE"].notna().any():
        return None
    blocks = _mode_blocks(telemetry, start, end)
    for i, block in enumerate(blocks):
        if block["mode"] == "SLEW":
            return {
                "start": block["start"],
                "seconds": float((block["end"] - block["start"]).total_seconds()),
                "completed": i + 1 < len(blocks),
            }
    return None


_ROW_BREAK = "\n"  # summary key that starts a new row of header cards


def _exposure_number(name):
    """Return the zero-padded exposure number in a name like r<visit>_0002_wfi01_f213."""
    parts = str(name).split("_")
    return parts[1] if len(parts) > 1 else str(name)


def initial_offsets(telemetry, slew_start):
    """Return (delta, epsilon, radial) in mas from the first nonzero values.

    Only samples at or after ``slew_start`` are used; each coordinate takes its
    own first finite, nonzero value. Returns None if either is missing.
    """
    after = telemetry.loc[telemetry["ObsTime"] >= pd.Timestamp(slew_start).tz_localize(None)
                          if pd.Timestamp(slew_start).tzinfo else
                          telemetry["ObsTime"] >= pd.Timestamp(slew_start)]
    scale = (180 / np.pi) * 3_600 * 1_000
    values = []
    for column in ("WFIF_FAC_DELTA", "WFIF_FAC_EPSILON"):
        data = pd.to_numeric(after[column], errors="coerce")
        data = data[np.isfinite(data) & (data != 0)]
        if data.empty:
            return None
        values.append(float(data.iloc[0]) * scale)
    return values[0], values[1], float(np.hypot(*values))


def get_visit_summary(visit_id, start, exposures, telemetry, exposure=None):
    """Return display strings for the dashboard header cards.

    ``exposure`` adds cards for the selected exposure: MA table number,
    exposure time and the bad FACE values rejected during it.
    """
    slew = first_slew_seconds(telemetry, start, _telemetry_end(exposures))
    if slew is None:
        slew_text = "Unavailable"
    else:
        slew_text = f"{slew['seconds']:.1f} s"
        if not slew["completed"]:
            slew_text = ">= " + slew_text
    if "bad_face_rejected" in telemetry:
        bad_text = f"{int(pd.to_numeric(telemetry['bad_face_rejected']).fillna(0).sum()):,}"
    else:
        bad_text = "Unavailable"
    summary = {
        "Visit ID": str(visit_id),
        "Visit start (UTC)": pd.Timestamp(start).strftime("%Y-%m-%d %H:%M:%S"),
        "Exposures": str(len(exposures)),
        "First slew duration": slew_text,
        "Bad FACE values (visit)": bad_text,
        _ROW_BREAK: "",
    }
    if exposure is not None:
        begin = pd.Timestamp(exposure["expstart"]).tz_convert("UTC").tz_localize(None)
        stop = pd.Timestamp(exposure["expend"]).tz_convert("UTC").tz_localize(None)
        if "bad_face_rejected" in telemetry:
            inside = telemetry["ObsTime"].between(begin, stop)
            exposure_bad = f"{int(pd.to_numeric(telemetry.loc[inside, 'bad_face_rejected']).fillna(0).sum()):,}"
        else:
            exposure_bad = "Unavailable"
        summary.update({
            "Selected exposure": _exposure_number(exposure["name"]),
            "MA table name": exposure.get("ma_table_name") or "Unavailable",
            "Optical element": exposure.get("optical_element") or "Unavailable",
            "Exposure time": f"{(stop - begin).total_seconds():.1f} s",
            "Bad FACE values (exposure)": exposure_bad,
        })
    offsets = initial_offsets(telemetry, slew["start"]) if slew else None
    summary["\n\n"] = ""
    for label, index in (
        ("Initial delta offset", 0), ("Initial epsilon offset", 1), ("Initial radial offset", 2)
    ):
        summary[label] = (
            "Unavailable" if offsets is None else f"{offsets[index]:.2f} mas"
        )
    return summary


_MA_TABLE_CACHE = {}


def get_ma_table(ma_table_number, exposure_start, detector="WFI01"):
    """Return the science MA table (as plain Python values) from CRDS.

    ``ma_table_number`` comes from MAST. The CRDS context follows the usual
    CRDS_CONTEXT/CRDS_SERVER_URL environment variables.
    """
    import crds

    number = int(ma_table_number)
    stamp = pd.Timestamp(exposure_start)
    if stamp.tzinfo is not None:
        stamp = stamp.tz_convert("UTC").tz_localize(None)
    cache_key = (number, stamp.strftime("%Y-%m-%d"))
    if cache_key in _MA_TABLE_CACHE:
        return _MA_TABLE_CACHE[cache_key]
    os.environ.setdefault("CRDS_SERVER_URL", "https://roman-crds.stsci.edu")
    meta = {
        "ROMAN.META.INSTRUMENT.NAME": "WFI",
        "ROMAN.META.INSTRUMENT.DETECTOR": detector,
        "ROMAN.META.EXPOSURE.START_TIME": stamp.strftime("%Y-%m-%d %H:%M:%S"),
    }
    reference = crds.getreferences(
        meta, reftypes=["matable"], observatory="roman"
    )["matable"]
    key = f"SCI{number:04d}"
    with rdm.open(reference) as model:
        tables = model.science_tables
        if key not in tables:
            raise KeyError(f"{key} is not in MA table reference file {reference}.")
        table = tables[key]
        result = {
            "frame_time": float(table["frame_time"]),
            "reset_frame_time": float(table["reset_frame_time"]),
            "science_read_pattern": [
                [int(read) for read in resultant]
                for resultant in table["science_read_pattern"]
            ],
            "pre_science_read_types": [
                str(kind) for kind in table["pre_science_read_types"]
            ],
            "reference": os.path.basename(str(reference)),
        }
    _MA_TABLE_CACHE[cache_key] = result
    return result


def resultant_intervals(table, expstart, expend):
    """Return the resultants that fall within an exposure.

    Time starts at the exposure start. Pre-science reads run first, each
    lasting ``reset_frame_time`` for a ``reset_read`` and ``frame_time``
    otherwise; science read ``n`` then spans ``(n - 1)`` to ``n`` frame times
    after the last pre-science read. A resultant covers the first through the
    last read in its read-pattern entry. Resultants beginning at or after the
    exposure end (within half a frame) are dropped.
    """
    frame_time = float(table["frame_time"])
    reset_time = float(table.get("reset_frame_time", frame_time))
    kinds = list(table.get("pre_science_read_types") or [])
    seconds = sum(reset_time if kind == "reset_read" else frame_time for kind in kinds)
    science_start = pd.Timestamp(expstart) + pd.Timedelta(seconds=seconds)
    expend = pd.Timestamp(expend)
    tolerance = pd.Timedelta(seconds=0.5 * frame_time)
    results = []
    for index, reads in enumerate(table["science_read_pattern"], 1):
        first, last = min(reads), max(reads)
        start = science_start + pd.Timedelta(seconds=(first - 1) * frame_time)
        end = science_start + pd.Timedelta(seconds=last * frame_time)
        if results and start >= expend - tolerance:
            break
        results.append({
            "index": index, "reads": list(reads), "start": start, "end": end,
        })
    return results


def resultant_label(item):
    reads = item["reads"]
    span = str(reads[0]) if len(reads) == 1 else f"{min(reads)}-{max(reads)}"
    return (
        f"Resultant {item['index']} (reads {span}, "
        f"{pd.Timestamp(item['start']).strftime('%H:%M:%S.%f')[:-3]} - "
        f"{pd.Timestamp(item['end']).strftime('%H:%M:%S.%f')[:-3]})"
    )


GW_GRID = (
    ("WFI16", "WFI13", "WFI10", "WFI01", "WFI04", "WFI07"),
    ("WFI17", "WFI14", "WFI11", "WFI02", "WFI05", "WFI08"),
    ("WFI18", "WFI15", "WFI12", "WFI03", "WFI06", "WFI09"),
)
GW_DETECTORS = tuple(name for row in GW_GRID for name in row)
SCIENCE_CENTER = 2043.5
GW_SPECTRAL_ELEMENTS = ("PRISM", "GRISM")
GW_MIN_CELL_WIDTH = 130


def centroid_science_xy(telemetry, detector, times):
    """Return science (X, Y) of the centroid at ``times``, NaN if unknown.

    Telemetry centroids (H_COORD, V_COORD) are relative to the guide window
    center (GW_H_CENTER, GW_V_CENTER), which is in absolute H, V. Latest
    values at or before each time are used, never future ones. Then
    X = H + 2043.5 and Y = 2043.5 - V.
    """
    prefix = f"WFIF_FAC_OPD{detector[-2:]}_"
    names = [prefix + suffix for suffix in (
        "H_COORD", "V_COORD", "GW_H_CENTER", "GW_V_CENTER"
    )]
    data = telemetry[["ObsTime", *names]].sort_values("ObsTime")
    values = data[names].apply(pd.to_numeric, errors="coerce").ffill()
    observed = data["ObsTime"].to_numpy(dtype="datetime64[ns]")
    times = np.asarray(times, dtype="datetime64[ns]")
    index = np.searchsorted(observed, times, side="right") - 1
    columns = values.to_numpy(dtype=float)
    picked = np.where(
        (index >= 0)[:, None], columns[np.clip(index, 0, None)], np.nan
    )
    h = picked[:, 0] + picked[:, 2]
    v = picked[:, 1] + picked[:, 3]
    return h + SCIENCE_CENTER, SCIENCE_CENTER - v


def centroid_hv(telemetry, detector, times):
    """Return telemetry (H, -V) centroid positions at ``times`` (NaN if unknown).

    Latest values at or before each time are used, never future ones.
    """
    prefix = f"WFIF_FAC_OPD{detector[-2:]}_"
    names = [prefix + "H_COORD", prefix + "V_COORD"]
    data = telemetry[["ObsTime", *names]].sort_values("ObsTime")
    values = data[names].apply(pd.to_numeric, errors="coerce").ffill().to_numpy(float)
    observed = data["ObsTime"].to_numpy(dtype="datetime64[ns]")
    index = np.searchsorted(
        observed, np.asarray(times, dtype="datetime64[ns]"), side="right"
    ) - 1
    picked = np.where((index >= 0)[:, None], values[np.clip(index, 0, None)], np.nan)
    return picked[:, 0], -picked[:, 1]


def extract_gw_window(gw, expstart, expend):
    """Return guide window track frames within an exposure, or None.

    Pixels are signal minus pedestal resultants. Frames are selected by their
    signal times (UTC) between ``expstart`` and ``expend`` inclusive.
    """
    section = gw.track_data
    signal = np.asarray(section.signal_resultants)
    if signal.ndim != 3 or len(signal) == 0:
        return None
    pedestal = np.asarray(section.pedestal_resultants)
    if pedestal.shape != signal.shape:
        raise ValueError("Guide window signal and pedestal shapes must match.")
    times = np.asarray(
        Time(section.signal_times).utc.to_datetime(), dtype="datetime64[ns]"
    )
    if len(times) != len(signal):
        raise ValueError("Guide window signal times must match the frame count.")
    start, end = (
        np.datetime64(pd.Timestamp(value).tz_convert("UTC").tz_localize(None), "ns")
        if pd.Timestamp(value).tzinfo is not None
        else np.datetime64(pd.Timestamp(value), "ns")
        for value in (expstart, expend)
    )
    keep = np.flatnonzero((times >= start) & (times <= end))
    if not len(keep):
        return None
    frames = signal[keep].astype(np.int32) - pedestal[keep].astype(np.int32)
    try:
        corners = np.asarray(section.lower_left_corners, dtype=float)[keep]
    except (AttributeError, KeyError, TypeError):
        window = gw.meta.guide_window
        corners = np.tile(
            [float(window.min_track_xstart), float(window.min_track_ystart)],
            (len(keep), 1),
        )
    instrument = gw.meta.instrument
    star = getattr(gw.meta, "guide_star", None)
    star_name = getattr(star, "gsc_id", None)
    pseudo = str(getattr(star, "pseudo_star_flag", "N") or "N").strip().upper() == "Y"
    optical = str(getattr(instrument, "optical_element", "") or "")
    edge = getattr(gw.meta, "wsm_edge_used", None)
    return {
        "detector": str(instrument.detector).upper(),
        "optical_element": optical,
        "edge": None if edge is None else str(edge),
        "star_name": None if star_name is None else str(star_name).strip(),
        "pseudo": pseudo,
        "times": times[keep],
        "frames": frames,
        "x0": corners[:, 0],
        "y0": corners[:, 1],
        "filename": os.path.basename(str(getattr(gw.meta, "filename", ""))),
    }


class GWProvider:
    """Find and cache one guide window file per detector for each exposure.

    Give ``folder`` to read local ``*_gw.asdf`` files; otherwise files are
    taken from the MAST products of each exposure's detector file sets. A
    visit can have several guide window files per detector (one per guide
    star acquisition), so the file is chosen per exposure.
    """

    def __init__(self, visit_id, env_variables=None, folder=None, opener=None):
        self.visit_id = _validate_visit_id(visit_id)
        self.env_variables = env_variables
        self.folder = folder
        self._opener = opener or rdm.open
        self._local = threading.local()
        self._search = None
        self._models = {}
        self._lookup_errors = {}
        self._tempdir = None

    def close(self):
        for model in self._models.values():
            model.close()
        self._models.clear()
        if self._tempdir is not None:
            self._tempdir.cleanup()
            self._tempdir = None

    def _open_local(self, path):
        if path not in self._models:
            self._models[path] = self._opener(str(path))
        return self._models[path]

    def _local_files(self, detector):
        from pathlib import Path

        folder = Path(self.folder).expanduser()
        if not folder.is_dir():
            raise ValueError(f"Guide window folder not found: {folder}")
        return sorted(
            path for path in folder.rglob("*_gw.asdf")
            if f"_{detector.lower()}_" in path.name.lower()
            or detector.lower() in path.name.lower()
        )

    def _mast(self):
        # MastMissions keeps per-request state, so each thread gets its own.
        mission = getattr(self._local, "mission", None)
        if mission is None:
            mission = MastMissions(mission="roman")
            if self.env_variables:
                load_dotenv(self.env_variables, override=True)
                mission.login(token=os.getenv("MAST_API_TOKEN"))
            self._local.mission = mission
        return mission

    def _visit_search(self):
        from astropy.table import vstack

        if self._search is None:
            mission = self._mast()
            pages, offset, limit = [], 0, 1000
            while True:
                page = mission.query_criteria(
                    visit_id=self.visit_id, limit=limit, offset=offset,
                    select_cols=["detector", "exposure_start_time", "guide_star_id"],
                )
                if len(page):
                    pages.append(page)
                if len(page) < limit:
                    break
                offset += len(page)
            if not pages:
                raise ValueError(f"No MAST observations found for visit {self.visit_id}.")
            self._search = vstack(pages) if len(pages) > 1 else pages[0]
            missing = {"detector", "exposure_start_time", "guide_star_id", "fileSetName"} - set(
                self._search.colnames
            )
            if missing:
                raise ValueError(f"MAST visit results lack columns: {', '.join(sorted(missing))}")
        return self._search

    def _exposure_rows(self, exposure):
        search = self._visit_search()
        start = pd.Timestamp(exposure["expstart"])
        return [
            row for row in search
            if not np.ma.is_masked(row["exposure_start_time"])
            and not pd.isna(row["exposure_start_time"])
            and abs(pd.to_datetime(row["exposure_start_time"], utc=True) - start)
            <= pd.Timedelta(seconds=1)
        ]

    def guide_stars(self, exposure):
        """Return known MAST guide-star IDs for an exposure's detectors."""
        stars = {}
        search = self._visit_search()
        for row in self._exposure_rows(exposure):
            detector = _optional_text(row, search, "detector")
            star = _optional_text(row, search, "guide_star_id")
            if detector is None or star is None:
                continue
            detector = detector.upper()
            if detector in stars and stars[detector] != star:
                raise ValueError(f"Conflicting guide-star IDs for {detector} in {exposure['name']}.")
            stars[detector] = star
        return stars

    def _mast_filenames(self, exposure):
        rows = self._exposure_rows(exposure)
        file_sets = {}
        for row in rows:
            detector = _optional_text(row, self._search, "detector")
            file_set = _optional_text(row, self._search, "fileSetName")
            if detector is None or file_set is None:
                continue
            detector = detector.upper()
            if detector in file_sets and file_sets[detector] != file_set:
                raise ValueError(f"Conflicting file sets for {detector} in {exposure['name']}.")
            file_sets[detector] = file_set
        logger.info(
            "Guide windows: %d of %d MAST rows match exposure %s (columns: %s).",
            len(rows), len(self._search), exposure.get("name"),
            ", ".join(self._search.colnames),
        )
        if not file_sets:
            return {}
        filenames = {}
        errors = {}

        def lookup(detector, file_set):
            # Same lookup as get_data: products of the file set ending in _gw.asdf.
            mission = self._mast()
            with _MAST_LOCK:
                search = mission.query_criteria(fileSetName=file_set)
                products = mission.get_product_list(search)
            matches = sorted(
                name for name in set(products["filename"]) if name.endswith("_gw.asdf")
            )
            if len(matches) != 1:
                raise ValueError(
                    f"expected one guide window product in {file_set}; found {matches}"
                )
            return matches[0]

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(lookup, detector, file_set): detector
                for detector, file_set in file_sets.items()
            }
            for future, detector in futures.items():
                try:
                    filenames[detector] = future.result()
                except Exception as exc:
                    errors[detector] = str(exc)
        self._lookup_errors = errors
        for detector, message in errors.items():
            logger.warning("%s: guide window lookup failed: %s", detector, message)
        logger.info("Guide windows: found %d _gw.asdf products.", len(filenames))
        return filenames

    def _load_remote(self, filename):
        if filename not in self._models:
            from pathlib import Path
            from tempfile import TemporaryDirectory

            with _MAST_LOCK:
                if self._tempdir is None:
                    self._tempdir = TemporaryDirectory(prefix="guiding-products-")
                path = Path(self._tempdir.name) / os.path.basename(filename)
                status, message, _ = self._mast().download_file(
                    filename, local_path=path, verbose=False
                )
                if status not in ("COMPLETE", "SKIPPED"):
                    raise RuntimeError(f"Could not download {filename}: {message}")
                self._models[filename] = rdm.open(path)
        return self._models[filename]

    def window(self, detector, exposure, filename=None):
        """Return the exposure's guide window frames for one detector, or None."""
        if self.folder:
            best = None
            for path in self._local_files(detector):
                window = extract_gw_window(
                    self._open_local(path), exposure["expstart"], exposure["expend"]
                )
                if (
                    window is not None and window["detector"] == detector
                    and (best is None or len(window["times"]) > len(best["times"]))
                ):
                    window["source_path"] = str(path)
                    best = window
            return best
        if filename is None:
            return None
        window = extract_gw_window(
            self._load_remote(filename), exposure["expstart"], exposure["expend"]
        )
        if window is not None:
            window["filename"] = filename
        return window

    def windows(self, exposure):
        """Return ({detector: window or None}, {detector: error message})."""
        filenames = {} if self.folder else self._mast_filenames(exposure)
        lookup_errors = {} if self.folder else dict(self._lookup_errors)
        if not self.folder and not filenames and not lookup_errors:
            lookup_errors = {
                "all": "no MAST rows matched this exposure's start time "
                "(check the detector and exposure_start_time columns)"
            }

        def one(detector):
            try:
                return detector, self.window(detector, exposure, filenames.get(detector)), None
            except Exception as exc:
                logger.warning("%s: guide window unavailable: %s", detector, exc)
                return detector, None, str(exc)

        with ThreadPoolExecutor(max_workers=1 if self.folder else 8) as pool:
            results = list(pool.map(one, GW_DETECTORS))
        return (
            {detector: window for detector, window, _ in results},
            {**lookup_errors, **{d: e for d, _, e in results if e}},
        )

    def save_products(self, exposure, windows, directory):
        """Save the selected exposure's loaded GW products and FACE products."""
        from pathlib import Path
        from shutil import copyfileobj
        from tempfile import TemporaryDirectory

        destination = Path(directory).expanduser()
        if not destination.is_dir():
            raise ValueError(f"Destination directory not found: {destination}")
        loaded = [window for window in windows.values() if window]
        if not loaded:
            raise ValueError("Load guide windows for the selected exposure first.")
        products = {}
        if self.folder:
            for window in loaded:
                path = Path(window["source_path"])
                if path.name in products and products[path.name] != path:
                    raise ValueError(f"Duplicate local product filename: {path.name}")
                products[path.name] = path
            prefix = exposure["name"] + "_"
            faces = []
            start = pd.Timestamp(exposure["expstart"]).tz_convert("UTC").tz_localize(None)
            end = pd.Timestamp(exposure["expend"]).tz_convert("UTC").tz_localize(None)
            for path in sorted(Path(self.folder).expanduser().rglob("*_face.asdf")):
                if path.name.startswith(prefix):
                    faces.append(path)
                    continue
                face = get_face_info(self._open_local(path))
                times = pd.to_datetime(face["time"], utc=True).tz_localize(None)
                if ((times >= start) & (times <= end)).any():
                    faces.append(path)
            for path in faces:
                if path.name in products and products[path.name] != path:
                    raise ValueError(f"Duplicate local product filename: {path.name}")
                products[path.name] = path
        else:
            for window in loaded:
                name = window["filename"]
                if not name or os.path.basename(name) != name:
                    raise ValueError("A loaded guide window has no valid product filename.")
                products[name] = None
            face_names = set()
            mission = self._mast()
            file_sets = {
                _optional_text(row, self._search, "fileSetName")
                for row in self._exposure_rows(exposure)
            }
            for file_set in sorted(name for name in file_sets if name):
                with _MAST_LOCK:
                    search = mission.query_criteria(fileSetName=file_set)
                    listing = mission.get_product_list(search)
                face_names.update(
                    str(name) for name in listing["filename"]
                    if str(name).endswith("_face.asdf")
                )
            for name in face_names:
                if os.path.basename(name) != name:
                    raise ValueError(f"Invalid FACE product filename: {name}")
                products[name] = None
            faces = face_names
        if not faces:
            raise ValueError("No FACE product found for the selected exposure.")
        existing = [name for name in products if (destination / name).exists()]
        if existing:
            raise FileExistsError(f"Products already exist: {', '.join(sorted(existing))}")

        with TemporaryDirectory(prefix="guiding-export-") as directory:
            for name, source in list(products.items()):
                if source is None:
                    path = Path(directory) / name
                    status, message, _ = self._mast().download_file(
                        name, local_path=path, verbose=False
                    )
                    if status not in ("COMPLETE", "SKIPPED"):
                        raise RuntimeError(f"Could not download {name}: {message}")
                    products[name] = path
            for name, source in products.items():
                with source.open("rb") as src, (destination / name).open("xb") as dst:
                    copyfileobj(src, dst)
        return sorted(products)


class GWGrid:
    """A 6x3 grid of guide window panels whose frame can be changed in place.

    Each panel is sized to its window (16x16 normally, 128 rows x 32 columns
    for PRISM/GRISM) at ``scale`` screen pixels per detector pixel. Panels
    show signal minus pedestal in inverted grayscale with a fixed color range
    per detector, the telemetry centroid, the WFI name and the frame time.
    """

    def __init__(self, windows, telemetry, *, scale=8):
        from bokeh.layouts import gridplot
        from bokeh.models import Label, LinearColorMapper, Title
        from bokeh.palettes import Greys256

        self.windows = windows
        self.n_frames = max(
            (len(w["times"]) for w in windows.values() if w), default=0
        )
        self._panels = {}
        pixels = np.concatenate(
            [w["frames"].ravel() for w in windows.values() if w]
        ) if self.n_frames else np.zeros(1)
        from astropy.visualization import ZScaleInterval

        # One zscale over every pixel so all panels share a common scaling.
        low, high = ZScaleInterval().get_limits(pixels.astype(float))
        high = max(high, low + 1)
        rows = []
        for names in GW_GRID:
            row = []
            for detector in names:
                window = windows.get(detector)
                rows_px, cols_px = window["frames"].shape[1:] if window else (16, 16)
                fig = figure(
                    frame_width=max(24, int(cols_px * scale)),
                    frame_height=max(24, int(rows_px * scale)),
                    toolbar_location=None, tools="",
                    x_range=Range1d(-cols_px / 2, cols_px / 2),
                    y_range=Range1d(-rows_px / 2, rows_px / 2),
                    title=detector, name=f"gw_{detector}",
                )
                # Pad narrow panels so the time label and subtitle are not clipped.
                pad = int(max(8, (GW_MIN_CELL_WIDTH - fig.frame_width) / 2))
                fig.min_border_left = fig.min_border_right = pad
                fig.title.text_font_size = "13pt"
                fig.title.align = "center"
                subtitle = "No guide window data"
                if window:
                    subtitle = window["optical_element"] or "Optical element unknown"
                    if window["optical_element"].upper() in GW_SPECTRAL_ELEMENTS:
                        subtitle += f" - {window['edge'] or 'unknown'} edge"
                fig.add_layout(
                    Title(text=subtitle, text_font_style="italic", align="center"),
                    "above",
                )
                fig.grid.visible = False
                fig.yaxis.visible = False
                fig.xaxis.major_label_text_font_size = "0pt"
                fig.xaxis.major_tick_line_color = None
                fig.xaxis.minor_tick_line_color = None
                fig.xaxis.axis_label_text_font_style = "normal"
                fig.xaxis.axis_label = " "
                panel = {"figure": fig, "window": window}
                if window:
                    frames = window["frames"]
                    mapper = LinearColorMapper(
                        palette=Greys256[::-1], low=low, high=max(high, low + 1),
                        nan_color=(255, 255, 255, 0),
                    )
                    panel["image"] = ColumnDataSource({
                        "image": [frames[0].astype(np.float32)],
                        "x": [-cols_px / 2], "y": [-rows_px / 2],
                        "dw": [cols_px], "dh": [rows_px],
                    })
                    panel["centroid"] = ColumnDataSource({"x": [np.nan], "y": [np.nan]})
                    fig.image(
                        image="image", x="x", y="y", dw="dw", dh="dh",
                        source=panel["image"], color_mapper=mapper,
                    )
                    star = window.get("star_name") or "Unknown star"
                    if window.get("pseudo"):
                        star += " (pseudo)"
                    fig.add_layout(Label(
                        x=3, y=3, x_units="screen", y_units="screen", text=star,
                        text_font_size="9pt", text_color="red",
                        background_fill_color="white", background_fill_alpha=0.6,
                    ))
                    fig.scatter(
                        "x", "y", source=panel["centroid"], marker="circle_cross",
                        size=max(8, scale * 1.2), line_color="red", line_width=2,
                        fill_color=None,
                    )
                    panel["cx"], panel["cy"] = centroid_hv(
                        telemetry, detector, window["times"]
                    )
                self._panels[detector] = panel
                row.append(fig)
            rows.append(row)
        self.layout = gridplot(rows, toolbar_location=None)
        self.set_frame(0)

    def set_frame(self, index):
        """Show frame ``index`` (blank for detectors with fewer frames)."""
        for panel in self._panels.values():
            window = panel["window"]
            if window is None:
                continue
            fig = panel["figure"]
            if index >= len(window["times"]):
                fig.xaxis.axis_label = "no frame"
                panel["image"].data = {**panel["image"].data, "image": [
                    np.full(window["frames"].shape[1:], np.nan, dtype=np.float32)
                ]}
                panel["centroid"].data = {"x": [np.nan], "y": [np.nan]}
                continue
            rows_px, cols_px = window["frames"].shape[1:]
            panel["image"].data = {
                "image": [window["frames"][index].astype(np.float32)],
                "x": [-cols_px / 2], "y": [-rows_px / 2], "dw": [cols_px], "dh": [rows_px],
            }
            if window.get("pseudo"):
                panel["centroid"].data = {"x": [np.nan], "y": [np.nan]}
            else:
                panel["centroid"].data = {
                    "x": [panel["cx"][index]], "y": [panel["cy"][index]],
                }
            stamp = pd.Timestamp(window["times"][index])
            fig.xaxis.axis_label = stamp.strftime("%H:%M:%S.%f")[:-3] + " UTC"


def make_gw_grid_movie(windows, telemetry, path, fps=5.0, progress=None, scale=None):
    """Write an MP4 of the guide window grid showing every frame; return ``path``.

    Mirrors the dashboard: 3x6 detector layout, shared zscale, inverted
    grayscale, telemetry centroid (omitted for pseudo stars) and frame times.
    ``progress(done, total)`` is called after each frame. Needs Pillow >= 10.1
    and imageio-ffmpeg.
    """
    try:
        import imageio_ffmpeg
        from astropy.visualization import ZScaleInterval
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise ImportError(
            "GW movies require Pillow >= 10.1 and imageio-ffmpeg. "
            "Install them with %pip install 'Pillow>=10.1' imageio-ffmpeg"
        ) from exc
    available = {d: w for d, w in windows.items() if w}
    if not available:
        raise ValueError("No guide window frames are loaded.")
    n_frames = max(len(w["times"]) for w in available.values())
    low, high = ZScaleInterval().get_limits(
        np.concatenate([w["frames"].ravel() for w in available.values()]).astype(float)
    )
    span = max(high - low, 1.0)
    def scale_of(window):
        return scale or (3 if window["frames"].shape[1] >= 64 else 10)

    # Rows and columns are sized to their largest window.
    row_h = [
        max([60] + [
            window["frames"].shape[1] * scale_of(window) + 70
            for d in names if (window := available.get(d))
        ])
        for names in GW_GRID
    ]
    col_w = [
        max([150] + [
            window["frames"].shape[2] * scale_of(window) + 16
            for names in GW_GRID if (window := available.get(names[c]))
        ])
        for c in range(len(GW_GRID[0]))
    ]
    row_y = np.concatenate([[0], np.cumsum(row_h)]).astype(int)
    col_x = np.concatenate([[0], np.cumsum(col_w)]).astype(int)
    font = ImageFont.load_default(size=13)
    small = ImageFont.load_default(size=11)
    width = int(col_x[-1] + 1) // 2 * 2
    height = int(row_y[-1] + 1) // 2 * 2
    centroids = {
        d: centroid_hv(telemetry, d, w["times"]) for d, w in available.items()
    }
    writer = imageio_ffmpeg.write_frames(
        str(path), size=(width, height), fps=float(fps), codec="libx264",
        pix_fmt_in="rgb24", pix_fmt_out="yuv420p", macro_block_size=1,
        output_params=["-movflags", "+faststart"],
    )
    writer.send(None)
    try:
        for index in range(n_frames):
            canvas = Image.new("RGB", (width, height), "white")
            draw = ImageDraw.Draw(canvas)
            for r, names in enumerate(GW_GRID):
                for c, detector in enumerate(names):
                    x0, y0 = int(col_x[c]), int(row_y[r])
                    window = available.get(detector)
                    draw.text((x0 + 8, y0 + 4), detector, font=font, fill="black")
                    if window is None:
                        draw.text((x0 + 8, y0 + 24), "No guide window data",
                                  font=small, fill="gray")
                        continue
                    subtitle = window["optical_element"] or "Optical element unknown"
                    if window["optical_element"].upper() in GW_SPECTRAL_ELEMENTS:
                        subtitle += f" - {window['edge'] or 'unknown'} edge"
                    draw.text((x0 + 8, y0 + 20), subtitle, font=small, fill="gray")
                    star = window.get("star_name") or "Unknown star"
                    if window.get("pseudo"):
                        star += " (pseudo)"
                    draw.text((x0 + 8, y0 + 34), star, font=small, fill="red")
                    zoom = scale_of(window)
                    if index >= len(window["times"]):
                        draw.text((x0 + 8, y0 + 52), "no frame",
                                  font=small, fill="black")
                        continue
                    rows_px, cols_px = window["frames"].shape[1:]
                    norm = ((window["frames"][index] - low) / span).clip(0, 1)
                    # Row 0 is drawn at the bottom, as in the dashboard.
                    pixels = np.flipud(255 - (norm * 255)).astype(np.uint8)
                    tile = Image.fromarray(pixels).resize(
                        (cols_px * zoom, rows_px * zoom), Image.Resampling.NEAREST
                    )
                    ox = x0 + (int(col_w[c]) - tile.width) // 2
                    oy = y0 + 50
                    canvas.paste(tile.convert("RGB"), (ox, oy))
                    cx, cy = centroids[detector][0][index], centroids[detector][1][index]
                    if not window.get("pseudo") and np.isfinite(cx) and np.isfinite(cy):
                        px = ox + tile.width / 2 + cx * zoom
                        py = oy + tile.height / 2 - cy * zoom
                        rad = max(5, zoom * 0.6)
                        draw.ellipse(
                            (px - rad, py - rad, px + rad, py + rad),
                            outline="red", width=2,
                        )
                        draw.line((px - rad, py, px + rad, py), fill="red", width=1)
                        draw.line((px, py - rad, px, py + rad), fill="red", width=1)
                    stamp = pd.Timestamp(window["times"][index])
                    draw.text(
                        (x0 + 8, oy + tile.height + 4),
                        stamp.strftime("%H:%M:%S.%f")[:-3] + " UTC",
                        font=small, fill="black",
                    )
            writer.send(np.asarray(canvas))
            if progress:
                progress(index + 1, n_frames)
    finally:
        writer.close()
    return path


def _gw_movie_section(section, label, subtract_pedestal=True):
    """Validate signal frames and, when requested, matching pedestal frames."""
    signal = np.asarray(section.signal_resultants)
    if signal.ndim != 3:
        raise ValueError(
            f"{label}: signal must have a (frame, row, column) shape; "
            f"got {signal.shape}."
        )
    if signal.dtype.kind != "u" or signal.dtype.itemsize != 2:
        raise TypeError(f"{label}: expected uint16 signal data.")
    if signal.shape[1] == 0 or signal.shape[2] == 0:
        raise ValueError(f"{label}: pixel dimensions must be nonzero.")
    if len(section.signal_times) != len(signal):
        raise ValueError(f"{label}: signal timestamps must match frame count.")
    pedestal = None
    if subtract_pedestal:
        pedestal = np.asarray(section.pedestal_resultants)
        if pedestal.shape != signal.shape:
            raise ValueError(f"{label}: signal and pedestal shapes must match.")
        if pedestal.dtype.kind != "u" or pedestal.dtype.itemsize != 2:
            raise TypeError(f"{label}: expected uint16 pedestal data.")
    return signal, pedestal, section.signal_times


def make_gw_movies(
    gw_file, fps=3.0, progress=None, *, section=None, sci_info=None,
    subtract_pedestal=True,
):
    """Return acquisition/track MP4 bytes using signal - pedestal by default.

    Requires Pillow >= 10.1 and imageio-ffmpeg. ``fps`` controls playback, not
    the telemetry cadence. Each movie uses a fixed grayscale DN range across
    its frames. ``progress(done, total, message)`` reports rendering progress
    at most five times per second, plus initial and final updates.
    Empty sections are skipped with a warning.

    Set section to "acq_data" or "track_data" to encode only that section;
    None encodes both. Pass sci_info from get_sci_info() to label frames with
    the science exposure start and stop times (otherwise "Not provided").
    Set subtract_pedestal=False to show signal frames only.
    """
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from textwrap import wrap
    from time import monotonic

    try:
        import imageio_ffmpeg
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise ImportError(
            "GW movies require Pillow >= 10.1 and imageio-ffmpeg. "
            "Install them in the notebook kernel with "
            "%pip install 'Pillow>=10.1' imageio-ffmpeg"
        ) from exc

    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("Movie FPS must be a finite positive number.")
    if section not in (None, "acq_data", "track_data"):
        raise ValueError("Movie section must be 'acq_data' or 'track_data'.")

    sections = []
    for key, label in [
        ("acq_data", "Guide Star Acquisition"),
        ("track_data", "Guide Star Track"),
    ]:
        if section is not None and key != section:
            continue
        signal, pedestal, times = _gw_movie_section(
            getattr(gw_file, key), label, subtract_pedestal
        )
        if len(signal) == 0:
            warnings.warn(f"{label}: no frames available; no movie created.")
            continue
        sections.append((label, signal, pedestal, times))
    if not sections:
        raise ValueError("No frames are available in the requested GW section(s).")

    total = sum(2 * len(signal) + 1 for _, signal, _, _ in sections)
    done = 0
    last_report = None

    def report(message):
        nonlocal last_report
        if progress is None:
            return
        now = monotonic()
        if last_report is None or done == total or now - last_report >= 0.2:
            progress(done, total, message)
            last_report = now

    def frame_pixels(signal, pedestal, i):
        pixels = signal[i].astype(np.int32)
        if pedestal is not None:
            pixels -= pedestal[i]
        return pixels

    filename = os.path.basename(str(gw_file.meta.filename))
    font = ImageFont.load_default(size=16)
    width, height = 720, 700
    exposure_labels = {}
    for key, label in [("expstart", "start"), ("expend", "stop")]:
        value = "Not provided"
        if sci_info is not None:
            exposure_time = Time(sci_info[key]).utc
            exposure_time.precision = 3
            value = exposure_time.isot
        exposure_labels[label] = f"Exposure {label} (UTC): {value}"
    movies = {}
    report("Preparing guide window movies")
    with TemporaryDirectory(prefix="guiding-movies-") as directory:
        for movie_index, (label, signal, pedestal, times) in enumerate(sections):
            low, high = np.inf, -np.inf
            for i in range(len(signal)):
                pixels = frame_pixels(signal, pedestal, i)
                low = min(low, int(pixels.min()))
                high = max(high, int(pixels.max()))
                done += 1
                report(f"{label}: measuring contrast")

            path = Path(directory) / f"movie-{movie_index}.mp4"
            writer = imageio_ffmpeg.write_frames(
                str(path),
                size=(width, height),
                fps=float(fps),
                codec="libx264",
                pix_fmt_in="rgb24",
                pix_fmt_out="yuv420p",
                macro_block_size=1,
                output_params=["-movflags", "+faststart"],
            )
            writer.send(None)
            try:
                for i in range(len(signal)):
                    scaled = (
                        (frame_pixels(signal, pedestal, i) - low)
                        * (255.0 / max(high - low, 1))
                    ).clip(0, 255).astype(np.uint8)
                    image = Image.fromarray(scaled)
                    # Enlarge small windows without smoothing detector pixels.
                    scale = min(680 / scaled.shape[1], 440 / scaled.shape[0])
                    image = image.resize(
                        (
                            max(1, round(scaled.shape[1] * scale)),
                            max(1, round(scaled.shape[0] * scale)),
                        ),
                        Image.Resampling.NEAREST,
                    )
                    frame = Image.new("RGB", (width, height), "black")
                    frame.paste(image, ((width - image.width) // 2, 110))
                    draw = ImageDraw.Draw(frame)
                    draw.multiline_text(
                        (20, 12), "\n".join(wrap(filename, width=76)),
                        font=font, fill="white", spacing=3,
                    )
                    draw.text((20, 80), label, font=font, fill="white")
                    stamp = Time(times[i]).utc
                    stamp.precision = 3
                    draw.text(
                        (20, 565), f"Signal time (UTC): {stamp.isot}",
                        font=font, fill="white",
                    )
                    draw.text(
                        (20, 595),
                        exposure_labels["start"],
                        font=font, fill="white",
                    )
                    draw.text(
                        (20, 625),
                        exposure_labels["stop"],
                        font=font, fill="white",
                    )
                    draw.text(
                        (20, 660),
                        f"Frame {i + 1}/{len(signal)} | {fps:g} fps",
                        font=font, fill="white",
                    )
                    writer.send(np.asarray(frame))
                    done += 1
                    report(f"{label}: encoding frame {i + 1}/{len(signal)}")
            finally:
                writer.close()
            movies[label] = path.read_bytes()
            done += 1
            report(f"{label}: movie ready")
    return movies


def _cards_html(summary):
    """Return header cards (label/value pairs) as an HTML string."""
    from html import escape

    cards = "".join(
        '<div style="flex-basis:100%;height:0"></div>' if label.startswith(_ROW_BREAK) else
        '<div style="flex:1;min-width:150px;background:#f5f7fa;border:1px solid #e1e5ea;'
        'border-radius:10px;padding:10px 14px">'
        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.06em;'
        f'color:#6b7785">{escape(label)}</div>'
        f'<div style="font-size:18px;font-weight:600;color:#1f2d3d">{escape(value)}</div>'
        "</div>"
        for label, value in summary.items()
    )
    return f'<div style="display:flex;flex-wrap:wrap;gap:10px">{cards}</div>'


def _show_bokeh(output, obj, *, notebook_handle=False):
    """Replace the contents of an ipywidgets Output with a Bokeh object."""
    from bokeh.io import show
    from IPython.display import clear_output

    with output:
        clear_output(wait=obj is not None)
        if obj is not None:
            return show(obj, notebook_handle=notebook_handle)


def create_dashboard():
    """Return an ipywidgets dashboard for visit telemetry, NEA, jitter and guide windows.

    Call ``bokeh.io.output_notebook()`` first (done here too), then display the
    returned widget. Load a visit first; the header cards, NEA plot, jitter
    plot and guide window grid all use the cached telemetry until the inputs
    change. File reading and exports use the kernel filesystem. Saved timing
    and telemetry can replay multiple visits. Timing exports include guide-star
    IDs; older timing files without them offer only FACE for jitter. To export
    original ASDF products, first load guide windows for the selected exposure.
    """
    import traceback
    from html import escape
    from pathlib import Path

    import ipywidgets as widgets
    from bokeh.io import output_notebook, push_notebook

    output_notebook(hide_banner=True)

    style = {"description_width": "initial"}
    full = widgets.Layout(width="98%")

    def text_input(description, placeholder, value=""):
        return widgets.Text(
            description=description, placeholder=placeholder, value=value,
            style=style, layout=full,
        )

    def button(description, style_name="", disabled=False):
        return widgets.Button(
            description=description, button_style=style_name, disabled=disabled
        )

    def status_box():
        return widgets.HTML("")

    def error_html(prefix=""):
        return f"{escape(prefix)}<pre>{escape(traceback.format_exc())}</pre>"

    def path_picker(field, *, directory=False):
        browse = button("Browse")
        entries = widgets.Select(options=[], rows=8, layout=full)
        location = widgets.HTML()
        message = widgets.HTML()
        open_button = button("Open")
        select_button = button("Select")
        close_button = button("Close")
        browser = widgets.VBox(
            [location, entries, widgets.HBox([open_button, select_button, close_button]), message],
            layout=widgets.Layout(display="none", width="98%"),
        )
        current_dir = [Path.cwd()]

        def refresh():
            try:
                children = sorted(current_dir[0].iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                choices = [("..", str(current_dir[0].parent))]
                choices.extend(
                    (path.name + ("/" if path.is_dir() else ""), str(path))
                    for path in children if path.is_dir() or not directory
                )
                entries.options = choices
                location.value = f"<b>{escape(str(current_dir[0]))}</b>"
                message.value = ""
            except OSError as exc:
                message.value = escape(str(exc))

        def toggle(_):
            if browser.layout.display != "none":
                browser.layout.display = "none"
                return
            given = Path(field.value.strip()).expanduser() if field.value.strip() else Path.cwd()
            current_dir[0] = given if given.is_dir() else given.parent
            browser.layout.display = ""
            refresh()

        def open_entry(_):
            path = Path(entries.value)
            if path.is_dir():
                current_dir[0] = path
                refresh()
            else:
                message.value = "Select a directory to open."

        def select_entry(_):
            path = Path(entries.value) if entries.value else current_dir[0]
            if directory:
                if path == current_dir[0].parent:
                    path = current_dir[0]
                if not path.is_dir():
                    message.value = "Select a directory."
                    return
            elif not path.is_file():
                message.value = "Select a file."
                return
            field.value = str(path)
            browser.layout.display = "none"

        browse.on_click(toggle)
        open_button.on_click(open_entry)
        select_button.on_click(select_entry)
        close_button.on_click(lambda _: setattr(browser.layout, "display", "none"))
        return widgets.VBox([widgets.HBox([field, browse]), browser])

    visit_input = text_input("Visit ID", "e.g. 0102406034001002001 (comma-separate for batch)")
    telemetry_input = text_input("Input CSV (optional)", "Saved telemetry CSV; blank queries MAST")
    timing_input = text_input("Timing JSON (optional)", "Bypasses MAST exposure metadata")
    timing_input.continuous_update = False
    timing_status = status_box()
    gw_folder_input = text_input(
        "Guide window folder (optional)", "Local *_gw.asdf files; blank uses MAST"
    )
    env_input = text_input(
        "ENV file (optional)", "Path to file containing MAST_API_TOKEN; blank uses none"
    )
    load_button = button("Load visit", "primary")
    reset_button = button("Reset")
    load_status = status_box()
    header = widgets.HTML("", layout=full)
    visit_select = widgets.Dropdown(
        description="Visit", options=[], style=style,
        layout=widgets.Layout(display="none"),
    )

    state = {
        "telemetry": None, "loaded": {}, "ih": None, "providers": {},
        "windows": None, "resultants": [], "jitter_drawn": False, "busy": False,
        "gw_grid": None, "gw_handle": None,
    }

    def selected_env():
        return env_input.value.strip() or None

    def current():
        if state["telemetry"] is None:
            raise ValueError("Load a visit first.")
        visit_id, start, exposures = state["loaded"][visit_select.value]
        data = state["telemetry"]
        data = data.loc[data["visit_id"].eq(visit_id)].reset_index(drop=True)
        return visit_id, start, exposures, data

    def exposure_by_name(exposures, name):
        return next(item for item in exposures if item["name"] == name)

    # --- NEA tab ---
    exposure_select = widgets.Dropdown(
        description="Exposure", options=[], style=style,
        layout=widgets.Layout(width="420px"),
    )
    nea_whole = widgets.Checkbox(description="Whole visit", value=True, indent=False)
    nea_width = widgets.BoundedIntText(
        description="Width (px)", value=1000, min=200, max=5000, style=style,
        layout=widgets.Layout(width="170px"),
    )
    nea_height = widgets.BoundedIntText(
        description="Height (px)", value=400, min=150, max=5000, style=style,
        layout=widgets.Layout(width="170px"),
    )
    nea_button = button("Draw NEA plot", "primary", disabled=True)
    nea_status = status_box()
    nea_out = widgets.Output()

    def draw_nea(*_):
        try:
            visit_id, start, exposures, data = current()
            exposure = (
                None if nea_whole.value
                else exposure_by_name(exposures, exposure_select.value)
            )
            plot, _ = _make_visit_plot(
                visit_id, start, exposures, data, width=nea_width.value,
                height=nea_height.value, exposure=exposure,
            )
            _show_bokeh(nea_out, plot)
            nea_status.value = ""
        except Exception:
            nea_status.value = error_html()

    nea_button.on_click(draw_nea)

    # --- Jitter tab ---
    ma_override = widgets.BoundedIntText(
        description="MA table override (0 = use MAST)", value=0, min=0, max=9999,
        style=style,
    )
    resultant_select = widgets.Dropdown(
        description="Highlight resultant", options=[("None", -1)], value=-1,
        style=style, layout=widgets.Layout(width="480px"),
    )
    jitter_sources = widgets.SelectMultiple(
        description="Sources", options=["FACE"], value=("FACE",),
        rows=10, style=style,
    )
    jitter_units = widgets.RadioButtons(
        description="Units", options=("mas", "pixels"), value="mas",
        disabled=True, style=style,
    )
    jitter_source_note = widgets.HTML()
    jitter_width = widgets.BoundedIntText(
        description="Width (px)", value=800, min=200, max=5000, style=style,
        layout=widgets.Layout(width="170px"),
    )
    jitter_height = widgets.BoundedIntText(
        description="Height (px)", value=500, min=200, max=5000, style=style,
        layout=widgets.Layout(width="170px"),
    )
    jitter_button = button("Draw jitter plot", "primary", disabled=True)
    jitter_status = status_box()
    jitter_out = widgets.Output()

    def jitter_selection_changed(change):
        selected = change["new"]
        added = set(selected) - set(change["old"])
        if "FACE" in selected and len(selected) > 1:
            jitter_sources.value = ("FACE",) if "FACE" in added else tuple(
                source for source in selected if source != "FACE"
            )
            return
        if not state["busy"]:
            state["jitter_drawn"] = False
            _show_bokeh(jitter_out, None)
        is_face = "FACE" in selected or not selected
        jitter_units.disabled = is_face
        if is_face:
            jitter_units.value = "mas"

    def units_changed(change):
        if not state["busy"] and state["jitter_drawn"]:
            draw_jitter()

    jitter_sources.observe(jitter_selection_changed, "value")
    jitter_units.observe(units_changed, "value")

    def refresh_jitter_sources(exposure):
        stars = exposure.get("guide_stars")
        available = [
            detector for detector in JITTER_SOURCES[1:]
            if stars and stars.get(detector, "").strip()
            and not stars[detector].strip().upper().startswith("PGS")
        ]
        previous = jitter_sources.value
        jitter_sources.options = ["FACE", *available]
        selected = tuple(source for source in previous if source in jitter_sources.options)
        jitter_sources.value = selected or ("FACE",)
        missing = [
            detector for detector in JITTER_SOURCES[1:]
            if not stars or not stars.get(detector, "").strip()
        ]
        jitter_source_note.value = (
            f"Guide-star ID unavailable for {len(missing)} detector(s); "
            "they are excluded. Reload from MAST to obtain IDs."
            if missing else ""
        )

    def refresh_resultants():
        """Look up the exposure's resultant timing from its MA table in CRDS."""
        state["resultants"] = []
        resultant_select.options = [("None", -1)]
        resultant_select.value = -1
        if state["telemetry"] is None or not exposure_select.value:
            return
        try:
            _, _, exposures, _ = current()
            exposure = exposure_by_name(exposures, exposure_select.value)
            number = ma_override.value or exposure.get("ma_table_number")
            if number is None:
                jitter_status.value = (
                    "No MA table number for this exposure, so resultants are "
                    "unavailable. Enter one in the override field."
                )
                return
            table = get_ma_table(number, exposure["expstart"])
            state["resultants"] = resultant_intervals(
                table, exposure["expstart"], exposure["expend"]
            )
            resultant_select.options = [("None", -1)] + [
                (resultant_label(item), i) for i, item in enumerate(state["resultants"])
            ]
            resultant_select.value = -1
            jitter_status.value = (
                f"MA table {number}: {len(state['resultants'])} resultants "
                f"in this exposure ({escape(table['reference'])})."
            )
        except Exception:
            jitter_status.value = error_html()

    def draw_jitter(*_):
        try:
            visit_id, _, exposures, data = current()
            if not exposure_select.value:
                raise ValueError("Select an exposure.")
            exposure = exposure_by_name(exposures, exposure_select.value)
            index = resultant_select.value
            resultant = state["resultants"][index] if index >= 0 else None
            _show_bokeh(jitter_out, make_jitter_plot(
                data, list(jitter_sources.value), exposure=exposure,
                width=jitter_width.value, height=jitter_height.value,
                resultant=resultant,
                title=f"Jitter - {visit_id} - {exposure['name']}",
                units=jitter_units.value,
            ))
            state["jitter_drawn"] = True
        except Exception:
            state["jitter_drawn"] = False
            _show_bokeh(jitter_out, None)
            jitter_status.value = error_html()

    def jitter_exposure_changed(_):
        if state["busy"]:
            return
        state["jitter_drawn"] = False
        _show_bokeh(jitter_out, None)
        _, _, exposures, _ = current()
        refresh_jitter_sources(exposure_by_name(exposures, exposure_select.value))
        refresh_resultants()

    def resultant_changed(_):
        if not state["busy"] and state["jitter_drawn"]:
            draw_jitter()

    exposure_select.observe(jitter_exposure_changed, "value")
    ma_override.observe(jitter_exposure_changed, "value")
    resultant_select.observe(resultant_changed, "value")
    jitter_button.on_click(draw_jitter)

    # --- Guide window tab ---
    gw_scale = widgets.IntSlider(
        description="Pixel scale", min=2, max=24, value=8, continuous_update=False,
        style=style, layout=widgets.Layout(width="500px"),
    )
    gw_frame = widgets.IntSlider(
        description="Frame index", min=0, max=0, value=0, continuous_update=False,
        style=style, layout=widgets.Layout(width="700px"),
    )
    gw_step = widgets.BoundedIntText(
        description="Step (frames)", value=1, min=1, max=100000, style=style,
        layout=widgets.Layout(width="170px"),
    )
    gw_back = widgets.Button(description="\u25c0", tooltip="Step back")
    gw_forward = widgets.Button(description="\u25b6", tooltip="Step forward")

    def step(direction):
        gw_frame.value = min(
            max(gw_frame.value + direction * gw_step.value, gw_frame.min), gw_frame.max
        )

    gw_back.on_click(lambda _: step(-1))
    gw_forward.on_click(lambda _: step(1))
    gw_button = button("Load guide windows", "primary", disabled=True)
    product_directory = text_input("ASDF destination", "Existing directory for selected exposure products")
    save_products_button = button("Save GW and FACE ASDF files", disabled=True)
    product_status = status_box()
    movie_fps = widgets.BoundedFloatText(
        description="Movie FPS", value=5.0, min=0.1, max=60.0, style=style,
        layout=widgets.Layout(width="170px"),
    )
    movie_name = widgets.Text(
        description="Movie file", value="guide_windows.mp4", style=style,
        layout=widgets.Layout(width="320px"),
    )
    movie_button = button("Make GW Movie", "", disabled=True)
    movie_progress = widgets.IntProgress(
        description="Movie", min=0, max=1, value=0, style=style,
        layout=widgets.Layout(width="400px", display="none"),
    )
    gw_status = status_box()
    gw_out = widgets.Output()
    movie_status = status_box()

    def make_movie(*_):
        movie_button.disabled = True
        movie_progress.value = 0
        movie_progress.layout.display = ""
        movie_status.value = "Rendering movie..."

        def advance(done, total):
            movie_progress.max = total
            movie_progress.value = done

        try:
            _, _, _, data = current()
            path = os.path.abspath(os.path.expanduser(movie_name.value.strip()))
            if not movie_name.value.strip():
                raise ValueError("Enter a movie filename.")
            make_gw_grid_movie(
                state["windows"], data, path, fps=movie_fps.value, progress=advance
            )
            movie_status.value = f"Saved <b>{escape(path)}</b>"
        except Exception:
            movie_status.value = error_html()
        finally:
            movie_button.disabled = state["windows"] is None

    movie_button.on_click(make_movie)

    def draw_gw(*_):
        if state["windows"] is None or state["busy"]:
            return
        try:
            _, _, _, data = current()
            grid = GWGrid(state["windows"], data, scale=gw_scale.value)
            grid.set_frame(gw_frame.value)
            state["gw_grid"] = grid
            state["gw_handle"] = _show_bokeh(gw_out, grid.layout, notebook_handle=True)
        except Exception:
            gw_status.value = error_html()

    def update_gw_frame(_):
        if state["busy"] or state["gw_grid"] is None:
            return
        try:
            state["gw_grid"].set_frame(gw_frame.value)
            if state["gw_handle"] is None:
                raise RuntimeError("The Bokeh notebook display handle is unavailable.")
            push_notebook(handle=state["gw_handle"])
        except Exception:
            gw_status.value = error_html()

    def load_gw(*_):
        gw_button.disabled = True
        try:
            visit_id, _, exposures, _ = current()
            exposure = exposure_by_name(exposures, exposure_select.value)
            provider = state["providers"].get(visit_id)
            if provider is None:
                provider = state["providers"][visit_id] = GWProvider(
                    visit_id, selected_env(), gw_folder_input.value.strip() or None
                )
            gw_status.value = "Loading guide windows..."
            windows, errors = provider.windows(exposure)
            state["windows"] = windows
            n_frames = max((len(w["times"]) for w in windows.values() if w), default=0)
            tall = any(w and w["frames"].shape[1] >= 64 for w in windows.values())
            state["busy"] = True
            gw_scale.value = 3 if tall else 10
            gw_frame.max = max(n_frames - 1, 0)
            gw_frame.value = 0
            state["busy"] = False
            draw_gw()
            movie_button.disabled = not any(w for w in windows.values())
            save_products_button.disabled = not any(w for w in windows.values())
            found = sum(w is not None for w in windows.values())
            notes = "".join(f"<li>{escape(d)}: {escape(e)}</li>" for d, e in errors.items())
            gw_status.value = (
                f"{found}/18 detectors have guide window frames in "
                f"<b>{escape(exposure['name'])}</b> ({n_frames} frames max)."
                f"<ul>{notes}</ul>"
            )
        except Exception:
            state["busy"] = False
            gw_status.value = error_html()
        finally:
            gw_button.disabled = False

    def gw_exposure_changed(_):
        if state["busy"]:
            return
        state["windows"] = None
        state["gw_grid"] = state["gw_handle"] = None
        movie_button.disabled = True
        save_products_button.disabled = True
        movie_status.value = ""
        product_status.value = ""
        gw_status.value = ""
        _show_bokeh(gw_out, None)

    def save_products(_):
        try:
            if not product_directory.value.strip():
                raise ValueError("Select an ASDF destination directory.")
            visit_id, _, exposures, _ = current()
            exposure = exposure_by_name(exposures, exposure_select.value)
            names = state["providers"][visit_id].save_products(
                exposure, state["windows"], product_directory.value.strip()
            )
            product_status.value = f"Saved {len(names)} ASDF files."
        except Exception:
            product_status.value = error_html()

    gw_button.on_click(load_gw)
    save_products_button.on_click(save_products)
    exposure_select.observe(gw_exposure_changed, "value")
    exposure_select.observe(lambda _: show_header(), "value")
    gw_scale.observe(draw_gw, "value")
    gw_frame.observe(update_gw_frame, "value")

    # --- Table and export tab ---
    ih_html = widgets.HTML("Not calculated")

    def file_controls(label, default):
        name = text_input(label, "Output filename on the kernel filesystem", default)
        save = button("Save", disabled=True)
        overwrite = widgets.Checkbox(description="Overwrite", value=False, indent=False)
        return name, save, overwrite, status_box()

    csv_controls = file_controls("Telemetry CSV", "guiding_telemetry.csv")
    ih_controls = file_controls("IH table CSV", "inertial_hold.csv")
    timing_controls = file_controls("Timing JSON", "visit_timing.json")

    def save_output(controls, payload):
        name, _, overwrite, status = controls
        try:
            if not name.value.strip():
                raise ValueError("Enter an output filename.")
            path = Path(name.value.strip()).expanduser()
            payload(path, "w" if overwrite.value else "x")
        except (OSError, ValueError) as exc:
            status.value = f"Could not save: {escape(str(exc))}"
        else:
            status.value = f"Saved {escape(str(path.resolve()))}"

    csv_controls[1].on_click(lambda _: save_output(
        csv_controls,
        lambda path, mode: state["telemetry"].to_csv(path, index=False, mode=mode),
    ))
    ih_controls[1].on_click(lambda _: save_output(
        ih_controls,
        lambda path, mode: state["ih"].to_csv(path, index=False, mode=mode),
    ))

    def write_timing(path, mode):
        payloads = [visit_timing_data(*meta) for meta in state["loaded"].values()]
        payload = {"visits": payloads} if "," in visit_input.value else payloads[0]
        with path.open(mode) as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")

    timing_controls[1].on_click(lambda _: save_output(timing_controls, write_timing))

    def show_ih_results(results):
        table = results.copy()
        table["ih_seconds"] = [
            "Unavailable" if pd.isna(v) else f"{v:.3f}" for v in table["ih_seconds"]
        ]
        for column in ("ih_start", "ih_end", "exposure_start", "exposure_end"):
            table[column] = [
                "Unavailable" if pd.isna(v)
                else pd.Timestamp(v).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                for v in table[column]
            ]
            table = table.rename(columns={column: f"{column} (UTC)"})
        ih_html.value = table.to_html(index=False, escape=True)

    # --- Loading ---
    action_buttons = (
        nea_button, jitter_button, gw_button,
        csv_controls[1], ih_controls[1], timing_controls[1],
    )

    def clear_results(text=""):
        state["busy"] = True
        for provider in state["providers"].values():
            provider.close()
        state.update(
            telemetry=None, loaded={}, ih=None, providers={}, windows=None,
            resultants=[], jitter_drawn=False, busy=True,
            gw_grid=None, gw_handle=None,
        )
        # Drop cached CRDS tables and collect old plot/telemetry objects.
        _MA_TABLE_CACHE.clear()
        gc.collect()
        for out in (nea_out, jitter_out, gw_out):
            _show_bokeh(out, None)
        for box in (nea_status, jitter_status, gw_status):
            box.value = ""
        header.value = ""
        movie_button.disabled = True
        save_products_button.disabled = True
        movie_status.value = ""
        product_status.value = ""
        movie_progress.value = 0
        movie_progress.layout.display = "none"
        jitter_source_note.value = ""
        jitter_sources.options = ["FACE"]
        jitter_sources.value = ("FACE",)
        resultant_select.options = [("None", -1)]
        for controls in (csv_controls, ih_controls, timing_controls):
            controls[3].value = ""
        log_lines.clear()
        log_box.value = ""
        ih_html.value = "Not calculated"
        visit_select.options = []
        visit_select.layout.display = "none"
        exposure_select.options = []
        state["busy"] = False
        for each in action_buttons:
            each.disabled = True
        load_status.value = text

    def show_header(*_):
        if state["telemetry"] is None or visit_select.value not in state["loaded"]:
            return
        visit_id, start, exposures = state["loaded"][visit_select.value]
        _, _, _, data = current()
        exposure = next(
            (e for e in exposures if e["name"] == exposure_select.value), None
        )
        header.value = _cards_html(
            get_visit_summary(visit_id, start, exposures, data, exposure)
        )

    def populate_exposures(*_):
        if state["telemetry"] is None or visit_select.value not in state["loaded"]:
            return
        visit_id, start, exposures = state["loaded"][visit_select.value]
        names = [item["name"] for item in exposures]
        state["busy"] = True
        exposure_select.options = names
        exposure_select.value = names[0]
        state["busy"] = False
        state.update(windows=None, jitter_drawn=False)
        state["gw_grid"] = state["gw_handle"] = None
        movie_button.disabled = True
        save_products_button.disabled = True
        movie_status.value = product_status.value = gw_status.value = ""
        for out in (nea_out, jitter_out, gw_out):
            _show_bokeh(out, None)
        refresh_jitter_sources(exposures[0])
        refresh_resultants()
        _, _, _, data = current()
        show_header()

    visit_select.observe(populate_exposures, "value")

    def load_visit(_):
        clear_results()
        load_button.disabled = True
        load_status.value = "Loading visit metadata and telemetry..."
        try:
            if "," in visit_input.value:
                data, results, metadata = get_batch_telemetry(
                    visit_input.value, selected_env(), return_metadata=True,
                    telemetry_csv=telemetry_input.value.strip() or None,
                    timing_json=timing_input.value.strip() or None,
                )
            else:
                visit_id = _validate_visit_id(visit_input.value)
                start, exposures = get_visit_data(
                    visit_id, selected_env(),
                    timing_json=timing_input.value.strip() or None,
                )
                data = get_telemetry_data(
                    visit_id, start, _telemetry_end(exposures), selected_env(),
                    telemetry_csv=telemetry_input.value.strip() or None,
                )
                results = get_ih_results(start, exposures, data)
                metadata = {visit_id: (visit_id, start, exposures)}
            for visit_id, (_, _, exposures) in metadata.items():
                provider = state["providers"][visit_id] = GWProvider(
                    visit_id, selected_env(), gw_folder_input.value.strip() or None
                )
                if not timing_input.value.strip():
                    logger.info("Loading guide-star IDs for visit %s...", visit_id)
                    for exposure in exposures:
                        exposure["guide_stars"] = provider.guide_stars(exposure)
            state.update(telemetry=data, loaded=metadata, ih=results)
            show_ih_results(results)
            state["busy"] = True
            visit_select.options = list(metadata)
            state["busy"] = False
            visit_select.layout.display = "" if len(metadata) > 1 else "none"
            visit_select.value = next(iter(metadata))
            populate_exposures()
            for each in action_buttons:
                each.disabled = False
            load_status.value = (
                f"Loaded {len(metadata)} visit(s), {len(data):,} telemetry timestamps."
            )
        except Exception:
            clear_results(error_html("Could not load the visit:"))
        finally:
            load_button.disabled = False

    def inputs_changed(_):
        if state["telemetry"] is not None:
            clear_results("Inputs changed; click Load visit.")

    def timing_changed(change):
        timing_status.value = ""
        path = change["new"].strip()
        if not path:
            return
        try:
            with Path(path).expanduser().open(encoding="utf-8") as stream:
                ids = _timing_visit_ids(json.load(stream))
        except (OSError, UnicodeError, ValueError) as exc:
            timing_status.value = f"Could not read visit IDs: {escape(str(exc))}"
            return
        visit_input.value = ", ".join(ids)

    load_button.on_click(load_visit)
    reset_button.on_click(lambda _: clear_results("Dashboard reset."))
    for field in (visit_input, telemetry_input, timing_input, env_input, gw_folder_input):
        field.observe(inputs_changed, "value")
    timing_input.observe(timing_changed, "value")

    controls = widgets.VBox(
        [
            widgets.HTML("<h3>Visit</h3>"), visit_input, path_picker(telemetry_input),
            path_picker(timing_input), timing_status, path_picker(gw_folder_input, directory=True),
            path_picker(env_input), widgets.HBox([load_button, reset_button]), load_status,
        ],
        layout=widgets.Layout(width="100%"),
    )
    tabs = widgets.Tab(children=[
        widgets.VBox([
            widgets.HBox([nea_whole, nea_width, nea_height, nea_button]),
            nea_status, nea_out,
        ]),
        widgets.VBox([
            widgets.HBox([
                widgets.VBox([ma_override, resultant_select]),
                jitter_sources,
                widgets.VBox([
                    jitter_units,
                    jitter_width, jitter_height, jitter_button,
                ]),
            ]),
            jitter_source_note, jitter_status, jitter_out,
        ]),
        widgets.VBox([
            widgets.HTML(
                "<i>Retrieving guide window data may take a few moments.</i>"
            ),
            widgets.HBox([gw_button]),
            path_picker(product_directory, directory=True),
            save_products_button, product_status,
            gw_scale, widgets.HBox([gw_back, gw_frame, gw_forward, gw_step]),
            widgets.HBox([movie_fps, movie_name, movie_button, movie_progress]),
            movie_status,
            gw_status, gw_out,
        ]),
        widgets.VBox([
            widgets.HTML("<h4>Time since inertial hold per exposure (seconds)</h4>"),
            ih_html,
        ]),
        widgets.VBox([
            widgets.HTML("<h4>Exports</h4>"),
            widgets.HBox(list(csv_controls[:3])), csv_controls[3],
            widgets.HBox(list(ih_controls[:3])), ih_controls[3],
            widgets.HBox(list(timing_controls[:3])), timing_controls[3],
        ]),
    ])
    for i, title in enumerate(("NEA", "Jitter", "Guide Windows", "Inertial Hold Report", "Export Results")):
        tabs.set_title(i, title)
    log_box = widgets.HTML(layout=widgets.Layout(width="98%"))
    log_lines = []

    class _WidgetLogHandler(logging.Handler):
        def emit(self, record):
            log_lines.append(self.format(record))
            del log_lines[:-200]
            log_box.value = (
                '<div style="max-height:160px;overflow-y:auto;background:#000;color:#fff;'
                'border:1px solid #444;padding:4px 8px;font:12px monospace;'
                'white-space:pre-wrap">' + escape("\n".join(log_lines)) + "</div>"
            )

    # Replace the handler from any earlier dashboard so messages are not duplicated.
    for old in [h for h in logger.handlers if getattr(h, "_dashboard_log", False)]:
        logger.removeHandler(old)
    handler = _WidgetLogHandler()
    handler._dashboard_log = True
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S")
    )
    logger.addHandler(handler)

    return widgets.VBox([
        widgets.HTML("<h2>Guiding dashboard</h2>"),
        widgets.HTML("<b>Log</b>"), log_box,
        controls, header, visit_select, exposure_select, tabs,
    ])
