'''Remap geogenic CH4 emissions to the CMAQ domain
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


def redistribute_spatially(LATshape, ind_x, ind_y, coefs, idom, subset):
    '''Redistribute geogenic CH4 emissions horizontally - this little function does most of the work

    Args:
        LATshape: shape of the LAT variable
        ind_x: x-indices in the geogenic CH4 domain corresponding to indices in the CMAQ domain
        ind_y: y-indices in the geogenic CH4 domain corresponding to indices in the CMAQ domain
        coefs: Area-weighting coefficients to redistribute the emissions
        idom: Index of the domain
        subset: the geogenic CH4 emissions [units: tonnes/year/(geogenic gridcell)]

    Returns: 
        gridded: concentrations on the 2D CMAQ grid [units: tonnes/year/(CMAQ gridcell)]
        
    '''
    
    ##
    gridded = numpy.zeros(LATshape,dtype = numpy.float32)
    ij = -1
    for i in range(LATshape[0]):
        for j in range(LATshape[1]):
            ij += 1
            for k in range(len(ind_x[idom][ij])):
                try:
                    ix      = ind_x[idom][ij][k]
                    iy      = ind_y[idom][ij][k]
                    ## tonnes/year     tonnes/year/gridcell   frac of geogenic CH4 cell covered   
                    gridded[i,j]    += subset[iy,ix] *        coefs[idom][ij][k]              
                except:
                    pdb.set_trace()
    ##
    return gridded

def checkGeogenicEmisFilesExist(dates,doms,ctmDir, prefix = 'geogenic_emis'):
    '''Check if geogenic CH4 emission files already exist

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        ctmDir: base directory for the CCTM inputs and outputs

    Returns:
        Boolean (True/False) for whether all the geogenic CH4 emission files exist
    '''
    ##
    geogenic_emis_files_exist = True
    for date in dates:
        yyyymmddhh = date.strftime('%Y%m%d%H')
        yyyymmdd = date.strftime('%Y-%m-%d')
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')
        for idom, dom in enumerate(doms):
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            outputGeogenicEmisFile = '{}/{}_{}.nc'.format(chemdir,prefix,dom)
            exists = os.path.exists(outputGeogenicEmisFile)
            if not exists:
                geogenic_emis_files_exist = False
                print("File {} not found - will rerun geogenic emission scripts...".format(outputGeogenicEmisFile))
                ##
                break
        ##
        if not geogenic_emis_files_exist:
            break
    return geogenic_emis_files_exist

def prepareGeogenicEmis(dates, doms, geogenicFile, metDir, ctmDir, mcipsuffix, forceUpdate):
    '''Function to remap geogenic CH4 emissions to the CMAQ domain

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        geogenicFile: the file (within directory GEOGENICfolder) containing geogenic CH4 emission data
        metDir: base directory for the MCIP output
        ctmDir: base directory for the CCTM inputs and outputs
        mcipsuffix: Suffix for the MCIP output files
        forceUpdate: Force the update of geogenic CH4 emission files

    Returns:
        Nothing
    '''
            
    attrnames = ['IOAPI_VERSION', 'EXEC_ID', 'FTYPE', 'CDATE', 'CTIME', 'WDATE', 'WTIME',
                 'SDATE', 'STIME', 'TSTEP', 'NTHIK', 'NCOLS', 'NROWS', 'NLAYS', 'NVARS',
                 'GDTYP', 'P_ALP', 'P_BET', 'P_GAM', 'XCENT', 'YCENT', 'XORIG', 'YORIG',
                 'XCELL', 'YCELL', 'VGTYP', 'VGTOP', 'VGLVLS', 'GDNAM', 'UPNAM', 'VAR-LIST', 'FILEDESC']
    unicodeType = type('foo')

    print("Read grid parameters from the geogenic CH4 file")
    exists = os.path.exists(geogenicFile)
    if not exists:
        raise RuntimeError("geogenic CH4 file {} not found...".format(geogenicFile))
    
    ncin = netCDF4.Dataset(geogenicFile, 'r', format='NETCDF4')
    latGeogenic  = ncin.variables['lat'][:]
    lonGeogenic  = ncin.variables['lon'][:]
    
    dlatGeogenic = latGeogenic[0] - latGeogenic[1]
    dlonGeogenic = lonGeogenic[1] - lonGeogenic[0]
    lonGeogenic_edge = numpy.zeros((len(lonGeogenic) + 1))
    lonGeogenic_edge[0:-1] = lonGeogenic - dlonGeogenic/2.0
    lonGeogenic_edge[-1] = lonGeogenic[-1] + dlonGeogenic/2.0

    geogenicEmis = ncin.variables['Total_geoCH4'][:] ## units: tonnes/year/gridcell
    ncin.close()

    latGeogenic_edge = numpy.zeros((len(latGeogenic) + 1))
    latGeogenic_edge[0:-1] = latGeogenic + dlatGeogenic/2.0
    latGeogenic_edge[-1] = latGeogenic[-1] + dlatGeogenic/2.0

    nlonGeogenic = len(lonGeogenic)
    nlatGeogenic = len(latGeogenic)

    ## latGeogenicrev = latGeogenic[::-1]
    ## latGeogenicrev_edge = latGeogenic_edge[::-1]
    
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

    indxPath = "{}/geogenic_ind_x.p.gz".format(ctmDir)
    indyPath = "{}/geogenic_ind_y.p.gz".format(ctmDir)
    coefsPath = "{}/geogenic_coefs.p.gz".format(ctmDir)
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

                    ixminl = bisect.bisect_right(lonGeogenic_edge,xmin)
                    ixmaxr = bisect.bisect_right(lonGeogenic_edge,xmax)
                    iyminl = bisect.bisect_right(latGeogenic_edge,ymin)
                    iymaxr = bisect.bisect_right(latGeogenic_edge,ymax)
                    ## pdb.set_trace()

                    for ix in range(max(0,ixminl-2),min(nlonGeogenic,ixmaxr+2)):
                        for iy in range(max(0,iyminl-2),min(nlatGeogenic,iymaxr+2)):
                            geogenic_gridcell = geometry.box(lonGeogenic_edge[ix],latGeogenic_edge[iy],lonGeogenic_edge[ix+1],latGeogenic_edge[iy+1])
                            if CMAQ_gridcell.intersects(geogenic_gridcell):
                                intersection = CMAQ_gridcell.intersection(geogenic_gridcell)
                                if intersection.area == 0.0:
                                    continue
                                weight1 = intersection.area/CMAQ_gridcell.area ## fraction of CMAQ cell covered - use for averaging
                                weight2 = intersection.area/geogenic_gridcell.area ## fraction of geogenic CH4 cell covered - use for adding
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

    template = []
    for idom, dom in enumerate(doms):
        template.append(numpy.zeros((24+1,1, domShape[idom][0], domShape[idom][1],)))

    cmaqData = {}
    cmaqSpecList = ['CH4']
    for spec in cmaqSpecList:
        cmaqData[spec] = copy.copy(template)

    cmaqspec = 'CH4'

    ## moles CH4/(tonne CH4)
    unit_factor       =       (1.0e6 / 16.01)
    ## year / s
    time_factor       =       1.0 / (365.25 * 24. * 60. * 60.)

    ## assume that there is ONLY ONE time slices (monthly average) in the file
    for idom, dom in enumerate(doms):
        idate = 0

        for date in dates:

            ## reset values
            cmaqData[cmaqspec][idom][:] = 0.0
            
            yyyymmddhh = date.strftime('%Y%m%d%H')
            yyyymmdd = date.strftime('%Y-%m-%d')
            yyyymmdd_dashed = date.strftime('%Y-%m-%d')
            gridded = redistribute_spatially(domShape[idom], ind_x, ind_y, coefs, idom, geogenicEmis)

            Date = datetime.datetime(date.year, date.month, date.day, 0, 0, 0)
            Times = [Date + datetime.timedelta(seconds = h*3600) for h in range(25)] 
            YYYYJJJ = numpy.array([ t.year*1000 + t.timetuple().tm_yday for t in Times ], dtype = numpy.int32)
            HHMMSS =  numpy.array([ t.hour*10000 + t.minute*100 + t.second for t in Times ], dtype = numpy.int32)

            mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,dom)
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            metcroFile = '{}/METCRO3D_{}'.format(mcipdir,mcipsuffix[idom])
            outputGeogenicEmisFile = '{}/geogenic_emis_{}.nc'.format(chemdir,dom)
            ncmetcro = netCDF4.Dataset(metcroFile, 'r', format='NETCDF4')
            if os.path.exists(outputGeogenicEmisFile):
                os.remove(outputGeogenicEmisFile)

            ## print outputGeogenicEmisFile
            ncout = netCDF4.Dataset(outputGeogenicEmisFile, 'w', format='NETCDF4')
            lens = dict()
            outdims = dict()

            for k in list(ncmetcro.dimensions.keys()):
                lens[k] = len(ncmetcro.dimensions[k])

            print("Calculate the emissions for domain",dom,"and date",yyyymmdd)
            for ihour in range(24+1):

                ## mg CH4 day-1 = 1e-3/(24*60*60) g CH4 s-1
                
                ## molecular weight of CH4 = 12.01 + 4*1.00 = 16.01 g/mole
                ## 1 kg C = 1000g C / (12.01 g C / mole C) = 83.2639 moles C = 83.2639 moles CH4
                ## moles CH4  =  (kgC in CH4) *    (moles CH4)/(kgC in CH4)
                ## (moles CH4)/(kgC in CH4) = (moles CH4)/(kgC in CH4) = 
                ## moles CH4    (kgC in CH4) m-2 s-1    (moles CH4)/(kgC in CH4)
                
                ##
                ## moles CH4/s                         tonnes CH4/year/gridcell    moles CH4/(tonne CH4)     year / s
                cmaqData[cmaqspec][idom][ihour,0,:,:] = gridded                  * unit_factor        *      time_factor

            nlay = 1
            nvar = 1
            lens['VAR'] = nvar
            lens['LAY'] = nlay

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


def addGeogenicFluxes(dates, doms, metDir, ctmDir, CMAQdir, mechCMAQ, mcipsuffix, forceUpdate):
    '''Function to add geogenic fluxes to other emissions to the CMAQ domain

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
            geogenicEmisFile = '{}/geogenic_emis_{}.nc'.format(chemdir,dom)
            assert os.path.exists(geogenicEmisFile), 'file {} not found'.format(geogenicEmisFile)
            combinedEmisFile = '{}/combined_emis_{}.nc'.format(chemdir,dom)
            assert os.path.exists(combinedEmisFile), 'file {} not found'.format(combinedEmisFile)

            print("\tAdd the geogenic emissions for domain",dom,"and date",yyyymmdd_dashed)
            ncin  = netCDF4.Dataset(geogenicEmisFile)
            ncout = netCDF4.Dataset(combinedEmisFile, 'a')
            existingAtts =  ncout.ncattrs()
            if 'geogenic_flux_added' in existingAtts:
                geogenic_flux_added = ncout.getncattr('geogenic_flux_added')
                if geogenic_flux_added == 'true':
                    print("\tgeogenic fluxes already added to {} - exiting...".format(combinedEmisFile))
                    ncout.close()
                    continue
            ##
            OTHER_flux = ncout.variables['CH4'][:]
            GEOGENIC_flux = ncin.variables['CH4'][:]
            CH4_flux = numpy.zeros(OTHER_flux.shape, dtype = OTHER_flux.dtype)
            ## check sizes match
            assert numpy.array_equal( numpy.array(GEOGENIC_flux[0,0,:,:].shape), numpy.array(OTHER_flux[0,0,:,:].shape)), "Array sizes not equal when adding geogenic geogenic emissions to combined emis"
            for ihour in range(OTHER_flux.shape[0]):
                ## use upper-air fluxes from the combined file
                CH4_flux[ihour,1:,:,:] = OTHER_flux[ihour,1:,:,:]
                ## add the surface fluxes
                CH4_flux[ihour,0,:,:] = OTHER_flux[ihour,0,:,:] + GEOGENIC_flux[0,0,:,:]
            ##
            ncout.variables['CH4'][:] = CH4_flux
            ncout.setncattr('geogenic_flux_added','true')
            ncout.close()
            ncin.close()
