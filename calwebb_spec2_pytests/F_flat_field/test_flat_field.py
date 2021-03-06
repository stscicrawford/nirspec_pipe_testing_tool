
"""
py.test module for unit testing the flat field step.
"""

import pytest
import os
import time
import subprocess
from astropy.io import fits

from jwst.flatfield.flat_field_step import FlatFieldStep
from .. import core_utils
from . import flat_field_utils
from .. auxiliary_code import flattest_mos
from .. auxiliary_code import flattest_fs
from .. auxiliary_code import flattest_ifu


# Set up the fixtures needed for all of the tests, i.e. open up all of the FITS files

# Default names of pipeline input and output files
@pytest.fixture(scope="module")
def set_inandout_filenames(request, config):
    step = "flat_field"
    step_info = core_utils.set_inandout_filenames(step, config)
    step_input_filename, step_output_filename, in_file_suffix, out_file_suffix, True_steps_suffix_map = step_info
    return step, step_input_filename, step_output_filename, in_file_suffix, out_file_suffix, True_steps_suffix_map


# fixture to read the output file header
@pytest.fixture(scope="module")
def output_hdul(set_inandout_filenames, config):
    set_inandout_filenames_info = core_utils.read_info4outputhdul(config, set_inandout_filenames)
    step, txt_name, step_input_file, step_output_file, run_calwebb_spec2, outstep_file_suffix = set_inandout_filenames_info
    stp = FlatFieldStep()
    msa_shutter_conf = config.get("esa_intermediary_products", "msa_conf_name")
    msametfl = os.path.basename(msa_shutter_conf)
    dflat_path = config.get("esa_intermediary_products", "dflat_path")
    sflat_path = config.get("esa_intermediary_products", "sflat_path")
    fflat_path = config.get("esa_intermediary_products", "fflat_path")
    flattest_threshold_diff = config.get("additional_arguments", "flattest_threshold_diff")
    save_flattest_plot = config.getboolean("additional_arguments", "save_flattest_plot")
    write_flattest_files = config.getboolean("additional_arguments", "write_flattest_files")
    flattest_paths = [step_output_file, msa_shutter_conf, dflat_path, sflat_path, fflat_path]
    flattest_switches = [flattest_threshold_diff, save_flattest_plot, write_flattest_files]
    skip_runing_pipe_step = config.getboolean("tests_only", "_".join((step, "tests")))
    # if run_calwebb_spec2 is True calwebb_spec2 will be called, else individual steps will be ran
    step_completed = False
    end_time = '0.0'
    # get the MSA shutter configuration file full path only for MOS data
    inhdu = core_utils.read_hdrfits(step_input_file, info=False, show_hdr=False)
    if run_calwebb_spec2:
        # read the assign wcs fits file
        local_step_output_file = core_utils.read_completion_to_full_run_map("full_run_map.txt", step)
        hdul = core_utils.read_hdrfits(local_step_output_file, info=False, show_hdr=False)
        # move the output file into the working directory
        working_directory = config.get("calwebb_spec2_input_file", "working_directory")
        step_output_file = os.path.join(working_directory, local_step_output_file)
        print ("Step product was saved as: ", step_output_file)
        subprocess.run(["mv", local_step_output_file, step_output_file])
        return hdul, flattest_paths, flattest_switches
    else:
        if config.getboolean("steps", step):
            print ("*** Step "+step+" set to True")
            if os.path.isfile(step_input_file):
                if not skip_runing_pipe_step:
                    if core_utils.check_MOS_true(inhdu):
                        # copy the MSA shutter configuration file into the pytest directory
                        subprocess.run(["cp", msa_shutter_conf, "."])
                    # start the timer to compute the step running time
                    ontheflyflat = step_output_file.replace("flat_field.fits", "intflat.fits")
                    print ("Step product will be saved as: ", step_output_file)
                    print ("on-the-fly flat will be saved as: ", ontheflyflat)
                    # get the right configuration files to run the step
                    local_pipe_cfg_path = config.get("calwebb_spec2_input_file", "local_pipe_cfg_path")
                    # start the timer to compute the step running time
                    start_time = time.time()
                    if local_pipe_cfg_path == "pipe_source_tree_code":
                        result = stp.call(step_input_file, flat_suffix="intflat")
                                          #override_dflat="/grp/crds/jwst/references/jwst/jwst_nirspec_dflat_0001.fits",
                                          #override_fflat="/grp/crds/jwst/references/jwst/jwst_nirspec_fflat_0015.fits",
                                          #override_sflat="/grp/crds/jwst/references/jwst/jwst_nirspec_sflat_0034.fits")
                    else:
                        result = stp.call(step_input_file, flat_suffix="intflat", config_file=local_pipe_cfg_path+'/flat_field.cfg')
                    result.save(step_output_file)
                    # end the timer to compute the step running time
                    end_time = repr(time.time() - start_time)   # this is in seconds
                    print("Step "+step+" took "+end_time+" seconds to finish")
                    # move the on-the-fly flat to the working directory
                    subprocess.run(["mv", os.path.basename(ontheflyflat), ontheflyflat])
                    if core_utils.check_MOS_true(inhdu):
                        # remove the copy of the MSA shutter configuration file
                        subprocess.run(["rm", msametfl])
                step_completed = True
                core_utils.add_completed_steps(txt_name, step, outstep_file_suffix, step_completed, end_time)
                hdul = core_utils.read_hdrfits(step_output_file, info=False, show_hdr=False)
                return hdul, flattest_paths, flattest_switches
            else:
                core_utils.add_completed_steps(txt_name, step, outstep_file_suffix, step_completed, end_time)
                pytest.skip("Skipping "+step+" because the input file does not exist.")
        else:
            core_utils.add_completed_steps(txt_name, step, outstep_file_suffix, step_completed, end_time)
            pytest.skip("Skipping "+step+". Step set to False in configuration file.")



