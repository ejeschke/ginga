#
# LayerImage.py -- Abstraction of an generic layered image.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy
import time

from ginga import BaseImage
from ginga.misc import Bunch

class LayerImage(object):
    """Mixin class for BaseImage subclasses.  Adds layers and alpha/rgb
    compositing.
    """

    def __init__(self):
        self._layer = []
        self.cnt = 0
        self.compose_types = ('alpha', 'rgb')
        self.compose = 'alpha'

    def _insert_layer(self, idx, image, alpha=None, name=None):
        if alpha is None:
            alpha = 1.0
        if name is None:
            name = "layer%d" % (self.cnt)
            self.cnt += 1
        bnch = Bunch.Bunch(image=image, alpha=alpha, name=name)
        self._layer.insert(idx, bnch)

    def insert_layer(self, idx, image, alpha=None, name=None,
                    compose=True):
        self._insert_layer(idx, image, alpha=alpha, name=name)

        if compose:
            self.compose_layers()

    def set_layer(self, idx, image, alpha=None, name=None,
                    compose=True):
        self.delete_layer(idx, compose=False)
        self._insert_layer(idx, image, alpha=alpha, name=name)

        if compose:
            self.compose_layers()

    def delete_layer(self, idx, compose=True):
        self._layer.pop(idx)

        if compose:
            self.compose_layers()

    def get_layer(self, idx):
        return self._layer[idx]

    def num_layers(self):
        return len(self._layer)

    def get_max_shape(self, entity='image'):
        maxdim = -1
        maxshape = ()
        for layer in self._layer:
            if entity == 'image':
                shape = layer[entity].get_shape()
            elif entity == 'alpha':
                item = layer.alpha
                # If alpha is an image, get the array
                if isinstance(item, BaseImage.BaseImage):
                    item = layer.alpha.get_data()
                shape = numpy.shape(item)
            else:
                raise BaseImage.ImageError("entity '%s' not in (image, alpha)" % (
                    entity))

            if len(shape) > maxdim:
                maxdim = len(shape)
                maxshape = shape
        return maxshape

    ## def alpha_combine(self, src, alpha, dst):
    ##     return (src * alpha) + (dst * (1.0 - alpha))

    def mono2color(self, data):
        return numpy.dstack((data, data, data))

    def alpha_multiply(self, alpha, data, shape=None):
        """(alpha) can be a scalar or an array.
        """
        # alpha can be a scalar or an array
        if shape is None:
            shape = data.shape

        if len(data.shape) == 2:
            res = alpha * data
            # If desired shape is monochrome then return a mono image
            # otherwise broadcast to a grey color image.
            if len(shape) == 2:
                return res

            # note: in timing tests, dstack was not as efficient here...
            #data = numpy.dstack((res, res, res))
            data = numpy.empty(shape)
            data[:, :, 0] = res[:, :]
            data[:, :, 1] = res[:, :]
            data[:, :, 2] = res[:, :]
            return data

        else:
            # note: in timing tests, dstack was not as efficient here...
            #res = numpy.dstack((data[:, :, 0] * alpha,
            #                    data[:, :, 1] * alpha,
            #                    data[:, :, 2] * alpha))
            res = numpy.empty(shape)
            res[:, :, 0] = data[:, :, 0] * alpha
            res[:, :, 1] = data[:, :, 1] * alpha
            res[:, :, 2] = data[:, :, 2] * alpha
            return res


    def alpha_compose(self):
        start_time = time.time()
        shape = self.get_max_shape()
        ## ht, wd = shape[:2]
        ## # alpha can be a scalar or an array, prepare for the appropriate kind
        ## ashape = self.get_max_shape(entity='alpha')
        ## if len(ashape) == 0:
        ##     alpha_used = 0.0
        ## else:
        ##     alpha_used = numpy.zeros((ht, wd))

        # result holds the result of the composition
        result = numpy.zeros(shape)

        cnt = 0
        for layer in self._layer:
            alpha = layer.alpha
            if isinstance(alpha, BaseImage.BaseImage):
                alpha = alpha.get_data()
            #alpha = numpy.clip((1.0 - alpha_used) * alpha, 0.0, 1.0)
            #mina = numpy.min(alpha)
            #print "cnt=%d mina=%f" % (cnt, mina)
            data = layer.image.get_data()
            result += self.alpha_multiply(alpha, data, shape=shape)
            ## alpha_used += layer.alpha
            #numpy.clip(alpha_used, 0.0, 1.0)
            cnt += 1

        self.set_data(result)
        end_time = time.time()
        self.logger.debug("alpha compose=%.4f sec" % (end_time - start_time))

    # def rgb_compose(self):
    #     slices = []
    #     start_time = time.time()
    #     for i in xrange(len(self._layer)):
    #         layer = self.get_layer(i)
    #         data = self.alpha_multiply(layer.alpha, layer.image.get_data())
    #         slices.append(data)
    #     split_time = time.time()
    #     result = numpy.dstack(slices)
    #     end_time = time.time()

    #     self.set_data(result)
    #     print "rgb_compose alpha multiply=%.4f sec  dstack=%.4f sec  sec total=%.4f sec" % (
    #         split_time - start_time, end_time - split_time,
    #         end_time - start_time)

    def rgb_compose(self):
        #num = self.num_layers()
        num = 3
        layer = self.get_layer(0)
        wd, ht = layer.image.get_size()
        result = numpy.empty((ht, wd, num))

        start_time = time.time()
        for i in range(len(self._layer)):
            layer = self.get_layer(i)
            alpha = layer.alpha
            if isinstance(alpha, BaseImage.BaseImage):
                alpha = alpha.get_data()
            data = self.alpha_multiply(alpha, layer.image.get_data())
            result[:, :, i] = data[:, :]
        end_time = time.time()

        self.set_data(result)
        self.logger.debug("rgb_compose  total=%.4f sec" % (
            end_time - start_time))

    def rgb_decompose(self, image):
        data = image.get_data()

        shape = data.shape
        if len(shape) == 2:
            self._insert_layer(0, image)

        else:
            names = ("Red", "Green", "Blue")
            alphas = (0.292, 0.594, 0.114)

            for i in range(shape[2]):
                imgslice = data[:, :, i]
                #img = BaseImage.BaseImage(data_np=imgslice, logger=self.logger)
                # Create the same type of image as we are decomposing
                img = image.__class__(data_np=imgslice, logger=self.logger)
                if i < 3:
                    name = names[i]
                    alpha = alphas[i]
                else:
                    name = "layer%d" % i
                    alpha = 0.0
                self._insert_layer(i, img, name=name, alpha=alpha)

        self.compose_layers()

    def set_compose_type(self, ctype):
        assert ctype in self.compose_types, \
               BaseImage.ImageError("Bad compose type '%s': must be one of %s" % (
            ctype, str(self.compose_types)))
        self.compose = ctype

        self.compose_layers()

    def set_alpha(self, lidx, val):
        layer = self._layer[lidx]
        layer.alpha = val

        self.compose_layers()

    def set_alphas(self, vals):
        for lidx in range(len(vals)):
            layer = self._layer[lidx]
            layer.alpha = vals[lidx]

        self.compose_layers()

    def compose_layers(self):
        if self.compose == 'rgb':
            self.rgb_compose()
        else:
            self.alpha_compose()


#END
