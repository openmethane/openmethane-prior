'''Remap WetCHARTs wetlands CH4 emissions to the CMAQ domain
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
from dateutil.relativedelta import relativedelta


def redistribute_spatially(LATshape, ind_x, ind_y, coefs, idom, subset, areas):
    '''Redistribute WetCHARTs wetlands CH4 emissions horizontally - this little function does most of the work

    Args:
        LATshape: shape of the LAT variable
        nz: Number of vertical levels in the CMAQ grid
        ind_x: x-indices in the WetCHARTs wetlands CH4 domain corresponding to indices in the CMAQ domain
        ind_y: y-indices in the WetCHARTs wetlands CH4 domain corresponding to indices in the CMAQ domain
        coefs: Area-weighting coefficients to redistribute the emissions
        idom: Index of the domain
        subset: the WetCHARTs wetlands CH4 emissions
        areas: Areas of WetCHARTs wetlands CH4 grid-cells in units of m^2

    Returns: 
        gridded: concentrations on the 2D CMAQ grid
        
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
                    ## mg day-1     mg m-2 day-1          frac of WetCHARTs wetlands CH4 cell covered   m2/gridcell
                    gridded[i,j] += subset[iy,ix] *        coefs[idom][ij][k]                        *  areas[iy,ix]
                except:
                    pdb.set_trace()
    ##
    return gridded

def checkWetlandEmisFilesExist(dates,doms,ctmDir, prefix = 'wetlands_emis'):
    '''Check if WetCHARTs wetlands CH4 emission files already exist

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        ctmDir: base directory for the CCTM inputs and outputs

    Returns:
        Boolean (True/False) for whether all the WetCHARTs wetlands CH4 emission files exist
    '''
    ##
    wetlands_emis_files_exist = True
    for date in dates:
        yyyymmddhh = date.strftime('%Y%m%d%H')
        yyyymmdd = date.strftime('%Y-%m-%d')
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')
        for idom, dom in enumerate(doms):
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            outputWetlandsEmisFile = '{}/{}_{}.nc'.format(chemdir,prefix,dom)
            exists = os.path.exists(outputWetlandsEmisFile)
            if not exists:
                wetlands_emis_files_exist = False
                print("File {} not found - will rerun wetlands emission scripts...".format(outputWetlandsEmisFile))
                ##
                break
        ##
        if not wetlands_emis_files_exist:
            break
    return wetlands_emis_files_exist



