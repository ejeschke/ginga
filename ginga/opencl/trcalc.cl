__kernel void image_rotate_uint32(
    // input, output buffers in global memory
    __global unsigned int * src_data, __global unsigned int * dst_data,
    int rotctr_x, int rotctr_y,                      // rotation about pt
    int wd, int ht,                                  // src image dimensions
    int dst_wd, int dst_ht,                          // dst image dimensions
    int dst_dx, int dst_dy,                          // dst offsets in image
    double sin_theta, double cos_theta,              // rotation parameters
    unsigned int clip_val )                          // clip subst value
{    
    // Thread gets its index within index space
    const int iy = get_global_id(0);    // height, y-axis
    const int ix = get_global_id(1);    // width,  x-axis

    int xi = ix - dst_dx - rotctr_x;
    int yi = iy - dst_dy - rotctr_y;

    // Calculate location of data to move into ix and iy
    double xpos = (((double)xi) * cos_theta - ((double)yi) * sin_theta) + rotctr_x;    
    double ypos = (((double)xi) * sin_theta + ((double)yi) * cos_theta) + rotctr_y; 

    int xp = (int) round(xpos);
    int yp = (int) round(ypos);

    // Bound Checking
    if (((xp >= 0) && (xp < wd)) && ((yp >= 0) && (yp < ht)))
    {
        // Read (xp, yp) src_data and store at (ix, iy) in dst_data
        dst_data[iy * dst_wd + ix] = src_data[yp * wd + xp]; 
    }
    else {
        dst_data[iy * dst_wd + ix] = clip_val;
    }
}

__kernel void image_rotate_float64(
    // input, output buffers in global memory
    __global double * src_data, __global double * dst_data,
    int rotctr_x, int rotctr_y,                      // rotation about pt
    int wd, int ht,                                  // src image dimensions
    int dst_wd, int dst_ht,                          // dst image dimensions
    int dst_dx, int dst_dy,                          // dst offsets in image
    double sin_theta, double cos_theta,              // rotation parameters
    double clip_val )                                // clip subst value
{    
    // Thread gets its index within index space
    const int iy = get_global_id(0);    // height, y-axis
    const int ix = get_global_id(1);    // width,  x-axis

    int xi = ix - dst_dx - rotctr_x;
    int yi = iy - dst_dy - rotctr_y;

    // Calculate location of data to move into ix and iy
    double xpos = (((double)xi) * cos_theta - ((double)yi) * sin_theta) + rotctr_x;    
    double ypos = (((double)xi) * sin_theta + ((double)yi) * cos_theta) + rotctr_y; 

    int xp = (int) round(xpos);
    int yp = (int) round(ypos);

    // Bound Checking
    if (((xp >= 0) && (xp < wd)) && ((yp >= 0) && (yp < ht)))
    {
        // Read (xp, yp) src_data and store at (ix, iy) in dst_data
        dst_data[iy * dst_wd + ix] = src_data[yp * wd + xp]; 
    }
    else {
        dst_data[iy * dst_wd + ix] = clip_val;
    }
}

__kernel void image_transform_uint32(
    // input, output buffers in global memory
    __global unsigned int * src_data, __global unsigned int * dst_data,
    int wd, int ht,                                  // image dimensions
    int flipx, int flipy, int swapxy )               // transform flags
{    
    // Thread gets its index within index space
    const int ix = get_global_id(1);
    const int iy = get_global_id(0);

    // default is to simply pass through
    int dst_x = ix;
    int dst_y = iy;

    if (flipy != 0) {
        dst_y = ht - 1 - iy;
    }

    if (flipx != 0) {
        dst_x = wd - 1 - ix;
    }

    if (swapxy != 0) {
        dst_data[dst_x * ht + dst_y] = src_data[iy * wd + ix];
    }
    else {
        dst_data[dst_y * wd + dst_x] = src_data[iy * wd + ix];
    }
}

__kernel void image_resize_uint32(
    __global const uint *src_data,
    __global uint *dst_data,
    const int old_wd,
    const int new_wd,
    const double scale_x,
    const double scale_y)
{
    // Thread gets its index within index space
    const int ix = get_global_id(1);
    const int iy = get_global_id(0);

    int new_idx = iy * new_wd + ix;
    int old_idx = convert_int_rtz(iy * (1.0/scale_y)) * old_wd + convert_int_rtz(ix * (1.0/scale_x));

    dst_data[new_idx] = src_data[old_idx];
}

__kernel void image_resize_float64(
    __global const double * src_data,
    __global double * dst_data,
    const int old_wd,
    const int new_wd,
    const double scale_x,
    const double scale_y)
{
    // Thread gets its index within index space
    const int ix = get_global_id(1);
    const int iy = get_global_id(0);

    int new_idx = iy * new_wd + ix;
    int old_idx = convert_int_rtz(iy * (1.0/scale_y)) * old_wd + convert_int_rtz(ix * (1.0/scale_x));

    dst_data[new_idx] = src_data[old_idx];
}
