# work around until folder structure is updated^
import os
import sys
# insert root directory into python module search path
sys.path.insert(1, os.getcwd())

from temporary_file_for_tests import downloads, remote
import pytest
import requests

@pytest.mark.xfail
def test_response_for_download_links() :
    for filename, filepath in downloads :
        url = f"{remote}{filename}"
        with requests.get(url, stream=True) as response :
            print(f"Response code for {url}: {response.status_code}")
            assert response.status_code == 200

# @pytest.mark.xfail
# def test_download_input_files():
#     assert False

# EXPECTED_FILE_NAMES = ["file1.txt", "file2.txt", "file3.txt"]
#
# def test_empty_folder():
#     # Check if the folder is empty before running the script
#     assert not os.listdir(TEST_FOLDER), f"Folder '{TEST_FOLDER}' is not empty"
#
# def test_execute_script():
#     # Execute the script
#     subprocess.run(SCRIPT_COMMAND, shell=True, cwd=TEST_FOLDER)
#
# def test_generated_files():
#     # Check if the generated files have the correct names
#     generated_files = os.listdir(TEST_FOLDER)
#     assert sorted(generated_files) == sorted(EXPECTED_FILE_NAMES), \
#         f"Generated files {generated_files} do not match expected names {EXPECTED_FILE_NAMES}"