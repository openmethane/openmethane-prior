'''Remap point source emissions to the CMAQ domain
'''
import os
import copy
import numpy
import datetime
import netCDF4
import pandas
import helper_funcs
import pdb

def checkPointSourceEmisFilesExist(dates,doms,ctmDir, prefix = 'point_source_emis'):
    '''Check if point source emission files already exist

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        ctmDir: base directory for the CCTM inputs and outputs

    Returns:
        Boolean (True/False) for whether all the point source emission files exist
    '''
    ##
    point_source_emis_files_exist = True
    for date in dates:
        yyyymmddhh = date.strftime('%Y%m%d%H')
        yyyymmdd = date.strftime('%Y-%m-%d')
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')
        for idom, dom in enumerate(doms):
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            outputPointSourceEmisFile = '{}/{}_{}.nc'.format(chemdir,prefix,dom)
            exists = os.path.exists(outputPointSourceEmisFile)
            if not exists:
                point_source_emis_files_exist = False
                print("File {} not found - will rerun point source emission scripts...".format(outputPointSourceEmisFile))
                ##
                break
        ##
        if not point_source_emis_files_exist:
            break
    return point_source_emis_files_exist


def preparePointSourceEmis(dates, doms, pointSourceCsvFile, metDir, ctmDir, mcipsuffix, emis_col, prefix = 'point_source_emis', forceUpdate = False):
    '''Function to remap point source emissions to the CMAQ domain

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        pointSourceCsvFile: the .csv file containing point source emission data. 
        metDir: base directory for the MCIP output
        ctmDir: base directory for the CCTM inputs and outputs
        mcipsuffix: Suffix for the MCIP output files
        emis_col: column name in the pointSourceCsvFile which gives the emissions (in untis of kg CH4/year)
        prefix: prefix for the resulting emission files
        forceUpdate: Force the update of point source emission files

    Returns:
        Nothing
    '''
            
    attrnames = ['IOAPI_VERSION', 'EXEC_ID', 'FTYPE', 'CDATE', 'CTIME', 'WDATE', 'WTIME',
                 'SDATE', 'STIME', 'TSTEP', 'NTHIK', 'NCOLS', 'NROWS', 'NLAYS', 'NVARS',
                 'GDTYP', 'P_ALP', 'P_BET', 'P_GAM', 'XCENT', 'YCENT', 'XORIG', 'YORIG',
                 'XCELL', 'YCELL', 'VGTYP', 'VGTOP', 'VGLVLS', 'GDNAM', 'UPNAM', 'VAR-LIST', 'FILEDESC']
    unicodeType = type('foo')

    print("Read grid parameters from the point source file")
    exists = os.path.exists(pointSourceCsvFile)
    if not exists:
        raise RuntimeError("point source file {} not found...".format(pointSourceCsvFile))

    pointSourceData = pandas.read_csv(pointSourceCsvFile)
    assert 'lat' in list(pointSourceData.keys()), "Latitude heading not found"
    assert 'lon' in list(pointSourceData.keys()), "Longitude heading not found"
    assert emis_col in list(pointSourceData.keys()), "Emission column heading not found"
    npoints = pointSourceData.shape[0]
    print('npoints',npoints)

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

    ## year/s
    time_factor = 1./(365.25*24.*60.*60.)
    ## 1 mole weighs 16.01 g, so there are 1000.0/16.01 moles of CH4 in 1 kg CH4
    unit_factor = 1.0e3 / 16.01

    ## loop through the domains, calculating the indices and coefficients
    domShape = []
    LAT  = {}
    LON  = {}
    LATD = {}
    LOND = {}
    XCELL = {}
    YCELL = {}
    gridded = {}
    for idom, dom in enumerate(doms):
        print("Calculate the indices and coefficients for domain",dom)

        croFile = '{}/{}/{}/GRIDCRO2D_{}'.format(metDir,yyyymmdd_dashed,dom,mcipsuffix[idom])
        dotFile = '{}/{}/{}/GRIDDOT2D_{}'.format(metDir,yyyymmdd_dashed,dom,mcipsuffix[idom])
        ncdot = netCDF4.Dataset(dotFile, 'r', format='NETCDF4')
        nccro = netCDF4.Dataset(croFile, 'r', format='NETCDF4')

        LAT[dom]  = nccro.variables['LAT'][:].squeeze()
        LON[dom]  = nccro.variables['LON'][:].squeeze()
        LATD[dom] = ncdot.variables['LATD'][:].squeeze()
        LOND[dom] = ncdot.variables['LOND'][:].squeeze()
        XCELL[dom] = nccro.getncattr('XCELL')
        YCELL[dom] = nccro.getncattr('YCELL')
        ncdot.close()
        nccro.close()

        Irows = numpy.zeros(npoints)
        Icols = numpy.zeros(npoints)
        domShape.append(LAT[dom].shape)

        gridded[dom] = numpy.zeros(LAT[dom].shape)

        for ipoint in range(npoints):
            dists = helper_funcs.getDistanceFromLatLonInKm(pointSourceData['lat'][ipoint],
                                                           pointSourceData['lon'][ipoint],
                                                           LAT[dom],
                                                           LON[dom])
            irow,icol = numpy.unravel_index(numpy.argmin(dists),LAT[dom].shape)
            minDist = dists[irow,icol]
            maxExpected = numpy.sqrt((XCELL[dom]/2.0)**2 + (YCELL[dom]/2.0)**2) / 1000.0
            ## print dom, ipoint, irow, icol, dists.min(), dists[irow,icol], maxExpected, (minDist <= maxExpected)
            if minDist <= maxExpected:
                ## assert minDist <= maxExpected, "Minimum distance ({} km) larger than expected ({} km), at coordinates {}, {}".format(minDist, maxExpected, irow, icol)
                Irows[ipoint] = irow
                Icols[ipoint] = icol
                ## mol CH4/s               kg CH4 / year                     year/s        (moles CH4) / (kg CH4)
                gridded[dom][irow,icol] += pointSourceData[emis_col][irow] * time_factor * unit_factor
            else:
                ## outside of the domain - do not use
                Irows[ipoint] = -1
                Icols[ipoint] = -1

        irow_var = 'irow_{}'.format(dom)
        icol_var = 'icol_{}'.format(dom)
        
        pointSourceData[irow_var] = Irows
        pointSourceData[icol_var] = Icols
        print(dom, gridded[dom].sum())
    
    template = []
    for idom, dom in enumerate(doms):
        template.append(numpy.zeros((24+1,1, domShape[idom][0], domShape[idom][1],), dtype = numpy.float32))

    edgarspec = 'ch4_emis_total'
    cmaqspec = 'CH4'

    cmaqData = {}
    cmaqSpecList = ['CH4']
    for spec in cmaqSpecList:
        cmaqData[spec] = copy.copy(template)
        for idom, dom in enumerate(doms):
            for ihour in range(24+1):
                cmaqData[spec][idom][ihour,0,:,:] = gridded[dom]


    ## assume that there is ONLY ONE time slices (monthly average) in the file
    for idom, dom in enumerate(doms):
        idate = 0

        for date in dates:
            yyyymmddhh = date.strftime('%Y%m%d%H')
            yyyymmdd = date.strftime('%Y-%m-%d')
            yyyymmdd_dashed = date.strftime('%Y-%m-%d')

            Date = datetime.datetime(date.year, date.month, date.day, 0, 0, 0)
            Times = [Date + datetime.timedelta(seconds = h*3600) for h in range(25)] 
            YYYYJJJ = numpy.array([ t.year*1000 + t.timetuple().tm_yday for t in Times ], dtype = numpy.int32)
            HHMMSS =  numpy.array([ t.hour*10000 + t.minute*100 + t.second for t in Times ], dtype = numpy.int32)

            mcipdir = '{}/{}/{}'.format(metDir,yyyymmdd_dashed,dom)
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            metcroFile = '{}/METCRO3D_{}'.format(mcipdir,mcipsuffix[idom])
            outputPointSourceEmisFile = '{}/{}_{}.nc'.format(chemdir,prefix,dom)
            ncmetcro = netCDF4.Dataset(metcroFile, 'r', format='NETCDF4')
            if os.path.exists(outputPointSourceEmisFile):
                os.remove(outputPointSourceEmisFile)

            ## print outputPointSourceEmisFile
            ncout = netCDF4.Dataset(outputPointSourceEmisFile, 'w', format='NETCDF4')
            lens = dict()
            outdims = dict()

            for k in list(ncmetcro.dimensions.keys()):
                lens[k] = len(ncmetcro.dimensions[k])

            print("Store the emissions for domain",dom,"and date",yyyymmdd)

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


