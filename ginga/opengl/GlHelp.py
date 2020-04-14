#
# GlHelp.py -- help classes for OpenGL drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import os.path

from OpenGL import GL as gl

from ginga import colors
import ginga.fonts
from ginga.canvas import transform

# Set up known fonts
fontdir, xx = os.path.split(ginga.fonts.__file__)
known_font = os.path.join(fontdir, 'Roboto', 'Roboto-Regular.ttf')

font_cache = {}


def get_cached_font(fontpath, fontsize):
    global font_cache

    key = (fontpath, fontsize)
    try:
        return font_cache[key]

    except KeyError:
        from PIL import ImageFont

        # TODO: try to lookup font before overriding
        fontpath = known_font

        font = ImageFont.truetype(fontpath, fontsize)
        font_cache[key] = font
        return font


class Pen(object):
    def __init__(self, color='black', alpha=1.0, linewidth=1,
                 linestyle='solid'):
        self.color = color
        self.linewidth = linewidth
        self.linestyle = linestyle
        self.alpha = alpha


class Brush(object):
    def __init__(self, color='black', fill=False, alpha=1.0):
        self.color = color
        self.fill = fill
        self.alpha = alpha


class Font(object):
    def __init__(self, fontname='ariel', fontsize=12.0, color='black',
                 linewidth=1, alpha=1.0):
        self.fontname = fontname
        self.fontsize = fontsize * 2.0
        self.color = color
        self.linewidth = linewidth
        # scale relative to a 12pt font
        self.scale = fontsize / 12.0
        self.alpha = alpha
        # TODO: currently there is only support for some simple built-in
        # fonts.  What kind of fonts/lookup can we use for this?
        #self.font = get_cached_font(self.fontname, self.fontsize)