def prepareWetlandEmis(dates, doms, wetlandsFile, metDir, ctmDir, mcipsuffix, forceUpdate):
    '''Function to remap WetCHARTs wetlands CH4 emissions to the CMAQ domain

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        wetlandsFile: the file (within directory WETLANDSfolder) containing WetCHARTs wetlands CH4 emission data
        metDir: base directory for the MCIP output
        ctmDir: base directory for the CCTM inputs and outputs
        mcipsuffix: Suffix for the MCIP output files
        forceUpdate: Force the update of WetCHARTs wetlands CH4 emission files

    Returns:
        Nothing
    '''
            
    attrnames = ['IOAPI_VERSION', 'EXEC_ID', 'FTYPE', 'CDATE', 'CTIME', 'WDATE', 'WTIME',
                 'SDATE', 'STIME', 'TSTEP', 'NTHIK', 'NCOLS', 'NROWS', 'NLAYS', 'NVARS',
                 'GDTYP', 'P_ALP', 'P_BET', 'P_GAM', 'XCENT', 'YCENT', 'XORIG', 'YORIG',
                 'XCELL', 'YCELL', 'VGTYP', 'VGTOP', 'VGLVLS', 'GDNAM', 'UPNAM', 'VAR-LIST', 'FILEDESC']
    unicodeType = type('foo')

    print("Read grid parameters from the WetCHARTs wetlands CH4 file")
    exists = os.path.exists(wetlandsFile)
    if not exists:
        raise RuntimeError("WetCHARTs wetlands CH4 file {} not found...".format(wetlandsFile))
    
    ncin = netCDF4.Dataset(wetlandsFile, 'r', format='NETCDF4')
    latWetlands  = ncin.variables['lat'][:]
    lonWetlands  = ncin.variables['lon'][:]
    timeWetlands = ncin.variables['time'][:] ## months since 2009-01-01 00:00:00
    basetime = datetime.datetime(2009, 1, 1, 0, 0, 0)
    timeWetlands = [ basetime + relativedelta(months = int(month)) + relativedelta(days = 15) for month in timeWetlands ]
    
    dlatWetlands = latWetlands[0] - latWetlands[1]
    dlonWetlands = lonWetlands[1] - lonWetlands[0]
    lonWetlands_edge = numpy.zeros((len(lonWetlands) + 1))
    lonWetlands_edge[0:-1] = lonWetlands - dlonWetlands/2.0
    lonWetlands_edge[-1] = lonWetlands[-1] + dlonWetlands/2.0

    wetlandsEmis = ncin.variables['wetland_CH4_emissions_mean'][:]
    ncin.close()

    latWetlands_edge = numpy.zeros((len(latWetlands) + 1))
    latWetlands_edge[0:-1] = latWetlands + dlatWetlands/2.0
    latWetlands_edge[-1] = latWetlands[-1] + dlatWetlands/2.0

    nlonWetlands = len(lonWetlands)
    nlatWetlands = len(latWetlands)

    ## latWetlandsrev = latWetlands[::-1]
    ## latWetlandsrev_edge = latWetlands_edge[::-1]
    
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

    print("Calculate grid cell areas for the WetCHARTs wetlands CH4 grid")
    areas = numpy.zeros((nlatWetlands,nlonWetlands))
    for ix in range(nlonWetlands):
        for iy in range(nlatWetlands):
            areas[iy,ix] = helper_funcs.area_of_rectangle_m2(latWetlands_edge[iy],latWetlands_edge[iy+1],lonWetlands_edge[ix],lonWetlands_edge[ix+1])

    indxPath = "{}/wetlands_ind_x.p.gz".format(ctmDir)
    indyPath = "{}/wetlands_ind_y.p.gz".format(ctmDir)
    coefsPath = "{}/wetlands_coefs.p.gz".format(ctmDir)
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

                    ixminl = bisect.bisect_right(lonWetlands_edge,xmin)
                    ixmaxr = bisect.bisect_right(lonWetlands_edge,xmax)
                    iyminl = bisect.bisect_right(latWetlands_edge,ymin)
                    iymaxr = bisect.bisect_right(latWetlands_edge,ymax)
                    ## pdb.set_trace()

                    for ix in range(max(0,ixminl-2),min(nlonWetlands,ixmaxr+2)):
                        for iy in range(max(0,iyminl-2),min(nlatWetlands,iymaxr+2)):
                            wetlands_gridcell = geometry.box(lonWetlands_edge[ix],latWetlands_edge[iy],lonWetlands_edge[ix+1],latWetlands_edge[iy+1])
                            if CMAQ_gridcell.intersects(wetlands_gridcell):
                                intersection = CMAQ_gridcell.intersection(wetlands_gridcell)
                                if intersection.area == 0.0:
                                    continue
                                weight1 = intersection.area/CMAQ_gridcell.area ## fraction of CMAQ cell covered - use for averaging
                                weight2 = intersection.area/wetlands_gridcell.area ## fraction of WetCHARTs wetlands CH4 cell covered - use for adding
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

    unit_factor       =       (1.0e-3 / 16.01)
    time_factor       =       1.0 / (24. * 60. * 60.)

    ## assume that there is ONLY ONE time slices (monthly average) in the file
    for idom, dom in enumerate(doms):
        idate = 0

        for date in dates:
            ## reset values
            cmaqData[cmaqspec][idom][:] = 0.0
            
            yyyymmddhh = date.strftime('%Y%m%d%H')
            yyyymmdd = date.strftime('%Y-%m-%d')
            yyyymmdd_dashed = date.strftime('%Y-%m-%d')
            month = int(date.strftime('%m'))
            imonth = month - 1
            ## find the closest time in the wetlands array - should actaully get this to match the months
            itimeWetlands = numpy.argmin(numpy.abs(numpy.array([ (date - d).days for d in timeWetlands ])))
            ## - up to here - TODO: units, finding the time dimension correctly
            gridded = redistribute_spatially(domShape[idom], ind_x, ind_y, coefs, idom, wetlandsEmis[itimeWetlands,:,:], areas)

            Date = datetime.datetime(date.year, date.month, date.day, 0, 0, 0)
            Times = [Date + datetime.timedelta(seconds = h*3600) for h in range(25)] 
            YYYYJJJ = numpy.array([ t.year*1000 + t.timetuple().tm_yday for t in Times ], dtype = numpy.int32)
            HHMMSS =  numpy.array([ t.hour*10000 + t.minute*100 + t.second for t in Times ], dtype = numpy.int32)

            mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,dom)
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            metcroFile = '{}/METCRO3D_{}'.format(mcipdir,mcipsuffix[idom])
            outputWetlandsEmisFile = '{}/wetlands_emis_{}.nc'.format(chemdir,dom)
            ncmetcro = netCDF4.Dataset(metcroFile, 'r', format='NETCDF4')
            if os.path.exists(outputWetlandsEmisFile):
                os.remove(outputWetlandsEmisFile)

            ## print outputWetlandsEmisFile
            ncout = netCDF4.Dataset(outputWetlandsEmisFile, 'w', format='NETCDF4')
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
                ## moles CH4/s                         mg CH4 day-1    moles CH4/(mg CH4)     day / s
                cmaqData[cmaqspec][idom][ihour,0,:,:] = gridded      * unit_factor    *      time_factor

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


