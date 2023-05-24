'''Remap GFAS fire emissions to the CMAQ domain
'''
import os
import re
import copy
import numpy
import datetime
import netCDF4
from shapely import geometry
import bisect
import csv
import glob
import helper_funcs
import pdb

# ch4fire       Carbon Dioxide -> CH4


def redistribute_spatially(LATshape, nz, ind_x, ind_y, coefs, idom, subset, heights, ZH, HT, areas):
    '''Redistribute GFAS emissions horizontally and vertically - this little function does most of the work

    Args:
        LATshape: shape of the LAT variable
        nz: Number of vertical levels in the CMAQ grid
        ind_x: x-indices in the GFAS domain corresponding to indices in the CMAQ domain
        ind_y: y-indices in the GFAS domain corresponding to indices in the CMAQ domain
        coefs: Area-weighting coefficients to redistribute the emissions
        idom: Index of the domain
        subset: the GFAS emissionsx
        heights: Injection heights
        ZH: Geopotential heights in the CMAQ domain
        HT: Terrain heights in the CMAQ domain
        areas: Areas of GFAS grid-cells in units of m^2

    Returns: 
        gridded: concentrations on the 3D CMAQ grid
        
    '''
    
    ##
    nxyz = [nz] + list(LATshape)
    gridded = numpy.zeros(nxyz,dtype = numpy.float32)
    ij = -1
    for i in range(LATshape[0]):
        for j in range(LATshape[1]):
            ij += 1
            for k in range(len(ind_x[idom][ij])):
                ix      = ind_x[idom][ij][k]
                iy      = ind_y[idom][ij][k]
                if subset[iy,ix] == 0.0:
                    continue
                ## find the injection level
                ilev = bisect.bisect_right(ZH[:,i,j] + HT[i,j], heights[iy,ix])
                ## kg/s                      kg/m2/s        fraction of GFAS cell covered   m2/gridcell      layer fraction
                gridded[0:(ilev+1),i,j] += subset[iy,ix] *        coefs[idom][ij][k]   * areas[iy,ix]   /  float(ilev+1)
    ##
    return gridded

def checkFireEmisFilesExist(dates,doms,ctmDir):
    '''Check if GFAS fire emission files already exist

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        ctmDir: base directory for the CCTM inputs and outputs

    Returns:
        Boolean (True/False) for whether all the GFAS emission files exist
    '''
    ##
    fire_emis_files_exist = True
    for date in dates:
        yyyymmddhh = date.strftime('%Y%m%d%H')
        yyyymmdd = date.strftime('%Y-%m-%d')
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')
        for idom, dom in enumerate(doms):
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            outputFireEmisFile = '{}/fire_emis_{}.nc'.format(chemdir,dom)
            exists = os.path.exists(outputFireEmisFile)
            if not exists:
                fire_emis_files_exist = False
                print("File {} not found - will rerun fire emission scripts...".format(outputFireEmisFile))
                ##
                break
        ##
        if not fire_emis_files_exist:
            break
    return fire_emis_files_exist



