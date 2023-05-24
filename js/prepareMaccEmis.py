'''Remap MACC emissions to the CMAQ domain
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
import scipy.ndimage
import pdb
from scipy.ndimage.morphology import binary_fill_holes


def redistribute_spatially(LATshape, nz, ind_x, ind_y, coefs, idom, subset, areas):
    '''Redistribute MACC emissions horizontally - this little function does most of the work

    Args:
        LATshape: shape of the LAT variable
        nz: Number of vertical levels in the CMAQ grid
        ind_x: x-indices in the MACC domain corresponding to indices in the CMAQ domain
        ind_y: y-indices in the MACC domain corresponding to indices in the CMAQ domain
        coefs: Area-weighting coefficients to redistribute the emissions
        idom: Index of the domain
        subset: the MACC emissions
        areas: Areas of MACC grid-cells in units of m^2

    Returns: 
        gridded: concentrations on the 2D CMAQ grid
        
    '''
    
    ##
    nxyz = [nz] + list(LATshape)
    gridded = numpy.zeros(nxyz,dtype = numpy.float32)
    ij = -1
    for i in range(LATshape[0]):
        for j in range(LATshape[1]):
            ij += 1
            
            for k in range(len(ind_x[idom][ij])):
                try:
                    ix      = ind_x[idom][ij][k]
                    iy      = ind_y[idom][ij][k]
                    ## kg/s          kg/m2/s        frac of MACC cell covered   m2/gridcell
                    gridded[0,i,j] += subset[iy,ix] *        coefs[idom][ij][k]   * areas[iy,ix]
                except:
                    pdb.set_trace()
    ##
    return gridded

def checkMaccEmisFilesExist(dates,doms,ctmDir, prefix = 'macc_emis'):
    '''Check if MACC emission files already exist

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        ctmDir: base directory for the CCTM inputs and outputs

    Returns:
        Boolean (True/False) for whether all the MACC emission files exist
    '''
    ##
    macc_emis_files_exist = True
    for date in dates:
        yyyymmddhh = date.strftime('%Y%m%d%H')
        yyyymmdd = date.strftime('%Y-%m-%d')
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')
        for idom, dom in enumerate(doms):
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            outputMaccEmisFile = '{}/{}_{}.nc'.format(chemdir,prefix,dom)
            exists = os.path.exists(outputMaccEmisFile)
            if not exists:
                macc_emis_files_exist = False
                print("File {} not found - will rerun macc emission scripts...".format(outputMaccEmisFile))
                ##
                break
        ##
        if not macc_emis_files_exist:
            break
    return macc_emis_files_exist



def prepareMaccEmis(dates, doms, MACCfile, metDir, ctmDir, CMAQdir, mechCMAQ, mcipsuffix, forceUpdate):
    '''Function to remap MACC emissions to the CMAQ domain

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        MACCfile: the file (within directory MACCfolder) containing MACC emission data
        metDir: base directory for the MCIP output
        ctmDir: base directory for the CCTM inputs and outputs
        CMAQdir: base directory for the CMAQ model
        mechCMAQ: name of chemical mechanism given to CMAQ
        mcipsuffix: Suffix for the MCIP output files
        forceUpdate: Force the update of MACC emission files

    Returns:
        Nothing
    '''
            
    attrnames = ['IOAPI_VERSION', 'EXEC_ID', 'FTYPE', 'CDATE', 'CTIME', 'WDATE', 'WTIME',
                 'SDATE', 'STIME', 'TSTEP', 'NTHIK', 'NCOLS', 'NROWS', 'NLAYS', 'NVARS',
                 'GDTYP', 'P_ALP', 'P_BET', 'P_GAM', 'XCENT', 'YCENT', 'XORIG', 'YORIG',
                 'XCELL', 'YCELL', 'VGTYP', 'VGTOP', 'VGLVLS', 'GDNAM', 'UPNAM', 'VAR-LIST', 'FILEDESC']
    unicodeType = type('foo')

    print("Read grid parameters from the MACC file")
    exists = os.path.exists(MACCfile)
    if not exists:
        raise RuntimeError("MACC file {} not found...".format(MACCfile))
    
    ncin = netCDF4.Dataset(MACCfile, 'r', format='NETCDF4')
    latMacc  = ncin.variables['latitude'][:]
    lonMacc  = ncin.variables['longitude'][:]
    areas    = ncin.variables['area'][:]
    lsf      = ncin.variables['lsf'][:]
    
    dlatMacc = latMacc[0] - latMacc[1]
    dlonMacc = lonMacc[1] - lonMacc[0]
    lonMacc_edge = numpy.zeros((len(lonMacc) + 1))
    lonMacc_edge[0:-1] = lonMacc - dlonMacc/2.0
    lonMacc_edge[-1] = lonMacc[-1] + dlonMacc/2.0

    baseTimeString = ncin.variables['time'].units
    baseTime = datetime.datetime.strptime(baseTimeString,"hours since %Y-%m-%d %H:%M:%S")
    hoursSinceBase = ncin.variables['time'][:]
    maccTimes = [baseTime + datetime.timedelta(seconds=h*3600) for h in list(hoursSinceBase)]

    latMacc_edge = numpy.zeros((len(latMacc) + 1))
    latMacc_edge[0:-1] = latMacc + dlatMacc/2.0
    latMacc_edge[-1] = latMacc[-1] + dlatMacc/2.0

    nlonMacc = len(lonMacc)
    nlatMacc = len(latMacc)

    ## latMaccrev = latMacc[::-1]
    ## latMaccrev_edge = latMacc_edge[::-1]
    
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

    # print "Calculate grid cell areas for the MACC grid"
    # areas = numpy.zeros((nlatMacc,nlonMacc))
    # for ix in range(nlonMacc):
    #     for iy in range(nlatMacc):
    #         areas[iy,ix] = helper_funcs.area_of_rectangle_m2(latMacc_edge[iy],latMacc_edge[iy+1],lonMacc_edge[ix],lonMacc_edge[ix+1])

    indxPath = "{}/MACC_ind_x.p.gz".format(ctmDir)
    indyPath = "{}/MACC_ind_y.p.gz".format(ctmDir)
    coefsPath = "{}/MACC_coefs.p.gz".format(ctmDir)
    if os.path.exists(indxPath) and os.path.exists(indyPath) and os.path.exists(coefsPath) and (not forceUpdate):
        ind_x = helper_funcs.load_zipped_pickle( indxPath )
        ind_y = helper_funcs.load_zipped_pickle( indyPath )
        coefs = helper_funcs.load_zipped_pickle( coefsPath )
        ## pdb.set_trace()
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
            ncdot.close()
            nccro.close()

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

                    ixminl = bisect.bisect_right(lonMacc_edge,xmin)
                    ixmaxr = bisect.bisect_right(lonMacc_edge,xmax)
                    iyminl = bisect.bisect_right(latMacc_edge,ymin)
                    iymaxr = bisect.bisect_right(latMacc_edge,ymax)
                    ## pdb.set_trace()

                    for ix in range(max(0,ixminl-2),min(nlonMacc,ixmaxr+2)):
                        for iy in range(max(0,iyminl-2),min(nlatMacc,iymaxr+2)):
                            macc_gridcell = geometry.box(lonMacc_edge[ix],latMacc_edge[iy],lonMacc_edge[ix+1],latMacc_edge[iy+1])
                            if CMAQ_gridcell.intersects(macc_gridcell):
                                intersection = CMAQ_gridcell.intersection(macc_gridcell)
                                ## print ix, iy
                                ## print (lonMacc_edge[ix],latMacc_edge[iy],lonMacc_edge[ix+1],latMacc_edge[iy+1]), intersection.area
                                if intersection.area == 0.0:
                                    pdb.set_trace()
                                weight1 = intersection.area/CMAQ_gridcell.area ## fraction of CMAQ cell covered
                                weight2 = intersection.area/macc_gridcell.area ## fraction of MACC cell covered
                                count2[ i,j] += weight2
                                ## if ix >= 90 or iy >= 90:
                                ##    pdb.set_trace()
                                IND_X.append(ix)
                                IND_Y.append(iy)
                                COEFS.append(weight2)

                    ind_x[idom].append(IND_X)
                    ind_y[idom].append(IND_Y)
                    
                    # COEFS = numpy.array(COEFS)
                    # COEFS = COEFS / COEFS.sum()
                    coefs[idom].append(COEFS)
            count.append(count2)
        ##
        helper_funcs.save_zipped_pickle(ind_x, indxPath )
        helper_funcs.save_zipped_pickle(ind_y, indyPath )
        helper_funcs.save_zipped_pickle(coefs, coefsPath )

    
    date = dates[0]
    yyyymmddhh = date.strftime('%Y%m%d%H')
    yyyymmdd = date.strftime('%Y-%m-%d')
    yyyymmdd_dashed = date.strftime('%Y-%m-%d')
    idom = 0
    dom = doms[idom]
    mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,dom)
    metcroFile = '{}/METCRO3D_{}'.format(mcipdir,mcipsuffix[idom])
    ncmetcro = netCDF4.Dataset(metcroFile, 'r', format='NETCDF4')
    nz = len(ncmetcro.dimensions['LAY'])

    template = []
    for idom, dom in enumerate(doms):
        template.append(numpy.zeros((24+1,nz, domShape[idom][0], domShape[idom][1],)))

    cmaqData = {}
    cmaqSpecList = ['CO2']
    for spec in cmaqSpecList:
        cmaqData[spec] = copy.copy(template)

    for date in dates:
        yyyymmddhh = date.strftime('%Y%m%d%H')
        yyyymmdd = date.strftime('%Y-%m-%d')
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')

        Date = datetime.datetime(date.year, date.month, date.day, 0, 0, 0)
        Times = [Date + datetime.timedelta(seconds = h*3600) for h in range(25)] 
        YYYYJJJ = numpy.array([ t.year*1000 + t.timetuple().tm_yday for t in Times ], dtype = numpy.int32)
        HHMMSS =  numpy.array([ t.hour*10000 + t.minute*100 + t.second for t in Times ], dtype = numpy.int32)

        ## reset values
        for spec in cmaqSpecList:
            for idom, dom in enumerate(doms):
                cmaqData[spec][idom][:] = 0.0

        for idom, dom in enumerate(doms):
            mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,dom)
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            metcroFile = '{}/METCRO3D_{}'.format(mcipdir,mcipsuffix[idom])
            outputMaccEmisFile = '{}/macc_emis_{}.nc'.format(chemdir,dom)
            ncmetcro = netCDF4.Dataset(metcroFile, 'r', format='NETCDF4')
            if os.path.exists(outputMaccEmisFile):
                os.remove(outputMaccEmisFile)

            ## print outputMaccEmisFile
            ncout = netCDF4.Dataset(outputMaccEmisFile, 'w', format='NETCDF4')
            lens = dict()
            outdims = dict()

            for k in list(ncmetcro.dimensions.keys()):
                lens[k] = len(ncmetcro.dimensions[k])

            area_factor = ncmetcro.XCELL * ncmetcro.YCELL ## m2 per grid-cell

            maccspec = 'flux_apos'
            cmaqspec = 'CO2'
            print("Calculate the emissions for domain",dom,"and date",yyyymmdd)
            for ihour in range(24+1):
                Date = datetime.datetime(date.year, date.month, date.day, 0, 0, 0) + datetime.timedelta(seconds = ihour*3600)
                idate = bisect.bisect_right(maccTimes,Date)

                if idate == len(maccTimes):
                    print("")
                    print("WARNING: at boundary of MACC times: will use previous date...")
                    print("")
                    idate = len(maccTimes)-1
                elif idate > len(maccTimes):
                    raise RuntimeError("idate > len(maccTimes)")

                subset = ncin.variables[maccspec][idate,:,:]
                
                gridded = redistribute_spatially(domShape[idom], nz, ind_x, ind_y, coefs, idom, subset, areas)
                ## molecular weight of CO2 = 12.01 + 2*16.00 = 44.01 g/mole = 0.04401 kg CO2/mole = 0.04401 kg CO2/mole
                ## 1 kg C = 1000g C / (12.01 g C / mole C) = 83.2639 moles C = 83.2639 moles CO2
                ## moles CO2  =  (kgC in CO2) *    (moles CO2)/(kgC in CO2)
                ## (moles CO2)/(kgC in CO2) = (moles CO2)/(kgC in CO2) = 
                ## moles CO2    (kgC in CO2) m-2 s-1    (moles CO2)/(kgC in CO2)
                unit_factor       =       (1000. / 12.01)
                ##
                ## moles/s                 kg C/s    moles/(kg C)
                cmaqData[cmaqspec][idom][ihour,0,:,:] = gridded[0,:,:] * unit_factor

            nlay = 1
            nvar = 1
            lens['VAR'] = nvar
            lens['LAY'] = nz

            for k in list(lens.keys()):
                outdims[k] = ncout.createDimension(k, lens[k])

            outvars = dict()
            outvars['TFLAG'] = ncout.createVariable('TFLAG', 'i4', ('TSTEP','VAR','DATE-TIME',))
            
            outvars[cmaqspec] = ncout.createVariable(cmaqspec, 'f4', ('TSTEP', 'LAY', 'ROW', 'COL'), zlib = True, shuffle = False)
            outvars[cmaqspec].setncattr('long_name',"{:<16}".format(cmaqspec))
            outvars[cmaqspec].setncattr('units',"{:<16}".format("moles/s"))
            outvars[cmaqspec].setncattr('var_desc',"{:<80}".format("Emissions of " + cmaqspec))
            outvars[cmaqspec][:] = numpy.float32(cmaqData[cmaqspec][idom])

            for a in attrnames:
                val = ncmetcro.getncattr(a)
                if type(val) == unicodeType:
                    val = str(val)
                    ##
                ncout.setncattr(a,val)

            for ivar in range(nvar):
                ncout.variables['TFLAG'][:,ivar,0] = YYYYJJJ
                ncout.variables['TFLAG'][:,ivar,1] = HHMMSS
            ##
            outvars['TFLAG'].setncattr('long_name',"{:<16}".format('TFLAG'))
            outvars['TFLAG'].setncattr('units',"<YYYYDDD,HHMMSS>")
            outvars['TFLAG'].setncattr('var_desc',"Timestep-valid flags:  (1) YYYYDDD or (2) HHMMSS                                ")

            VarString = "".join([ "{:<16}".format(k) for k in cmaqSpecList ])
            ncout.setncattr('VAR-LIST',VarString)
            ncout.setncattr('GDNAM',"{:<16}".format('Sydney'))
            ncout.setncattr('NVARS',numpy.int32(len(cmaqSpecList)))
            ncout.setncattr('HISTORY',"")
            ncout.setncattr('SDATE',numpy.int32(-635))

            ncout.close()
            ncmetcro.close()

def prepareMaccOceanFluxes(dates, doms, MACCfile, metDir, ctmDir, CMAQdir, mechCMAQ, mcipsuffix, forceUpdate):
    '''Function to remap MACC oceanic fluxes to the CMAQ domain (by nearest neighbour interpolation)

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        MACCfile: the file (within directory MACCfolder) containing MACC flux data
        metDir: base directory for the MCIP output
        ctmDir: base directory for the CCTM inputs and outputs
        CMAQdir: base directory for the CMAQ model
        mechCMAQ: name of chemical mechanism given to CMAQ
        mcipsuffix: Suffix for the MCIP output files
        forceUpdate: Force the update of MACC flux files

    Returns:
        Nothing
    '''
            
    attrnames = ['IOAPI_VERSION', 'EXEC_ID', 'FTYPE', 'CDATE', 'CTIME', 'WDATE', 'WTIME',
                 'SDATE', 'STIME', 'TSTEP', 'NTHIK', 'NCOLS', 'NROWS', 'NLAYS', 'NVARS',
                 'GDTYP', 'P_ALP', 'P_BET', 'P_GAM', 'XCENT', 'YCENT', 'XORIG', 'YORIG',
                 'XCELL', 'YCELL', 'VGTYP', 'VGTOP', 'VGLVLS', 'GDNAM', 'UPNAM', 'VAR-LIST', 'FILEDESC']
    unicodeType = type('foo')

    print("Read grid parameters from the MACC file")
    exists = os.path.exists(MACCfile)
    if not exists:
        raise RuntimeError("MACC file {} not found...".format(MACCfile))
    
    ncin = netCDF4.Dataset(MACCfile, 'r', format='NETCDF4')
    latMacc  = ncin.variables['latitude'][:]
    lonMacc  = ncin.variables['longitude'][:]
    lsf      = ncin.variables['lsf'][:]
    
    baseTimeString = ncin.variables['time'].units
    baseTime = datetime.datetime.strptime(baseTimeString,"hours since %Y-%m-%d %H:%M:%S")
    hoursSinceBase = ncin.variables['time'][:]
    maccTimes = [baseTime + datetime.timedelta(seconds=h*3600) for h in list(hoursSinceBase)]

    nlonMacc = len(lonMacc)
    nlatMacc = len(latMacc)
    
    ## get the number of vertical levels in the MCIP (and hence CMAQ) files
    print("Read grid parameters from the MCIP file")
    date = dates[0]
    idom = 0
    dom = doms[idom]
    yyyymmddhh = date.strftime('%Y%m%d%H')
    yyyymmdd_dashed = date.strftime('%Y-%m-%d')
    mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,dom)

    LAT = {}
    LON = {}
    LWMASK = {}
    for idom, dom in enumerate(doms):
        croFile = '{}/{}/{}/GRIDCRO2D_{}'.format(metDir,yyyymmdd_dashed,dom,mcipsuffix[idom])
        nccro= netCDF4.Dataset(croFile, 'r', format='NETCDF4')
        ##
        LAT[dom]  = nccro.variables['LAT'][:].squeeze()
        LON[dom]  = nccro.variables['LON'][:].squeeze()
        LWMASK[dom] = binary_fill_holes(nccro.variables['LWMASK'][0,0,:,:].astype(numpy.int)).astype(numpy.float)
        nccro.close()
    
    ## find water bodies to get *ocean* fluxes from MACC
    oceanNearestNeighbours = {}
    ioceanWhereMACC = numpy.where(lsf == 0.0)
    for idom, dom in enumerate(doms):
        ## find contiguous water features
        labeled_array, num_features = scipy.ndimage.label(1.0 - LWMASK[dom])
        for ifeature in range(1,num_features+1):
            iwhere = numpy.where(labeled_array == ifeature)
            I = iwhere[0][0]
            J = iwhere[1][0]
            ## print dom, ifeature, num_features, LWMASK[dom][I,J], (LWMASK[dom][I,J] == 0.0), len(iwhere[0])
            ## if it is over water *and* less than 30 continguous cells
            if (LWMASK[dom][I,J] == 0.0) and len(iwhere[0]) < 30:
                LWMASK[dom][labeled_array == ifeature] = 0.5
        ##
        del labeled_array, iwhere
        ##
        ##
        print("Calculate the indices and coefficients for domain",dom)
        ##
        ioceanWhereCMAQ = numpy.where(LWMASK[dom] == 0.0)
        oceanNearestNeighbours[dom] = []
        for i,j in zip(ioceanWhereCMAQ[0],ioceanWhereCMAQ[1]):
            thislat = LAT[dom][i,j]
            thislon = LON[dom][i,j]
            dists = numpy.sqrt((thislat - latMacc[ioceanWhereMACC[0]])**2 + (thislon - lonMacc[ioceanWhereMACC[1]])**2)
            imin = numpy.argmin(dists)
            I = ioceanWhereMACC[0][imin]
            J = ioceanWhereMACC[1][imin]
            assert dists.min() == numpy.sqrt((thislat - latMacc[I])**2 + (thislon - lonMacc[J])**2), "min dist not matching..."
            oceanNearestNeighbours[dom].append([i,j,I,J])

    date = dates[0]
    yyyymmddhh = date.strftime('%Y%m%d%H')
    yyyymmdd = date.strftime('%Y-%m-%d')
    yyyymmdd_dashed = date.strftime('%Y-%m-%d')
    idom = 0
    dom = doms[idom]
    mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,dom)
    metcroFile = '{}/METCRO3D_{}'.format(mcipdir,mcipsuffix[idom])
    ncmetcro = netCDF4.Dataset(metcroFile, 'r', format='NETCDF4')
    nz = len(ncmetcro.dimensions['LAY'])
    ncmetcro.close()

    template = []
    for idom, dom in enumerate(doms):
        template.append(numpy.zeros((24+1,nz, LAT[dom].shape[0], LAT[dom].shape[1],)))

    cmaqData = {}
    cmaqSpecList = ['CO2']
    for spec in cmaqSpecList:
        cmaqData[spec] = copy.copy(template)

    for date in dates:
        yyyymmddhh = date.strftime('%Y%m%d%H')
        yyyymmdd = date.strftime('%Y-%m-%d')
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')

        Date = datetime.datetime(date.year, date.month, date.day, 0, 0, 0)
        Times = [Date + datetime.timedelta(seconds = h*3600) for h in range(25)] 
        YYYYJJJ = numpy.array([ t.year*1000 + t.timetuple().tm_yday for t in Times ], dtype = numpy.int32)
        HHMMSS =  numpy.array([ t.hour*10000 + t.minute*100 + t.second for t in Times ], dtype = numpy.int32)

        ## reset values
        for spec in cmaqSpecList:
            for idom, dom in enumerate(doms):
                cmaqData[spec][idom][:] = 0.0

        for idom, dom in enumerate(doms):
            mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,dom)
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            metcroFile = '{}/METCRO3D_{}'.format(mcipdir,mcipsuffix[idom])
            outputMaccOceanicFluxesFile = '{}/macc_ocean_flux_{}.nc'.format(chemdir,dom)
            ncmetcro = netCDF4.Dataset(metcroFile, 'r', format='NETCDF4')
            if os.path.exists(outputMaccOceanicFluxesFile):
                os.remove(outputMaccOceanicFluxesFile)

            ## print outputMaccOceanicFluxesFile
            ncout = netCDF4.Dataset(outputMaccOceanicFluxesFile, 'w', format='NETCDF4')
            lens = dict()
            outdims = dict()

            for k in list(ncmetcro.dimensions.keys()):
                lens[k] = len(ncmetcro.dimensions[k])

            area_factor = ncmetcro.XCELL * ncmetcro.YCELL ## m2 per grid-cell

            maccspec = 'flux_apos'
            cmaqspec = 'CO2'
            print("Calculate the oceanic fluxes for domain",dom,"and date",yyyymmdd)
            for ihour in range(24+1):
                Date = datetime.datetime(date.year, date.month, date.day, 0, 0, 0) + datetime.timedelta(seconds = ihour*3600)
                idate = bisect.bisect_right(maccTimes,Date)

                if idate == len(maccTimes):
                    print("")
                    print("WARNING: at boundary of MACC times: will use previous date...")
                    print("")
                    idate = len(maccTimes)-1
                elif idate > len(maccTimes):
                    raise RuntimeError("idate > len(maccTimes)")

                subset = ncin.variables[maccspec][idate,:,:]

                ## (moles CO2 * m2)/(gridcell * kgC)           (moles CO2)/(kgC)   *   (m2 / gridcell)
                unit_factor                           =       (1000. / 12.01) *       area_factor

                for ipoint in range(len(oceanNearestNeighbours[dom])):
                    i,j,I,J = oceanNearestNeighbours[dom][ipoint]
                    ## moles/gridcell/s                    kg C/(m2 * s)    (moles CO2 * m2)/(gridcell * kgC)
                    cmaqData[cmaqspec][idom][ihour,0,i,j] = subset[I,J]   *   unit_factor

            nlay = 1
            nvar = 1
            lens['VAR'] = nvar
            lens['LAY'] = nz

            for k in list(lens.keys()):
                outdims[k] = ncout.createDimension(k, lens[k])

            outvars = dict()
            outvars['TFLAG'] = ncout.createVariable('TFLAG', 'i4', ('TSTEP','VAR','DATE-TIME',))
            
            outvars[cmaqspec] = ncout.createVariable(cmaqspec, 'f4', ('TSTEP', 'LAY', 'ROW', 'COL'), zlib = True, shuffle = False)
            outvars[cmaqspec].setncattr('long_name',"{:<16}".format(cmaqspec))
            outvars[cmaqspec].setncattr('units',"{:<16}".format("moles/s"))
            outvars[cmaqspec].setncattr('var_desc',"{:<80}".format("Emissions of " + cmaqspec))
            outvars[cmaqspec][:] = numpy.float32(cmaqData[cmaqspec][idom])

            for a in attrnames:
                val = ncmetcro.getncattr(a)
                if type(val) == unicodeType:
                    val = str(val)
                    ##
                ncout.setncattr(a,val)

            for ivar in range(nvar):
                ncout.variables['TFLAG'][:,ivar,0] = YYYYJJJ
                ncout.variables['TFLAG'][:,ivar,1] = HHMMSS
            ##
            outvars['TFLAG'].setncattr('long_name',"{:<16}".format('TFLAG'))
            outvars['TFLAG'].setncattr('units',"<YYYYDDD,HHMMSS>")
            outvars['TFLAG'].setncattr('var_desc',"Timestep-valid flags:  (1) YYYYDDD or (2) HHMMSS                                ")

            VarString = "".join([ "{:<16}".format(k) for k in cmaqSpecList ])
            ncout.setncattr('VAR-LIST',VarString)
            ncout.setncattr('GDNAM',"{:<16}".format('Sydney'))
            ncout.setncattr('NVARS',numpy.int32(len(cmaqSpecList)))
            ncout.setncattr('HISTORY',"")
            ncout.setncattr('SDATE',numpy.int32(-635))

            ncout.close()
            ncmetcro.close()

