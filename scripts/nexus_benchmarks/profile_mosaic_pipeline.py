"""Profile RomanCal mosaic processing on representative WFI associations.

The benchmark cases process four- or eighteen-detector associations, with
source catalog generation enabled or skipped as configured.
"""

import roman_datamodels as rdm
import s3fs
from romancal.pipeline import MosaicPipeline
from romancal.associations import asn_from_list

import os

from profile_workflows import profile_resources


def make_asn(input_files=None, product_name='custom_mosaic'):
    """Build a Roman association from input calibrated exposures.

    Args:
        input_files: Exposure paths; defaults to four public Nexus files.
        product_name: Name assigned to the mosaic product.

    Returns:
        The association object consumed by ``MosaicPipeline``.
    """
    if not input_files:
        filenames = ['r0003201001001001004_0001_wfi11_f106_cal.asdf',
                     'r0003201001001001004_0002_wfi11_f106_cal.asdf',
                     'r0003201001001001004_0003_wfi11_f106_cal.asdf',
                     'r0003201001001001004_0004_wfi11_f106_cal.asdf']

        input_files = [
            'https://s3.amazonaws.com/stpubdata/roman/nexus/'
            f'soc_simulations/tutorial_data/{file}'
            for file in filenames
        ]

    # Create the ASN JSON object
    asn = asn_from_list.asn_from_list([(i, 'science') for i in input_files],
                                      product_name=product_name,
                                      with_exptype=True, target='')

    return asn


def pipeline(asn, skip_catalog=False, on_disk=False):
    """Run and profile the RomanCal mosaic pipeline for an association."""
    @profile_resources()
    def run_mlp(asn, skip=False):
        """Run the mosaic pipeline with source catalog steps configured."""
        dm = MosaicPipeline.call(
            asn.data,
            resample_on_skycell=False,
            save_results=False,
            on_disk=on_disk,
            update_version=True,
            steps={'source_catalog': {'skip': skip}},
        )

    _, result = run_mlp(asn, skip=skip_catalog)

    return result


def case1():
    """Profile a four-detector mosaic with catalog generation skipped."""
    asn = make_asn()
    result = pipeline(asn, skip_catalog=True)

    return result


def case2():
    """Profile a four-detector mosaic with catalog generation enabled."""
    asn = make_asn()
    result = pipeline(asn, skip_catalog=False)

    return result


def case3():
    """Profile an eighteen-detector mosaic with catalog generation skipped."""
    filenames = [
        f'r0003201001001001004_0001_wfi{sca:02d}_f106_cal.asdf'
        for sca in range(1, 19)
    ]
    input_files = [
        'https://s3.amazonaws.com/stpubdata/roman/nexus/'
        f'soc_simulations/tutorial_data/{file}'
        for file in filenames
    ]
    asn = make_asn(input_files=input_files)

    result = pipeline(asn, skip_catalog=True, on_disk=False)

    return result
