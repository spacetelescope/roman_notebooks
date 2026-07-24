import s3fs
from typing import cast
import re
import os
import typing
import yaml

import asdf
import roman_datamodels as rdm
from romancal.assign_wcs.assign_wcs_step import AssignWcsStep


# S3 file parsing magic
YAML_END_PATTERN = re.compile(rb"\r?\n\.\.\.((\r?\n)|$)")
MAX_HEADER_READ_LEN = 80 * 1024  # 80KB


class Dumper(yaml.SafeDumper):
    pass


class Loader(yaml.SafeLoader):
    pass


class Tagged(typing.NamedTuple):
    tag: str
    value: object
    def construct_undefined(self, node):
        if isinstance(node, yaml.nodes.ScalarNode):
            value = self.construct_scalar(node)
        elif isinstance(node, yaml.nodes.SequenceNode):
            value = self.construct_sequence(node)
        elif isinstance(node, yaml.nodes.MappingNode):
            value = self.construct_mapping(node)
        else:
            assert False, f"unexpected node: {node!r}"
        return Tagged(node.tag, value)

    Loader.add_constructor(None, construct_undefined)
    
    
def get_meta(s3_uri, chunk_size=8192):
    """
    This is cobbled together from the HLPP code here: 
        https://github.com/spacetelescope/roman_hlpp_dags/blob/main/dags/stage_l1_files_from_s3.py#L91-L110
    """

    def _remove_romanisim(file, content: bytes) -> bytes:
        romanisim_idx = content.find(b"romanisim:")
        roman_idx = content.find(b"roman:")
        if romanisim_idx != -1:
            if romanisim_idx < roman_idx:
                # Remove content between start of romanisim section and roman section
                content = content[:romanisim_idx] + content[roman_idx:]
            elif roman_idx < romanisim_idx:
                # Remove content between start of romanisim section and end of file
                content = content[:romanisim_idx] + b"...\n"
        else:
            raise Exception(f'Bad file {file}')
        return content

    fs = s3fs.S3FileSystem(default_block_size=chunk_size, anon=True)
    buffer = b""
    yaml_content = None
    
    with fs.open(s3_uri, "rb") as f:
        while not yaml_content:
            chunk = cast(bytes, f.read(chunk_size))

            if not chunk or len(buffer) > MAX_HEADER_READ_LEN:
                # EOF or exceeded 80KB without finding marker
                break

            buffer += chunk
            match = YAML_END_PATTERN.search(buffer)
            if match:
                yaml_content = buffer[: match.end()]
                
    meta = yaml.load(yaml_content, Loader=Loader).value['roman'].value['meta']

    return meta


def update_wcs(l2_file: str | rdm.DataModel, 
               l1_s3_path: str="s3://stpubdata/roman/nexus/soc_simulations/r00340/") -> rdm.DataModel:
    """
    PURPOSE: Update L2 file gwcs object to restore the original L1 pointing without the
             Gaia alignment from tweakreg.
    
    INPUTS:
        l2_file (str or roman_datamodels.DataModel):
            Either an S3 URI string to a L2 file, a string file path to an L2 file,
            or an already opened L2 datamodel.
        l1_s3_path (str):
            S3 URI to where the L1 files live. The default points to the GBTDS L1 files
            uploaded by the SOC. This should not need to be changed.
            
    RETURNS:
        result (roman_datamodels.DataModel):
            An updated L2 datamodel that contains the original L1 coarse WCS, i.e.,
            the WCS based solely on the simulated pointing without the Gaia alignment.
    """
    
    # Open the file if necessary. Will accept an S3 URI, a string
    # file path, or an open datamodel.
    if 's3://' in l2_file:
        fs = s3fs.S3FileSystem(anon=True)
        with fs.open(l2_file, 'rb') as fb:
            af = asdf.open(fb)
            datamodel = rdm.open(af).copy()
        l1_file = l2_file.replace('l2/', 'l1/').replace('_cal.asdf', '_uncal.asdf')
    elif isinstance(l2_file, str):
        datamodel = rdm.open(l2_file)
        l1_file = datamodel.meta.filename.replace('_cal.asdf', '_uncal.asdf')
        l1_file = os.path.join(l1_s3_path, "l1", l1_file)
    elif isinstance(l2_file, rdm.DataModel):
        datamodel = l2_file
        l1_file = datamodel.meta.filename.replace('_cal.asdf', '_uncal.asdf')
        l1_file = os.path.join(l1_s3_path, "l1", l1_file)
    else:
        raise TypeError("""Input l2_file variable is not an S3 URI, 
                        string file path, or data model.""")
    
    # Get JUST the metadata section of the L1 ASDF file from S3.
    l1_meta = get_meta(l1_file)
    
    # Revise the L2 metadata wcsinfo to restore the original pointing
    # information from the L1 file.
    datamodel.meta.wcsinfo.ra_ref = l1_meta['wcsinfo']['ra_ref']
    datamodel.meta.wcsinfo.dec_ref = l1_meta['wcsinfo']['dec_ref']
    datamodel.meta.wcsinfo.roll_ref = l1_meta['wcsinfo']['roll_ref']
    datamodel.meta.wcsinfo.s_region = l1_meta['wcsinfo']['s_region']

    # Run assign_wcs to update the GWCS object to clobber the
    # changes the tweakreg step made when the L2 was created.
    result = AssignWcsStep.call(datamodel)
    
    return result