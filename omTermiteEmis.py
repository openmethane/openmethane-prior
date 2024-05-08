#
# Copyright 2023-2024 The Superpower Institute Ltd.
#
# This file is part of OpenMethane.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Processing termite Methane emissions
"""

import numpy as np
import netCDF4 as nc
from omInputs import domainXr, termitePath
from omOutputs import writeLayer, intermediatesPath, sumLayers
import itertools
import omUtils
import os
from shapely import geometry
import bisect




def processEmissions(**kwargs): # doms, GFASfolder, GFASfile, metDir, ctmDir, CMAQdir, mechCMAQ, mcipsuffix, specTableFile, forceUpdate):
    '''Function to remap termite emissions to the CMAQ domain

    Args:
        startDate, endDate: currently ignored
        kwargs, specific arguments needed for this emission


    Returns:
        Nothing
    '''

    try:
        forceUpdate = kwargs['forceUpdate']
    except KeyError:
        forceUpdate = False
            
    ncin = nc.Dataset(termitePath, 'r')
    latTerm  = np.around(np.float64(ncin.variables['lat'][:]),3)
    latTerm = latTerm[-1::-1] # we need it south-north 
    lonTerm  = np.around(np.float64(ncin.variables['lon'][:]),3)
    dlatTerm = latTerm[0] - latTerm[1]
    dlonTerm = lonTerm[1] - lonTerm[0]
    lonTerm_edge = np.zeros((len(lonTerm) + 1))
    lonTerm_edge[0:-1] = lonTerm - dlonTerm/2.0
    lonTerm_edge[-1] = lonTerm[-1] + dlonTerm/2.0
    lonTerm_edge = np.around(lonTerm_edge,2)

    latTerm_edge = np.zeros((len(latTerm) + 1))
    latTerm_edge[0:-1] = latTerm + dlatTerm/2.0
    latTerm_edge[-1] = latTerm[-1] - dlatTerm/2.0
    latTerm_edge = np.around(latTerm_edge,2)

    nlonTerm = len(lonTerm)
    nlatTerm = len(latTerm)

    termAreas = np.zeros((nlatTerm,nlonTerm))
    # take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatTerm):
        termAreas[iy,:] = omUtils.area_of_rectangle_m2(latTerm_edge[iy],latTerm_edge[iy+1],lonTerm_edge[0],lonTerm_edge[-1])/lonTerm.size
    # now collect some domain information
    LATD = domainXr['LATD'][:].values.squeeze()
    LOND = domainXr['LOND'].values.squeeze()
    LAT  = domainXr.variables['LAT'].values.squeeze()
    LON  = domainXr.variables['LON'].values.squeeze()
    cmaqArea = domainXr.XCELL * domainXr.YCELL

    indxPath = "{}/TERM_ind_x.p.gz".format(intermediatesPath)
    indyPath = "{}/TERM_ind_y.p.gz".format(intermediatesPath)
    coefsPath = "{}/TERM_coefs.p.gz".format(intermediatesPath)

    if os.path.exists(indxPath) and os.path.exists(indyPath) and os.path.exists(coefsPath) and (not forceUpdate):
        ind_x = omUtils.load_zipped_pickle( indxPath )
        ind_y = omUtils.load_zipped_pickle( indyPath )
        coefs = omUtils.load_zipped_pickle( coefsPath )
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

            ixminl = bisect.bisect_right(lonTerm_edge,xmin)
            ixmaxr = bisect.bisect_right(lonTerm_edge,xmax)
            iyminl =  bisect.bisect_right(latTerm_edge,ymin)
            iymaxr =  bisect.bisect_right(latTerm_edge,ymax)

            for ix,iy  in itertools.product(range(max(0,ixminl-1),min(nlonTerm,ixmaxr)), range(max(0,iyminl-1),min(nlatTerm,iymaxr))):
                Term_gridcell = geometry.box(lonTerm_edge[ix],latTerm_edge[iy],lonTerm_edge[ix+1],latTerm_edge[iy+1])
                if CMAQ_gridcell.intersects(Term_gridcell):
                    intersection = CMAQ_gridcell.intersection(Term_gridcell)
                    weight1 = intersection.area/CMAQ_gridcell.area ## fraction of CMAQ cell covered
                    weight2 = intersection.area/Term_gridcell.area ## fraction of TERM cell covered
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
        omUtils.save_zipped_pickle(ind_x, indxPath )
        omUtils.save_zipped_pickle(ind_y, indyPath )
        omUtils.save_zipped_pickle(coefs, coefsPath )
        
    subset = ncin['ch4_emissions_2010_2016.asc'][...] # is masked array
    subset=subset.data # grab value
    np.clip(subset, 0., None, out=subset) # negative are missing values so remove by clipping in place
    subset = subset[-1::-1,:] # reverse latitudes
    subset *= 1e9/termAreas # converting from mtCH4/gridcell to kg/m^2
    cmaqAreas = np.ones( LAT.shape) * cmaqArea   # all grid cells equal area
    resultNd= omUtils.redistribute_spatially(LAT.shape, ind_x, ind_y, coefs, subset, termAreas, cmaqAreas)
    resultNd /= omUtils.secsPerYear
    ncin.close()
    
    writeLayer( 'OCH4_TERMITE', resultNd)
    return np.array( resultNd) 

def testTermiteEmis(**kwargs): # test totals for TERM emissions between original and remapped
    remapped = processEmissions(**kwargs)
    ncin = nc.Dataset(termitePath, 'r')
    latTerm  = np.around(np.float64(ncin.variables['lat'][:]),3)
    latTerm = latTerm[-1::-1] # reversing order, we need south first
    lonTerm  = np.around(np.float64(ncin.variables['lon'][:]),3)
    dlatTerm = latTerm[0] - latTerm[1]
    dlonTerm = lonTerm[1] - lonTerm[0]
    lonTerm_edge = np.zeros((len(lonTerm) + 1))
    lonTerm_edge[0:-1] = lonTerm - dlonTerm/2.0
    lonTerm_edge[-1] = lonTerm[-1] + dlonTerm/2.0
    lonTerm_edge = np.around(lonTerm_edge,2)

    latTerm_edge = np.zeros((len(latTerm) + 1))
    latTerm_edge[0:-1] = latTerm + dlatTerm/2.0
    latTerm_edge[-1] = latTerm[-1] - dlatTerm/2.0
    latTerm_edge = np.around(latTerm_edge,2)

    nlonTerm = len(lonTerm)
    nlatTerm = len(latTerm)

    latTermrev = latTerm[::-1]
    latTermrev_edge = latTerm_edge[::-1]
    areas = np.zeros((nlatTerm,nlonTerm))
# take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatTerm):
        areas[iy,:] = omUtils.area_of_rectangle_m2(latTerm_edge[iy],latTerm_edge[iy+1],lonTerm_edge[0],lonTerm_edge[-1])/lonTerm.size
    LATD = domainXr.variables['LATD'].values.squeeze()
    LOND = domainXr.variables['LOND'].values.squeeze()
    indLat = (latTerm > LATD.min()) &( latTerm < LATD.max())
    indLon = (lonTerm > LOND.min()) &( lonTerm < LOND.max())
    TermCH4 = ncin['ch4_emissions_2010_2016.asc'][...][-1::-1,:] # reverse latitudes
#    np.clip( TermCH4, 0., None, out=TermCH4) # remove negative values in place
    inds = np.ix_(indLat, indLon)
    TermTotals = TermCH4[inds].sum()
    area = domainXr.XCELL*domainXr.YCELL
    remappedTotals = remapped.sum()*area/1e9 # conversion from kg to mt
    print(TermTotals, remappedTotals)
    return
if __name__ == '__main__':
    processEmissions()
    sumLayers()
