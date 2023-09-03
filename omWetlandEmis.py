import numpy as np
import netCDF4 as nc
import xarray
import rioxarray as rxr
from omInputs import domainPath, sectoralEmissionsPath, sectoralMappingsPath, wetlandFilePath
from omOutputs import landuseReprojectionPath, writeLayer
import cdsapi
import itertools
import datetime
import helper_funcs
import os
from shapely import geometry
import bisect
from utils import dateTimeRange



def redistribute_spatially(LATshape, ind_x, ind_y, coefs, subset, fromAreas, toAreas):
    '''Redistribute wetland emissions horizontally and vertically - this little function does most of the work

    Args:
        LATshape: shape of the LAT variable
        ind_x: x-indices in the GFAS domain corresponding to indices in the CMAQ domain
        ind_y: y-indices in the GFAS domain corresponding to indices in the CMAQ domain
        coefs: Area-weighting coefficients to redistribute the emissions
        subset: the GFAS emissionsx
        fromAreas: Areas of input grid-cells in units of m^2
    toAreas: area of output gridcells in units of m^2
    Returns: 
        gridded: concentrations on the 2D CMAQ grid
        
    '''
    
    ##
    gridded = np.zeros(LATshape,dtype = np.float32)
    ij = 0
    for i in range(LATshape[0]):
        for j in range(LATshape[1]):
            ij += 1
            for k in range(len(ind_x[ij])):
                ix      = ind_x[ij][k]
                iy      = ind_y[ij][k]
                gridded[i,j] += subset[iy,ix] *coefs[ij][k] * fromAreas[iy,ix]   
    gridded /= toAreas
    return gridded

def makeWetlandClimatology( **kwargs): # doms, GFASfolder, GFASfile, metDir, ctmDir, CMAQdir, mechCMAQ, mcipsuffix, specTableFile, forceUpdate):
    '''Function to remap termite emissions to the CMAQ domain

    Args:
        startDate, endDate: date limits, note that inputs are only monthly resolution so emissions will be constant within a month
        kwargs, specific arguments needed for this emission


    Returns:
        Nothing
    '''

    try:
        forceUpdate = kwargs['forceUpdate']
    except KeyError:
        forceUpdate = False
            
    ncin = nc.Dataset(wetlandFilePath, 'r')
    latWetland  = np.around(np.float64(ncin.variables['lat'][:]),3)
    lonWetland  = np.around(np.float64(ncin.variables['lon'][:]),3)
    dlatWetland = latWetland[0] - latWetland[1]
    dlonWetland = lonWetland[1] - lonWetland[0]
    lonWetland_edge = np.zeros((len(lonWetland) + 1))
    lonWetland_edge[0:-1] = lonWetland - dlonWetland/2.0
    lonWetland_edge[-1] = lonWetland[-1] + dlonWetland/2.0
    lonWetland_edge = np.around(lonWetland_edge,2)

    latWetland_edge = np.zeros((len(latWetland) + 1))
    latWetland_edge[0:-1] = latWetland + dlatWetland/2.0
    latWetland_edge[-1] = latWetland[-1] - dlatWetland/2.0
    latWetland_edge = np.around(latWetland_edge,2)

    nlonWetland = len(lonWetland)
    nlatWetland = len(latWetland)

    wetlandAreas = np.zeros((nlatWetland,nlonWetland))
    # take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatWetland):
        wetlandAreas[iy,:] = helper_funcs.area_of_rectangle_m2(latWetland_edge[iy],latWetland_edge[iy+1],lonWetland_edge[0],lonWetland_edge[-1])/lonWetland.size
