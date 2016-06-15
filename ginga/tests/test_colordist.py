import unittest
import numpy as np

from ginga import ColorDist as cd

class TestColorDist(unittest.TestCase):
    pass
    # we'll add tests here, look in __main__

# Tests for each of the distributions #

# wrapper needed to first scale the data to range(0,1)
# then returns with the original range given
def scale_and_rescale(func):
    def wrapper(x, **kwargs):
        base = x / float(hashsize)
        out = func(base , **kwargs)
        result = out.clip(0.0, 1.0) * (colorlen-1)
        return result.astype('int')
    return wrapper

# look at http://ds9.si.edu/doc/ref/how.html or in 'ColorDist.py' 
# for how these functions are defined
@scale_and_rescale
def test_linear(x):
    return x

@scale_and_rescale
def test_log(x, a= 1000):
    return np.log(a*x + 1)/np.log(a)

@scale_and_rescale
def test_power(x, a= 1000):
    return (np.power(a, x) - 1.0)/a

@scale_and_rescale
def test_sqrt(x):
    return np.sqrt(x)

@scale_and_rescale
def test_squared(x):
    return x*x

@scale_and_rescale
def test_asinh(x, factor= 10.0, nonlinearity= 3.0):
    return np.arcsinh(factor*x)/nonlinearity

@scale_and_rescale
def test_sinh(x, factor= 10.0, nonlinearity= 3.0):
    return np.sinh(nonlinearity*x)/factor

def test_histeq(x):
    idx = x.clip(0, hashsize-1)
    hist, bins = np.histogram(idx.ravel(), hashsize, density=False)
    cdf = hist.cumsum()

    l = (cdf - cdf.min()) * (colorlen - 1) / (cdf.max() - cdf.min())
    hash = l.astype('int')
    return hash[idx]


if __name__ == '__main__':
    
    hashsize = 256
    colorlen = 256

    # test data
    data = np.tile(np.arange(hashsize, dtype='int'), (20,1))
    x = data[0] # only using the first row as input

    # example test functions as defined above, use this to compare against the actual module
    dists = {
        'linear': test_linear,
        'log': test_log,
        'power': test_power,
        'sqrt': test_sqrt,
        'squared': test_squared,
        'asinh': test_asinh,
        'sinh': test_sinh,
        'histeq': test_histeq,}

    def test_dist_function(dist_name):
        def test_this_dist():
            dist = cd.get_dist(dist_name)(hashsize, colorlen=colorlen)
            out = dist.hash_array(data)
            y = out[0] # again, only using first row for input/ouput testing
            expected_y = dists[dist_name](x)

            try:
                assert np.array_equal(y, expected_y)
            except:
                raise AssertionError("Assertion failed for " + dist_name)
        return test_this_dist


    for dist_name in dists.keys():
        # add test function for each distribution into the class TestColorDist
        setattr(TestColorDist, 'test_' + dist_name, staticmethod(test_dist_function(dist_name)))

    # now run tests with class populated with test methods
    unittest.main()
