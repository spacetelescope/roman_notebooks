import roman_datamodels as rdm
import s3fs
from romancal.pipeline import ExposurePipeline
import dotenv
import os

from profile_workflows import profile_resources


def pipeline(filename=None, skip_catalog=False):

    if not filename:
        filename = (
            "https://s3.amazonaws.com/stpubdata/roman/nexus/"
            "soc_simulations/tutorial_data/r0003201001001001004_0001_wfi01_f106_uncal.asdf"
        )

    dm = rdm.open(filename)

    @profile_resources()
    def run_elp(dm, skip=False):
    
        result = ExposurePipeline.call(dm, save_results=False, 
                                       steps={
                                           'source_catalog': {'skip': skip}, 
                                           'tweakreg': {'skip': skip}
                                       }
                                      )

    _, result = run_elp(dm, skip=skip_catalog)
    
    return result


def case1():

    result = pipeline(skip_catalog=False)
    return result


def case2():

    result = pipeline(skip_catalog=True)
    return result


def case3():

    result = pipeline(filename='elp_case3_uncal.asdf', skip_catalog=True)
    return result
