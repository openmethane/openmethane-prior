'''Functions to check folders, files and attributes from MCIP output
'''
import os
import numpy
import netCDF4
import glob
import warnings
import helper_funcs
import shutil
import pdb

def checkInputMetAndOutputFolders(ctmDir,metDir,dates,domains):
    '''
    Check that MCIP inputs are present, and create directories for CCTM input/output if need be

    Args:
        ctmDir: base directory for the CCTM inputs and outputs
        metDir: base directory for the MCIP output
        dates: list of datetime objects, one per date MCIP and CCTM output should be defined
        domains: list of domain names (e.g. ['d01', 'd02'] )

    Returns:
        True if all the required MCIP files are present, False if not
    '''
    allMcipFilesFound = True
    if not os.path.exists(ctmDir):
        os.mkdir(ctmDir)
    ##
    for idate, date in enumerate(dates):
        yyyyjjj = date.strftime('%Y%j')
        yyyymmdd = date.strftime('%Y%m%d')
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')
        yyyymmddhh = date.strftime('%Y%m%d%H')
        ##
        parent_chemdir = '{}/{}'.format(ctmDir,yyyymmdd_dashed)
        ## create output destination
        if not os.path.exists(parent_chemdir):
            os.mkdir(parent_chemdir)
        for idomain, domain in enumerate(domains):
            mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,domain)
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,domain)
            if not os.path.exists(mcipdir):
                warnings.warn("MCIP output directory not found at {} ... ".format(mcipdir))
            ## create output destination
            if not os.path.exists(chemdir):
                os.mkdir(chemdir)
            ## check that the MCIP GRIDDESC file is present
            griddescFilePath = '{}/GRIDDESC'.format(mcipdir)
            if not os.path.exists(griddescFilePath):
                warnings.warn("GRIDDESC file not found at {} ... ".format(griddescFilePath))
                allMcipFilesFound = False
            ## check that the other MCIP output files are present
            filetypes = ['GRIDBDY2D', 'GRIDCRO2D', 'GRIDDOT2D', 'METBDY3D', 'METCRO2D', 'METCRO3D', 'METDOT3D']
            APPL = []
            for filetype in filetypes:
                matches = glob.glob("{}/{}_*".format(mcipdir,filetype))
                if len(matches) == 0:
                    warnings.warn("{} file not found in folder {} ... ".format(filetype,mcipdir))
                    allMcipFilesFound = False
                elif len(matches) > 1:
                    warnings.warn("Multiple files match the {} pattern in {}, using file {}".format(filetype,mcipdir,matches[0]))
                else:
                    APPL.append(matches[0].split('/')[-1].replace('{}_'.format(filetype),''))
                    if not all([appl == APPL[0] for appl in APPL]):
                        raise RuntimeError("MCIP suffices in folder {} are not consistent ... ".format(filetype,mcipdir))
    ##
    return allMcipFilesFound

def getMcipGridNames(metDir, dates, domains):
    '''Get grid names from the MCIP GRIDDESC file

    Args: 
        metDir: base directory for the MCIP output
        dates: list of datetime objects for the dates to run
        domains: list of which domains should be run?

    Returns: 
        CoordNames: list of MCIP scenario tags (one per domain)
        GridNames: list of MCIP map projection names (one per domain)
        APPL: list of MCIP grid names (one per domain)
    '''
    
    date = dates[0]
    yyyymmdd_dashed = date.strftime('%Y-%m-%d')
    ##
    ndom = len(domains)
    ##
    CoordNames = [[]] * ndom
    GridNames = [[]] * ndom
    APPL = [[]] * ndom
    for idomain, domain in enumerate(domains):
        mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,domain)
        griddescFilePath = '{}/GRIDDESC'.format(mcipdir)
        if not os.path.exists(griddescFilePath):
            raise RuntimeError("GRIDDESC file not found at {} ... ".format(griddescFilePath))
        f = open(griddescFilePath)
        lines = f.readlines()
        f.close()
        CoordNames[idomain] = lines[1].strip().replace("'","").replace('"','')
        GridNames[idomain] = lines[4].strip().replace("'","").replace('"','')
        ## find the APPL suffix
        filetype = 'GRIDCRO2D'
        matches = glob.glob("{}/{}_*".format(mcipdir,filetype))
        if len(matches) == 0:
            raise RuntimeError("{} file not found in folder {} ... ".format(filetype,mcipdir))
        ##
        APPL[idomain] = matches[0].split('/')[-1].replace('{}_'.format(filetype),'')
    ##
    return CoordNames, GridNames, APPL

