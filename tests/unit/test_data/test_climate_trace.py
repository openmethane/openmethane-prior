import datetime
import pandas as pd
import pytest

from openmethane_prior.data_sources.climate_trace import filter_emissions_sources

@pytest.fixture()
def emissions_sources_df():
    # subset of rows/columns from coal-mining_emissions_sources CSV
    test_data_df = pd.DataFrame(
        data=[
            ('14857','Airly Coal Mine','Underground','2025-01-01 00:00:00','2025-01-31 00:00:00','-33.1130709','150.0149367','861.530929052861'),
            ('14857','Airly Coal Mine','Underground','2025-02-01 00:00:00','2025-02-28 00:00:00','-33.1130709','150.0149367','813.898507614351'),
            ('14857','Airly Coal Mine','Underground','2025-03-01 00:00:00','2025-03-31 00:00:00','-33.1130709','150.0149367','798.933107297206'),
            ('14857','Airly Coal Mine','Underground','2025-04-01 00:00:00','2025-04-30 00:00:00','-33.1130709','150.0149367','862.387952639349'),
            ('14857','Airly Coal Mine','Underground','2025-05-01 00:00:00','2025-05-31 00:00:00','-33.1130709','150.0149367','849.304149218833'),
            ('14857','Airly Coal Mine','Underground','2025-06-01 00:00:00','2025-06-30 00:00:00','-33.1130709','150.0149367','847.101777851265'),
            ('14857','Airly Coal Mine','Underground','2025-07-01 00:00:00','2025-07-31 00:00:00','-33.1130709','150.0149367','861.530929052861'),
            ('14857','Airly Coal Mine','Underground','2025-08-01 00:00:00','2025-08-31 00:00:00','-33.1130709','150.0149367','813.898507614351'),
            ('43159456','Angus Place Coal Mine','Underground','2025-01-01 00:00:00','2025-01-31 00:00:00','-33.349157','150.199019','0'),
            ('43159456','Angus Place Coal Mine','Underground','2025-02-01 00:00:00','2025-02-28 00:00:00','-33.349157','150.199019','0'),
            ('43159456','Angus Place Coal Mine','Underground','2025-03-01 00:00:00','2025-03-31 00:00:00','-33.349157','150.199019','0'),
            ('43159456','Angus Place Coal Mine','Underground','2025-04-01 00:00:00','2025-04-30 00:00:00','-33.349157','150.199019','0'),
            ('43159456','Angus Place Coal Mine','Underground','2025-05-01 00:00:00','2025-05-31 00:00:00','-33.349157','150.199019','0'),
            ('43159456','Angus Place Coal Mine','Underground','2025-06-01 00:00:00','2025-06-30 00:00:00','-33.349157','150.199019','0'),
            ('43159456','Angus Place Coal Mine','Underground','2025-07-01 00:00:00','2025-07-31 00:00:00','-33.349157','150.199019','0'),
            ('43159456','Angus Place Coal Mine','Underground','2025-08-01 00:00:00','2025-08-31 00:00:00','-33.349157','150.199019','0'),
            ('14858','Appin Coal Mine','Underground','2025-01-01 00:00:00','2025-01-31 00:00:00','-34.211194','150.792736','5219.12939629125'),
            ('14858','Appin Coal Mine','Underground','2025-02-01 00:00:00','2025-02-28 00:00:00','-34.211194','150.792736','4930.57356786665'),
            ('14858','Appin Coal Mine','Underground','2025-03-01 00:00:00','2025-03-31 00:00:00','-34.211194','150.792736','4839.9136065251'),
            ('14858','Appin Coal Mine','Underground','2025-04-01 00:00:00','2025-04-30 00:00:00','-34.211194','150.792736','5224.32122033692'),
            ('14858','Appin Coal Mine','Underground','2025-05-01 00:00:00','2025-05-31 00:00:00','-34.211194','150.792736','5145.05991845612'),
            ('14858','Appin Coal Mine','Underground','2025-06-01 00:00:00','2025-06-30 00:00:00','-34.211194','150.792736','5131.71801654824'),
            ('14858','Appin Coal Mine','Underground','2025-07-01 00:00:00','2025-07-31 00:00:00','-34.211194','150.792736','5219.12939629125'),
            ('14858','Appin Coal Mine','Underground','2025-08-01 00:00:00','2025-08-31 00:00:00','-34.211194','150.792736','4930.57356786665'),
        ],
        columns=['source_id','source_name','source_type','start_time','end_time','lat','lon','emissions_quantity'],
    )

    # convert strings to datetime, done automatically by pd.read_csv()
    test_data_df["start_time"] = pd.to_datetime(test_data_df["start_time"])
    test_data_df["end_time"] = pd.to_datetime(test_data_df["end_time"])

    return test_data_df

def test_filter_emissions_sources(emissions_sources_df):
    test_filtered_2025_aug = filter_emissions_sources(
        emissions_sources_df,
        datetime.datetime(2025, 8, 1),
        datetime.datetime(2025, 8, 31),
    )

    # filtered by period gives 3 rows, one for each source
    assert test_filtered_2025_aug.shape == (3, 8)
    assert test_filtered_2025_aug.iloc[0].start_time == datetime.datetime(2025, 8, 1)
    assert test_filtered_2025_aug.iloc[0].end_time == datetime.datetime(2025, 8, 31)

    # period outside the available data
    test_filtered_2025_dec = filter_emissions_sources(
        emissions_sources_df,
        datetime.datetime(2025, 12, 1),
    datetime.datetime(2025, 12, 31),
    )

    # 2025-12 is outside the available data, so 2025-08 (the last period) is returned
    pd.testing.assert_frame_equal(test_filtered_2025_dec, test_filtered_2025_aug)

    test_filtered_2025_jan = filter_emissions_sources(
        emissions_sources_df,
        datetime.datetime(2025, 1, 1),
        datetime.datetime(2025, 1, 31),
    )

    # 2023 has the same number of results, but is not the same
    assert test_filtered_2025_jan.shape == (3, 8)
    assert test_filtered_2025_jan.iloc[0].start_time == datetime.datetime(2025, 1, 1)
    assert test_filtered_2025_jan.iloc[0].end_time == datetime.datetime(2025, 1, 31)

    # filter period of only 2 days still returns the full month
    test_filtered_partial = filter_emissions_sources(
        emissions_sources_df,
        datetime.datetime(2025, 1, 1),
        datetime.datetime(2025, 1, 2),
    )

    pd.testing.assert_frame_equal(test_filtered_2025_jan, test_filtered_partial)
    assert test_filtered_partial.iloc[0].start_time == datetime.datetime(2025, 1, 1)
    assert test_filtered_partial.iloc[0].end_time == datetime.datetime(2025, 1, 31)

    test_filtered_2024 = filter_emissions_sources(
        emissions_sources_df,
        datetime.datetime(2024, 12, 1),
        datetime.datetime(2024, 12, 31),
    )

    # when a period before the available data is selected, no rows are returned
    assert test_filtered_2024.shape == (0, 8)

    with pytest.raises(NotImplementedError):
        # filtering across multiple months not supported
        filter_emissions_sources(
            emissions_sources_df,
            datetime.datetime(2022, 6, 1),
            datetime.datetime(2022, 7, 31),
        )
