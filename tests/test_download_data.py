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