def checkWrfMcipDomainSizes(metDir, date, domains, wrfDir = None):
    '''Cross check the WRF and MCIP domain sizes

    Args:
        metDir: base directory for the MCIP output
        date: the date in question
        domains: list of domains
        wrfDir:directory containing wrfout_* files

    Returns:
        nx_wrf: length of the x-dimension for the WRF grid
        ny_wrf: length of the y-dimension for the WRF grid
        nx_cmaq: length of the x-dimension for the CMAQ grid
        ny_cmaq: length of the y-dimension for the CMAQ grid
        ix0: the index in the WRF grid of the first CMAQ grid-point in the x-direction
        iy0: the index in the WRF grid of the first CMAQ grid-point in the y-direction
        ncolsin: length of the x-dimension for the CMAQ grid
        nrowsin: length of the y-dimension for the CMAQ grid
    '''
    
    yyyymmdd_dashed = date.strftime('%Y-%m-%d')
    ##
    ndom = len(domains)
    ##
    nx_wrf = numpy.zeros((ndom,),dtype = int)
    ny_wrf = numpy.zeros((ndom,),dtype = int)
    nx_cmaq = numpy.zeros((ndom,),dtype = int)
    ny_cmaq = numpy.zeros((ndom,),dtype = int)
    ix0  = numpy.zeros((ndom,),dtype = int)
    iy0 = numpy.zeros((ndom,),dtype = int)
    ncolsin = numpy.zeros((ndom,),dtype = int)
    nrowsin = numpy.zeros((ndom,),dtype = int)
    for idomain, domain in enumerate(domains):
        mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,domain)
        ## find the APPL suffix
        filetype = 'GRIDCRO2D'
        matches = glob.glob("{}/{}_*".format(mcipdir,filetype))
        if len(matches) == 0:
            raise RuntimeError("{} file not found in folder {} ... ".format(filetype,mcipdir))
        ##
        APPL = matches[0].split('/')[-1].replace('{}_'.format(filetype),'')
        ## open the GRIDCRO2D file
        gridcro2dfilepath = "{}/{}_{}".format(mcipdir,filetype,APPL)
        nc = netCDF4.Dataset(gridcro2dfilepath)
        ## read in the latitudes and longitudes
        mcipLat = nc.variables['LAT'][0,0,:,:]
        mcipLon = nc.variables['LON'][0,0,:,:]
        nc.close()
        ## find a WRF file
        matches = glob.glob("{}/wrfout_{}_*".format(mcipdir,domain))
        if len(matches) == 0:
            if type(wrfDir) == type(None):
                raise RuntimeError("No files matched the pattern wrfout_{}_* in folder {}, and no alternative WRF directory was provided...".format(domain,mcipdir))
            elif len(matches) > 1:
                warnings.warn("Multiple files match the pattern wrfout_{}_* in folder {}, using file {}".format(domain,mcipdir,matches[0]))
            else:
                matches = glob.glob("{}/wrfout_{}_*".format(wrfDir,domain))
                if len(matches) == 0:
                    raise RuntimeError("No files matched the pattern wrfout_{}_* the folders {} and {} ...".format(domain,mcipdir, wrfDir))
                elif len(matches) > 1:
                    warnings.warn("Multiple files match the pattern wrfout_{}_* in folder {}, using file {}".format(domain,wrfDir,matches[0]))
        ##
        wrfFile = matches[0]
        nc = netCDF4.Dataset(wrfFile)
        ## read in the latitudes and longitudes
        wrfLat = nc.variables['XLAT'][0,:,:]
        wrfLon = nc.variables['XLONG'][0,:,:]
        nc.close()

        ix = [0,0,-1,-1]
        iy = [0,-1,0,-1]
        ncorn = len(ix)
        icorn = [0] * ncorn
        jcorn = [0] * ncorn
        for i in range(ncorn):
            dists = helper_funcs.getDistanceFromLatLonInKm(mcipLat[ix[i],iy[i]],mcipLon[ix[i],iy[i]],wrfLat,wrfLon)
            minidx = numpy.argmin(dists)
            mindist = dists.min()
            if mindist > 0.5:
                warnings.warn("Distance between grid-points was {} km for domain {}".format(mindist,domain))
            icorn[i], jcorn[i] = numpy.unravel_index(minidx, wrfLat.shape)
        if icorn[0] != icorn[1] or icorn[2] != icorn[3] or jcorn[0] != jcorn[2] or jcorn[1] != jcorn[3]:
            print("icorn =",icorn)
            print("jcorn =",jcorn)
            raise RuntimeError("Indices of the corner points not completely consistent between the WRF and MCIP grids for domain {}".format(domain))

        nx_wrf[idomain] = wrfLat.shape[0] 
        ny_wrf[idomain] = wrfLat.shape[1]
        nx_cmaq[idomain] = mcipLat.shape[0] 
        ny_cmaq[idomain] = mcipLat.shape[1]
        ix0[idomain] = icorn[0]
        iy0[idomain] = jcorn[0]
        ncolsin[idomain] = mcipLat.shape[1]
        nrowsin[idomain] = mcipLat.shape[0]

    return nx_wrf, ny_wrf, nx_cmaq, ny_cmaq, ix0, iy0, ncolsin, nrowsin