def addSurfaceFluxes(dates, doms, ctmDir, prefix, combined_prefix,
                     added_attribute, forceUpdate):
    '''Function to add surface fluxes to other fluxes to the CMAQ domain

    Args:
        dates: the dates in question (list of datetime objects)
        doms: list of which domains should be run?
        ctmDir: base directory for the CCTM inputs and outputs
        prefix: prefix for the surface emission files
        combined_prefix: prefix for the combined emission files
        added_attribute: the global attribute set when adding the emissions
        forceUpdate: Force the update of combined emission files

    Returns:
        Nothing
    '''
    
    for date in dates:
        yyyymmdd_dashed = date.strftime('%Y-%m-%d')

        for idom, dom in enumerate(doms):
            chemdir = '{}/{}/{}'.format(ctmDir,yyyymmdd_dashed,dom)
            ## check input/output files exist
            surface_emis_file = '{}/{}_{}.nc'.format(chemdir,prefix,dom)
            assert os.path.exists(surface_emis_file), 'file {} not found'.format(surface_emis_file)
            combinedEmisFile = '{}/{}_{}.nc'.format(chemdir,combined_prefix,dom)
            assert os.path.exists(combinedEmisFile), 'file {} not found'.format(combinedEmisFile)

            print("\tAdd the surface emissions for domain",dom,"and date",yyyymmdd_dashed)
            ncin  = netCDF4.Dataset(surface_emis_file)
            ncout = netCDF4.Dataset(combinedEmisFile, 'a')
            existingAtts =  ncout.ncattrs()
            if added_attribute in existingAtts:
                surface_flux_added = ncout.getncattr(added_attribute)
                if surface_flux_added == 'true':
                    print("\tSurface fluxes for {} files already added to {} - exiting...".format(surface_emis_file,combinedEmisFile))
                    ncout.close()
                    continue
            ##
            out_spec = [ v for v in list(ncout.variables.keys()) if v != 'TFLAG' ]
            in_spec  = [ v for v in list(ncin.variables.keys())   if v != 'TFLAG' ]
            ## check that all of the species in the surface emissions file are present in the combined emissions file
            assert all([ v in out_spec for v in in_spec]), 'Not all input species were found in the combined emissions file'
            for spec in in_spec:
                OTHER_flux = ncout.variables[spec][:]
                SURFACE_flux = ncin.variables[spec][:]
                TOTAL_flux = numpy.zeros(OTHER_flux.shape, dtype = OTHER_flux.dtype)
                ## check sizes match
                assert numpy.array_equal( numpy.array(SURFACE_flux[0,0,:,:].shape), numpy.array(OTHER_flux[0,0,:,:].shape)), "Array sizes not equal when adding point source fluxes to combined emis file"
                for ihour in range(OTHER_flux.shape[0]):
                    TOTAL_flux[ihour,1:,:,:] = OTHER_flux[ihour,1:,:,:]
                    TOTAL_flux[ihour,0,:,:] = OTHER_flux[ihour,0,:,:] + SURFACE_flux[0,0,:,:]
                ##
            ncout.variables[spec][:] = TOTAL_flux
            ncout.setncattr(added_attribute,'true')
            ncout.close()
            ncin.close()
