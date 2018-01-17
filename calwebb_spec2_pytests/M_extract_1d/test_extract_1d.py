
"""
py.test module for unit testing the extract_1d step.
"""

import pytest
import os
import time
import subprocess

from jwst.extract_1d.extract_1d_step import Extract1dStep
from .. import core_utils
from . import extract_1d_utils


# Set up the fixtures needed for all of the tests, i.e. open up all of the FITS files

# Default names of pipeline input and output files
@pytest.fixture(scope="module")
def set_inandout_filenames(request, config):
    step = "extract_1d"
    step_info = core_utils.set_inandout_filenames(step, config)
    step_input_filename, step_output_filename, in_file_suffix, out_file_suffix, True_steps_suffix_map = step_info
    return step, step_input_filename, step_output_filename, in_file_suffix, out_file_suffix, True_steps_suffix_map


# fixture to read the output file header
@pytest.fixture(scope="module")
def output_hdul(set_inandout_filenames, config):
    set_inandout_filenames_info = core_utils.read_info4outputhdul(config, set_inandout_filenames)
    step, txt_name, step_input_file, step_output_file, run_calwebb_spec2, outstep_file_suffix = set_inandout_filenames_info
    skip_runing_pipe_step = config.getboolean("tests_only", "_".join((step, "tests")))
    stp = Extract1dStep()
    # if run_calwebb_spec2 is True calwebb_spec2 will be called, else individual steps will be ran
    step_completed = False
    end_time = '0.0'
    if run_calwebb_spec2:
        # read the assign wcs fits file
        local_step_output_file = core_utils.read_completion_to_full_run_map("full_run_map.txt", step)
        hdul = core_utils.read_hdrfits(local_step_output_file, info=False, show_hdr=False)
        # move the output file into the working directory
        working_directory = config.get("calwebb_spec2_input_file", "working_directory")
        step_output_file = os.path.join(working_directory, local_step_output_file)
        print ("Step product was saved as: ", step_output_file)
        subprocess.run(["mv", local_step_output_file, step_output_file])
        return hdul
    else:
        if config.getboolean("steps", step):
            print ("*** Step "+step+" set to True")
            if os.path.isfile(step_input_file):
                if not skip_runing_pipe_step:
                    # start the timer to compute the step running time
                    start_time = time.time()
                    result = stp.call(step_input_file)
                    result.save(step_output_file)
                    # end the timer to compute the step running time
                    end_time = repr(time.time() - start_time)   # this is in seconds
                    print("Step "+step+" took "+end_time+" seconds to finish")
                step_completed = True
                core_utils.add_completed_steps(txt_name, step, outstep_file_suffix, step_completed, end_time)
                hdul = core_utils.read_hdrfits(step_output_file, info=False, show_hdr=False)
                # get the total running time and print it in the file
                total_time = core_utils.get_time_to_run_pipeline(txt_name)
                total_time_min = float(total_time)/60.0
                print ("The total time for the pipeline to run was "+total_time+" seconds.")
                print ("   ( = "+repr(total_time_min)+" minutes )")
                line2write = "{:<20} {:<20} {:<20} {:<20}".format('', '', ' total_time  ', total_time, '  ='+repr(total_time_min)+'min')
                print (line2write)
                with open(txt_name, "a") as tf:
                    tf.write(line2write+"\n")
                return hdul
            else:
                core_utils.add_completed_steps(txt_name, step, outstep_file_suffix, step_completed, end_time)
                pytest.skip("Skipping "+step+" because the input file does not exist.")
        else:
            core_utils.add_completed_steps(txt_name, step, outstep_file_suffix, step_completed, end_time)
            pytest.skip("Skipping "+step+". Step set to False in configuration file.")



# Unit tests

def test_s_extr1d_exists(output_hdul):
    assert extract_1d_utils.s_extr1d_exists(output_hdul), "The keyword S_EXTR1D was not added to the header --> Extract 1D step was not completed."

def test_extract1d_rfile(output_hdul):
    assert extract_1d_utils.extract1d_rfile_is_correct(output_hdul)