### THESE FUNCTIONS ARE TO VALIDATE BOTH THE WCS AND THE 2D_EXTRACT STEPS

# fixture to validate the WCS and extract 2d steps
@pytest.fixture(scope="module")
def validate_flat_field(output_hdul):
    # get the input information for the wcs routine
    hdu = output_hdul[0]
    step_output_file, msa_shutter_conf, dflatref_path, sfile_path, fflat_path = output_hdul[1]
    flattest_threshold_diff, save_flattest_plot, write_flattest_files = output_hdul[2]

    # show the figures
    show_figs = False

    if core_utils.check_FS_true(hdu):
        median_diff, msg = flattest_fs.flattest(step_output_file, dflatref_path=dflatref_path, sfile_path=sfile_path,
                                                fflat_path=fflat_path, writefile=write_flattest_files,
                                                show_figs=show_figs, save_figs=save_flattest_plot, plot_name=None,
                                                threshold_diff=flattest_threshold_diff, debug=False)

    elif core_utils.check_MOS_true(hdu):
        median_diff, msg = flattest_mos.flattest(step_output_file, dflatref_path=dflatref_path, sfile_path=sfile_path,
                                               fflat_path=fflat_path, msa_shutter_conf=msa_shutter_conf,
                                               writefile=write_flattest_files,
                                               show_figs=show_figs, save_figs=save_flattest_plot, plot_name=None,
                                               threshold_diff=flattest_threshold_diff, debug=False)

    elif core_utils.check_IFU_true(hdu):
        median_diff, msg = flattest_ifu.flattest(step_output_file, dflatref_path=dflatref_path, sfile_path=sfile_path,
                                                fflat_path=fflat_path, writefile=write_flattest_files,
                                                mk_all_slices_plt=False, show_figs=show_figs,
                                                save_figs=save_flattest_plot, plot_name=None,
                                                threshold_diff=flattest_threshold_diff, debug=False)

    else:
        pytest.skip("Skipping pytest: The input fits file is not FS, MOS, or IFU. This tool does not yet include the "
                    "routine to verify this kind of file.")

    if median_diff == "skip":
        pytest.skip(msg)
    else:
        print(msg)

    return median_diff



# Unit tests

def test_s_flat_exists(output_hdul):
    assert flat_field_utils.s_flat_exists(output_hdul[0]), "The keyword S_FLAT was not added to the header --> flat_field step was not completed."

def test_validate_flat_field(output_hdul):
    assert validate_flat_field(output_hdul), "Output value from flattest.py is greater than threshold."

def test_fflat_rfile(output_hdul):
    assert flat_field_utils.fflat_rfile_is_correct(output_hdul[0])

def test_sflat_sfile(output_hdul):
    assert flat_field_utils.sflat_rfile_is_correct(output_hdul[0])

def test_dflat_dfile(output_hdul):
    assert flat_field_utils.dflat_rfile_is_correct(output_hdul[0])

