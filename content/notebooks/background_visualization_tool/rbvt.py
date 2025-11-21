import numpy as np
import pandas as pd

from bokeh.layouts import row, column, Spacer
from bokeh.models import (
    Slider, CheckboxGroup, Div, ColumnDataSource, Button,
    TextInput, Select, InlineStyleSheet, BoxZoomTool, Legend, LegendItem,
    Range1d, LabelSet, Label, Span
)
from bokeh.plotting import figure
from bokeh.events import ButtonClick

from rbt import background


def plot_rbt(doc):
    # ---------- Plot text styling ----------
    title_font = "28pt"
    axis_label_font = "26pt"
    major_label_font = "24pt"
    legend_font = "16pt"

    def style_plot(p):
        p.title.text_font_size = title_font
        p.xaxis.axis_label_text_font_size = axis_label_font
        p.yaxis.axis_label_text_font_size = axis_label_font
        p.xaxis.major_label_text_font_size = major_label_font
        p.yaxis.major_label_text_font_size = major_label_font
        if p.legend:
            p.legend.label_text_font_size = legend_font
        return p

    # ---------- Only enlarge slider/input titles ----------
    TITLE_ONLY_CSS = """
    .bk-root .bk-input-group > label {
      font-size: 28pt !important;
      line-height: 1.25 !important;
    }
    """
    title_sheet = InlineStyleSheet(css=TITLE_ONLY_CSS)

    # ---------- Filters ----------
    overlay_filters = {
        "F062": 0.62, "F087": 0.87, "F106": 1.06, "F129": 1.29,
        "F146": 1.46, "F158": 1.58, "F184": 1.84, "F213": 2.13,
        "Prism": 1.25, "Grism": 1.42
    }
    color_gradient = ["navy", "blue", "dodgerblue", "green", "orange", "red", "firebrick", "darkred", "gray", "pink"]
    default_filter = "F184"

    # ---------- Initial values ----------
    ra, dec, thresh, thisday = 180, 0, 1.1, 100
    wavelength = overlay_filters[default_filter]

    bkg = background(ra, dec, wavelength, thresh)
    cal = bkg.bkg_data['calendar']
    wave_array = bkg.bkg_data['wave_array']
    bkg.make_bathtub(wavelength)
    bathtub = bkg.bathtub

    if thisday not in cal and len(cal) > 0:
        thisday = int(cal[len(cal) // 2])
    elif len(cal) == 0:
        thisday = 0

    # ---------- Gap helpers ----------
    def _gap_spans(days):
        """Internal gaps only (missing integer days between available days)."""
        d = np.asarray(days, dtype=float)
        if d.size < 2:
            return []
        spans = []
        for i in range(d.size - 1):
            if (d[i+1] - d[i]) > 1:
                left = d[i] + 0.5
                right = d[i+1] - 0.5
                if right > left:
                    spans.append((left, right))
        return spans

    def _edge_spans(days):
        """Add edge 'not visible' spans before first and after last visible day."""
        d = np.asarray(days, dtype=float)
        spans = []
        if d.size == 0:
            spans.append((0.0, 365.0))
            return spans
        first_day = float(np.min(d))
        last_day  = float(np.max(d))
        if first_day > 0:
            spans.append((0.0, first_day - 0.5))
        if last_day < 365:
            spans.append((last_day + 0.5, 365.0))
        return [(L, R) for (L, R) in spans if (R > L)]

    def _insert_nans_for_gaps(x, y):
        x = np.asarray(x, float); y = np.asarray(y, float)
        if x.size == 0:
            return x, y
        X = [x[0]]; Y = [y[0]]
        for i in range(1, len(x)):
            if (x[i] - x[i-1]) > 1:
                X.append(np.nan); Y.append(np.nan)
            X.append(x[i]); Y.append(y[i])
        return np.array(X), np.array(Y)

    def _gap_segments(x, y):
        x = np.asarray(x, float); y = np.asarray(y, float)
        xs0, ys0, xs1, ys1 = [], [], [], []
        for i in range(len(x)-1):
            if (x[i+1] - x[i]) > 1 and np.isfinite(y[i]) and np.isfinite(y[i+1]):
                xs0.append(x[i]);   ys0.append(y[i])
                xs1.append(x[i+1]); ys1.append(y[i+1])
        return dict(x0=xs0, y0=ys0, x1=xs1, y1=ys1)

    # ---------- Data sources ----------
    source_bathtub = ColumnDataSource(data=dict(
        day=cal,
        total=bathtub['total_thiswave'],
        zodi=bathtub['zodi_thiswave'],
        thermal=[bathtub['thermal_thiswave']] * len(cal),
        nonzodi=[bathtub['nonzodi_thiswave']] * len(cal),
    ))
    source_bathtub_plot = ColumnDataSource(data=dict(
        day_total=[], total=[], day_zodi=[], zodi=[],
        day_therm=[], thermal=[], day_ism=[], nonzodi=[]
    ))
    gap_seg_total   = ColumnDataSource(data=dict(x0=[], y0=[], x1=[], y1=[]))
    gap_seg_zodi    = ColumnDataSource(data=dict(x0=[], y0=[], x1=[], y1=[]))
    gap_seg_thermal = ColumnDataSource(data=dict(x0=[], y0=[], x1=[], y1=[]))
    gap_seg_ism     = ColumnDataSource(data=dict(x0=[], y0=[], x1=[], y1=[]))

    shade_source = ColumnDataSource(data=dict(left=[], right=[], bottom=[], top=[]))
    shade_label_source = ColumnDataSource(data=dict(x=[], y=[], text=[]))

    day_idx = np.where(cal == thisday)[0][0] if thisday in cal else 0
    source_spectrum = ColumnDataSource(data=dict(
        wave=wave_array,
        ism=bkg.bkg_data['nonzodi_bg'],
        zodi=bkg.bkg_data['zodi_bg'][day_idx],
        thermal=bkg.bkg_data['thermal_bg'],
        total=bkg.bkg_data['total_bg'][day_idx],
    ))

    # ---------- Sizing for 2×2 layout ----------
    PANEL_W = 965       # width for controls & all three plots (change this to grow/shrink everything)
    PANEL_H = 520

    # ---------- Bathtub plot ----------
    plot_bathtub = figure(
        title="Background vs Calendar Day",
        x_axis_label="Day of Year", y_axis_label="Background (MJy/sr)",
        width=PANEL_W, height=PANEL_H, y_axis_type="log",
        x_range=Range1d(0, 366),
        tools="pan,box_zoom,reset,save,hover"
    )
    plot_bathtub.y_range.start = 3e-2
    plot_bathtub.y_range.end = 10.2

    # translucent shading
    shade_quad = plot_bathtub.quad(
        left='left', right='right', bottom='bottom', top='top',
        source=shade_source, fill_color="lightgray", fill_alpha=0.5, line_color=None
    )
    shade_quad.level = "underlay"

    # labels for gaps/shaded regions
    gap_labels = LabelSet(
        x='x', y='y', text='text', source=shade_label_source,
        text_align='center', text_baseline='middle', text_font_size='14pt',
        text_color='gray'
    )
    plot_bathtub.add_layout(gap_labels)

    # base lines
    bathtub_total   = plot_bathtub.line('day_total', 'total',   source=source_bathtub_plot, line_color="black",  line_width=6)
    bathtub_zodi    = plot_bathtub.line('day_zodi',  'zodi',    source=source_bathtub_plot, line_color="orange", line_width=6)
    bathtub_thermal = plot_bathtub.line('day_therm', 'thermal', source=source_bathtub_plot, line_color="red",    line_width=6)
    bathtub_ism     = plot_bathtub.line('day_ism',   'nonzodi', source=source_bathtub_plot, line_color="blue",   line_width=6)

    dash_seg = {
        'total':   plot_bathtub.segment('x0','y0','x1','y1', source=gap_seg_total,   line_dash='dashed', line_alpha=0.7, line_color="black",  line_width=2),
        'zodi':    plot_bathtub.segment('x0','y0','x1','y1', source=gap_seg_zodi,    line_dash='dashed', line_alpha=0.7, line_color="orange", line_width=2),
        'thermal': plot_bathtub.segment('x0','y0','x1','y1', source=gap_seg_thermal, line_dash='dashed', line_alpha=0.7, line_color="red",    line_width=2),
        'nonzodi': plot_bathtub.segment('x0','y0','x1','y1', source=gap_seg_ism,     line_dash='dashed', line_alpha=0.7, line_color="blue",   line_width=2),
    }

    # overlay filter totals
    overlay_sources_raw, overlay_sources_plot, overlay_lines, overlay_gap_sources, overlay_gap_renders = {}, {}, {}, {}, {}
    for (filt, wave_f), color in zip(overlay_filters.items(), color_gradient):
        bkg.make_bathtub(wave_f)
        day_raw = cal
        y_raw   = bkg.bathtub['total_thiswave']
        x_p, y_p = _insert_nans_for_gaps(day_raw, y_raw)
        overlay_sources_raw[filt]  = ColumnDataSource(data=dict(day=day_raw, total=y_raw))
        overlay_sources_plot[filt] = ColumnDataSource(data=dict(day=x_p,   total=y_p))
        overlay_lines[filt] = plot_bathtub.line('day', 'total', source=overlay_sources_plot[filt], line_width=4, color=color)
        overlay_gap_sources[filt] = ColumnDataSource(_gap_segments(day_raw, y_raw))
        overlay_gap_renders[filt] = plot_bathtub.segment('x0','y0','x1','y1',
                                                         source=overlay_gap_sources[filt],
                                                         line_dash='dashed', line_alpha=0.6,
                                                         line_color=color, line_width=2)

    # legend and style
    legend_bath = Legend(items=[], location="top_left", click_policy="hide", orientation="horizontal")
    plot_bathtub.add_layout(legend_bath)
    plot_bathtub = style_plot(plot_bathtub)

    # --- single-filter badge (top-right) ---
    selected_filter_label = Label(
        x=365, y=plot_bathtub.y_range.end, x_units="data", y_units="data",
        text=f"Optical Element: {default_filter}",
        text_font_size="16pt", text_color="gray",
        background_fill_color="white", background_fill_alpha=0.6,
        border_line_alpha=0, text_align="right", text_baseline="top"
    )
    plot_bathtub.add_layout(selected_filter_label)

    def _reposition_filter_label():
        xr = plot_bathtub.x_range
        yr = plot_bathtub.y_range
        x_pad = 0.8
        x_pos = xr.end - x_pad
        y_start = max(float(yr.start), 1e-30)
        y_end   = float(yr.end)
        frac_from_bottom = 0.98
        y_pos = 10 ** (np.log10(y_start) + frac_from_bottom * (np.log10(y_end) - np.log10(y_start)))
        selected_filter_label.x = x_pos
        selected_filter_label.y = y_pos

    plot_bathtub.x_range.on_change('start', lambda a,o,n: _reposition_filter_label())
    plot_bathtub.x_range.on_change('end',   lambda a,o,n: _reposition_filter_label())
    plot_bathtub.y_range.on_change('start', lambda a,o,n: _reposition_filter_label())
    plot_bathtub.y_range.on_change('end',   lambda a,o,n: _reposition_filter_label())

    # --- threshold/min horizontal lines + label (top-right of threshold line) ---
    min_line = Span(location=bathtub['themin'], dimension='width', line_color='black', line_dash='dashed', line_width=2)
    thr_line = Span(location=bathtub['themin'] * thresh, dimension='width', line_color='black', line_dash='dotted', line_width=2)
    plot_bathtub.add_layout(min_line)
    plot_bathtub.add_layout(thr_line)

    good_days_label = Label(
        x=362, y=bathtub['themin']*thresh, x_units="data", y_units="data",
        text=f"{bathtub['good_days']} good days for threshold = {thresh:.2f}",
        text_font_size="14pt", text_color="gray",
        background_fill_color="white", background_fill_alpha=0.7,
        text_align="right", text_baseline="bottom"
    )
    plot_bathtub.add_layout(good_days_label)

    def _reposition_good_days_label():
        xr = plot_bathtub.x_range
        good_days_label.x = xr.end - 3.0  # inset from the right

    # ---------- VIOLIN PLOT ----------
    plot_violin = figure(
        title="Background Distribution by Optical Element",
        x_axis_label="Wavelength (μm)", y_axis_label="Background (MJy/sr)",
        width=PANEL_W, height=PANEL_H, y_axis_type="linear",
        x_range=(0.5, 2.5), y_range=Range1d(0.1, 2.5),
        tools="pan,box_zoom,reset,save,hover"
    )
    bz = plot_violin.select_one(BoxZoomTool) or BoxZoomTool()
    if bz not in plot_violin.tools:
        plot_violin.add_tools(bz)
    plot_violin.toolbar.active_drag = bz

    violin_sources, box_sources, whisker_sources, cap_sources, median_sources = {}, {}, {}, {}, {}
    violin_patch_rend, whisker_rend, quad_rend, cap_rend, median_rend = {}, {}, {}, {}, {}
    VIOLIN_HALFWIDTH = 0.045
    BOX_HALFWIDTH    = 0.018
    CAP_HALFWIDTH    = 0.014

    def _make_violin_source(total_bg_matrix, wave_arr, center_wave, halfwidth=VIOLIN_HALFWIDTH):
        idx = int(np.argmin(np.abs(wave_arr - center_wave)))
        samples = np.asarray(total_bg_matrix[:, idx]).ravel()
        samples = samples[np.isfinite(samples) & (samples > 0)]
        if samples.size < 5:
            if samples.size == 0:
                y = np.array([1e-2, 1e-1])
            else:
                y = np.array([samples.min(), samples.max()])
            x = np.array([center_wave, center_wave])
            return dict(x=np.r_[x, x[::-1]], y=np.r_[y, y[::-1]]), (np.nan,)*5

        q0, q1, q2, q3, q4 = np.percentile(samples, [0, 25, 50, 75, 100])
        logs = np.log10(samples)
        ygrid = np.linspace(logs.min(), logs.max(), 200)
        std = logs.std()
        bw = 0.2 * std if std > 0 else 0.1
        diffs = (ygrid[:, None] - logs[None, :]) / bw
        kernel = np.exp(-0.5 * diffs**2) / (bw * np.sqrt(2 * np.pi))
        density = kernel.mean(axis=1)
        if density.max() > 0:
            density /= density.max()

        y_lin = 10 ** ygrid
        half = density * halfwidth
        x_left  = center_wave - half
        x_right = center_wave + half
        x = np.r_[x_left, x_right[::-1]]
        y = np.r_[y_lin,  y_lin[::-1]]
        return dict(x=x, y=y), (q0, q1, q2, q3, q4)

    for (filt, cw), color in zip(overlay_filters.items(), color_gradient):
        data_patch, (q0, q1, q2, q3, q4) = _make_violin_source(
            bkg.bkg_data['total_bg'], wave_array, cw, VIOLIN_HALFWIDTH
        )
        violin_sources[filt] = ColumnDataSource(data=data_patch)
        violin_patch_rend[filt] = plot_violin.patch(
            'x', 'y', source=violin_sources[filt],
            fill_alpha=0.35, line_color=color, fill_color=color
        )
        box_sources[filt] = ColumnDataSource(data=dict(
            left=[cw - BOX_HALFWIDTH], right=[cw + BOX_HALFWIDTH],
            bottom=[max(q1, 1e-9)], top=[max(q3, 1e-9)]
        ))
        quad_rend[filt] = plot_violin.quad(
            left='left', right='right', bottom='bottom', top='top',
            source=box_sources[filt], fill_alpha=0.35, fill_color="white",
            line_color=color, line_width=3
        )
        whisker_sources[filt] = ColumnDataSource(data=dict(
            x0=[cw], y0=[max(q0, 1e-9)], x1=[cw], y1=[max(q4, 1e-9)]
        ))
        whisker_rend[filt] = plot_violin.segment(
            'x0','y0','x1','y1', source=whisker_sources[filt],
            line_color=color, line_width=3
        )
        cap_sources[filt] = ColumnDataSource(data=dict(
            x0=[cw - CAP_HALFWIDTH, cw - CAP_HALFWIDTH],
            y0=[max(q0, 1e-9),       max(q4, 1e-9)],
            x1=[cw + CAP_HALFWIDTH, cw + CAP_HALFWIDTH],
            y1=[max(q0, 1e-9),       max(q4, 1e-9)],
        ))
        cap_rend[filt] = plot_violin.segment(
            'x0','y0','x1','y1', source=cap_sources[filt],
            line_color=color, line_width=3
        )
        median_sources[filt] = ColumnDataSource(data=dict(x=[cw], y=[max(q2, 1e-9)]))
        median_rend[filt] = plot_violin.scatter(
            'x','y', source=median_sources[filt],
            size=12, marker="circle", fill_color="white",
            line_color=color, line_width=3
        )

    legend_violin = Legend(items=[], location="top_right", click_policy="hide")
    plot_violin.add_layout(legend_violin)
    plot_violin = style_plot(plot_violin)

    # ---------- Spectrum plot ----------
    plot_spectrum = figure(
        title=f"Background Spectrum on Calendar Day {thisday}",
        x_axis_label="Wavelength (μm)", y_axis_label="Background (MJy/sr)",
        width=PANEL_W, height=PANEL_H, y_axis_type="log", x_range=(0.5, 2.5),
        tools="pan,box_zoom,reset,save,hover"
    )
    plot_spectrum.y_range.start = 1e-5
    plot_spectrum.y_range.end = 100

    spectrum_total   = plot_spectrum.line('wave', 'total',   source=source_spectrum, line_color="black",  line_width=6, legend_label="Total")
    spectrum_zodi    = plot_spectrum.line('wave', 'zodi',    source=source_spectrum, line_color="orange", line_width=6, legend_label="Zodi")
    spectrum_thermal = plot_spectrum.line('wave', 'thermal', source=source_spectrum, line_color="red",    line_width=6, legend_label="Thermal")
    spectrum_ism     = plot_spectrum.line('wave', 'ism',     source=source_spectrum, line_color="blue",   line_width=6, legend_label="ISM+CIB")

    not_visible_label = Label(
        x=(plot_spectrum.x_range.start + plot_spectrum.x_range.end)/2.0,
        y=10 ** ((np.log10(plot_spectrum.y_range.start) + np.log10(plot_spectrum.y_range.end))/2.0),
        x_units="data", y_units="data",
        text="Not visible",
        text_font_size="48pt", text_color="gray",
        text_align="center", text_baseline="middle",
        background_fill_color="white", background_fill_alpha=0.65,
        border_line_alpha=0,
        visible=False,
    )
    plot_spectrum.add_layout(not_visible_label)

    def _recenter_not_visible_label():
        x0, x1 = float(plot_spectrum.x_range.start), float(plot_spectrum.x_range.end)
        y0, y1 = float(plot_spectrum.y_range.start), float(plot_spectrum.y_range.end)
        not_visible_label.x = 0.5 * (x0 + x1)
        not_visible_label.y = 10 ** (0.5 * (np.log10(max(y0, 1e-30)) + np.log10(y1)))

    plot_spectrum.x_range.on_change('start', lambda a,o,n: _recenter_not_visible_label())
    plot_spectrum.x_range.on_change('end',   lambda a,o,n: _recenter_not_visible_label())
    plot_spectrum.y_range.on_change('start', lambda a,o,n: _recenter_not_visible_label())
    plot_spectrum.y_range.on_change('end',   lambda a,o,n: _recenter_not_visible_label())

    plot_spectrum.legend.location = "bottom_right"
    plot_spectrum.legend.click_policy = "hide"
    plot_spectrum.legend.ncols = 4
    plot_spectrum = style_plot(plot_spectrum)

    # ---------- Sliders ----------
    ra_slider     = Slider(title="RA (deg)", start=0, end=360, value=ra, step=0.1, show_value=True, format="0.0")
    dec_slider    = Slider(title="DEC (deg)", start=-90, end=90, value=dec, step=0.1, show_value=True, format="0.0")
    thresh_slider = Slider(title="Threshold (× min bkg)", start=1.0, end=2, value=thresh, step=0.01, show_value=True, format="0.00")
    day_slider    = Slider(title="Calendar Day", start=0, end=365, value=thisday, step=1, show_value=True, format="0")

    # ---------- Text inputs ----------
    ra_input     = TextInput(title="RA (deg) value", value=str(ra))
    dec_input    = TextInput(title="DEC (deg) value", value=str(dec))
    thresh_input = TextInput(title="Threshold value", value=str(thresh))
    day_input    = TextInput(title="Calendar Day value", value=str(thisday))

    _sync_guard = {'ra': False, 'dec': False, 'thresh': False, 'day': False}

    def _safe_float(s, default):
        try:
            return float(s)
        except Exception:
            return default

    def _parse_ra(s):
        v = _safe_float(s, None)
        if v is None or v < 0 or v > 360:
            return None
        return v

    def _parse_dec(s):
        v = _safe_float(s, None)
        if v is None or v < -90 or v > 90:
            return None
        return v

    def _parse_thresh(s):
        v = _safe_float(s, None)
        if v is None or v < 1.0 or v > 2.0:
            return None
        return v

    def _parse_day(s):
        try:
            v = int(float(s))
        except Exception:
            return None
        if 0 <= v <= 365:
            return v
        return None

    # ENTER/blur commit handlers (server-side)
    def _on_ra_commit(attr, old, new):
        if _sync_guard['ra']:
            return
        v = _parse_ra(new)
        if v is not None and not np.isclose(v, ra_slider.value):
            ra_slider.value = v
            update(None, None, None)

    def _on_dec_commit(attr, old, new):
        if _sync_guard['dec']:
            return
        v = _parse_dec(new)
        if v is not None and not np.isclose(v, dec_slider.value):
            dec_slider.value = v
            update(None, None, None)

    def _on_thresh_commit(attr, old, new):
        if _sync_guard['thresh']:
            return
        v = _parse_thresh(new)
        if v is not None and not np.isclose(v, thresh_slider.value):
            thresh_slider.value = v
            update(None, None, None)

    def _on_day_commit(attr, old, new):
        if _sync_guard['day']:
            return
        v = _parse_day(new)
        if v is not None and v != int(day_slider.value):
            day_slider.value = v
            update(None, None, None)

    ra_input.on_change('value', _on_ra_commit)
    dec_input.on_change('value', _on_dec_commit)
    thresh_input.on_change('value', _on_thresh_commit)
    day_input.on_change('value', _on_day_commit)

    def sync_inputs_from_sliders():
        _sync_guard['ra'] = True;     ra_input.value     = f"{ra_slider.value:.3f}"; _sync_guard['ra'] = False
        _sync_guard['dec'] = True;    dec_input.value    = f"{dec_slider.value:.3f}"; _sync_guard['dec'] = False
        _sync_guard['thresh'] = True; thresh_input.value = f"{thresh_slider.value:.3f}"; _sync_guard['thresh'] = False
        _sync_guard['day'] = True;    day_input.value    = f"{int(day_slider.value)}"; _sync_guard['day'] = False

    for s in [ra_slider, dec_slider, thresh_slider, day_slider]:
        s.on_change('value', lambda a,o,n: sync_inputs_from_sliders())

    # ---------- Controls ----------
    toggle_components = CheckboxGroup(labels=["Total", "Zodi", "Thermal", "ISM+CIB"], active=[0,1,2,3])
    show_all_filters  = CheckboxGroup(labels=["Show all elements"], active=[])
    single_filter     = Select(title="Single element", value=default_filter, options=list(overlay_filters.keys()))

    # ---------- Legend refreshers ----------
    def _refresh_bathtub_legend():
        items = []
        if bathtub_total.visible:   items.append(LegendItem(label="Total",   renderers=[bathtub_total]))
        if bathtub_zodi.visible:    items.append(LegendItem(label="Zodi",    renderers=[bathtub_zodi]))
        if bathtub_thermal.visible: items.append(LegendItem(label="Thermal", renderers=[bathtub_thermal]))
        if bathtub_ism.visible:     items.append(LegendItem(label="ISM+CIB", renderers=[bathtub_ism]))
        show_all = 0 in show_all_filters.active
        if show_all:
            for filt, r in overlay_lines.items():
                if r.visible:
                    items.append(LegendItem(label=filt, renderers=[r]))
        legend_bath.items = items
        legend_bath.ncols = max(1, len(items))

    def _refresh_violin_legend():
        items = []
        for f in overlay_filters:
            if violin_patch_rend[f].visible:
                items.append(LegendItem(label=f, renderers=[violin_patch_rend[f]]))
        legend_violin.items = items

    def _autoscale_violin_y():
        show_all = 0 in show_all_filters.active
        filters = list(overlay_filters.keys()) if show_all else [single_filter.value]
        ymin, ymax = np.inf, -np.inf
        for f in filters:
            if not violin_patch_rend[f].visible:
                continue
            d = whisker_sources[f].data
            if len(d.get('y0', [])):
                ymin = min(ymin, float(d['y0'][0]), float(d['y1'][0]))
                ymax = max(ymax, float(d['y0'][0]), float(d['y1'][0]))
            ypatch = np.asarray(violin_sources[f].data.get('y', []), float)
            if ypatch.size:
                ymin = min(ymin, np.nanmin(ypatch))
                ymax = max(ymax, np.nanmax(ypatch))
        if not np.isfinite(ymin) or not np.isfinite(ymax):
            return
        if np.isclose(ymin, ymax):
            pad = 0.1 * (ymin if ymin > 0 else 1.0)
            start = max(1e-9, ymin - pad)
            end   = ymax + pad
        else:
            span = ymax - ymin
            pad  = 0.12 * span
            start = max(1e-9, ymin - pad)
            end   = ymax + pad
        plot_violin.y_range.start = start
        plot_violin.y_range.end   = end

    # ---------- Update logic ----------
    LABEL_FRAC = 0.82

    def _recompute_shading(cal_new):
        """Shade both internal gaps AND edge invisible regions."""
        spans_internal = _gap_spans(cal_new)
        spans_edges    = _edge_spans(cal_new)
        spans = spans_internal + spans_edges
        if spans:
            L, R = zip(*spans)
            n = len(spans)
            y_start = float(plot_bathtub.y_range.start)
            y_end   = float(plot_bathtub.y_range.end)
            y_pos = 10 ** (np.log10(y_start) + LABEL_FRAC * (np.log10(y_end) - np.log10(y_start)))
            shade_source.data = dict(left=list(L), right=list(R), bottom=[y_start]*n, top=[y_end]*n)
            centers = [(l+r)/2.0 for l, r in spans]
            shade_label_source.data = dict(x=centers, y=[y_pos]*n, text=["Not visible"]*n)
        else:
            shade_source.data = dict(left=[], right=[], bottom=[], top=[])
            shade_label_source.data = dict(x=[], y=[], text=[])

    def update(attr, old, new):
        ra_val, dec_val = ra_slider.value, dec_slider.value
        thresh_val, day_val = thresh_slider.value, day_slider.value
        wav = overlay_filters[single_filter.value]

        bkg_new = background(ra_val, dec_val, wav, thresh_val)
        bkg_new.make_bathtub(wav)
        bathtub_new = bkg_new.bathtub
        cal_new = bkg_new.bkg_data['calendar']
        wave_array_new = bkg_new.bkg_data['wave_array']

        # Update base data
        source_bathtub.data = dict(
            day=cal_new,
            total=bathtub_new['total_thiswave'],
            zodi=bathtub_new['zodi_thiswave'],
            thermal=[bathtub_new['thermal_thiswave']] * len(cal_new),
            nonzodi=[bathtub_new['nonzodi_thiswave']] * len(cal_new),
        )
        _update_bathtub_plot_source_from_raw()

        # Update shading (internal + edges)
        _recompute_shading(cal_new)

        # Update threshold/min lines and label
        min_line.location = float(bathtub_new['themin'])
        thr_line.location = float(bathtub_new['themin'] * thresh_val)
        good_days_label.y = thr_line.location
        good_days_label.text = f"{bathtub_new['good_days']} good days for threshold = {thresh_val:.2f}"
        _reposition_good_days_label()

        # Spectrum visibility
        day_int = int(day_val)
        is_visible = (len(cal_new) > 0) and (day_int in set(map(int, cal_new.tolist())))

        if not is_visible:
            not_visible_label.visible = True
            spectrum_total.visible = False
            spectrum_zodi.visible = False
            spectrum_thermal.visible = False
            spectrum_ism.visible = False
            plot_spectrum.title.text = f"Background Spectrum on Calendar Day {day_int}"
            _recenter_not_visible_label()
        else:
            not_visible_label.visible = False
            spectrum_total.visible = True
            spectrum_zodi.visible = True
            spectrum_thermal.visible = True
            spectrum_ism.visible = True

            idx_candidates = np.where(np.asarray(cal_new, int) == day_int)[0]
            if idx_candidates.size:
                idx = int(idx_candidates[0])
                nearest_day = day_int
            else:
                idx = int(np.argmin(np.abs(cal_new - day_val))) if len(cal_new) else 0
                nearest_day = int(cal_new[idx]) if len(cal_new) else day_int

            source_spectrum.data = dict(
                wave=wave_array_new,
                ism=bkg_new.bkg_data['nonzodi_bg'],
                zodi=bkg_new.bkg_data['zodi_bg'][idx] if len(cal_new) else np.zeros_like(wave_array_new),
                thermal=bkg_new.bkg_data['thermal_bg'],
                total=bkg_new.bkg_data['total_bg'][idx] if len(cal_new) else np.zeros_like(wave_array_new),
            )
            plot_spectrum.title.text = f"Background Spectrum on Calendar Day {nearest_day}"
            _recenter_not_visible_label()

        # overlay per-filter
        for filt, wave_f in overlay_filters.items():
            bkg_new.make_bathtub(wave_f)
            day_raw = bkg_new.bkg_data['calendar']
            y_raw   = bkg_new.bathtub['total_thiswave']
            overlay_sources_raw[filt].data = dict(day=day_raw, total=y_raw)
            _update_overlay_plot_source_from_raw(filt)

        # violins refreshed + autoscale
        total_bg_matrix = bkg_new.bkg_data['total_bg']
        for filt, cw in overlay_filters.items():
            data_patch, (q0, q1, q2, q3, q4) = _make_violin_source(
                total_bg_matrix, wave_array_new, cw, VIOLIN_HALFWIDTH
            )
            violin_sources[filt].data = data_patch
            box_sources[filt].data = dict(
                left=[cw - BOX_HALFWIDTH], right=[cw + BOX_HALFWIDTH],
                bottom=[max(q1, 1e-9)], top=[max(q3, 1e-9)]
            )
            whisker_sources[filt].data = dict(
                x0=[cw], y0=[max(q0, 1e-9)], x1=[cw], y1=[max(q4, 1e-9)]
            )
            cap_sources[filt].data = dict(
                x0=[cw -  CAP_HALFWIDTH, cw - CAP_HALFWIDTH],
                y0=[max(q0, 1e-9),        max(q4, 1e-9)],
                x1=[cw +  CAP_HALFWIDTH, cw +  CAP_HALFWIDTH],
                y1=[max(q0, 1e-9),        max(q4, 1e-9)],
            )
            median_sources[filt].data = dict(x=[cw], y=[max(q2, 1e-9)])

        _refresh_bathtub_legend()
        _refresh_violin_legend()
        _autoscale_violin_y()
        _reposition_filter_label()
        _reposition_good_days_label()
        sync_inputs_from_sliders()

    # convert raw→plotted sources
    def _update_bathtub_plot_source_from_raw():
        D = source_bathtub.data
        x_tot, y_tot = _insert_nans_for_gaps(D['day'], np.asarray(D['total']))
        x_z,   y_z   = _insert_nans_for_gaps(D['day'], np.asarray(D['zodi']))
        x_t,   y_t   = _insert_nans_for_gaps(D['day'], np.asarray(D['thermal']))
        x_i,   y_i   = _insert_nans_for_gaps(D['day'], np.asarray(D['nonzodi']))
        source_bathtub_plot.data = dict(
            day_total=x_tot, total=y_tot,
            day_zodi=x_z,    zodi=y_z,
            day_therm=x_t,   thermal=y_t,
            day_ism=x_i,     nonzodi=y_i,
        )
        gap_seg_total.data   = _gap_segments(D['day'], D['total'])
        gap_seg_zodi.data    = _gap_segments(D['day'], D['zodi'])
        gap_seg_thermal.data = _gap_segments(D['day'], D['thermal'])
        gap_seg_ism.data     = _gap_segments(D['day'], D['nonzodi'])

    def _update_overlay_plot_source_from_raw(filt):
        D = overlay_sources_raw[filt].data
        x_p, y_p = _insert_nans_for_gaps(D['day'], np.asarray(D['total']))
        overlay_sources_plot[filt].data = dict(day=x_p, total=y_p)
        overlay_gap_sources[filt].data = _gap_segments(D['day'], D['total'])

    # ---------- Visibility toggles ----------
    def toggle_visibility(attr, old, new):
        active = toggle_components.active
        want_total   = 0 in active
        want_zodi    = 1 in active
        want_thermal = 2 in active
        want_ism     = 3 in active

        show_all = 0 in show_all_filters.active
        selected = single_filter.value

        if show_all:
            bathtub_total.visible = False
            dash_seg['total'].visible = False
        else:
            bathtub_total.visible = want_total
            dash_seg['total'].visible = want_total

        bathtub_zodi.visible    = (not show_all) and want_zodi
        bathtub_thermal.visible = (not show_all) and want_thermal
        bathtub_ism.visible     = (not show_all) and want_ism
        dash_seg['zodi'].visible    = (not show_all) and want_zodi
        dash_seg['thermal'].visible = (not show_all) and want_thermal
        dash_seg['nonzodi'].visible = (not show_all) and want_ism

        for f in overlay_filters:
            vis = show_all
            overlay_lines[f].visible = vis
            overlay_gap_renders[f].visible = vis

        for f in overlay_filters:
            visible = (show_all) or (not show_all and want_total and f == selected)
            violin_patch_rend[f].visible = visible
            whisker_rend[f].visible      = visible
            quad_rend[f].visible         = visible
            cap_rend[f].visible          = visible
            median_rend[f].visible       = visible

        selected_filter_label.text = f"Optical element: {selected}"
        selected_filter_label.visible = not show_all

        _refresh_bathtub_legend()
        _refresh_violin_legend()
        _autoscale_violin_y()
        _reposition_filter_label()
        _reposition_good_days_label()

    # ---------- Callbacks ----------
    for s in [ra_slider, dec_slider, thresh_slider]:
        s.on_change('value_throttled', update)
        s.on_change('value', lambda a, o, n: sync_inputs_from_sliders())
    day_slider.on_change('value_throttled', update)
    day_slider.on_change('value', lambda a,o,n: sync_inputs_from_sliders())

    toggle_components.on_change('active', toggle_visibility)
    show_all_filters.on_change('active', toggle_visibility)

    def _on_filter_change(attr, old, new):
        toggle_visibility(attr, old, new)
        update(attr, old, new)

    single_filter.on_change('value', _on_filter_change)

    # ---------- Buttons ----------
    save_bathtub = Button(label="Save Bathtub Data", button_type="primary")
    save_spectrum = Button(label="Save Spectrum Data", button_type="primary")
    save_violin = Button(label="Save Violin Data", button_type="primary")

    save_bathtub.on_event(ButtonClick, lambda e: pd.DataFrame(source_bathtub.data).to_csv("bathtub_background.csv", index=False))
    save_spectrum.on_event(ButtonClick, lambda e: pd.DataFrame(source_spectrum.data).to_csv(f"spectrum_day{int(day_slider.value)}.csv", index=False))

    def _save_violin():
        save_filters = list(overlay_filters.keys()) if (0 in show_all_filters.active) else [single_filter.value]
        for f in save_filters:
            pd.DataFrame(violin_sources[f].data).to_csv(f"violin_{f}.csv", index=False)
            q0 = whisker_sources[f].data['y0'][0]
            q4 = whisker_sources[f].data['y1'][0]
            q1 = box_sources[f].data['bottom'][0]
            q3 = box_sources[f].data['top'][0]
            q2 = median_sources[f].data['y'][0]
            pd.DataFrame([{
                "filter": f,
                "center_wave_um": overlay_filters[f],
                "q0_min": q0, "q1": q1, "q2_median": q2, "q3": q3, "q4_max": q4
            }]).to_csv(f"violin_summary_{f}.csv", index=False)

    save_violin.on_event(ButtonClick, lambda e: _save_violin())

    # --- NEW: put all three save buttons on one line ---
    for b in (save_bathtub, save_spectrum, save_violin):
        b.width = 170  # optional: makes them equal width on a single row

    button_bar = row(save_bathtub, save_spectrum, save_violin)

    # ---------- Layout (2×2) ----------
    controls = column(
        Div(text="<h2>Roman Background Visualization Tool (RBVT)</h2>"),
        row(ra_slider,   ra_input),
        row(dec_slider,  dec_input),
        row(thresh_slider, thresh_input),
        row(day_slider,  day_input),
        toggle_components,
        row(show_all_filters, single_filter),
        button_bar,  # <-- buttons now on the same line
        width=PANEL_W
    )
    controls.height = PANEL_H  # align violin’s top with spectrum’s top
    controls.stylesheets = [title_sheet]

    # Right column: Bathtub over Spectrum
    right_col = column(plot_bathtub, plot_spectrum, width=PANEL_W)

    # Left column: Controls over Violin
    left_col = column(controls, plot_violin, width=PANEL_W)

    doc.add_root(row(left_col, Spacer(width=100), right_col))

    # ---------- Initialize ----------
    def _init_gap_labels_from(data_days):
        _recompute_shading(data_days)

    _update_bathtub_plot_source_from_raw()
    _init_gap_labels_from(source_bathtub.data['day'])
    _refresh_bathtub_legend()
    _refresh_violin_legend()
    _reposition_filter_label()
    _reposition_good_days_label()
    _recenter_not_visible_label()
    sync_inputs_from_sliders()
    toggle_visibility(None, None, None)
