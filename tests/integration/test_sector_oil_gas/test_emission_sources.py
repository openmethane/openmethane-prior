import datetime

from openmethane_prior.sectors.oil_gas.data.nopta import (
    nopta_titles_data_source, nopta_wells_data_source,
)
from openmethane_prior.sectors.oil_gas.data.nsw_geo import (
    nsw_drillholes_data_source, nsw_titles_data_source,
)
from openmethane_prior.sectors.oil_gas.data.nt_geo import (
    nt_titles_data_source, nt_wells_data_source,
)
from openmethane_prior.sectors.oil_gas.data.qld_gis import (
    qld_boreholes_data_source, qld_leases_data_source,
)
from openmethane_prior.sectors.oil_gas.data.sa_wells import (
    sa_wells_data_source, sa_wells_production_data_source,
)
from openmethane_prior.sectors.oil_gas.data.wa_gis import (
    wa_titles_data_source, wa_wells_data_source,
)
from openmethane_prior.sectors.oil_gas.emission_sources.all_sources import all_emission_sources
from openmethane_prior.sectors.oil_gas.emission_sources.nsw_sources import nsw_emission_sources
from openmethane_prior.sectors.oil_gas.emission_sources.nt_sources import nt_emission_sources
from openmethane_prior.sectors.oil_gas.emission_sources.offshore_sources import offshore_emission_sources
from openmethane_prior.sectors.oil_gas.emission_sources.qld_sources import qld_emission_sources
from openmethane_prior.sectors.oil_gas.emission_sources.sa_sources import sa_emission_sources
from openmethane_prior.sectors.oil_gas.emission_sources.wa_sources import wa_emission_sources


def test_nsw_emission_sources(input_files, data_manager):
    start_date = datetime.datetime(2023, 1, 1, 0, 0)
    start_date_end = datetime.datetime(2023, 1, 2, 0, 0)
    drillholes_da = data_manager.get_asset(nsw_drillholes_data_source)
    df = nsw_emission_sources(
        start_date=start_date.date(),
        end_date=start_date.date(),
        nsw_drillholes_da=drillholes_da,
        nsw_titles_da=data_manager.get_asset(nsw_titles_data_source),
    )

    # original drillholes dataset has been filtered down
    assert len(drillholes_da.data) > 0
    assert len(df) <= len(drillholes_da.data)

    # no sources where activity period doesn't intersect date period
    assert len(df[(df["activity_end"] < start_date) & (df["activity_start"] > start_date_end)]) == 0

    # no sources which aren't related to production
    assert list(df["hole_purpose"].unique()) == ["Production"]
    assert list(df["resource"].unique()) == ["PETROLEUM"]

    # no duplicate entries for the same location
    assert len(df["geometry"].unique()) == len(df)


def test_nt_emission_sources(input_files, data_manager):
    start_date = datetime.datetime(2023, 1, 1, 0, 0)
    start_date_end = datetime.datetime(2023, 1, 2, 0, 0)
    wells_da = data_manager.get_asset(nt_wells_data_source)
    df = nt_emission_sources(
        start_date=start_date.date(),
        end_date=start_date.date(),
        nt_wells_da=wells_da,
        nt_titles_da=data_manager.get_asset(nt_titles_data_source),
    )

    # original drillholes dataset has been filtered down
    assert len(wells_da.data) > 0
    assert len(df) <= len(wells_da.data)

    # no sources where activity period doesn't intersect date period
    assert len(df[(df["activity_end"] < start_date) & (df["activity_start"] > start_date_end)]) == 0

    # no sources which aren't related to production
    assert set(df["PURPOSE"].unique()) == {"Production", "Development"}

    # no duplicate entries for the same location
    assert len(df["geometry"].unique()) == len(df)


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
    assert len(boreholes_da.data) > 0
    assert len(df) <= len(boreholes_da.data)

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

    assert len(df["geometry"].unique()) == len(df)


def test_sa_emission_sources(input_files, data_manager):
    start_date = datetime.datetime(2023, 1, 1, 0, 0)
    start_date_end = datetime.datetime(2023, 1, 2, 0, 0)
    wells_da = data_manager.get_asset(sa_wells_data_source)
    production_da = data_manager.get_asset(sa_wells_production_data_source)
    df = sa_emission_sources(
        start_date=start_date.date(),
        end_date=start_date.date(),
        sa_wells_da=wells_da,
        sa_production_da=production_da,
    )

    # original wells dataset has been filtered down
    assert len(wells_da.data) > 0
    assert len(df) <= len(wells_da.data)

    # no sources where activity period doesn't intersect date period
    assert len(df[(df["activity_end"] < start_date) & (df["activity_start"] > start_date_end)]) == 0

    # # no sources which didn't have recorded production within the period
    assert len(df[(df["Oil (m3)"] <= 0) & (df["Gas (m3E6)"] <= 0)]) == 0


def test_wa_emission_sources(input_files, data_manager):
    start_date = datetime.datetime(2023, 1, 1, 0, 0)
    start_date_end = datetime.datetime(2023, 1, 2, 0, 0)
    wells_da = data_manager.get_asset(wa_wells_data_source)
    df = wa_emission_sources(
        start_date=start_date.date(),
        end_date=start_date.date(),
        wa_wells_da=wells_da,
        wa_titles_da=data_manager.get_asset(wa_titles_data_source),
    )

    # original wells dataset has been filtered down
    assert len(wells_da.data) > 0
    assert len(df) <= len(wells_da.data)

    # no sources where activity period doesn't intersect date period
    assert len(df[(df["activity_end"] < start_date) & (df["activity_start"] > start_date_end)]) == 0

    # no sources which aren't related to production
    assert set(df["class"].unique()) == {"DEV"}

    # no duplicate check, as we allow duplicate geometries from WA dataset


def test_offshore_emission_sources(input_files, data_manager):
    start_date = datetime.datetime(2023, 1, 1, 0, 0)
    start_date_end = datetime.datetime(2023, 1, 2, 0, 0)
    wells_da = data_manager.get_asset(nopta_wells_data_source)
    df = offshore_emission_sources(
        start_date=start_date.date(),
        end_date=start_date.date(),
        offshore_wells_da=wells_da,
        offshore_titles_da=data_manager.get_asset(nopta_titles_data_source),
    )

    # original wells dataset has been filtered down
    assert len(wells_da.data) > 0
    assert len(df) <= len(wells_da.data)

    # no sources where activity period doesn't intersect date period
    assert len(df[(df["activity_end"] < start_date) & (df["activity_start"] > start_date_end)]) == 0

    # no sources which aren't related to production
    assert set(df["Purpose"].unique()) == {"Development"}
    assert set(df["TitleType"].unique()) == {"Production Licence"}

    # no duplicate check, as we allow duplicate geometries from NOPTA dataset


def test_all_emission_sources(input_files, data_manager, config):
    end_date_end = config.end_date + datetime.timedelta(days=1)
    df = all_emission_sources(
        data_manager=data_manager,
        prior_config=config,
    )

    assert len(df) > 0

    # no sources where activity period doesn't intersect config period
    assert len(df[(df["activity_end"] < config.start_date) & (df["activity_start"] > end_date_end)]) == 0

