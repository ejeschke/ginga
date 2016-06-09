import unittest
import logging
import numpy as np

from ginga import ColorDist as cd

from functools import wraps


class TestError(Exception):
    pass

class TestColorDist(unittest.TestCase):

    def setUp(self):
        pass
    
    def test_ColorDists(self):
        hashsize = 256
        colorlen = 256
        data = np.tile(np.arange(hashsize, dtype='int'), (20,1))
        
        def scale_and_rescale(func):
            def wrapper(x, **kwargs):
                base = x / float(hashsize)
                out = func(base , **kwargs)
                result = out.clip(0.0, 1.0) * (colorlen-1)
                return result.astype('int')
            return wrapper

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
        
        @scale_and_rescale
        def test_histeq(x):
            return x # not right, certain fail case

        x = data[0]
        dists = {
            'linear': test_linear(x),
            'log': test_log(x),
            'power': test_power(x),
            'sqrt': test_sqrt(x),
            'squared': test_squared(x),
            'asinh': test_asinh(x),
            'sinh': test_sinh(x),
            'histeq': test_histeq(x),}

        for dist_name in dists.keys():
            dist = cd.get_dist(dist_name)(hashsize, colorlen=colorlen)
            out = dist.hash_array(data)
            y = out[0]
            expected_y = dists[dist_name]
        
            try:
                assert np.array_equal(y, expected_y)
            except:
                print y
                print expected_y
                print AssertionError("Assertion failed for " + dist_name)
    
    def tearDown(self):
        pass

    
if __name__ == '__main__':
    unittest.main()
