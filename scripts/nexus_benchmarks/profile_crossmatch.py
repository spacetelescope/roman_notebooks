from os import cpu_count
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from astropy.coordinates import SkyCoord
from astropy import units as u

import lsdb
import dask
from dask.distributed import Client, LocalCluster
import cdshealpix
import hats
import lsdb

from profile_workflows import profile_resources


@profile_resources()
def case1(nrows=10_000, *, client=None):
    """Load catalogs, build the cross-match, and compute its result.

    nrows selects the notebook's approximate-size cone, not an exact row limit.
    Use -1 for the full catalog only with adequate resources.
    A supplied client must have a fixed set of local workers.
    Without a client, computation explicitly uses the threaded scheduler.
    """
    import lsdb
    from astropy import units as u
    from astropy.coordinates import SkyCoord

    radii = {
        10_000: 331,
        100_000: 1047,
        1_000_000: 3318,
        10_000_000: 11_180,
        100_000_000: 33_743,
        1_000_000_000: 102_000,
    }
    if nrows != -1 and nrows not in radii:
        raise ValueError(f"nrows must be -1 or one of {list(radii)}.")

    center = SkyCoord("19:22:40  +44:30:00", unit=(u.hourangle, u.deg))
    search_filter = (
        None if nrows == -1
        else lsdb.ConeSearch(center.ra.value, center.dec.value, radii[nrows])
    )
    ztf = lsdb.open_catalog(
        "s3://ipac-irsa-ztf/contributed/dr23/objects/hats",
        columns=["oid", "ra", "dec"],
        search_filter=search_filter,
    )
    ps1 = lsdb.open_catalog(
        "s3://stpubdata/panstarrs/ps1/public/hats/otmo",
        columns=["objName", "objID", "raMean", "decMean"],
    )
    
    matched = ztf.crossmatch(
        ps1,
        radius_arcsec=1,
        n_neighbors=1,
        suffixes=("_ztf", "_ps1"),
        suffix_method="all_columns",
    )
    
    if client is None:
        with dask.config.set(scheduler="threads"):
            return matched.compute()
    
    with client.as_current():
        return matched.compute()