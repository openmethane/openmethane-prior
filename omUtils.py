"""
omUtils.py

Copyright 2023 The Superpower Institute Ltd
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import numpy as np
import json
import subprocess
import os
import copy
import pickle
import gzip

import dotenv
dotenv.load_dotenv()
getenv = os.environ.get

secsPerYear = 365 * 24 * 60 * 60

## UTILS
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def rebin(a, shape):
    sh = shape[0], a.shape[0] // shape[0], shape[1], a.shape[1] // shape[1]
    return a.reshape(sh).sum(3).sum(1)

def dateTimeRange( start, end, delta):
    t = start
    while t < end:
        yield t
        t += delta

        '''Utility functions used by a number of different functions
'''

def deg2rad(deg):
    '''
    Convert degrees to radians

    Args:
        deg: a number in degrees (may be a numpy array)

    Returns:
        rad: the corresponding value in radians

    '''
    return deg * np.pi/180.

def getDistanceFromLatLonInKm(lat1,lon1,lat2,lon2):
    '''Calculate the distance between points based on the latides and longitudes

    Distances between multiple pairs of points can be calculated, so
    long as point 1 is a one value and point 2 is given as
    equally-sized numpy arrays of latitudes and longitudes.

    Args:
        lat1: latitude of point 1
        lon1: longitude of point 1
        lat2: latitude of point(s) 2 
        lon2: longitude of point(s) 2

    Returns:
        d: distance(s) between point 1 and point(s) 2

    '''
    
    R = 6371.0 ## Radius of the earth in km
    dLat = deg2rad(lat2-lat1)  ## deg2rad below
    dLon = deg2rad(lon2-lon1)
    a = np.sin(dLat/2) * np.sin(dLat/2) + np.cos(deg2rad(lat1)) * np.cos(deg2rad(lat2)) * np.sin(dLon/2) * np.sin(dLon/2)
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    d = R * c ## Distance in km
    return d


def compressNCfile(filename,ppc = None):
    '''Compress a netCDF3 file to netCDF4 using ncks
    
    Args: 
        filename: Path to the netCDF3 file to commpress
        ppc: number of significant digits to retain (default is to retain all)

    Returns:
        Nothing
    '''
    
    if os.path.exists(filename):
        print("Compress file {} with ncks".format(filename))
        command = 'ncks -4 -L4 -O {} {}'.format(filename, filename)
        print('\t'+command)
        commandList = command.split(' ')
        if ppc is None:
            ppcText = ''
        else:
            if not isinstance(ppc, int):
                raise RuntimeError("Argument ppc should be an integer...")
            elif ppc < 1 or ppc > 6:
                raise RuntimeError("Argument ppc should be between 1 and 6...")
            else:
                ppcText = '--ppc default={}'.format(ppc)
                commandList = [commandList[0]] + ppcText.split(' ') + commandList[1:]
        ##
        ##
        p = subprocess.Popen(commandList, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if len(stderr) > 0 or len(stdout) > 0:
            print("stdout = " + stdout)
            print("stderr = " + stderr)
            raise RuntimeError("Error from ncks...")
    else:
        print("File {} not found...".format(filename))

def loadScripts(Scripts):
    '''Read the contents (i.e. the lines of text) of a set of scripts into a dictionary
    
    Args:
        scripts: A dictionary of dictionaries, with the inner level containing the key 'path'

    Returns: 
        scripts: A dictionary of dictionaries, with the inner level containing the keys 'path' and 'lines' (giving their file path and lines of text, respectively)
    '''
    scripts = copy.copy(Scripts)
    ## for each of the scripts, read in the contents
    for k in list(scripts.keys()):
        ## check that the script is found
        if not os.path.exists(scripts[k]['path']):
            raise RuntimeError("Template run script {} not found at {} ... ".format(k,scripts[k]['path']))
        ##
        f = open(scripts[k]['path'])
        scripts[k]['lines'] = f.readlines()
        f.close()
    ##
    return scripts
    
def replace_and_write(lines, outfile, substitutions, strict = True, makeExecutable = False):
    '''Make a set of substitutions from a list of strings and write to file

    Args: 
        lines: List of strings
        outfile: Place to write the destination
        substitutions: List of substitutions
        strict: Boolean, if True, it will cause an error if substitutions don't mattch exactly once
        makeExecutable: Make the output script an executable

    Returns:
        Nothing
    '''
    Lines = copy.copy(lines)
    for subst in substitutions:
        token = subst[0]
        replc = subst[1]
        matches = [ iline for iline, line in enumerate(Lines) if line.find(token) != -1 ]
        nmatches = len(matches)
        if (nmatches == 1) or (nmatches > 0 and (not strict)):
            for iline in matches:
                ## Lines[iline] = re.sub(token, replc, Lines[iline])
                Lines[iline] = Lines[iline].replace(token, replc)
        elif strict:
            raise ValueError("Token '%s' matches %i times..." % (token, nmatches))
    if os.path.exists(outfile):
        os.remove(outfile)
    f = open(outfile, 'w')
    for line in Lines:
        f.write(line)
    f.close()
    if makeExecutable:
        os.chmod(outfile,0o0744)

def int_array_to_comma_separated_string(arr):
    '''Convert an list of integers to a comma-separated string

    Args:
        Arr: list of integers

    Returns:
        Str: comma-separated string
    '''
    return ''.join(['%i, ' % i for i in arr])


def source2(script, shell = 'bash'):
    '''Source a shell script, list all the shell environment variables, return them as a dictionary
   
    Args: 
        script: path to the script to source 
        shell: which shell to use (e.g. 'csh' or 'bash')
    
    Returns:
        Env: Dictionary of shell environment variables
    '''
    command = [shell, '-c', 'source %s && env' % script]

    proc = subprocess.Popen(command, stdout = subprocess.PIPE)

    Env = os.environ.copy()
    for line in proc.stdout:
        (key, _, value) = line.partition("=")
        Env[key] = value

    proc.communicate()

    return Env

def save_zipped_pickle(obj, filename, protocol=-1):
    with gzip.open(filename, 'wb') as f:
        pickle.dump(obj, f, protocol)

def load_zipped_pickle(filename):
    with gzip.open(filename, 'rb') as f:
        loaded_object = pickle.load(f)
    return loaded_object
                        
def area_of_rectangle_km2(lat1,lat2,lon1,lon2):
    '''Calculate the area of a latitude/longitude rectangle, returning the result in km^2

    Args:
        lat1: Latitude of one corner
        lat2: Latitude of the diagonally opposite corner
        lon1: Longitude of one corner
        lon2: Longitude of the diagonally opposite corner

    Returns:
        A: area in units of km^2
    '''
    LAT1 = np.pi*lat1/180.0
    LAT2 = np.pi*lat2/180.0
    # LON1 = np.pi*lon1/180.0
    # LON2 = np.pi*lon2/180.0
    R = 6371 ## radius of earth
    coef = 708422.8776524838 ## (np.pi/180.0) * R**2
    A = coef * np.abs(np.sin(LAT1)-np.sin(LAT2)) * np.abs(lon1-lon2)
    return A

def area_of_rectangle_m2(lat1,lat2,lon1,lon2):
    '''Calculate the area of a latitude/longitude rectangle, returning the result in m^2

    Args:
        lat1: Latitude of one corner
        lat2: Latitude of the diagonally opposite corner
        lon1: Longitude of one corner
        lon2: Longitude of the diagonally opposite corner

    Returns:
        A: area in units of m^2
    '''
    LAT1 = np.pi*lat1/180.0
    LAT2 = np.pi*lat2/180.0
    # LON1 = np.pi*lon1/180.0
    # LON2 = np.pi*lon2/180.0
    R = 6371 ## radius of earth
    coef = 708422.8776524838 ## (np.pi/180.0) * R**2
    A = coef * np.abs(np.sin(LAT1)-np.sin(LAT2)) * np.abs(lon1-lon2) * 1e6
    return A
