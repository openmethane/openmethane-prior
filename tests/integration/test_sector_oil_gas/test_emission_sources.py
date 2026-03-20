import datetime

from openmethane_prior.sectors.oil_gas.data.qld_boreholes import qld_boreholes_data_source
from openmethane_prior.sectors.oil_gas.data.qld_leases import qld_leases_data_source
from openmethane_prior.sectors.oil_gas.emission_sources.qld_sources import qld_emission_sources


def test_qld_emission_sources(input_files, data_manager):
    start_date = datetime.datetime(2023, 1, 1, 0, 0)
    start_date_end = datetime.datetime(2023, 1, 2, 0, 0)
    boreholes_da = data_manager.get_asset(qld_boreholes_data_source)
    df = qld_emission_sources(
        start_date=start_date.date(),
        end_date=start_date.date(),
        qld_boreholes_da=boreholes_da,
        qld_leases_da=data_manager.get_asset(qld_leases_data_source),
    )

    # original boreholes dataset has been filtered down
    assert len(boreholes_da.data) == 23908
    assert len(df) == 8670

    # no sources where activity period doesn't intersect date period
    assert len(df[(df["activity_end"] < start_date) & (df["activity_start"] > start_date_end)]) == 0

    # no sources which aren't related to hydrocarbon production
    allowed_bore_types = {
        "COAL SEAM GAS", "PETROLEUM", "UNCONVENTIONAL PETROLEUM", "GREENHOUSE GAS STORAGE",
    }
    assert set(df["bore_type"].unique()) - allowed_bore_types == set()

    allowed_bore_subtypes = {
        "DEVELOPMENT WELL", "COAL SEAM GAS INJECTION WELL", "PETROLEUM INJECTION WELL",
    }
    assert set(df["bore_subtype"].unique()) - allowed_bore_subtypes == set()

    allowed_results = {
        "GAS", "OIL AND GAS", "GAS PLUS CONDENSATE SHOW", "OIL", "DRY PLUS GAS SHOW",
        "DRY PLUS OIL SHOW", "OIL PLUS GAS SHOW", "GAS AND CONDENSATE",
        "GAS PLUS OIL SHOW", "COAL SEAM GAS", "DRY PLUS OIL AND GAS SHOW",
    }
    assert set(df["result"].unique()) - allowed_results == set()

    allowed_status = {
        "PLUGGED AND ABANDONED", "SUSPENDED/CAPPED/SHUT-IN", "PRODUCING HYDROCARBONS",
    }
    assert set(df["status"].unique()) - allowed_status == set()

    # no duplicate entries for the same location
    assert len(df["geometry"].unique()) == len(df)
