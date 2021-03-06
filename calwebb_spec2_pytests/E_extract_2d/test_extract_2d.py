
"""
py.test module for unit testing the extract_2d step.
"""

import pytest
import os
import time
import subprocess
from astropy.io import fits

from jwst.extract_2d.extract_2d_step import Extract2dStep
from .. import core_utils
from . import extract_2d_utils
from .. auxiliary_code import compare_wcs_fs
from .. auxiliary_code import compare_wcs_mos


# Set up the fixtures needed for all of the tests, i.e. open up all of the FITS files

# Default names of pipeline input and output files
@pytest.fixture(scope="module")
def set_inandout_filenames(request, config):
    step = "extract_2d"
    step_info = core_utils.set_inandout_filenames(step, config)
    step_input_filename, step_output_filename, in_file_suffix, out_file_suffix, True_steps_suffix_map = step_info
    return step, step_input_filename, step_output_filename, in_file_suffix, out_file_suffix, True_steps_suffix_map


# fixture to read the output file header
@pytest.fixture(scope="module")
def output_hdul(set_inandout_filenames, config):
    set_inandout_filenames_info = core_utils.read_info4outputhdul(config, set_inandout_filenames)
    step, txt_name, step_input_file, step_output_file, run_calwebb_spec2, outstep_file_suffix = set_inandout_filenames_info
    skip_runing_pipe_step = config.getboolean("tests_only", "_".join((step, "tests")))
    stp = Extract2dStep()
    esa_files_path = config.get("esa_intermediary_products", "esa_files_path")
    msa_conf_name = config.get("esa_intermediary_products", "msa_conf_name")
    wcs_threshold_diff = config.get("additional_arguments", "wcs_threshold_diff")
    save_wcs_plots = config.getboolean("additional_arguments", "save_wcs_plots")
    # if run_calwebb_spec2 is True calwebb_spec2 will be called, else individual steps will be ran
    step_completed = False
    end_time = '0.0'
    # only do this step if data is NOT IFU
    inhdu = core_utils.read_hdrfits(step_input_file, info=False, show_hdr=False)
    if not core_utils.check_IFU_true(inhdu):
        if run_calwebb_spec2:
            # read the assign wcs fits file
            local_step_output_file = core_utils.read_completion_to_full_run_map("full_run_map.txt", step)
            hdul = core_utils.read_hdrfits(local_step_output_file, info=False, show_hdr=False)
            # move the output file into the working directory
            working_directory = config.get("calwebb_spec2_input_file", "working_directory")
            step_output_file = os.path.join(working_directory, local_step_output_file)
            print ("Step product was saved as: ", step_output_file)
            subprocess.run(["mv", local_step_output_file, step_output_file])
            return hdul, step_output_file, msa_conf_name, esa_files_path, wcs_threshold_diff, save_wcs_plots
        else:
            if config.getboolean("steps", step):
                print ("*** Step "+step+" set to True")
                if os.path.isfile(step_input_file):
                    if not skip_runing_pipe_step:
                        # get the right configuration files to run the step
                        local_pipe_cfg_path = config.get("calwebb_spec2_input_file", "local_pipe_cfg_path")
                        # start the timer to compute the step running time
                        start_time = time.time()
                        if local_pipe_cfg_path == "pipe_source_tree_code":
                            result = stp.call(step_input_file)
                        else:
                            result = stp.call(step_input_file, config_file=local_pipe_cfg_path+'/extract_2d.cfg')
                        result.save(step_output_file)
                        # end the timer to compute the step running time
                        end_time = repr(time.time() - start_time)   # this is in seconds
                        print("Step "+step+" took "+end_time+" seconds to finish")
                    step_completed = True
                    core_utils.add_completed_steps(txt_name, step, outstep_file_suffix, step_completed, end_time)
                    hdul = core_utils.read_hdrfits(step_output_file, info=False, show_hdr=False)
                    return hdul, step_output_file, msa_conf_name, esa_files_path, wcs_threshold_diff, save_wcs_plots
                else:
                    core_utils.add_completed_steps(txt_name, step, outstep_file_suffix, step_completed, end_time)
                    pytest.skip("Skiping "+step+" because the input file does not exist.")
            else:
                core_utils.add_completed_steps(txt_name, step, outstep_file_suffix, step_completed, end_time)
                pytest.skip("Skiping "+step+". Step set to False in configuration file.")
    else:
        pytest.skip("Skipping "+step+" because data is IFU.")



### THESE FUNCTIONS ARE TO VALIDATE BOTH THE WCS AND THE 2D_EXTRACT STEPS

# fixture to validate the WCS and extract 2d steps
@pytest.fixture(scope="module")
def validate_wcs_extract2d(output_hdul):
    # get the input information for the wcs routine
    hdu = output_hdul[0]
    infile_name = output_hdul[1]
    msa_conf_name = output_hdul[2]
    esa_files_path = output_hdul[3]

    # define the threshold difference between the pipeline output and the ESA files for the pytest to pass or fail
    threshold_diff = float(output_hdul[4])

    # save the output plots
    save_wcs_plots = output_hdul[5]

    # show the figures
    show_figs = False

    if core_utils.check_FS_true(hdu):
        # Find what slit the data corresponds to and populate the keyword
        #sltname_list = []
        #sltname = fits.getval(infile_name, "SLTNAME", extname="SCI")
        #fits.setval(infile_name, "FXD_SLIT", extname="SCI", value=sltname)
        median_diff = compare_wcs_fs.compare_wcs(infile_name, esa_files_path=esa_files_path,
                                                 auxiliary_code_path=None, plot_names=None,
                                                 show_figs=show_figs, save_figs=save_wcs_plots,
                                                 threshold_diff=threshold_diff)

    elif core_utils.check_MOS_true(hdu):
        median_diff = compare_wcs_mos.compare_wcs(infile_name, msa_conf_name=msa_conf_name,
                                                  esa_files_path=esa_files_path, auxiliary_code_path=None,
                                                  plot_names=None, show_figs=show_figs, save_figs=save_wcs_plots,
                                                  threshold_diff=threshold_diff)

    else:
        pytest.skip("Skipping pytest: The fits file is not FS, MOS, or IFU. Tool does not yet include the routine to verify this kind of file.")

    if median_diff == "skip":
        pytest.skip("WCS validation quit because there are no extensions that match detector NRS2 in the ESA file.")

    return median_diff



### Unit tests

def test_s_ext2d_exists(output_hdul):
    assert extract_2d_utils.s_ext2d_exists(output_hdul[0]), "The keyword S_EXTR2D was not added to the header --> extract_2d step was not completed."


def test_validate_wcs_extract2d(output_hdul):
    assert validate_wcs_extract2d(output_hdul), "Output value from compare_wcs.py is greater than threshold."