def prepareFireEmis(dates, doms, GFASfolder, GFASfile, metDir, ctmDir, CMAQdir, mechCMAQ, mcipsuffix, specTableFile, forceUpdate):
    '''Function to remap GFAS fire emissions to the CMAQ domain

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        GFASfolder: directory containing the GFAS data
        GFASfile: the file (within directory GFASfolder) containing GFAS fire emission data
        metDir: base directory for the MCIP output
        ctmDir: base directory for the CCTM inputs and outputs
        CMAQdir: base directory for the CMAQ model
        mechCMAQ: name of chemical mechanism given to CMAQ
        mcipsuffix: Suffix for the MCIP output files
        specTableFile: speciation file, mapping GFAS to CMAQ 
        forceUpdate: Force the update of GFAS emission files

    Returns:
        Nothing
    '''


    print("Read the species table file")
    f = open(specTableFile, "r")
    line = f.readline() ## skip the first line
    species_map = {}
    for line in f:
        if len(line) <= 1:
            continue
        words = line.split(";")
        GFASspec = words[0].strip()
        CMspec = [s.strip() for s in words[1].split(",")]
        coef = [float(s) for s in words[2].split(",")]
        species_map[GFASspec] = {'spec':CMspec, 'coef':coef}
    f.close()

    print("Read molecular weights and calculate the conversion factors from GFAS to CMAQ")
    nmlfiles = glob.glob('{}/models/CCTM/MECHS/{}/*_{}.nml'.format(CMAQdir,mechCMAQ,mechCMAQ))
    molWts = {}
    for nmlfile in nmlfiles:
        f = open(nmlfile)
        lines = f.readlines()
        f.close()
        lines = [l.strip() for l in lines]
        ihead = [i for i,s in enumerate(lines) if s.find("'SPC:MOLWT:") >= 0]
        if not len(ihead) == 1:
            print(nmlfile)
            raise RuntimeError("Could not read the header of the namelist file...")
        ##
        ihead = ihead[0] + 2
        itail = [i for i,s in enumerate(lines) if s == "/"]
        if not len(itail) == 1:
            print(nmlfile)
            raise RuntimeError("Could not read the tail of the namelist file...")
        ##
        itail = itail[0]
        if ihead > itail:
            print(nmlfile)
            raise RuntimeError("Head should come before the tail in the namelist file...")
        ##
        for l in lines[ihead:itail]:
            l = l.replace("'",'')
            parts = l.split(':')
            spec = parts[0]
            molwt = float(parts[1])
            molWts[spec] = molwt

    ## unique set of species
    ## flatten list-of-lists following: http://stackoverflow.com/a/952946/356426
    cmaqSpecList = list(set(sum([species_map[gfasspec]['spec'] for gfasspec in list(species_map.keys())],[])))
    cmaqSpecList.sort()

    unit_factor = {}
    cmaqSpecIsAerosol = {}
    for spec in cmaqSpecList:
        ## we assume that CMAQ species end in the letters I, J, K if
        ## and only if they represent aerosol components
        cmaqSpecIsAerosol[spec] = spec[-1] in ['I','J','K']
        if cmaqSpecIsAerosol[spec]:
            ## g/kg
            unit_factor[spec] = 1.0e3
        else:
            ## moles/kg      ~   moles/g              g/kg
            unit_factor[spec] = (1.0/molWts[spec]) * 1.0e3

            
    attrnames = ['IOAPI_VERSION', 'EXEC_ID', 'FTYPE', 'CDATE', 'CTIME', 'WDATE', 'WTIME',
                 'SDATE', 'STIME', 'TSTEP', 'NTHIK', 'NCOLS', 'NROWS', 'NLAYS', 'NVARS',
                 'GDTYP', 'P_ALP', 'P_BET', 'P_GAM', 'XCENT', 'YCENT', 'XORIG', 'YORIG',
                 'XCELL', 'YCELL', 'VGTYP', 'VGTOP', 'VGLVLS', 'GDNAM', 'UPNAM', 'VAR-LIST', 'FILEDESC']
    unicodeType = type('foo')

    print("Read grid parameters from the GFAS file")
    GFASpath = '{}/{}'.format(GFASfolder, GFASfile)
    exists = os.path.exists(GFASpath)
    if not exists:
        raise RuntimeError("GFAS file {} not found...".format(GFASpath))
    
    ncin = netCDF4.Dataset(GFASpath, 'r', format='NETCDF4')
    latGfas  = numpy.around(numpy.float64(ncin.variables['g0_lat_1'][:]),3)
    lonGfas  = numpy.around(numpy.float64(ncin.variables['g0_lon_2'][:]),3)
    dlatGfas = latGfas[0] - latGfas[1]
    dlonGfas = lonGfas[1] - lonGfas[0]
    lonGfas_edge = numpy.zeros((len(lonGfas) + 1))
    lonGfas_edge[0:-1] = lonGfas - dlonGfas/2.0
    lonGfas_edge[-1] = lonGfas[-1] + dlonGfas/2.0
    lonGfas_edge = numpy.around(lonGfas_edge,2)
    gfasHoursSince1900 = ncin.variables['initial_time0_hours'][:]
    basedate = datetime.datetime(1900,1,1,0,0,0)
    gfasTimes = netCDF4.num2date( ncin.variables['initial_time0_hours'][:], ncin.variables['initial_time0_hours'].getncattr('units') )
    ## gfasTimes = [basedate + datetime.timedelta(seconds = h*3600) for h in gfasHoursSince1900]

    latGfas_edge = numpy.zeros((len(latGfas) + 1))
    latGfas_edge[0:-1] = latGfas + dlatGfas/2.0
    latGfas_edge[-1] = latGfas[-1] - dlatGfas/2.0
    latGfas_edge = numpy.around(latGfas_edge,2)

    nlonGfas = len(lonGfas)
    nlatGfas = len(latGfas)

    latGfasrev = latGfas[::-1]
    latGfasrev_edge = latGfas_edge[::-1]

    
    ## get the number of vertical levels in the MCIP (and hence CMAQ) files
    print("Read grid parameters from the MCIP file")
    date = dates[0]
    idom = 0
    dom = doms[idom]
    yyyymmddhh = date.strftime('%Y%m%d%H')
    yyyymmdd_dashed = date.strftime('%Y-%m-%d')
    mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,dom)
    metFile = '{}/METCRO3D_{}'.format( mcipdir,mcipsuffix[idom])
    exists = os.path.exists(metFile)
    if not exists:
        raise RuntimeError("MCIP file {} not found...".format(metFile))
    ##
    ncmet = netCDF4.Dataset(metFile, 'r', format='NETCDF4')
    nz = len(ncmet.dimensions['LAY'])
    ncmet.close()

    print("Calculate grid cell areas for the GFAS grid")
    areas = numpy.zeros((nlatGfas,nlonGfas))
    for ix in range(nlonGfas):
        for iy in range(nlatGfas):
            areas[iy,ix] = helper_funcs.area_of_rectangle_m2(latGfas_edge[iy],latGfas_edge[iy+1],lonGfas_edge[ix],lonGfas_edge[ix+1])


    indxPath = "{}/GFAS_ind_x.p.gz".format(ctmDir)
    indyPath = "{}/GFAS_ind_y.p.gz".format(ctmDir)
    coefsPath = "{}/GFAS_coefs.p.gz".format(ctmDir)
    if os.path.exists(indxPath) and os.path.exists(indyPath) and os.path.exists(coefsPath) and (not forceUpdate):
        ind_x = helper_funcs.load_zipped_pickle( indxPath )
        ind_y = helper_funcs.load_zipped_pickle( indyPath )
        coefs = helper_funcs.load_zipped_pickle( coefsPath )
        ##
        domShape = []
        for idom, dom in enumerate(doms):
            croFile = '{}/{}/{}/GRIDCRO2D_{}'.format(metDir,yyyymmdd_dashed,dom,mcipsuffix[idom])
            nccro= netCDF4.Dataset(croFile, 'r', format='NETCDF4')
            LAT  = nccro.variables['LAT'][:].squeeze()
            domShape.append(LAT.shape)
            nccro.close()
    else:
        ind_x = []
        ind_y = []
        coefs = []
        count = []
        ## loop through the domains, calculating the indices and coefficients
        domShape = []
        for idom, dom in enumerate(doms):
            print("Calculate the indices and coefficients for domain",dom)

            ind_x.append([])
            ind_y.append([])
            coefs.append([])

            croFile = '{}/{}/{}/GRIDCRO2D_{}'.format(metDir,yyyymmdd_dashed,dom,mcipsuffix[idom])
            dotFile = '{}/{}/{}/GRIDDOT2D_{}'.format(metDir,yyyymmdd_dashed,dom,mcipsuffix[idom])
            ncdot= netCDF4.Dataset(dotFile, 'r', format='NETCDF4')
            nccro= netCDF4.Dataset(croFile, 'r', format='NETCDF4')

            LAT  = nccro.variables['LAT'][:].squeeze()
            LON  = nccro.variables['LON'][:].squeeze()
            LATD = ncdot.variables['LATD'][:].squeeze()
            LOND = ncdot.variables['LOND'][:].squeeze()

            domShape.append(LAT.shape)

            count2  = numpy.zeros(LAT.shape,dtype = numpy.float32)

            for i in range(LAT.shape[0]):
                for j in range(LAT.shape[1]):
                    IND_X = []
                    IND_Y = []
                    COEFS = []

                    xvals = numpy.array([LOND[i,  j], LOND[i,  j+1], LOND[i+1,  j], LOND[i+1,  j+1]])
                    yvals = numpy.array([LATD[i,  j], LATD[i,  j+1], LATD[i+1,  j], LATD[i+1,  j+1]])

                    xy = [[LOND[i,  j],LATD[i,  j]],[LOND[i,  j+1],LATD[i,  j+1]],[LOND[i+1,  j+1],LATD[i+1,  j+1]],[LOND[i+1,  j],LATD[i+1,  j]]]
                    CMAQ_gridcell = geometry.Polygon(xy)

                    xmin = numpy.min(xvals)
                    xmax = numpy.max(xvals)
                    ymin = numpy.min(yvals)
                    ymax = numpy.max(yvals)

                    ixminl = bisect.bisect_right(lonGfas_edge,xmin)
                    ixmaxr = bisect.bisect_right(lonGfas_edge,xmax)
                    iyminl = nlatGfas - bisect.bisect_right(latGfasrev_edge,ymax)
                    iymaxr = nlatGfas - bisect.bisect_right(latGfasrev_edge,ymin)

                    for ix in range(max(0,ixminl-1),min(nlonGfas,ixmaxr)):
                        for iy in range(max(0,iyminl),min(nlatGfas,iymaxr+1)):
                            gfas_gridcell = geometry.box(lonGfas_edge[ix],latGfas_edge[iy],lonGfas_edge[ix+1],latGfas_edge[iy+1])
                            if CMAQ_gridcell.intersects(gfas_gridcell):
                                intersection = CMAQ_gridcell.intersection(gfas_gridcell)
                                weight1 = intersection.area/CMAQ_gridcell.area ## fraction of CMAQ cell covered
                                weight2 = intersection.area/gfas_gridcell.area ## fraction of GFAS cell covered
                                count2[ i,j] += weight2
                                IND_X.append(ix)
                                IND_Y.append(iy)
                                COEFS.append(weight2)
                    ind_x[idom].append(IND_X)
                    ind_y[idom].append(IND_Y)
                    # COEFS = numpy.array(COEFS)
                    # COEFS = COEFS / COEFS.sum()
                    coefs[idom].append(COEFS)
            count.append(count2)
            ncdot.close()
            nccro.close()
        ##
        helper_funcs.save_zipped_pickle(ind_x, indxPath )
        helper_funcs.save_zipped_pickle(ind_y, indyPath )
        helper_funcs.save_zipped_pickle(coefs, coefsPath )

    template = []
    for idom, dom in enumerate(doms):
        template.append(numpy.zeros((nz, domShape[idom][0], domShape[idom][1],)))

    cmaqData = {}
    for spec in cmaqSpecList:
        cmaqData[spec] = copy.copy(template)

    for date in dates:
        yyyyjjj = int(date.strftime('%Y%j'))
        yyyymmddhh = date.strftime('%Y%m%d%H')
        yyyymmdd = date.strftime('%Y-%m-%d')
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')

        Date = datetime.datetime(date.year, date.month, date.day, 0, 0, 0)
        idate = bisect.bisect_right(gfasTimes,Date)

        if idate == len(gfasTimes):
            print("")
            print("WARNING: at boundary of GFAS times: will use previous date...")
            print("")
            idate = len(gfasTimes)-1
        elif idate > len(gfasTimes):
            raise RuntimeError("idate > len(gfasTimes)")

        ## reset values
        for spec in cmaqSpecList:
            for idom, dom in enumerate(doms):
                cmaqData[spec][idom][:] = 0.0

        for idom, dom in enumerate(doms):
            print("Calculate the emissions for domain",dom,"and date",yyyymmdd)
            # t0 = time.time()

            mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,dom)
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            croFile = '{}/GRIDCRO2D_{}'.format(mcipdir,mcipsuffix[idom])
            dotFile = '{}/GRIDDOT2D_{}'.format(mcipdir,mcipsuffix[idom])
            metFile = '{}/METCRO3D_{}'.format( mcipdir,mcipsuffix[idom])
            outputFireEmisFile = '{}/fire_emis_{}.nc'.format(chemdir,dom)
            ncdot = netCDF4.Dataset(dotFile, 'r', format='NETCDF4')
            nccro = netCDF4.Dataset(croFile, 'r', format='NETCDF4')
            ncmet = netCDF4.Dataset(metFile, 'r', format='NETCDF4')
            if os.path.exists(outputFireEmisFile):
                os.remove(outputFireEmisFile)

            print(outputFireEmisFile)
            ncout = netCDF4.Dataset(outputFireEmisFile, 'w', format='NETCDF4')
            lens = dict()
            outdims = dict()

            for k in list(nccro.dimensions.keys()):
                lens[k] = len(nccro.dimensions[k])

            LAT  = nccro.variables['LAT'][:].squeeze()
            ZF   = ncmet.variables['ZF'][:].mean(axis = 0)
            ZH   = ncmet.variables['ZH'][:].mean(axis = 0)
            HT   = nccro.variables['HT'][:].squeeze()

            area_factor = nccro.XCELL * nccro.YCELL ## m2 per grid-cell
            meanInjectionAltitudeNative = ncin.variables['MAMI_GDS0_SFC_ave24h'][idate,:,:] ## Mean altitude of maximum injection

            for gfasspec in list(species_map.keys()):
                subset = ncin.variables[gfasspec][idate,:,:]
                gridded = redistribute_spatially(LAT.shape, nz, ind_x, ind_y, coefs, idom, subset, meanInjectionAltitudeNative, ZH, HT, areas)
                ##
                nspecCmaq = len(species_map[gfasspec]['spec'])
                for ispec in range(nspecCmaq):
                    cmaqspec = species_map[gfasspec]['spec'][ispec]
                    fac = species_map[gfasspec]['coef'][ispec]
                    ## get the units right:
                    ## moles/s                                               kg/s      moles/kg             ## <- gases
                    ## g/s                                                   kg/s        g/kg               ## <- aerosols
                    cmaqData[cmaqspec][idom] = cmaqData[cmaqspec][idom] + gridded * unit_factor[cmaqspec] * fac

            nlay = 1
            nvar = 1
            lens['VAR'] = nvar
            lens['LAY'] = nz

            for k in list(ncdot.dimensions.keys()):
                outdims[k] = ncout.createDimension(k, lens[k])

            outvars = dict()
            outvars['TFLAG'] = ncout.createVariable('TFLAG', 'i4', ('TSTEP','VAR','DATE-TIME',))
            for spec in cmaqSpecList:
                outvars[spec] = ncout.createVariable(spec, 'f4', ('TSTEP', 'LAY', 'ROW', 'COL'), zlib = True, shuffle = False)
                outvars[spec].setncattr('long_name',"{:<16}".format(spec))
                if not cmaqSpecIsAerosol[spec]:
                    outvars[spec].setncattr('units',"{:<16}".format("moles/s"))
                else:
                    outvars[spec].setncattr('units',"{:<16}".format("g/s"))
                outvars[spec].setncattr('var_desc',"{:<80}".format("Emissions of " + spec))
                if cmaqData[spec][idom].min() < 0.0:
                    cmaqData[spec][idom][cmaqData[spec][idom] < 0.0] = 0.0
                outvars[spec][:] = numpy.float32(cmaqData[spec][idom])

            for a in attrnames:
                val = nccro.getncattr(a)
                if type(val) == unicodeType:
                    val = str(val)
                    ##
                ncout.setncattr(a,val)

            ncout.variables['TFLAG'][:] = 0
            outvars['TFLAG'].setncattr('long_name',"{:<16}".format('TFLAG'))
            outvars['TFLAG'].setncattr('units',"<YYYYDDD,HHMMSS>")
            outvars['TFLAG'].setncattr('var_desc',"Timestep-valid flags:  (1) YYYYDDD or (2) HHMMSS                                ")

            VarString = "".join([ "{:<16}".format(k) for k in cmaqSpecList ])
            ncout.setncattr('VAR-LIST',VarString)
            ncout.setncattr('GDNAM',"{:<16}".format('Sydney'))
            ncout.setncattr('NVARS',numpy.int32(len(cmaqSpecList)))
            ncout.setncattr('HISTORY',"")
            ncout.setncattr('SDATE',numpy.int32(yyyyjjj))

            ncout.close()
            ncdot.close()
            nccro.close()
            ncmet.close()


