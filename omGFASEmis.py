import numpy as np
import netCDF4 as nc
import xarray as xr 
import rioxarray as rxr
from omInputs import domainXr, sectoralEmissionsPath, sectoralMappingsPath
from omOutputs import landuseReprojectionPath, writeLayer
import cdsapi
import itertools
import datetime
import utils
import os
from shapely import geometry
import bisect

def downloadGFAS( startDate, endDate, fileName='download.nc'):
    """ download GFAS methane between two dates startDate and endDate, returns nothing"""
    dateString = startDate.strftime('%Y-%m-%d')+'/'+endDate.strftime('%Y-%m-%d')
    c = cdsapi.Client()

    c.retrieve(
        'cams-global-fire-emissions-gfas',
        {
            'date': dateString,
            'format': 'netcdf',
            'variable': [
                 'wildfire_flux_of_methane',
        ],
    },
        fileName)
    return fileName

def redistribute_spatially(LATshape, ind_x, ind_y, coefs, subset, areas):
    '''Redistribute GFAS emissions horizontally and vertically - this little function does most of the work

    Args:
        LATshape: shape of the LAT variable
        ind_x: x-indices in the GFAS domain corresponding to indices in the CMAQ domain
        ind_y: y-indices in the GFAS domain corresponding to indices in the CMAQ domain
        coefs: Area-weighting coefficients to redistribute the emissions
        subset: the GFAS emissionsx
        areas: Areas of GFAS grid-cells in units of m^2

    Returns: 
        gridded: concentrations on the 2D CMAQ grid
        
    '''
    
    ##
    gridded = np.zeros(LATshape,dtype = np.float32)
    ij = -1
    for i in range(LATshape[0]):
        for j in range(LATshape[1]):
            ij += 1
            for k in range(len(ind_x[ij])):
                ix      = ind_x[ij][k]
                iy      = ind_y[ij][k]
                gridded[i,j] += subset[iy,ix] *coefs[ij][k] * areas[iy,ix]   
    ##
    return gridded

def processEmissions(startDate, endDate, **kwargs): # doms, GFASfolder, GFASfile, metDir, ctmDir, CMAQdir, mechCMAQ, mcipsuffix, specTableFile, forceUpdate):
    '''Function to remap GFAS fire emissions to the CMAQ domain

    Args:
        startDate, endDate: the date range (datetime objects)
        kwargs, specific arguments needed for this emission


    Returns:
        Nothing
    '''

    try:
        forceUpdate = kwargs['forceUpdate']
    except KeyError:
        forceUpdate = False
            
    GFASfile = downloadGFAS( startDate, endDate)
    #GFASfile = 'download.nc' # for rapid testing
    ncin = nc.Dataset(GFASfile, 'r', format='NETCDF3')
    latGfas  = np.around(np.float64(ncin.variables['latitude'][:]),3)
    lonGfas  = np.around(np.float64(ncin.variables['longitude'][:]),3)
    dlatGfas = latGfas[0] - latGfas[1]
    dlonGfas = lonGfas[1] - lonGfas[0]
    lonGfas_edge = np.zeros((len(lonGfas) + 1))
    lonGfas_edge[0:-1] = lonGfas - dlonGfas/2.0
    lonGfas_edge[-1] = lonGfas[-1] + dlonGfas/2.0
    lonGfas_edge = np.around(lonGfas_edge,2)
    gfasHoursSince1900 = ncin.variables['time'][:]
    basedate = datetime.datetime(1900,1,1,0,0,0)
    gfasTimes = nc.num2date( ncin.variables['time'][:], ncin.variables['time'].getncattr('units') )

    latGfas_edge = np.zeros((len(latGfas) + 1))
    latGfas_edge[0:-1] = latGfas + dlatGfas/2.0
    latGfas_edge[-1] = latGfas[-1] - dlatGfas/2.0
    latGfas_edge = np.around(latGfas_edge,2)

    nlonGfas = len(lonGfas)
    nlatGfas = len(latGfas)

    latGfasrev = latGfas[::-1]
    latGfasrev_edge = latGfas_edge[::-1]

    

    print("Calculate grid cell areas for the GFAS grid")
    areas = np.zeros((nlatGfas,nlonGfas))
    # take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatGfas):
        areas[iy,:] = utils.area_of_rectangle_m2(latGfas_edge[iy],latGfas_edge[iy+1],lonGfas_edge[0],lonGfas_edge[-1])/lonGfas.size


    indxPath = "{}/GFAS_ind_x.p.gz".format(kwargs['ctmDir'])
    indyPath = "{}/GFAS_ind_y.p.gz".format(kwargs['ctmDir'])
    coefsPath = "{}/GFAS_coefs.p.gz".format(kwargs['ctmDir'])
    if os.path.exists(indxPath) and os.path.exists(indyPath) and os.path.exists(coefsPath) and (not forceUpdate):
        ind_x = utils.load_zipped_pickle( indxPath )
        ind_y = utils.load_zipped_pickle( indyPath )
        coefs = utils.load_zipped_pickle( coefsPath )
        ##
        domShape = []
        LAT  = domainXr.variables['LAT'].values.squeeze()
        domShape.append(LAT.shape)
    else:
        ind_x = []
        ind_y = []
        coefs = []
        count = []
        domShape = []

        ind_x.append([])
        ind_y.append([])
        coefs.append([])


        LAT  = domainXr.variables['LAT'].values.squeeze()
        LON  = domainXr.variables['LON'].values.squeeze()
        LATD = domainXr.variables['LATD'].values.squeeze()
        LOND = domainXr.variables['LOND'].values.squeeze()

        domShape.append(LAT.shape)

        count2  = np.zeros(LAT.shape,dtype = np.float32)

        for i,j  in itertools.product(range(LAT.shape[0]), range(LAT.shape[1])):
            IND_X = []
            IND_Y = []
            COEFS = []

            xvals = np.array([LOND[i,  j], LOND[i,  j+1], LOND[i+1,  j], LOND[i+1,  j+1]])
            yvals = np.array([LATD[i,  j], LATD[i,  j+1], LATD[i+1,  j], LATD[i+1,  j+1]])

            xy = [[LOND[i,  j],LATD[i,  j]],[LOND[i,  j+1],LATD[i,  j+1]],[LOND[i+1,  j+1],LATD[i+1,  j+1]],[LOND[i+1,  j],LATD[i+1,  j]]]
            CMAQ_gridcell = geometry.Polygon(xy)

            xmin = np.min(xvals)
            xmax = np.max(xvals)
            ymin = np.min(yvals)
            ymax = np.max(yvals)

            ixminl = bisect.bisect_right(lonGfas_edge,xmin)
            ixmaxr = bisect.bisect_right(lonGfas_edge,xmax)
            iyminl = nlatGfas - bisect.bisect_right(latGfasrev_edge,ymax)
            iymaxr = nlatGfas - bisect.bisect_right(latGfasrev_edge,ymin)

            for ix,iy  in itertools.product(range(max(0,ixminl-1),min(nlonGfas,ixmaxr)), range(max(0,iyminl),min(nlatGfas,iymaxr+1))):
                gfas_gridcell = geometry.box(lonGfas_edge[ix],latGfas_edge[iy],lonGfas_edge[ix+1],latGfas_edge[iy+1])
                if CMAQ_gridcell.intersects(gfas_gridcell):
                    intersection = CMAQ_gridcell.intersection(gfas_gridcell)
                    weight1 = intersection.area/CMAQ_gridcell.area ## fraction of CMAQ cell covered
                    weight2 = intersection.area/gfas_gridcell.area ## fraction of GFAS cell covered
                    count2[ i,j] += weight2
                    IND_X.append(ix)
                    IND_Y.append(iy)
                    COEFS.append(weight2)
            ind_x.append(IND_X)
            ind_y.append(IND_Y)
            # COEFS = np.array(COEFS)
            # COEFS = COEFS / COEFS.sum()
            coefs.append(COEFS)
        count.append(count2)
        ##
        utils.save_zipped_pickle(ind_x, indxPath )
        utils.save_zipped_pickle(ind_y, indyPath )
        utils.save_zipped_pickle(coefs, coefsPath )
        
    resultNd = [] # will become ndarray
    dates = []
    for i in range(gfasTimes.size):
        dates.append( startDate + datetime.timedelta( days=i))
        subset = ncin['ch4fire'][i,...]
        resultNd.append( redistribute_spatially(LAT.shape, ind_x, ind_y, coefs, subset, areas))
    resultNd = np.array( resultNd)
    resultXr = xr.DataArray( resultNd, coords={'date':dates, 'y':np.arange( resultNd.shape[-2]), 'x':np.arange( resultNd.shape[-1])})
    writeLayer('OCH4_FIRE', resultXr, True)
    return resultNd