# now collect some domain information
    croFile = kwargs['croFile']
    with nc.Dataset(croFile, 'r', format='NETCDF4') as nccro:
        LAT  = nccro.variables['LAT'][:].squeeze()
        LON  = nccro.variables['LON'][:].squeeze()
        cmaqArea = nccro.XCELL * nccro.YCELL

    indxPath = "{}/WETLAND_ind_x.p.gz".format(kwargs['ctmDir'])
    indyPath = "{}/WETLAND_ind_y.p.gz".format(kwargs['ctmDir'])
    coefsPath = "{}/WETLAND_coefs.p.gz".format(kwargs['ctmDir'])
    if os.path.exists(indxPath) and os.path.exists(indyPath) and os.path.exists(coefsPath) and (not forceUpdate):
        ind_x = helper_funcs.load_zipped_pickle( indxPath )
        ind_y = helper_funcs.load_zipped_pickle( indyPath )
        coefs = helper_funcs.load_zipped_pickle( coefsPath )
        ##
        domShape = []
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

        ncdot= nc.Dataset(kwargs['dotFile'], 'r', format='NETCDF4')
        LATD = ncdot.variables['LATD'][:].squeeze()
        LOND = ncdot.variables['LOND'][:].squeeze()


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

            ixminl = bisect.bisect_right(lonWetland_edge,xmin)
            ixmaxr = bisect.bisect_right(lonWetland_edge,xmax)
            iyminl =  bisect.bisect_right(latWetland_edge,ymax)
            iymaxr =  bisect.bisect_right(latWetland_edge,ymin)

            for ix,iy  in itertools.product(range(max(0,ixminl-1),min(nlonWetland,ixmaxr+1)), range(max(0,iyminl-1),min(nlatWetland,iymaxr+1))):
                Wetland_gridcell = geometry.box(lonWetland_edge[ix],latWetland_edge[iy],lonWetland_edge[ix-1],latWetland_edge[iy-1])
                if CMAQ_gridcell.intersects(Wetland_gridcell):
                    intersection = CMAQ_gridcell.intersection(Wetland_gridcell)
                    weight1 = intersection.area/CMAQ_gridcell.area ## fraction of CMAQ cell covered
                    weight2 = intersection.area/Wetland_gridcell.area ## fraction of WETLAND cell covered
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
        ncdot.close()
        ##
        helper_funcs.save_zipped_pickle(ind_x, indxPath )
        helper_funcs.save_zipped_pickle(ind_y, indyPath )
        helper_funcs.save_zipped_pickle(coefs, coefsPath )
    # now build monthly climatology
    flux = ncin['totflux'][...] # is masked array
    climatology=np.zeros((12,flux.shape[1], flux.shape[2])) # same spatial domain but monthly climatology
    for month in range(12): climatology[month,...] = flux[month::12,...].mean(axis=0) # average over time axis with stride 12
    np.clip(climatology, 0., None, out=climatology) # negative are missing values so remove by clipping in place
    cmaqAreas = np.ones( LAT.shape) * cmaqArea   # all grid cells equal area
    result = np.zeros((12, LAT.shape[0], LAT.shape[1]))
    for month in range(12): result[month,...]=redistribute_spatially(LAT.shape, ind_x, ind_y, coefs, climatology[month,...], wetlandAreas, cmaqAreas)
    ncin.close()
    return np.array( result) 

def processEmissions(startDate, endDate, **kwargs): # doms, GFASfolder, GFASfile, metDir, ctmDir, CMAQdir, mechCMAQ, mcipsuffix, specTableFile, forceUpdate):
    climatology = makeWetlandClimatolog( **kwargs)
    result = []
    delta = datetime.timedelta(days=1)
    for d in dateTimeRange( startDate, endDate, delta): result.append( climatology[d.month -1, ...]) # d.month is 1-based
    result.append( climatology[endDate.month -1, ...]) # we want endDate included, python doesn't
    return np.array( result)

def testWetlandEmis( startDate, endDate, **kwargs): # test totals for WETLAND emissions between original and remapped
    remapped = makeWetlandClimatology( **kwargs)
    ncin = nc.Dataset(wetlandFilePath, 'r')
    latWetland  = np.around(np.float64(ncin.variables['lat'][:]),3)
    lonWetland  = np.around(np.float64(ncin.variables['lon'][:]),3)
    dlatWetland = latWetland[0] - latWetland[1]
    dlonWetland = lonWetland[1] - lonWetland[0]
    lonWetland_edge = np.zeros((len(lonWetland) + 1))
    lonWetland_edge[0:-1] = lonWetland - dlonWetland/2.0
    lonWetland_edge[-1] = lonWetland[-1] + dlonWetland/2.0
    lonWetland_edge = np.around(lonWetland_edge,2)

    latWetland_edge = np.zeros((len(latWetland) + 1))
    latWetland_edge[0:-1] = latWetland + dlatWetland/2.0
    latWetland_edge[-1] = latWetland[-1] - dlatWetland/2.0
    latWetland_edge = np.around(latWetland_edge,2)

    nlonWetland = len(lonWetland)
    nlatWetland = len(latWetland)

    areas = np.zeros((nlatWetland,nlonWetland))
# take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatWetland):
        areas[iy,:] = helper_funcs.area_of_rectangle_m2(latWetland_edge[iy],latWetland_edge[iy+1],lonWetland_edge[0],lonWetland_edge[-1])/lonWetland.size
    ncdot= nc.Dataset(kwargs['dotFile'], 'r', format='NETCDF4')
    LATD = ncdot.variables['LATD'][:].squeeze()
    LOND = ncdot.variables['LOND'][:].squeeze()
    indLat = (latWetland > LATD.min()) &( latWetland < LATD.max())
    indLon = (lonWetland > LOND.min()) &( lonWetland < LOND.max())
    flux = ncin['totflux'][...]
    # make climatology
    climatology=np.zeros((12,flux.shape[1], flux.shape[2])) # same spatial domain but monthly climatology
    for month in range(12): climatology[month,...] = flux[month::12,...].mean(axis=0) # average over time axis with stride 12
    np.clip(climatology, 0., None, out=climatology) # negative are missing values so remove by clipping in place

    inds = np.ix_(indLat, indLon)
    wetlandTotals = [(areas * climatology[month])[inds].sum() for month in range(12)]
    area = ncdot.XCELL*ncdot.YCELL
    remappedTotals = [remapped[month,...].sum()*area for month in range(12)] # conversion from kg to mt
    print(list(zip(wetlandTotals, remappedTotals)))
    return
if __name__ == '__main__':
    startDate = datetime.datetime(2022,7,1)
    endDate = datetime.datetime(2022,7,2)
    testWetlandEmis(startDate, endDate, dotFile='GRIDDOT2D_1',croFile='GRIDCRO2D_1', ctmDir='.')