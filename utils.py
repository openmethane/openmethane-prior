import numpy as np
import json
import datetime

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