def testGFASEmis( startDate, endDate, **kwargs): # test totals for GFAS emissions between original and remapped
    remapped = processEmissions( startDate, endDate, **kwargs)
    GFASfile = 'download.nc'
    ncin = nc.Dataset(GFASfile, 'r', format='NETCDF3')
    latGfas  = np.around(np.float64(ncin.variables['latitude'][:]),3)
    lonGfas  = np.around(np.float64(ncin.variables['longitude'][:]),3)
    dlatGfas = latGfas[0] - latGfas[1]
    dlonGfas = lonGfas[1] - lonGfas[0]
    lonGfas_edge = np.zeros((len(lonGfas) + 1))
    lonGfas_edge[0:-1] = lonGfas - dlonGfas/2.0
    lonGfas_edge[-1] = lonGfas[-1] + dlonGfas/2.0
    lonGfas_edge = np.around(lonGfas_edge,2)

    latGfas_edge = np.zeros((len(latGfas) + 1))
    latGfas_edge[0:-1] = latGfas + dlatGfas/2.0
    latGfas_edge[-1] = latGfas[-1] - dlatGfas/2.0
    latGfas_edge = np.around(latGfas_edge,2)

    nlonGfas = len(lonGfas)
    nlatGfas = len(latGfas)

    latGfasrev = latGfas[::-1]
    latGfasrev_edge = latGfas_edge[::-1]
    areas = np.zeros((nlatGfas,nlonGfas))
# take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatGfas):
        areas[iy,:] = utils.area_of_rectangle_m2(latGfas_edge[iy],latGfas_edge[iy+1],lonGfas_edge[0],lonGfas_edge[-1])/lonGfas.size
    LATD = domainXr.variables['LATD'].values.squeeze()
    LOND = domainXr.variables['LOND'].values.squeeze()
    indLat = (latGfas > LATD.min()) &( latGfas < LATD.max())
    indLon = (lonGfas > LOND.min()) &( lonGfas < LOND.max())
    gfasCH4 = ncin['ch4fire'][...]
    inds = np.ix_(indLat, indLon)
    gfasTotals = [np.tensordot( gfasCH4[i][inds], areas[inds]) for i in range(gfasCH4.shape[0])]

    remappedTotals = remapped.sum(axis=(1,2))
    for t in zip(gfasTotals, remappedTotals): print(t)
    return
if __name__ == '__main__':
    startDate = datetime.datetime(2022,7,1)
    endDate = datetime.datetime(2022,7,2)
    processEmissions(startDate, endDate, ctmDir='.')

                  
