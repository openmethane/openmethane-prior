import datetime
import pandas as pd

from openmethane_prior.sectors.coal.data import coal_facilities_data_source, filter_coal_facilities

def test_filter_coal_facilities(config, input_files, data_manager):  # test totals for GFAS emissions between original and remapped
    coal_facilities_df = data_manager.get_asset(coal_facilities_data_source).data

    # unfiltered dataset has 3570 rows, 35 cols
    assert coal_facilities_df.shape == (3570, 35)

    test_filtered_2023 = filter_coal_facilities(
        coal_facilities_df,
        (datetime.datetime(2023, 7, 1), datetime.datetime(2023, 7, 31)),
    )

    # filtered by gas and year 2023 gives 93 rows
    assert test_filtered_2023.shape == (93, 35)

    test_filtered_2022 = filter_coal_facilities(
        coal_facilities_df,
        (datetime.datetime(2022, 7, 1), datetime.datetime(2022, 7, 31)),
    )
    # filtered 2022 is the last year in the dataset, so gives same result as 2023
    pd.testing.assert_frame_equal(test_filtered_2022, test_filtered_2023)

    test_filtered_2019 = filter_coal_facilities(
        coal_facilities_df,
        (datetime.datetime(2019, 7, 1), datetime.datetime(2019, 7, 31)),
    )
    # 2019 has fewer mines, so only 89 rows after filtering
    assert test_filtered_2019.shape == (89, 35)