class GlContext(object):

    def __init__(self, widget):
        #self.set_canvas(widget)
        self.widget = widget

    def get_color(self, color, alpha=1.0):
        if color is not None:
            r, g, b = colors.resolve_color(color)
        else:
            r, g, b = 1.0, 1.0, 1.0

        return (r, g, b, alpha)

    def get_pen(self, color, linewidth=1, linestyle='solid', alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Pen(color=color, linewidth=linewidth, linestyle=linestyle,
                   alpha=alpha)

    def get_brush(self, color, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Brush(color=color, fill=True, alpha=alpha)

    def get_font(self, name, size, color, linewidth=1, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Font(fontname=name, fontsize=size, color=color,
                    linewidth=linewidth, alpha=alpha)

    def text_extents(self, text, font):
        # TODO: we need a better approximation
        wd = len(text) * font.fontsize
        ht = font.fontsize
        return wd, ht


class ShaderManager:
    """Class for building/managing/using GLSL shader programs.
    """
    def __init__(self, logger):
        self.logger = logger

        self.pgms = {}
        self.program = None
        self.shader = None

    def build_program(self, name, vertex_source, fragment_source):
        """Build a GL shader program from vertex and fragment sources.

        Parameters
        ----------
        name : str
            Name under which to store this program

        vertex_source : str
            source code for the vertex shader

        fragment_source : str
            source code for the fragment shader

        Returns
        -------
        pgm_id : int
            program id of the compiled shader
        """
        pgm_id = gl.glCreateProgram()
        vert_id = self._add_shader(vertex_source, gl.GL_VERTEX_SHADER)
        frag_id = self._add_shader(fragment_source, gl.GL_FRAGMENT_SHADER)

        gl.glAttachShader(pgm_id, vert_id)
        gl.glAttachShader(pgm_id, frag_id)
        gl.glLinkProgram(pgm_id)

        if gl.glGetProgramiv(pgm_id, gl.GL_LINK_STATUS) != gl.GL_TRUE:
            info = gl.glGetProgramInfoLog(pgm_id)
            gl.glDeleteProgram(pgm_id)
            gl.glDeleteShader(vert_id)
            gl.glDeleteShader(frag_id)
            self.logger.error('Error linking GLSL program: %s' % (info))
            raise RuntimeError('Error linking GLSL program: %s' % (info))

        gl.glDeleteShader(vert_id)
        gl.glDeleteShader(frag_id)

        self.pgms[name] = pgm_id
        return pgm_id

    def load_program(self, name, dirpath):
        """Load a GL shader program from sources on disk.

        Parameters
        ----------
        name : str
            Name under which to store this program

        dirpath : str
            path to where the vertex and fragment shader sources are stored

        Returns
        -------
        pgm_id : int
            program id of the compiled shader
        """
        vspath = os.path.join(dirpath, name + '.vert')
        with open(vspath, 'r') as in_f:
            vert_source = in_f.read().encode()

        fgpath = os.path.join(dirpath, name + '.frag')
        with open(fgpath, 'r') as in_f:
            frag_source = in_f.read().encode()

        return self.build_program(name, vert_source, frag_source)

    def setup_program(self, name):
        """Set up to use a shader program.

        Parameters
        ----------
        name : str
            Name of the shader program to use

        Returns
        -------
        shader :
            The OpenGL shader program
        """
        self.program = name
        if name is None:
            gl.glUseProgram(0)
            self.shader = None
        else:
            self.shader = self.pgms[name]
            gl.glUseProgram(self.shader)
        return self.shader

    def get_uniform_loc(self, attr_name):
        """Get the location of a shader program uniform variable.

        Parameters
        ----------
        attr_name : str
            Name of the shader program attribute

        Returns
        -------
        loc : int
            The location of the attribute
        """
        _loc = gl.glGetUniformLocation(self.shader, attr_name)
        return _loc

    def _add_shader(self, source, shader_type):
        try:
            shader_id = gl.glCreateShader(shader_type)
            gl.glShaderSource(shader_id, source)
            gl.glCompileShader(shader_id)
            if gl.glGetShaderiv(shader_id, gl.GL_COMPILE_STATUS) != gl.GL_TRUE:
                info = gl.glGetShaderInfoLog(shader_id)
                raise RuntimeError('Shader compilation failed: %s' % (info))

            return shader_id

        except Exception as e:
            gl.glDeleteShader(shader_id)
            raise


def get_transforms(v):
    tform = {
        'window_to_native': (transform.CartesianWindowTransform(v).invert() +
                             transform.RotationTransform(v).invert() +
                             transform.ScaleTransform(v).invert()),
        'cartesian_to_window': (transform.FlipSwapTransform(v) +
                                transform.CartesianWindowTransform(v)),
        'cartesian_to_native': (transform.FlipSwapTransform(v) +
                                transform.RotationTransform(v) +
                                transform.CartesianNativeTransform(v)),
        'data_to_cartesian': (transform.DataCartesianTransform(v) +
                              transform.ScaleTransform(v)),
        'data_to_scrollbar': (transform.DataCartesianTransform(v) +
                              transform.FlipSwapTransform(v) +
                              transform.RotationTransform(v)),
        'mouse_to_data': (
            transform.InvertedTransform(transform.DataCartesianTransform(v) +
                                        transform.ScaleTransform(v) +
                                        transform.FlipSwapTransform(v) +
                                        transform.RotationTransform(v) +
                                        transform.CartesianWindowTransform(v)
                                        )),
        'data_to_window': (transform.DataCartesianTransform(v) +
                           transform.ScaleTransform(v) +
                           transform.FlipSwapTransform(v) +
                           transform.RotationTransform(v) +
                           transform.CartesianWindowTransform(v)
                           ),
        'data_to_percentage': (transform.DataCartesianTransform(v) +
                               transform.ScaleTransform(v) +
                               transform.FlipSwapTransform(v) +
                               transform.RotationTransform(v) +
                               transform.CartesianWindowTransform(v) +
                               transform.WindowPercentageTransform(v)),
        'data_to_native': (transform.DataCartesianTransform(v) +
                           transform.FlipSwapTransform(v)
                           ),
        'wcs_to_data': transform.WCSDataTransform(v),
        'wcs_to_native': (transform.WCSDataTransform(v) +
                          transform.DataCartesianTransform(v) +
                          transform.FlipSwapTransform(v)),
    }
    return tform
