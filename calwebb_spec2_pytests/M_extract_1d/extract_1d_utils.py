"""
This file contains the functions which will be used to test the extract_1d step
of the JWST Calibration Pipeline.

"""


### VERIFICATION FUNCTIONS

def s_extr1d_exists(output_hdul):
    """
    This function checks that the keyword S_EXTR1D was added.
    Args:
        outout_hdul: the HDU list of the header keywords

    Returns:
        result: boolean, true if the keyword was indeed added
    """
    result = "S_EXTR1D" in output_hdul
    return result


