## Top level run script for the preparation phase
#
# This is the top-level script that sets up the CMAQ inputs. Most of
# the detail and functionality is found in a series of accompanying
# files. Tasks performed:
#  - create output destinations (if need be)
#  - check the latitudes and longitudes of the WRF and MCIP grids against one another
#  - prepare the JPROC files (precomuted photochemical rate constants)
#  - map emissions onto the domain
#  - prepare the initial and boundary conditions from global CTM output
#  - prepare run scripts for ICON, BCON and CCTM programs within the CMAQ  bundle
#
# Author: Jeremy Silver (jeremy.silver@unimelb.edu.au)
# Date: 2016-11-04

## load standard python libraries (other are imported by the accompanying scripts)
import datetime
from dateutil.relativedelta import relativedelta
import os
import numpy
## custom python libraries (really these are just the accompanying files)
import helper_funcs
# import prepareJprocFiles
import prepareFireEmis
# import prepareCamsEmis
# import prepareEdgarEmis
import checkWrfMcipDomainSizes
# import interpolateFromCams
# import configureRunScripts
# import surfzonegeo
# import runMCIP
# import archiveWrf
import prepareWetlandEmis
import prepareGeogenicEmis
# import prepareCarbonTrackerEmis
import preparePointSourceEmis

## The main routine controlling the CMAQ preparation phase
#
#Most of the important variables are set here. These are:
#- CMAQdir:  base directory for the CMAQ model
#- MCIPdir:  directory containing the MCIP executable
#- photDir:  path to the photolysis data files (available with the CMAQ benchmark data set)
#- GFASdir: directory containing the GFAS data
#- ANTHROPdirs:  list of folders containing the wrfchemi_* anthropogenic emission files
#- templateDir:  folder containing the template run scripts
#- metDir: base directory for the MCIP output
#- ctmDir: base directory for the CCTM inputs and outputs
#- wrfDir: directory containing wrfout_* files
#- geoDir: directory containing geo_em.* files
#- mozartSpecIndex: speciation file, mapping MOZART to CMAQ species
#- gfasSpecIndexFile: speciation file, mapping GFAS to CMAQ species
#- wrfchemSpecIndexFile:  speciation file, mapping WRFCHEMI to CMAQ species
#- tempDir: directory for temporary files
#- inputCamsFile: Output from CAMS to use for boundary and initial conditions
#- cmaqVersionCode: abbreviated CMAQ number
#- coastlineShapefiles: a list of shapefiles describing coastlines for use in the surf-zone calculates. One per entry per domain
#- cmaqEnvScript: path to the (bash) shell script that sets all of the run-time variables for CMAQ (e.g. LD_LIBRARY_PATH, module load <name>, etc.)
#- GFASfile:  the file (within directory GFASdir) containing GFAS fire emission data
#- domains: list of which domains should be run?
#- run: name of the simulation, appears in some filenames (keep this *short* - longer)
#- startDate: this is the START of the first day
#- endDate: this is the START of the last day
#- nhoursPerRun: number of hours to run at a time (24 means run a whole day at once)
#- printFreqHours: frequency of the CMAQ output (1 means hourly output) - so far it is not set up to run for sub-hourly
#- case: the name of case to run (used in some filenames)
#- mech: name of chemical mechanism to appear in filenames
#- mechCMAQ: name of chemical mechanism given to CMAQ (should be one of: cb05e51_ae6_aq, cb05mp51_ae6_aq, cb05tucl_ae6_aq, cb05tump_ae6_aq, racm2_ae6_aq, saprc07tb_ae6_aq, saprc07tc_ae6_aq, saprc07tic_ae6i_aq, saprc07tic_ae6i_aqkmti)
#- addFires: combined emissions include GFAS fires
#- prepareEmis: prepare the emission files
#- prepareICandBC: prepare the initial and boundary conditions from global CAMS output
#- prepareRunScripts: prepare the run scripts
#- forceUpdateMcip: force the update of the MCIP files
#- forceUpdateJproc: force the update of the JPROC (photolysis rate constant) files
#- forceUpdateSZ: force the update of the surfzone files
#- forceUpdateFires: force the update of GFAS emission files
#- forceUpdateCAMS: force the update of CAMS emission files
#- forceUpdateMerger: force the merging of anthropogenic, biogenic and fire emissions
#- forceUpdateICandBC: force an update of the initial and boundary conditions from global CAMS output
#- forceUpdateRunScripts: force an update to the run scripts
#- scenarioTag: scenario tag (for MCIP). 16-character maximum
#- mapProjName: Map projection name (for MCIP). 16-character maximum
#- gridName: Grid name (for MCIP). 16-character maximum
#- doCompress: compress the output from netCDF3 to netCDF4 during the CMAQ run
#- compressScript: script to find and compress netCDF3 to netCDF4
#- restartDate: the date at which to restart (if 'None', then start from the beginning) - both restartDate and restartDom need to be set together to work
#- restartDom: the domain at which to restart (if 'None', then start from the beginning) - both restartDate and restartDom need to be set together to work
#- scripts: This is a dictionary with paths to each of the run-scripts. Elements of the dictionary should themselves be dictionaries, with the key 'path' and the value being the path to that file. The keys of the 'scripts' dictionary should be as follow: mcipRun: MCIP run script; bconRun: BCON run script; iconRun: ICON run script; cctmRun: CCTM run script; jprocRun: JPROC run script; cmaqRun: main CMAQ run script; pbsRun: PBS submission script.
#- copyInputsFromPreviousSimulation copy some/all of the inputs from a previous run
#- oldCtmDir: which directory to copy from (this is the base directory)
#- oldRun: the 'run' variable from the previous simulation
#- copyEFMAPS: copy the EFMAPS files?
#- copyLAIS: copy the LAIS files?
#- copyPFTS: copy the PFTS files
#- copySURFZONE: copy the surfzone files?
#- copyJTABLE: copy the JTABLE files?
#- copyTemplateIC: copy the template IC files
#- copyTemplateBC: copy the template BC files
#- copyBCON: copy the daily BC files
#- copyICON: copy the daily IC files
#- copyFIREEMIS: copy the fire emissions
#- copyMERGEDEMIS: copy the merged emissions
#- linkInsteadOfCopy: if 'True', symbolic links are made rather than copies
def main():

    
    ################ MOST USER INPUT SHOULD BE BELOW HERE ###################

    ## directories    
    CMAQdir = '/short/w22/jds563/code/CMAQv5.0.2_notpollen' ## base directory for the CMAQ model
    MCIPdir = '/short/w22/jds563/code/CMAQv5.0.2_notpollen/scripts/mcip/src' ## directory containing the MCIP executable
    photDir = '/short/w22/jds563/data/CMAQ-benchmark/CMAQv5.0.2/data/raw/phot' ## path to the photolysis data files (available with the CMAQ benchmark data set)
    GFASdir = '/short/w22/jds563/data/fire_emis/GFAS' ## directory containing the GFAS data

    templateDir = '/home/563/jds563/projects/runCMAQ/NWQLD/templateRunScripts' ## folder containing the template run scripts
    ##
    metDir = '/short/w22/jds563/data/WRF/NWQLD' ## base directory for the MCIP output        ************
    ctmDir = '/short/w22/jds563/data/CTM/NWQLD' ## base directory for the CCTM inputs and outputs  **********
    wrfDir = '/short/w22/jds563/data/WRF/NWQLD' ## directory containing wrfout_* files (organised in folders named as YYYYMMDDHH)
    ##
    wrfRunName = 'NWQLD' ## run name used for achiving the WRF output
    geoDir = '/home/563/jds563/projects/runWRF/NWQLD' ## directory containing geo_em.* files
    ##
    wrfCoordDir = '/home/563/jds563/projects/runCMAQ/NWQLD/wrfout_with_coords_only' ## directory with some wrfout_ files with XLAT,XLONG variables
    gfasSpecIndexFile = '/home/563/jds563/projects/runCMAQ/NWQLD/speciesTables/species_table_GFAS_CH4only.txt' ## speciation file, mapping GFAS to CMAQ species (CH4-only)
    tempDir = '/tmp' ## directory for temporary files
    cmaqVersionCode = 'D502a_CH4' ## abbreviated CMAQ number
    coastlineShapefiles = ["/short/w22/jds563/data/landuse/gshhg/GSHHS_shp/c/GSHHS_c_L1.shp",
                           "/short/w22/jds563/data/landuse/gshhg/GSHHS_shp/c/GSHHS_c_L1.shp",
                           "/short/w22/jds563/data/landuse/gshhg/GSHHS_shp/l/GSHHS_l_L1.shp",
                           "/short/w22/jds563/data/landuse/gshhg/GSHHS_shp/l/GSHHS_l_L1.shp"] ## a list of shapefiles describing coastlines for use in the surf-zone calculates. One per entry per domain
    cmaqEnvScript = '/home/563/jds563/projects/runCMAQ/NWQLD/load_cmaq_env.sh' ## path to the (bash) shell script that sets all of the run-time variables for CMAQ (e.g. LD_LIBRARY_PATH, module load <name>, etc.)

    domains = ['d01', 'd02', 'd03', 'd04'] ## which domains should be run?
    # domains = ['d03', 'd04'] ## which domains should be run?
    domains = ['d01', 'd02','d03'] ## which domains should be run?
    # run = 'GHGaus' ## name of the simulation, appears in some filenames (keep this *short* - longer)
    run = 'NWQLD' ## name of the simulation, appears in some filenames (keep this *short* - longer)

    ## You can provide different cases (i.e. periods with the same setup)
    # case = '201102'
    # startDate = datetime.datetime(2011,02,01)
    # ## endDate   = datetime.datetime(2011,02,04)
    # endDate   = datetime.datetime(2011,02,01)
    # GFASfile = 'GFAS_AUS_2011-02-01_2011-03-31.nc' ## the file (within directory GFASdir) containing GFAS fire emission data
    # CAMSfile = '/short/w22/jds563/data/CAMS_GHG_BCs_emis/z_cams_l_lsce_201102_v13r1_ra_sfc_3h_co2flux.nc' ## the file containing CAMS emission data     *****
    # inputCamsFile = '/short/w22/jds563/data/CAMS_GHG_BCs_emis/z_cams_l_lsce_201102_v13r1_ra_ml_3h_co2.nc' ## Output from CAMS to use for boundary and initial conditions    ************
    # restartDate = None ## datetime.datetime(2011,02,04)
    # restartDom = None ## 'd01'
    ##
    case = 'NWQLD'
    ##
    year = 2022
    month = 7    
    startDate = datetime.datetime(year,month, 1)
    endDate = startDate + relativedelta(months = 3)
    # endDate = datetime.datetime(year,month, 1)
    
    monthName = startDate.strftime('%b')
    monthCase = '{}_{}'.format(case, monthName)
    ## the file (within directory GFASdir) containing GFAS fire emission data
    GFASfile = 'GFAS_{}-{:02d}_Australia_CH4.nc'.format(year,month)
    CAMSversion = 'v17r1'
    year = 2017
    month = 9  
    CAMSfile = '/short/w22/jds563/data/MACC_GHG_BCs_emis/z_cams_l_tno-sron_{}{:02d}_{}_ra_sfc_mm_ch4flux.nc'.format(year,month,CAMSversion) ## the file containing CAMS emission data      *****
    inputCamsFile = '/short/w22/jds563/data/MACC_GHG_BCs_emis/z_cams_l_tno-sron_{}{:02d}_{}_ra_ml_6h_ch4.nc'.format(year,month,CAMSversion) ## Output from CAMS to use for boundary and initial conditions    ************
    ##
    sectorLevels = {'ENE': numpy.array([3]),
                    'REF_TRF': numpy.array([1]),
                    'IND': numpy.array([1]),
                    'TNR_Aviation_CDS': numpy.arange(12,23),
                    'TNR_Aviation_CRS': numpy.arange(23,27),
                    'TNR_Aviation_LTO': numpy.arange(0,12),
                    ## 'TNR_Aviation_SPS': numpy.arange(23,27),
                    'TRO': numpy.array([0]),
                    'TNR_Other': numpy.array([0]),
                    'TNR_Ship': numpy.array([0]),
                    'RCO': numpy.array([0]),
                    'PRO': numpy.array([0]),
                    'CHE': numpy.array([0]),
                    'IRO': numpy.array([1]),
                    'ENF': numpy.array([0]),
                    'MNM': numpy.array([0]),
                    'AGS': numpy.array([0]),
                    'AWB': numpy.array([1]),
                    'SWD_LDF': numpy.array([0]),
                    'WWT': numpy.array([0]),
                    'SWD_INC': numpy.array([1]),
                    'FFF': numpy.array([1])}
    EDGARfile = '/short/w22/jds563/data/CH4_emis/EDGAR/EDGAR_CH4_emis.nc'
    
    carbonTrackerSectors = ['natural', 'ocean'] ## don't use: 'agwaste', 'bioburn', 'fossil'
    carbonTrackerSectorsIsOcean = {'natural': False, 'ocean' : True, 'agwaste' : False, 'bioburn' : False, 'fossil' : False}

    CarbonTrackerFile = '/short/w22/jds563/data/CH4_emis/CarbonTracker/CarbonTracker_CH4_subset.nc'

    miningPointSourceFile = 'table_of_operating_coal_mines_and_emission_rate_estimates.csv'
    miningEmisColumnName = 'CH4_kg_4'
    

    wetlandsFile = '/short/w22/jds563/data/CH4_emis/CMS_Global_Monthly_Wetland_CH4_1502/WetCHARTs_full_ensemble_subset.nc4'

    geogenicFile = '/short/w22/jds563/data/CH4_emis/Geo-CH4_emission_grid_files/Gridded_geoCH4_csv_ESSD/geogenic_ch4_subset.nc'

    restartDate = None ## datetime.datetime(2011,02,04)
    restartDom = None ## 'd01'
    
    nhoursPerRun = 24 ## number of hours to run at a time (24 means run a whole day at once)
    printFreqHours = 1 ## frequency of the CMAQ output (1 means hourly output) - so far it is not set up to run for sub-hourly

    ## preparation
    mech       = 'CH4only' ## name of chemical mechanism to appear in filenames
    
    mechCMAQ   = 'CH4only' ## name of chemical mechanism given to CMAQ (should be one of: CH4only, cb05e51_ae6_aq, cb05mp51_ae6_aq, cb05tucl_ae6_aq, cb05tump_ae6_aq, racm2_ae6_aq, saprc07tb_ae6_aq, saprc07tc_ae6_aq, saprc07tic_ae6i_aq, saprc07tic_ae6i_aqkmti)

    ## model to use is /home/563/spt563/cmaq_adj/BLD_fwd_CH4only/ADJOINT_FWD

    doRunMcip = True # run MCIP? (this is normally set to True)
    doRunJproc = True # run JPROC? (this is normally set to True)

    retrieveFromMdss = True ## get the WRFOUT files from MDSS?
    mdssPath = 'jds563/WRF/NWQLD' ## folder on MDSS where the WRFOUT files reside
    
    prepareEmis = True # prepare the emission files
    addFires   = True # combined emissions include GFAS fires
    addWetlands   = False # combined emissions include WetCHARTs wetland CH4 emissions 
    addGeogenic   = True # combined emissions include geogenic CH4 emissions 
    addCarbonTracker = True # combined emissions include CarbonTracker emissions
    addMiningPointSource = False # combined emissions include mining point source emissions
    prepareICandBC = True # prepare the initial and boundary conditions from global CAMS output
    prepareRunScripts = True # prepare the run scripts

    # save additional variables in the multi-sector files to break down the totals into the per-sector contributions
    add_sector_vars = True

    fix_truelat2 = False
    truelat2 = -50.
    fix_truelat2 = False
    truelat2 = 19.52

    ## use CAMS emissions?
    useCAMSemissions = False
    ## use EDGAR emissions?
    useEDGARemissions = True

    doArchiveWrf = False ## archive WRF output once MCIP has been run

    forceUpdateMcip = False # force the update of the MCIP files
    forceUpdateJproc = False # force the update of the JPROC (photolysis rate constant) files
    forceUpdateSZ = False # force the update of the surfzone files
    forceUpdateFires = False # force the update of GFAS emission files
    forceUpdateWetlands = False # force theupdate of the wetland emission files
    forceUpdateGeogenic = False # force theupdate of the geogenic emission files
    forceUpdateCarbonTracker = True # force the update of CarbonTracker emission files
    forceUpdateMiningPointSource = False # force the update of mining emission files
    forceUpdateCAMS = False # force the update of CAMS emission files
    forceUpdateEDGAR = False # force the update of EDGAR emission files
    forceUpdateICandBC = False # force an update of the initial and boundary conditions from global CAMS output
    forceUpdateRunScripts = True # force an update to the run scripts

    scenarioTag = [ case for dom in domains ]                # scenario tag (for MCIP). 16-character maximum. One per domain
    mapProjName = ['LamCon_34S_134E' for dom in domains ]    # Map projection name (for MCIP). 16-character maximum. One per domain.
    gridName    = ['AUS_{}'.format(dom) for dom in domains]  # Grid name (for MCIP). 16-character maximum. One per domain.

    ## don't compress in the main routine, because this is done in the cleanup phase (on copyq)
    doCompress = False ## compress the output from netCDF3 to netCDF4 during the CMAQ run
    compressScript = '/home/563/jds563/bin/compress_netcdf_experimental2.sh' ## script to find and compress netCDF3 to netCDF4

    doCleanup = True ## Boolean (True/False) for whether the output should be "cleaned-up" (i.e. remove superfluous output fields, archive some data)

    ## This is a dictionary with paths to each of the
    ## run-scripts. Elements of the dictionary should themselves be
    ## dictionaries, with the key 'path' and the value being the path
    ## to that file. The keys of the 'scripts' dictionary should be as follow:
    # mcipRun - MCIP run script
    # bconRun - BCON run script
    # iconRun - ICON run script
    # cctmRun - CCTM run script
    # jprocRun - JPROC run script
    # cmaqRun - main CMAQ run script
    # pbsRun - PBS submission script
    # cleanup - script to remove superfluous output fields, archive some data
    # scripts = {'mcipRun':{'path': '{}/run.mcip'.format(templateDir)},
    #            'bconRun': {'path': '{}/run.bcon'.format(templateDir)},
    #            'iconRun': {'path': '{}/run.icon'.format(templateDir)},
    #            'cctmRun': {'path': '{}/run.cctm'.format(templateDir)}, ## 'cctmRun': {'path': '{}/run.cctm'.format(templateDir)},
    #            'jprocRun': {'path': '{}/run.jproc'.format(templateDir)}, 
    #            'cmaqRun': {'path': '{}/runCMAQ.sh'.format(templateDir)},
    #            'pbsRun': {'path': '{}/PBS_CMAQ_job.sh'.format(templateDir)},
    #            'cleanup': {'path': '{}/cleanupArchive.sh'.format(templateDir)}}

    copyInputsFromPreviousSimulation = False ## copy some/all of the inputs from a previous run
    oldCtmDir = '' ## which directory to copy from (this is the base directory)
    oldRun = '' ## the 'run' variable from the previous simulation
    copySURFZONE = False ## copy the surfzone files?
    copyJTABLE = False ## copy the JTABLE files?
    copyTemplateIC = False ## copy the template IC files
    copyTemplateBC = False ## copy the template BC files
    copyBCON = False ## copy the daily BC files
    copyICON = False ## copy the daily IC files
    copyMERGEDEMIS = False ## copy the merged emissions
    linkInsteadOfCopy = False ## if 'True', symbolic links are made rather than copies

    ################ MOST USER INPUT SHOULD BE ABOVE HERE ###################

    ## define date range
    ndates = (endDate - startDate).days + 1
    dates = [startDate + datetime.timedelta(days = d) for d in range(ndates)]

    ## read in the template run-scripts
    # scripts = helper_funcs.loadScripts(Scripts = scripts)

    ndomains = len(domains)

    ## create output destinations, if need be:
    # print("Check that input meteorology files are provided and create output destinations (if need be)")
    # mcipOuputFound = checkWrfMcipDomainSizes.checkInputMetAndOutputFolders(ctmDir,metDir,dates,domains)
    # print("\t... done")
    
    # if doRunMcip:
    #     if (not mcipOuputFound) or forceUpdateMcip:
    #         runMCIP.runMCIP(dates = dates, domains = domains, metDir = metDir, wrfDir = wrfDir, geoDir = geoDir, ProgDir = MCIPdir, APPL = scenarioTag, CoordName = mapProjName, GridName = gridName, scripts = scripts,
    #                         compressWithNco = True, fix_simulation_start_date = True,
    #                 fix_truelat2 = fix_truelat2, truelat2 = truelat2, doArchiveWrf = doArchiveWrf, wrfRunName = wrfRunName,
    #                 retrieveFromMdss = retrieveFromMdss, mdssPath = mdssPath,
    #                 forceUpdate = forceUpdateMcip)

    #     if doArchiveWrf:
    #         archiveWrf.archiveWrf(dates = dates, domains = domains, metDir = metDir, wrfDir = wrfDir,
    #                               wrfRunName = wrfRunName)

    ## extract some parameters about the MCIP setup
    CoordNames, GridNames, APPL = checkWrfMcipDomainSizes.getMcipGridNames(metDir,dates,domains)

    ## get the environment from the CMAQ/scripts/config.cmaq file
    # configFile = '{}/scripts/config.cmaq'.format(CMAQdir)
    # configEnv = helper_funcs.source2(configFile, shell = 'csh')

    ## figure out what the CCTM executable will be called
    # cctmExec = 'CCTM_{}_{}'.format(cmaqVersionCode,configEnv['EXEC_ID'])

    ## get the shell environment variables
    envVars = helper_funcs.source2('$HOME/.bashrc')

    # if copyInputsFromPreviousSimulation:
    #     checkWrfMcipDomainSizes.copyFromPreviousCtmDir(oldCtmDir = oldCtmDir, newCtmDir = ctmDir, dates = dates, domains = domains,
    #                                                    oldRun = oldRun, newRun = run,
    #                                                    CMAQmech = mechCMAQ, mech = mech, GridNames = GridNames, 
    #                                                    copySURFZONE = copySURFZONE,
    #                                                    copyJTABLE = copyJTABLE,
    #                                                    copyTemplateIC = copyTemplateIC,
    #                                                    copyTemplateBC = copyTemplateBC,
    #                                                    copyBCON = copyBCON,
    #                                                    copyICON = copyICON,
    #                                                    copyMERGEDEMIS = copyMERGEDEMIS,
    #                                                    link = linkInsteadOfCopy)    

    # if doRunMcip:
    #     ## check the latitudes and longitudes of the WRF and MCIP grids against one another
    #     print("Check the latitudes and longitudes of the WRF and MCIP grids against one another")
    #     nx_wrf, ny_wrf, nx_cmaq, ny_cmaq, x0, y0, ncolsin, nrowsin = checkWrfMcipDomainSizes.checkWrfMcipDomainSizes(metDir = metDir, date = dates[0], domains = domains, wrfDir = wrfCoordDir)
    # print("\t... done")

    if prepareEmis:
        print("Prepare emissions")
        ## prepare the jproc files
        # if doRunJproc:
        #     prepareJprocFiles.prepareJprocFiles(dates = dates,scripts = scripts,ctmDir = ctmDir,CMAQdir = CMAQdir, photDir = photDir, mechCMAQ = mechCMAQ, forceUpdate = forceUpdateJproc)
        ## prepare surf zone files
        # surfzoneFilesExist = surfzonegeo.checkSurfZoneFilesExist(ctmDir = ctmDir, doms = domains)
        # if (not surfzoneFilesExist) or forceUpdateSZ:
        #     surfzoneFiles = surfzonegeo.setupSurfZoneFiles(metDir = metDir, ctmDir = ctmDir, doms = domains, date = dates[0], mcipsuffix = APPL, shapefiles = coastlineShapefiles)


        # if useCAMSemissions:
        #     print("Check whether CAMS emission files exist ...")
        #     cams_emis_files_exist = prepareCamsEmis.checkCamsEmisFilesExist(dates = dates, doms = domains, ctmDir = ctmDir, prefix = 'cams_emis')
        #     print("\t... result =", cams_emis_files_exist)
        #     if (not cams_emis_files_exist) or forceUpdateCAMS:
        #         print("Prepare CAMS emissions")
        #         prepareCamsEmis.prepareCamsEmis(dates = dates, doms = domains,
        #                                         CAMSfile = CAMSfile,
        #                                         metDir = metDir,
        #                                         ctmDir = ctmDir, 
        #                                         mcipsuffix = APPL,
        #                                         forceUpdate = forceUpdateCAMS)
        #     ## copy the CAMS emissions to the 'combined' emision
        #     prepareCamsEmis.copy_to_combined(dates = dates, doms = domains, ctmDir = ctmDir, in_prefix = 'cams_emis', out_prefix = 'combined_emis')
        # elif useEDGARemissions:
        #     print("Check whether EDGAR emission files exist ...")
        #     edgar_emis_files_exist = prepareEdgarEmis.checkEdgarEmisFilesExist(dates = dates, doms = domains, ctmDir = ctmDir, prefix = 'edgar_emis')
        #     print("\t... result =", edgar_emis_files_exist)
        #     if (not edgar_emis_files_exist) or forceUpdateEDGAR:
        #         print("Prepare EDGAR emissions")
        #         prepareEdgarEmis.prepareEdgarEmis(dates = dates, doms = domains,
        #                                         EDGARfile = EDGARfile,
        #                                         metDir = metDir,
        #                                         ctmDir = ctmDir, 
        #                                         mcipsuffix = APPL,
        #                                         sector_levels = sectorLevels,
        #                                         add_sector_vars = add_sector_vars,
        #                                         forceUpdate = forceUpdateEDGAR)
        #     ## copy the EDGAR emissions to the 'combined' emision
        #     prepareCamsEmis.copy_to_combined(dates = dates, doms = domains, ctmDir = ctmDir, in_prefix = 'edgar_emis', out_prefix = 'combined_emis')
        # else:
        #     raise RuntimeError('The CAMS & EDGAR emissions are the only options here...')
                
        ##
        if addFires:
            print("Check whether fire emission files exist ...")
            fire_emis_files_exist = prepareFireEmis.checkFireEmisFilesExist(dates = dates, doms = domains, ctmDir = ctmDir)
            print("\t... result =", fire_emis_files_exist)
            if (not fire_emis_files_exist) or forceUpdateFires:
                print("Prepare fire emissions")
                prepareFireEmis.prepareFireEmis(dates = dates, doms = domains,
                                                GFASfolder = GFASdir, GFASfile = GFASfile,
                                                metDir = metDir, ctmDir = ctmDir, CMAQdir = CMAQdir,
                                                mechCMAQ = mechCMAQ, mcipsuffix = APPL,
                                                specTableFile = gfasSpecIndexFile,
                                                forceUpdate = forceUpdateFires)
            
            prepareFireEmis.addGfasFluxes(dates = dates, doms = domains,
                                          metDir = metDir,
                                          ctmDir = ctmDir, CMAQdir = CMAQdir,
                                          mechCMAQ = mechCMAQ, mcipsuffix = APPL,
                                          forceUpdate = forceUpdateFires)

        if addWetlands:
            print("Check whether wetland emission files exist ...")
            wetland_emis_files_exist = prepareWetlandEmis.checkWetlandEmisFilesExist(dates = dates, doms = domains, ctmDir = ctmDir)
            print("\t... result =", wetland_emis_files_exist)
            if (not wetland_emis_files_exist) or forceUpdateWetlands:
                print("Prepare wetland emissions")
                prepareWetlandEmis.prepareWetlandEmis(dates = dates, doms = domains,
                                                       wetlandsFile = wetlandsFile,
                                                       metDir = metDir, ctmDir = ctmDir,
                                                       mcipsuffix = APPL,
                                                       forceUpdate = forceUpdateWetlands)
            ##
            prepareWetlandEmis.addWetlandFluxes(dates = dates, doms = domains,
                                                metDir = metDir,
                                                ctmDir = ctmDir, CMAQdir = CMAQdir,
                                                mechCMAQ = mechCMAQ, mcipsuffix = APPL,
                                                forceUpdate = forceUpdateWetlands)

        if addGeogenic:
            print("Check whether geogenic emission files exist ...")
            geogenic_emis_files_exist = prepareGeogenicEmis.checkGeogenicEmisFilesExist(dates = dates, doms = domains, ctmDir = ctmDir)
            print("\t... result =", geogenic_emis_files_exist)
            if (not geogenic_emis_files_exist) or forceUpdateGeogenic:
                print("Prepare geogenic emissions")
                prepareGeogenicEmis.prepareGeogenicEmis(dates = dates, doms = domains,
                                                       geogenicFile = geogenicFile,
                                                       metDir = metDir, ctmDir = ctmDir,
                                                       mcipsuffix = APPL,
                                                       forceUpdate = forceUpdateGeogenic)
            ##
            prepareGeogenicEmis.addGeogenicFluxes(dates = dates, doms = domains,
                                                metDir = metDir,
                                                ctmDir = ctmDir, CMAQdir = CMAQdir,
                                                mechCMAQ = mechCMAQ, mcipsuffix = APPL,
                                                forceUpdate = forceUpdateGeogenic)

        # if addCarbonTracker:
        #     print("Check whether CarbonTracker emission files exist ...")
        #     carbontracker_emis_files_exist = prepareCarbonTrackerEmis.checkCarbonTrackerEmisFilesExist(dates = dates, doms = domains, ctmDir = ctmDir)
        #     print("\t... result =", carbontracker_emis_files_exist)
        #     if (not carbontracker_emis_files_exist) or forceUpdateCarbonTracker:
        #         print("Prepare carbontracker emissions")
        #         prepareCarbonTrackerEmis.prepareCarbonTrackerEmis(dates = dates, doms = domains,
        #                                                CarbonTrackerFile = CarbonTrackerFile,
        #                                                metDir = metDir, ctmDir = ctmDir,
        #                                                mcipsuffix = APPL,
        #                                                sectors = carbonTrackerSectors,
        #                                                sectorsIsOcean = carbonTrackerSectorsIsOcean,
        #                                                add_sector_vars = add_sector_vars,
        #                                                forceUpdate = forceUpdateCarbonTracker)
        #     ##
        #     prepareCarbonTrackerEmis.addCarbonTrackerFluxes(dates = dates, doms = domains,
        #                                         metDir = metDir,
        #                                         ctmDir = ctmDir, CMAQdir = CMAQdir,
        #                                         mechCMAQ = mechCMAQ, mcipsuffix = APPL,
        #                                         forceUpdate = forceUpdateCarbonTracker)

        if addMiningPointSource:
            print("Check whether mining point source emission files exist ...")
            mining_emis_files_exist = preparePointSourceEmis.checkPointSourceEmisFilesExist (dates = dates, doms = domains, ctmDir = ctmDir, prefix = 'mining_emis')
            print("\t... result =", mining_emis_files_exist)
            if (not mining_emis_files_exist) or forceUpdateMiningPointSource:
                print("Prepare mining emissions")
                preparePointSourceEmis.preparePointSourceEmis(dates = dates,
                                                              doms = domains,
                                                              pointSourceCsvFile = miningPointSourceFile,
                                                              metDir = metDir,
                                                              ctmDir = ctmDir,
                                                              mcipsuffix = APPL,
                                                              emis_col = 'CH4_kg_4',
                                                              prefix = 'mining_emis',
                                                              forceUpdate = forceUpdateMiningPointSource)
            ##
            preparePointSourceEmis.addSurfaceFluxes(dates = dates,
                                                    doms = domains,
                                                    ctmDir = ctmDir,
                                                    prefix = 'mining_emis',
                                                    combined_prefix = 'combined_emis',
                                                    added_attribute = 'mining_emis_added',
                                                    forceUpdate = forceUpdateMiningPointSource)

    # if prepareICandBC or forceUpdateICandBC:
    #     ## prepare the template boundary condition concentration files
    #     ## from profiles using BCON
    #     templateBconFiles = configureRunScripts.prepareTemplateBconFiles(date = dates[0], domains = domains, ctmDir = ctmDir, metDir = metDir, CMAQdir = CMAQdir, CFG = run, mech  = mechCMAQ, GridNames = GridNames, mcipsuffix = APPL, scripts = scripts, forceUpdate = forceUpdateICandBC)
    #     ## prepare the template initial condition concentration files
    #     ## from profiles using ICON
    #     templateIconFiles = configureRunScripts.prepareTemplateIconFiles(date = dates[0], domains = domains, ctmDir = ctmDir, metDir = metDir, CMAQdir = CMAQdir, CFG = run, mech  = mechCMAQ, GridNames = GridNames, mcipsuffix = APPL, scripts = scripts, forceUpdate = forceUpdateICandBC)
    #     ## use the template initial and boundary condition concentration
    #     ## files and populate them with values from CAMS output
    #     interpolateFromCams.interpolateFromCamsToCmaqGrid(dates = dates, doms = domains, mech = mech, inputCamsFile = inputCamsFile, templateIconFiles = templateIconFiles, templateBconFiles = templateBconFiles, metDir = metDir, ctmDir = ctmDir, GridNames = GridNames, mcipsuffix = APPL, forceUpdate = forceUpdateICandBC)

    # if prepareRunScripts:
    #     print("Prepare BCON, CCTM, main run, PBS and cleanup scripts")
    #     ## prepare the scripts for CCTM
    #     configureRunScripts.prepareCctmRunScripts(dates = dates, domains = domains, ctmDir = ctmDir, metDir = metDir, CMAQdir = CMAQdir, CFG = run, mech = mech, mechCMAQ = mechCMAQ, GridNames = GridNames, mcipsuffix = APPL, scripts = scripts, EXEC = cctmExec, SZpath = ctmDir, cmaqVersionCode = cmaqVersionCode, nhours = nhoursPerRun, printFreqHours = printFreqHours, forceUpdate = forceUpdateRunScripts)
    #     ## prepare the scripts for BCON
    #     configureRunScripts.prepareBconRunScripts(dates = dates, domains = domains, ctmDir = ctmDir, metDir = metDir, CMAQdir = CMAQdir, CFG = run, mech = mech, mechCMAQ = mechCMAQ, GridNames = GridNames, mcipsuffix = APPL, scripts = scripts, EXEC = cctmExec, forceUpdate = forceUpdateRunScripts)
        
    #     ## prepare the cleanup scripts
    #     configureRunScripts.prepareCleanupScripts(dates = dates, domains = domains, ctmDir = ctmDir, GridNames = GridNames, run = run, EXEC = cctmExec, mech = mech, compressScript = compressScript, scripts = scripts, forceUpdate = forceUpdateRunScripts)
        
    #     ## prepare the main run script
    #     configureRunScripts.prepareMainRunScript(dates = dates, domains = domains, ctmDir = ctmDir, CMAQdir = CMAQdir, scripts = scripts, doCompress = doCompress, compressScript = compressScript, doCleanup = doCleanup, run = run, case = monthCase, EXEC = cctmExec, forceUpdate = forceUpdateRunScripts, restartDate = restartDate, restartDom = restartDom)
        
    #     ## prepare the PBS submission script
    #     configureRunScripts.preparePbsRunScript(ctmDir = ctmDir, scripts = scripts, run = run, case = monthCase, cmaqEnvScript = cmaqEnvScript, forceUpdate = forceUpdateRunScripts)
    ##
    return

if __name__ == "__main__":
    main()