def addWetlandFluxes(dates, doms, metDir, ctmDir, CMAQdir, mechCMAQ, mcipsuffix, forceUpdate):
    '''Function to add wetland fluxes to other emissions to the CMAQ domain

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
            wetlandEmisFile = '{}/wetlands_emis_{}.nc'.format(chemdir,dom)
            assert os.path.exists(wetlandEmisFile), 'file {} not found'.format(wetlandEmisFile)
            combinedEmisFile = '{}/combined_emis_{}.nc'.format(chemdir,dom)
            assert os.path.exists(combinedEmisFile), 'file {} not found'.format(combinedEmisFile)

            print("\tAdd the wetland emissions for domain",dom,"and date",yyyymmdd_dashed)
            ncin  = netCDF4.Dataset(wetlandEmisFile)
            ncout = netCDF4.Dataset(combinedEmisFile, 'a')
            existingAtts =  ncout.ncattrs()
            if 'wetland_flux_added' in existingAtts:
                wetland_flux_added = ncout.getncattr('wetland_flux_added')
                if wetland_flux_added == 'true':
                    print("\twetland fluxes already added to {} - exiting...".format(combinedEmisFile))
                    ncout.close()
                    continue
            ##
            OTHER_flux = ncout.variables['CH4'][:]
            WETLAND_flux = ncin.variables['CH4'][:]
            CH4_flux = numpy.zeros(OTHER_flux.shape, dtype = OTHER_flux.dtype)
            ## check sizes match
            ## pdb.set_trace()
            assert numpy.array_equal( numpy.array(WETLAND_flux[0,0,:,:].shape), numpy.array(OTHER_flux[0,0,:,:].shape)), "Array sizes not equal when adding wetland wetland emissions to combined emis"
            for ihour in range(OTHER_flux.shape[0]):
                CH4_flux[ihour,1:,:,:] = OTHER_flux[ihour,1:,:,:]
                CH4_flux[ihour,0,:,:] = OTHER_flux[ihour,0,:,:] + WETLAND_flux[0,0,:,:]
            ##
            ncout.variables['CH4'][:] = CH4_flux
            ncout.setncattr('wetland_flux_added','true')
            ncout.close()
            ncin.close()