def copyFromPreviousCtmDir(oldCtmDir, newCtmDir, dates, domains,
                           oldRun, newRun,
                           CMAQmech, mech, mechMEGAN, GridNames, 
                           copyEFMAPS = False,
                           copyLAIS = False,
                           copyPFTS = False,
                           copySURFZONE = False,
                           copyJTABLE = False,
                           copyTemplateIC = False,
                           copyTemplateBC = False,
                           copyBCON = False,
                           copyICON = False,
                           copyFIREEMIS = False,
                           copyMEGANEMIS = False,
                           copyMERGEDEMIS = False,
                           link = False):
    '''Copy CMAQ inputs from a previous run

    Args:
        oldCtmDir: base directory for the existing CCTM inputs and outputs
        newCtmDir: base directory for the new CCTM inputs and outputs
        dates: list of datetime objects, one per date MCIP and CCTM output should be defined
        domains: list of which domains should be run?
        oldRun: name of the old simulation, appears in some filenames
        newRun: name of the new simulation, appears in some filenames
        CMAQmech: name of chemical mechanism given to CMAQ
        mech: name of chemical mechanism to appear in filenames
        GridNames: list of MCIP map projection names (one per domain)
        copyEFMAPS = copy the EFMAPS files?
        copyLAIS = copy the LAIS files?
        copyPFTS = copy the PFTS files
        copySURFZONE = copy the surfzone files?
        copyJTABLE = copy the JTABLE files?
        copyTemplateIC = copy the template IC files
        copyTemplateBC = copy the template BC files
        copyBCON = copy the daily BC files
        copyICON = copy the daily IC files
        copyFIREEMIS = copy the fire emissions
        copyMEGANEMIS = copy the megan emissions
        copyMERGEDEMIS = copy the merged emissions
        link = if 'True', symbolic links are made rather than copies

    Returns:
        Nothing
    '''

    def copyFunc(source, dest, link, strict = True):
        if strict and (not os.path.exists(source)):
            raise RuntimeError("File {} expected but not found ... ".format(source))
        if link:
            os.link(source, dest)
        else:
            shutil.copy(source, dest)
        return
    
    if not os.path.exists(newCtmDir):
        os.mkdir(newCtmDir)
    ##
    if not os.path.exists(oldCtmDir):
        raise RuntimeError("CTM folder {} expected but not found ... ".format(oldCtmDir))
    ##
    for idate, date in enumerate(dates):
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')
        ##
        parent_chemdir = '{}/{}'.format(newCtmDir,yyyymmdd_dashed)
        ## create output destination
        if not os.path.exists(parent_chemdir):
            os.mkdir(parent_chemdir)
        for idomain, domain in enumerate(domains):
            chemdir = '{}/{}/{}'.format(newCtmDir,yyyymmdd_dashed,domain)
            ## create output destination
            if not os.path.exists(chemdir):
                os.mkdir(chemdir)
    ##
    for idomain, domain in enumerate(domains):
        grid = GridNames[idomain]
        if copyEFMAPS:
            source = '{}/EFMAPS.{}_{}.ncf'.format(oldCtmDir,oldRun,domain)
            dest   = '{}/EFMAPS.{}_{}.ncf'.format(newCtmDir,newRun,domain)
            copyFunc(source, dest, link)
        if copyLAIS:
            source = '{}/LAIS46.{}_{}.ncf'.format(oldCtmDir,oldRun,domain)
            dest   = '{}/LAIS46.{}_{}.ncf'.format(newCtmDir,newRun,domain)
            copyFunc(source, dest, link)
        if copyPFTS:
            source = '{}/PFTS16.{}_{}.ncf'.format(oldCtmDir,oldRun,domain)
            dest   = '{}/PFTS16.{}_{}.ncf'.format(newCtmDir,newRun,domain)
            copyFunc(source, dest, link)
        if copySURFZONE:
            source = '{}/surfzone_{}.nc'.format(oldCtmDir,domain)
            dest   = '{}/surfzone_{}.nc'.format(newCtmDir,domain)
            copyFunc(source, dest, link)

        if copyTemplateBC:
            source = '{}/template_bcon_profile_{}_{}.nc'.format(oldCtmDir,CMAQmech,domain)
            dest   = '{}/template_bcon_profile_{}_{}.nc'.format(newCtmDir,CMAQmech,domain)
            copyFunc(source, dest, link)
            
        if copyTemplateIC:
            source = '{}/template_icon_profile_{}_{}.nc'.format(oldCtmDir,CMAQmech,domain)
            dest   = '{}/template_icon_profile_{}_{}.nc'.format(newCtmDir,CMAQmech,domain)
            copyFunc(source, dest, link)
            
    for idate, date in enumerate(dates):
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')
        yyyyjjj = date.strftime('%Y%j')
        ##
        if copyJTABLE:
            oldDateDir = '{}/{}'.format(oldCtmDir,yyyymmdd_dashed)
            newDateDir = '{}/{}'.format(newCtmDir,yyyymmdd_dashed)
            source = '{}/JTABLE_{}'.format(oldDateDir,yyyyjjj)
            dest   = '{}/JTABLE_{}'.format(newDateDir,yyyyjjj)
            copyFunc(source, dest, link)
        ##
        for idomain, domain in enumerate(domains):
            newchemdir = '{}/{}/{}'.format(newCtmDir,yyyymmdd_dashed,domain)
            oldchemdir = '{}/{}/{}'.format(oldCtmDir,yyyymmdd_dashed,domain)
            ##
            if copyBCON:
                source = '{}/BCON.{}.{}.{}.nc'.format(oldchemdir,dom,grid,mech)
                dest   = '{}/BCON.{}.{}.{}.nc'.format(newchemdir,dom,grid,mech)
                copyFunc(source, dest, link, strict = False)
            
            if copyICON:
                source = '{}/ICON.{}.{}.{}.nc'.format(oldchemdir,dom,grid,mech)
                dest   = '{}/ICON.{}.{}.{}.nc'.format(newchemdir,dom,grid,mech)
                copyFunc(source, dest, link, strict = False)

            if copyFIREEMIS:
                source = '{}/fire_emis_{}.nc'.format(oldchemdir,dom)
                dest   = '{}/fire_emis_{}.nc'.format(newchemdir,dom)
                copyFunc(source, dest, link)

            if copyMEGANEMIS:
                source = '{}/MEGANv2.10.{}.{}.{}.ncf'.format(oldchemdir,grid,mechMEGAN,yyyyjjj)
                dest   = '{}/MEGANv2.10.{}.{}.{}.ncf'.format(newchemdir,grid,mechMEGAN,yyyyjjj)
                copyFunc(source, dest, link)

            if copyMERGEDEMIS:
                source = '{}/mergedEmis_{}_{}_{}.nc'.format(oldchemdir,yyyymmdd_dashed,dom,mech)
                dest   = '{}/mergedEmis_{}_{}_{}.nc'.format(newchemdir,yyyymmdd_dashed,dom,mech)
                copyFunc(source, dest, link)
            
    
    
