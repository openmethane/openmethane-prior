import pandas as pd

from openmethane_prior.sectors.oil_gas.safeguard import safeguard_operating_periods


def test_safeguard_operating_periods():
    facility_locations_df = pd.DataFrame(
        data=[
            ("Closed Plant", "oil-gas-sites", "Closed Terminal"), # match by Site
            ("Open Plant", "oil-gas-sites", "Open Plant"), # match by Facility name
            ("Mixed Plant", "oil-gas-sites", "Mixed Plant"),
            ("Closed Plant", "NT-petroleum-wells", "NT/L1"), # ignored, not a site
            ("Wells Only", "NT-petroleum-wells", "NT/L2"),
        ],
        columns=["safeguard_facility_name", "data_source_name", "data_source_id"],
    )
    oil_gas_sites_df = pd.DataFrame(
        data=[
            ("Closed Plant", "Closed Terminal", "2006-01-01", "2023-11-11"),
            ("Open Plant", "Open Platform", "2012-01-01", None),
            ("Open Plant", "Open Terminal", "2010-01-01", None),
            ("Mixed Plant", "Mixed Station A", None, "2025-05-01"),
            ("Mixed Plant", "Mixed Station B", "2016-01-01", "2025-08-01"),
            ("Unlinked Plant", "Unlinked Terminal", "2000-01-01", "2001-01-01"),
        ],
        columns=["Facility name", "Site", "Operation start", "Operation end"],
    )
    oil_gas_sites_df["Operation start"] = pd.to_datetime(oil_gas_sites_df["Operation start"])
    oil_gas_sites_df["Operation end"] = pd.to_datetime(oil_gas_sites_df["Operation end"])

    result_df = safeguard_operating_periods(
        facility_locations_df=facility_locations_df,
        oil_gas_sites_df=oil_gas_sites_df,
        sites_data_source_name="oil-gas-sites",
    )

    result_df = result_df.set_index("facility_name")
    assert set(result_df.index) == {"Closed Plant", "Open Plant", "Mixed Plant"}

    assert result_df.loc["Closed Plant", "operation_start"] == pd.Timestamp("2006-01-01")
    assert result_df.loc["Closed Plant", "operation_end"] == pd.Timestamp("2023-11-11")

    # earliest start, open-ended since no site has an end date
    assert result_df.loc["Open Plant", "operation_start"] == pd.Timestamp("2010-01-01")
    assert pd.isna(result_df.loc["Open Plant", "operation_end"])

    # open start since one site has no start date, latest end date
    assert pd.isna(result_df.loc["Mixed Plant", "operation_start"])
    assert result_df.loc["Mixed Plant", "operation_end"] == pd.Timestamp("2025-08-01")