def addGfasFluxes(dates, doms, metDir, ctmDir, CMAQdir, mechCMAQ, mcipsuffix, forceUpdate):
    '''Function to add GFAS fluxes to FFDAS+VPRM emissions to the CMAQ domain

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        metDir: base directory for the MCIP output
        ctmDir: base directory for the CCTM inputs and outputs
        CMAQdir: base directory for the CMAQ model
        mechCMAQ: name of chemical mechanism given to CMAQ
        mcipsuffix: Suffix for the MCIP output files
        forceUpdate: Force the update of combined emission files

    Returns:
        Nothing
    '''
    
    for date in dates:
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')

        for idom, dom in enumerate(doms):
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            ## check input/output files exist
            gfasEmisFile = '{}/fire_emis_{}.nc'.format(chemdir,dom)
            assert os.path.exists(gfasEmisFile), 'file {} not found'.format(gfasEmisFile)
            combinedEmisFile = '{}/combined_emis_{}.nc'.format(chemdir,dom)
            assert os.path.exists(combinedEmisFile), 'file {} not found'.format(combinedEmisFile)

            print("\tAdd the fire emissions for domain",dom,"and date",yyyymmdd_dashed)
            ncin  = netCDF4.Dataset(gfasEmisFile)
            ncout = netCDF4.Dataset(combinedEmisFile, 'a')
            existingAtts =  ncout.ncattrs()
            if 'GFAS_flux_added' in existingAtts:
                GFAS_flux_added = ncout.getncattr('GFAS_flux_added')
                if GFAS_flux_added == 'true':
                    print("\tGFAS fluxes already added to {} - exiting...".format(combinedEmisFile))
                    ncout.close()
                    continue
            ##
            ANTHR_VPRM_flux = ncout.variables['CH4'][:]
            FIRE_flux = ncin.variables['CH4'][:]
            CH4_flux = numpy.zeros(ANTHR_VPRM_flux.shape, dtype = ANTHR_VPRM_flux.dtype)
            ## check sizes match
            ## pdb.set_trace()
            assert numpy.array_equal( numpy.array(FIRE_flux[0,:,:,:].shape), numpy.array(ANTHR_VPRM_flux[0,:,:,:].shape)), "Array sizes not equal when adding GFAS fire emissions to VPRM+FFDAS"
            for ihour in range(ANTHR_VPRM_flux.shape[0]):
                CH4_flux[ihour,:,:,:] = ANTHR_VPRM_flux[ihour,:,:,:] + FIRE_flux[0,:,:,:]
            ##
            ncout.variables['CH4'][:] = CH4_flux
            ncout.setncattr('GFAS_flux_added','true')
            ncout.close()
            ncin.close()
