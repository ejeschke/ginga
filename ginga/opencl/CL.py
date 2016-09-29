#
# CL.py -- OpenCL functions for
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os

import numpy as np

module_home = os.path.split(sys.modules[__name__].__file__)[0]

import pyopencl as cl


class CL(object):

    def __init__(self, filename=None):
        # TODO: we may want to choose GPU resources only
        self.ctx = cl.create_some_context()
        self.queue = cl.CommandQueue(self.ctx)

        if filename is not None:
            path = os.path.join(module_home, filename)
            self.load_program(path)

    def load_program(self, filename):
        #read in the OpenCL source file as a string
        with open(filename, 'r') as in_f:
            buf = in_f.read()
        self.load_program_buf(buf)

    def load_program_buf(self, buf):
        #create the program
        self.program = cl.Program(self.ctx, buf).build()

    def rotate(self, data_np, theta, rotctr_x=None, rotctr_y=None,
               clip_val=0,
               out=None, out_wd=0, out_ht=0, out_dx=0, out_dy=0):

        sin_theta = np.sin(np.radians(theta))
        cos_theta = np.cos(np.radians(theta))
        height, width = data_np.shape[:2]

        if rotctr_x is None:
            rotctr_x, rotctr_y = width // 2, height // 2

        mf = cl.mem_flags

        # convert to float64
        dtype = data_np.dtype
        data_np = np.ascontiguousarray(data_np, dtype=np.float64)

        if out is None:
            # no output array specified
            if out_ht == 0:
                # no desired output size specified--use dimensions of input
                # a clip, basically
                out_ht, out_wd = data_np.shape[:2]
            out_shape = (out_ht, out_wd) + data_np.shape[2:]
            out = np.empty(out_shape, dtype=data_np.dtype)
        else:
            # get dimensions of output array
            out_ht, out_wd = out.shape[:2]

        assert out.shape[2:] == data_np.shape[2:], ValueError(">2D dimensions don't match")

        numbytes = out_ht * out_wd * np.float64(0).nbytes

        #create OpenCL buffers on devices
        data_np = np.ascontiguousarray(data_np)
        src_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                            hostbuf=data_np)
        dst_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, numbytes)

        evt = self.program.image_rotate_float64(self.queue, [out_ht, out_wd], None,
                                                src_buf, dst_buf,
                                                np.int32(rotctr_x), np.int32(rotctr_y),
                                                np.int32(width), np.int32(height),
                                                np.int32(out_wd), np.int32(out_ht),
                                                np.int32(out_dx), np.int32(out_dy),
                                                np.float64(sin_theta), np.float64(cos_theta),
                                                np.float64(clip_val))

        if dtype == np.float64:
            out_np = out
        else:
            out_np = np.empty(out_shape, dtype=np.float64)

        cl.enqueue_read_buffer(self.queue, dst_buf, out_np).wait()
        #cl.enqueue_copy(self.queue, out_np, dst_buf).wait()

        res = out_np.astype(dtype)
        if out is not None:
            out[...] = res
        else:
            out = res

        return out

    def rotate_clip(self, data_np, theta, rotctr_x=None, rotctr_y=None,
                    clip_val=0, out=None):

        sin_theta = np.sin(np.radians(theta))
        cos_theta = np.cos(np.radians(theta))
        height, width = data_np.shape[:2]

        if rotctr_x is None:
            rotctr_x, rotctr_y = width // 2, height // 2

        mf = cl.mem_flags

        # convert to float64
        dtype = data_np.dtype
        data_np = np.ascontiguousarray(data_np, dtype=np.float64)

        # clipped array is same size as original
        out_ht, out_wd = data_np.shape[:2]
        out_dx, out_dy = 0, 0
        numbytes = data_np.nbytes

        #create OpenCL buffers on devices
        data_np = np.ascontiguousarray(data_np)
        src_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                            hostbuf=data_np)
        dst_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, numbytes)

        evt = self.program.image_rotate_float64(self.queue, [height, width], None,
                                                src_buf, dst_buf,
                                                np.int32(rotctr_x), np.int32(rotctr_y),
                                                np.int32(width), np.int32(height),
                                                np.int32(out_wd), np.int32(out_ht),
                                                np.int32(out_dx), np.int32(out_dy),
                                                np.float64(sin_theta), np.float64(cos_theta),
                                                np.float64(clip_val))

        out_np = np.empty_like(data_np)
        cl.enqueue_read_buffer(self.queue, dst_buf, out_np).wait()
        #cl.enqueue_copy(self.queue, out_np, dst_buf).wait()

        res = out_np.astype(dtype)
        if out is not None:
            out[...] = res
        else:
            out = res

        return out

    def rotate_clip_uint32(self, data_np, theta, rotctr_x=None, rotctr_y=None,
                           clip_val=0, out=None):

        sin_theta = np.sin(np.radians(theta))
        cos_theta = np.cos(np.radians(theta))
        height, width = data_np.shape[:2]

        if rotctr_x is None:
            rotctr_x, rotctr_y = width // 2, height // 2

        mf = cl.mem_flags

        if out is None:
            out = np.empty_like(data_np)
        # clipped array is same size as original
        out_ht, out_wd = out.shape[:2]
        out_dx, out_dy = 0, 0

        #create OpenCL buffers on devices
        data_np = np.ascontiguousarray(data_np)
        src_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                            hostbuf=data_np)
        dst_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, out.nbytes)

        evt = self.program.image_rotate_uint32(self.queue, [height, width], None,
                                               src_buf, dst_buf,
                                               np.int32(rotctr_x), np.int32(rotctr_y),
                                               np.int32(width), np.int32(height),
                                               np.int32(out_wd), np.int32(out_ht),
                                               np.int32(out_dx), np.int32(out_dy),
                                               np.float64(sin_theta), np.float64(cos_theta),
                                               np.uint32(clip_val))

        cl.enqueue_read_buffer(self.queue, dst_buf, out).wait()

        return out

    def rotate_uint32(self, data_np, theta, rotctr_x=None, rotctr_y=None,
                      clip_val=0,
                      out=None, out_wd=0, out_ht=0, out_dx=0, out_dy=0):

        sin_theta = np.sin(np.radians(theta))
        cos_theta = np.cos(np.radians(theta))
        height, width = data_np.shape[:2]

        if rotctr_x is None:
            rotctr_x, rotctr_y = width // 2, height // 2

        mf = cl.mem_flags

        if out is None:
            if out_ht == 0:
                out_ht, out_wd = data_np.shape[:2]
            out_shape = (out_ht, out_wd) + data_np.shape[2:]
            out = np.zeros(out_shape, dtype=data_np.dtype)
        else:
            out_ht, out_wd = out.shape[:2]

        assert out.shape[2:] == data_np.shape[2:], ValueError(">2D dimensions don't match")

        #create OpenCL buffers on devices
        data_np = np.ascontiguousarray(data_np)
        src_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                            hostbuf=data_np)
        dst_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, out.nbytes)

        evt = self.program.image_rotate_uint32(self.queue, [out_ht, out_wd], None,
                                               src_buf, dst_buf,
                                               np.int32(rotctr_x), np.int32(rotctr_y),
                                               np.int32(width), np.int32(height),
                                               np.int32(out_wd), np.int32(out_ht),
                                               np.int32(out_dx), np.int32(out_dy),
                                               np.float64(sin_theta), np.float64(cos_theta),
                                               np.uint32(clip_val))

        cl.enqueue_read_buffer(self.queue, dst_buf, out).wait()

        return out

    def transform_uint32(self, data_np,
                         flip_x=False, flip_y=False, swap_xy=False,
                         out=None):

        height, width = data_np.shape[:2]

        new_ht, new_wd = height, width
        if swap_xy:
            new_ht, new_wd = width, height
        new_size = [new_ht, new_wd] + list(data_np.shape[2:])

        mf = cl.mem_flags

        #create OpenCL buffers on devices
        data_np = np.ascontiguousarray(data_np)
        src_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                            hostbuf=data_np)
        dst_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, data_np.nbytes)

        evt = self.program.image_transform_uint32(self.queue, [height, width], None,
                                                  src_buf, dst_buf,
                                                  np.int32(width), np.int32(height),
                                                  np.int32(flip_x), np.int32(flip_y),
                                                  np.int32(swap_xy))

        if out is None:
            out = np.empty_like(data_np).reshape(new_size)
        cl.enqueue_read_buffer(self.queue, dst_buf, out).wait()

        return out


    def resize_uint32(self, data_np, scale_x, scale_y, out=None):

        height, width = data_np.shape[:2]

        new_ht = int(height * scale_y)
        new_wd = int(width * scale_x)
        new_shape = [new_ht, new_wd] + list(data_np.shape[2:])

        mf = cl.mem_flags

        #create OpenCL buffers on devices
        data_np = np.ascontiguousarray(data_np)
        src_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                            hostbuf=data_np)

        num_bytes = new_ht * new_wd * np.uint32(0).nbytes
        dst_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, num_bytes)

        evt = self.program.image_resize_uint32(self.queue, [new_ht, new_wd], None,
                                               src_buf, dst_buf,
                                               np.int32(width), np.int32(new_wd),
                                               np.float64(scale_x), np.float64(scale_y))

        if out is None:
            out = np.empty(new_shape, dtype=data_np.dtype)
        cl.enqueue_read_buffer(self.queue, dst_buf, out).wait()

        return out

    def resize(self, data_np, scale_x, scale_y, out=None):

        height, width = data_np.shape[:2]

        new_ht = int(height * scale_y)
        new_wd = int(width * scale_x)
        new_shape = [new_ht, new_wd] + list(data_np.shape[2:])

        mf = cl.mem_flags

        #create OpenCL buffers on devices
        dtype = data_np.dtype
        data_np = np.ascontiguousarray(data_np, dtype=np.float64)

        src_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                            hostbuf=data_np)

        num_bytes = new_ht * new_wd * np.float64(0).nbytes
        dst_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, num_bytes)

        evt = self.program.image_resize_float64(self.queue, [new_ht, new_wd], None,
                                                src_buf, dst_buf,
                                                np.int32(width), np.int32(new_wd),
                                                np.float64(scale_x), np.float64(scale_y))

        if dtype == np.float64:
            out_np = out
        else:
            out_np = np.empty(new_shape, dtype=np.float64)

        cl.enqueue_read_buffer(self.queue, dst_buf, out_np).wait()

        res = out_np.astype(dtype)
        if out is not None:
            out[...] = res
        else:
            out = res

        return out

    def get_scaled_cutout_basic(self, data_np, x1, y1, x2, y2, scale_x, scale_y,
                                out=None):

        if (data_np.dtype == np.uint32) or ((data_np.dtype == np.uint8) and
                                               (len(data_np.shape) == 3)):
            newdata = self.resize_uint32(data_np[y1:y2+1, x1:x2+1, ...],
                                         scale_x, scale_y, out=out)
        else:
            newdata = self.resize(data_np[y1:y2+1, x1:x2+1],
                                  scale_x, scale_y, out=out)

        old_ht, old_wd = data_np.shape[:2]
        ht, wd = newdata.shape[:2]
        scale_x, scale_y = float(wd) / old_wd, float(ht) / old_ht

        return newdata, (scale_x, scale_y)

#END
