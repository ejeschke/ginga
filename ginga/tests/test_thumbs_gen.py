"""Tests for the serialized thumbnail generator in the Thumbs plugin.

The thumb generator is one stateful viewer: ``_render_thumb()`` sets an
image on it and then reads the rendered pixels back out.  Those two steps
have to be atomic with respect to one another -- if two callers interleave
them, one publishes the other's pixels, and nothing raises to say so.  The
tests here pin down that the queue in front of it really does serialize
every caller, in both the threaded and the single-event-loop (async) modes,
and that a failed render can no longer lose the thumb entirely.
"""

import asyncio
import threading
import time

import numpy as np
import pytest

from ginga.misc import Bunch, Settings, Timer, log
from ginga.rv.plugins.Thumbs import Thumbs
from ginga.pilw.ImageViewPil import CanvasView
from ginga import AstroImage


class ReentryError(Exception):
    pass


class StubGenerator:
    """Stands in for the thumb generator, and objects to being shared.

    Rendering is "set the image, then read it back".  This stub puts a
    detectable gap between the two and fails loudly if anybody else sets
    an image inside that gap -- which is exactly the bug the queue exists
    to prevent, and which is otherwise silent.
    """

    rgb_order = 'RGB'

    def __init__(self, delay=0.0):
        self.delay = delay
        self.cur = None
        self.renders = []
        self.concurrent = []
        self._inside = False
        self._lock = threading.Lock()

    def viewable(self, image):
        return not image.get('unviewable', False)

    def set_image(self, image):
        with self._lock:
            if self._inside:
                self.concurrent.append(image.get('name'))
                raise ReentryError("two callers inside the generator at once")
            self._inside = True
        self.cur = image

    def apply_attributes(self, dct):
        assert self._inside, "attributes applied outside a render"
        self.cur.set(applied=dct)

    def get_image_as_array(self, order='RGB'):
        if self.delay:
            time.sleep(self.delay)
        name = self.cur.get('name')
        with self._lock:
            self.renders.append(name)
            self._inside = False
        # encode the name's length so a mismatched pairing is visible
        return np.full((4, 4, 3), len(name) % 256, dtype=np.uint8)


class FakeShell:
    """The slice of GingaShell that Thumbs needs, and nothing else."""

    def __init__(self, logger, tmpdir, async_mode=False):
        self.logger = logger
        self.ev_quit = threading.Event()
        self.async_mode = async_mode
        self.gui_thread_id = threading.get_ident()
        self.prefs = Settings.Preferences(basefolder=str(tmpdir),
                                          logger=logger)
        self.tfact = Timer.TimerFactory(logger=logger)
        self.gui_queue = []
        self.gui_lock = threading.Lock()
        self.threads = []
        self.aio_tasks = []

    # -- plugin scaffolding
    def get_plugin_spec(self, name):
        return Bunch.Bunch(hidden=True)

    def get_preferences(self):
        return self.prefs

    def get_backend_timer(self):
        return self.tfact.timer()

    def set_callback(self, name, fn, *args, **kwargs):
        pass

    def add_callback(self, name, fn, *args, **kwargs):
        pass

    # -- threading model
    def get_taskpool_type(self):
        return 'async' if self.async_mode else 'thread'

    def assert_gui_thread(self):
        if self.async_mode:
            return
        assert threading.get_ident() == self.gui_thread_id, \
            "non-GUI thread is executing GUI code"

    def assert_nongui_thread(self):
        if self.async_mode:
            return
        assert threading.get_ident() != self.gui_thread_id, \
            "GUI thread is executing non-GUI code"

    def gui_do(self, method, *args, **kwargs):
        with self.gui_lock:
            self.gui_queue.append((method, args, kwargs))

    def nongui_do(self, method, *args, **kwargs):
        if self.async_mode:
            res = method(*args, **kwargs)
            assert asyncio.iscoroutine(res), \
                "async mode got a plain function, which would never run"
            self.aio_tasks.append(asyncio.ensure_future(res))
            return
        t = threading.Thread(target=method, args=args, kwargs=kwargs,
                             daemon=True)
        self.threads.append(t)
        t.start()

    # -- test helpers
    def join_workers(self, timeout=20.0):
        deadline = time.time() + timeout
        while True:
            with self.gui_lock:
                pending = list(self.threads)
            alive = [t for t in pending if t.is_alive()]
            if not alive:
                return
            assert time.time() < deadline, "worker threads did not finish"
            for t in alive:
                t.join(0.05)

    def flush_gui(self):
        """Run the queued gui_do calls, as the GUI thread would."""
        while True:
            with self.gui_lock:
                if not self.gui_queue:
                    return
                method, args, kwargs = self.gui_queue.pop(0)
            method(*args, **kwargs)


def mk_image(name, unviewable=False):
    image = AstroImage.AstroImage(data_np=np.zeros((8, 8), dtype=np.float32))
    image.set(name=name, path='/nonexistent/%s.fits' % name)
    if unviewable:
        image.set(unviewable=True)
    return image


def mk_thumbs(tmpdir, async_mode=False, delay=0.0):
    logger = log.get_logger("test_thumbs", null=True)
    fv = FakeShell(logger, tmpdir, async_mode=async_mode)
    thumbs = Thumbs(fv)
    # swap in the stub so a shared render is detectable instead of silent
    gen = StubGenerator(delay=delay)
    thumbs.thumb_generator = gen
    return thumbs, fv, gen


def mk_request(thumbs, name, extras=None, unviewable=False, attrs=None):
    extras = Bunch.Bunch() if extras is None else extras
    return Bunch.Bunch(thumbkey=('Ch', name, '/nonexistent/%s.fits' % name),
                       image=mk_image(name, unviewable=unviewable),
                       extras=extras, metadata=None, save_thumb=False,
                       attrs=attrs, rgb_array=None, ignore=False)


# ---------------------------------------------------------------- threaded

def test_every_request_is_rendered_exactly_once(tmp_path):
    thumbs, fv, gen = mk_thumbs(tmp_path)

    names = ['img%02d' % n for n in range(40)]
    for name in names:
        thumbs._submit_gen_request(mk_request(thumbs, name))

    fv.join_workers()
    fv.flush_gui()

    assert gen.concurrent == []
    assert sorted(gen.renders) == sorted(names)


def test_concurrent_submitters_never_share_the_generator(tmp_path):
    """The real failure mode: several threads feeding thumbs at once."""
    thumbs, fv, gen = mk_thumbs(tmp_path, delay=0.002)

    names = ['img%03d' % n for n in range(60)]
    barrier = threading.Barrier(6)

    def submit(chunk):
        barrier.wait()
        for name in chunk:
            thumbs._submit_gen_request(mk_request(thumbs, name))

    # the submitters are not the GUI thread, so stand the assert down
    fv.gui_thread_id = None
    producers = [threading.Thread(target=submit, args=(names[i::6],))
                 for i in range(6)]
    for t in producers:
        t.start()
    for t in producers:
        t.join()

    fv.join_workers()

    assert gen.concurrent == []
    assert sorted(gen.renders) == sorted(names)


def test_a_request_queued_as_the_drain_exits_is_not_stranded(tmp_path):
    """The lost-wakeup window: producer arrives as the drain gives up.

    If the drain cleared its busy flag outside the lock, a producer could
    see "busy" after the drain had already decided to stop, and the work
    would sit in the queue forever.
    """
    thumbs, fv, gen = mk_thumbs(tmp_path)
    fv.gui_thread_id = None

    for round_n in range(200):
        name = 'img%03d' % round_n
        thumbs._submit_gen_request(mk_request(thumbs, name))
        # submit again with no synchronization, landing anywhere in the
        # drain's lifetime including right on its exit path
        thumbs._submit_gen_request(mk_request(thumbs, name + 'b'))

    fv.join_workers()

    assert gen.concurrent == []
    assert len(gen.renders) == 400
    with thumbs._gen_lock:
        assert len(thumbs._gen_queue) == 0
        assert not thumbs._gen_busy


def test_the_drain_does_not_park_a_worker(tmp_path):
    """A pool worker held forever is a thread lost for good."""
    thumbs, fv, gen = mk_thumbs(tmp_path)

    thumbs._submit_gen_request(mk_request(thumbs, 'only'))
    fv.join_workers(timeout=5.0)

    # the worker returned, and left the pipeline idle rather than busy
    with thumbs._gen_lock:
        assert not thumbs._gen_busy
    assert gen.renders == ['only']

    # ...and a later request starts a fresh drain
    thumbs._submit_gen_request(mk_request(thumbs, 'later'))
    fv.join_workers(timeout=5.0)
    assert gen.renders == ['only', 'later']


def test_a_queued_request_is_superseded_not_stacked(tmp_path):
    """Dragging cut levels should not build a backlog of renders."""
    thumbs, fv, gen = mk_thumbs(tmp_path)

    # pretend a drain is already running, so the batch has to queue
    thumbs._gen_busy = True
    for n in range(5):
        thumbs._submit_gen_request(
            mk_request(thumbs, 'same', attrs={'contrast': n}))

    with thumbs._gen_lock:
        assert len(thumbs._gen_queue) == 1
        assert thumbs._gen_queue[0].attrs == {'contrast': 4}
    assert fv.threads == [], "no drain should have been started"

    # a different thumb queues alongside it rather than replacing it
    thumbs._submit_gen_request(mk_request(thumbs, 'other'))
    with thumbs._gen_lock:
        assert [r.thumbkey[1] for r in thumbs._gen_queue] == ['same', 'other']


def test_attrs_are_applied_inside_the_render(tmp_path):
    thumbs, fv, gen = mk_thumbs(tmp_path)

    req = mk_request(thumbs, 'withattrs', attrs={'contrast': 0.25})
    thumb_image = thumbs._render_thumb(req)

    assert gen.renders == ['withattrs']
    assert req.image.get('applied') == {'contrast': 0.25}
    assert thumb_image is not None


def test_unviewable_data_is_not_retried_forever(tmp_path):
    thumbs, fv, gen = mk_thumbs(tmp_path)

    req = mk_request(thumbs, 'weird', unviewable=True)
    thumb_image = thumbs._render_thumb(req)

    assert req.ignore
    assert thumb_image is thumbs.placeholder_image
    assert gen.renders == []


def test_a_failed_render_clears_pending_so_autoload_retries(tmp_path):
    thumbs, fv, gen = mk_thumbs(tmp_path)

    class Boom(StubGenerator):
        def set_image(self, image):
            raise ValueError("render exploded")

    thumbs.thumb_generator = Boom()
    req = mk_request(thumbs, 'doomed')
    req.extras.setvals(pending=True)

    thumbs._render_and_publish(req)
    fv.flush_gui()

    assert not req.extras.get('pending', False)
    assert 'rgbimg' not in req.extras


# ------------------------------------------------- registration vs. render


class FakeViewer:
    def get_image(self):
        return None

    def get_dataobj(self):
        return None


class FakeChannel:
    def __init__(self, name, prefs):
        self.name = name
        self.viewer = FakeViewer()
        self.fitsimage = self.viewer
        self.settings = prefs.create_category('channel_%s' % name)
        self.settings.set_defaults(genthumb=True)
        self.extdata = Bunch.Bunch()
        self.info_dict = {}

    def add(self, name, path):
        info = Bunch.Bunch(name=name, path=path, nothumb=False,
                           image_future=None)
        self.info_dict[name] = info
        return info

    def get_image_info(self, imname):
        return self.info_dict[imname]

    def get_loaded_image(self, imname):
        raise KeyError(imname)


def mk_channel(thumbs, fv, name='HDS_Online'):
    channel = FakeChannel(name, fv.prefs)
    fv.get_channel = lambda chname: channel
    return channel


def test_add_image_registers_the_thumb_even_when_the_render_fails(tmp_path):
    """The reported bug: a frame that reaches Contents but not Thumbs.

    Generation used to happen inline, *before* the thumb was registered,
    so anything that threw on the way -- including the shared generator
    being clobbered by the autoload thread -- left no thumb at all, and
    the pane simply never showed the frame.
    """
    thumbs, fv, gen = mk_thumbs(tmp_path)
    channel = mk_channel(thumbs, fv)
    info = channel.add('HDSA00175452', '/nonexistent/HDSA00175452.fits')

    class Boom(StubGenerator):
        def set_image(self, image):
            raise ValueError("generator clobbered")

    thumbs.thumb_generator = Boom()

    assert thumbs._add_image(fv, channel.name, mk_image(info.name), info)
    fv.join_workers()
    fv.flush_gui()

    thumbkey = thumbs.get_thumb_key(channel.name, info.name, info.path)
    assert thumbkey in thumbs.thumb_dict, "the thumb was lost"
    assert thumbkey in thumbs.thumb_list
    # and the failure left it retryable rather than wedged
    assert not info.thumb_extras.get('pending', False)

    thumbs.timer_update.stop()


def test_add_image_queues_the_render_instead_of_doing_it_inline(tmp_path):
    """Rendering a 4k x 4k frame should not be on the GUI thread."""
    thumbs, fv, gen = mk_thumbs(tmp_path)
    channel = mk_channel(thumbs, fv)
    info = channel.add('HDSA00175452', '/nonexistent/HDSA00175452.fits')

    thumbs._add_image(fv, channel.name, mk_image(info.name), info)

    # registered immediately...
    thumbkey = thumbs.get_thumb_key(channel.name, info.name, info.path)
    assert thumbkey in thumbs.thumb_dict
    # ...and the image arrives from the drain, not from _add_image
    fv.join_workers()
    assert gen.renders == [info.name]
    fv.flush_gui()
    assert 'rgbimg' in info.thumb_extras
    assert not info.thumb_extras.get('placeholder', True)

    thumbs.timer_update.stop()


def test_add_visible_thumbs_does_not_re_enter_itself(tmp_path):
    """update_pending() can fire timer_update and recurse back in here.

    The pass in flight has already emptied the canvas and swapped
    _displayed_thumb_dict; letting a second pass rebuild both underneath
    it interleaves the two, and thumblock -- being reentrant -- does not
    notice.  The second pass must be deferred instead.
    """
    thumbs, fv, gen = mk_thumbs(tmp_path)
    thumbs.gui_up = True
    calls = []

    def body():
        calls.append('enter')
        # stands in for update_pending() letting timer_update fire
        thumbs.add_visible_thumbs()
        calls.append('exit')

    thumbs._add_visible_thumbs = body
    thumbs.add_visible_thumbs()

    assert calls == ['enter', 'exit'], "the nested pass ran the body"
    assert thumbs.timer_update.is_set(), "the deferred pass was dropped"
    assert not thumbs._updating_visible
    assert not thumbs._update_again

    thumbs.timer_update.stop()


# ---------------------------------------------- viewers that draw their own


def test_a_table_gets_a_real_thumbnail_even_when_not_displayed(tmp_path):
    """Plots and tables are not something the thumb generator can draw.

    They used to be handled by screenshotting the viewer's widget, which
    is only possible while the table is the viewer's current object -- so
    any later regeneration gave up and left a permanently-ignored
    placeholder.  The viewer draws its own thumbnail now, from whichever
    table it is handed.
    """
    pytest.importorskip('astropy.table')
    from astropy.table import Table
    from ginga.table import AstroTable
    from ginga.table.TableView import TableViewBase

    thumbs, fv, gen = mk_thumbs(tmp_path)

    def mk_table(seed):
        rng = np.random.default_rng(seed)
        return AstroTable.AstroTable(
            logger=thumbs.logger,
            data_ap=Table({'x': np.arange(20), 'f': rng.random(20)}))

    showing, wanted = mk_table(1), mk_table(2)
    viewer = TableViewBase(logger=thumbs.logger)
    viewer.set_table(showing)          # the viewer is on a *different* table

    req = thumbs._mk_gen_request(('Ch', 'tbl', None), wanted,
                                 Bunch.Bunch(), viewer)
    assert req.rgb_array is not None, "no thumbnail was obtained"

    thumb_image = thumbs._render_thumb(req)

    assert not req.ignore, "the table was written off as undrawable"
    assert thumb_image is not thumbs.placeholder_image
    arr = thumb_image.get_data()
    assert arr.shape[2] == 3
    assert arr.min() != arr.max(), "the thumbnail is blank"


def test_an_undrawable_object_still_falls_back_to_the_placeholder(tmp_path):
    thumbs, fv, gen = mk_thumbs(tmp_path)

    class SilentViewer:
        def get_thumbnail_array(self, dataobj, size):
            return None

    req = thumbs._mk_gen_request(('Ch', 'x', None),
                                 mk_image('x', unviewable=True),
                                 Bunch.Bunch(), SilentViewer())
    assert req.rgb_array is None

    assert thumbs._render_thumb(req) is thumbs.placeholder_image
    assert req.ignore


def test_a_viewer_that_raises_does_not_lose_the_thumb(tmp_path):
    thumbs, fv, gen = mk_thumbs(tmp_path)

    class BrokenViewer:
        def get_thumbnail_array(self, dataobj, size):
            raise RuntimeError("viewer exploded")

    # the request is still made; the thumb falls back to a placeholder
    req = thumbs._mk_gen_request(('Ch', 'x', None), mk_image('x'),
                                 Bunch.Bunch(), BrokenViewer())
    assert req.rgb_array is None


def test_an_rgba_rendering_is_not_mislabelled_as_rgb(tmp_path):
    """A four-channel array used to be handed to RGBImage as order=RGB."""
    thumbs, fv, gen = mk_thumbs(tmp_path)

    rgba = np.zeros((40, 60, 4), dtype=np.uint8)
    rgba[..., 0] = 200        # red
    rgba[..., 3] = 255        # opaque

    thumb_image = thumbs._scale_rgb_thumb(rgba)
    arr = thumb_image.get_data()

    assert arr.shape[2] == 3, "alpha was carried into an RGB image"
    r, g, b = arr[..., 0].max(), arr[..., 1].max(), arr[..., 2].max()
    assert r > g and r > b, "channels came out in the wrong order"


# ------------------------------------------------------------------- async

def test_async_mode_renders_everything_on_one_thread(tmp_path):
    """Pyodide/the browser: one event loop, no worker threads."""

    async def main():
        thumbs, fv, gen = mk_thumbs(tmp_path, async_mode=True)
        thumbs.gen_yield_interval = 0.0      # yield between every render

        names = ['img%02d' % n for n in range(25)]
        for name in names:
            thumbs._submit_gen_request(mk_request(thumbs, name))

        # exactly one drain coroutine, however many requests
        assert len(fv.aio_tasks) == 1

        await asyncio.gather(*fv.aio_tasks)
        fv.flush_gui()

        assert gen.concurrent == []
        assert gen.renders == names          # FIFO, and all of them
        with thumbs._gen_lock:
            assert not thumbs._gen_busy
        return thumbs, fv

    thumbs, fv = asyncio.run(main())
    # no threads were created: the drain shared the GUI thread
    assert fv.threads == []


def test_async_drain_yields_to_the_event_loop(tmp_path):
    """Without the yields a run of thumbs would stall the single thread."""

    async def main():
        thumbs, fv, gen = mk_thumbs(tmp_path, async_mode=True)
        thumbs.gen_yield_interval = 0.0

        ticks = []

        async def ticker():
            for _ in range(200):
                ticks.append(len(gen.renders))
                await asyncio.sleep(0)

        for n in range(20):
            thumbs._submit_gen_request(mk_request(thumbs, 'img%02d' % n))

        await asyncio.gather(ticker(), *fv.aio_tasks)
        return ticks, gen

    ticks, gen = asyncio.run(main())

    assert len(gen.renders) == 20
    # the ticker got the loop back while renders were still happening
    assert len(set(ticks)) > 1, "the drain never yielded"


def test_async_mode_picks_up_work_queued_after_a_drain_finishes(tmp_path):

    async def main():
        thumbs, fv, gen = mk_thumbs(tmp_path, async_mode=True)

        thumbs._submit_gen_request(mk_request(thumbs, 'first'))
        await asyncio.gather(*fv.aio_tasks)
        assert gen.renders == ['first']

        fv.aio_tasks.clear()
        thumbs._submit_gen_request(mk_request(thumbs, 'second'))
        assert len(fv.aio_tasks) == 1, "a new drain was not started"
        await asyncio.gather(*fv.aio_tasks)
        return gen

    gen = asyncio.run(main())
    assert gen.renders == ['first', 'second']


# ------------------------------------------- the ImageView snapshot API

def test_snapshot_and_apply_match_copy_attributes():
    attrlist = ['transforms', 'cutlevels', 'rgbmap', 'icc', 'interpolation']

    src = CanvasView()
    src.configure_surface(40, 40)
    src.set_image(mk_image('src'))
    src.transform(True, False, True)
    src.cut_levels(11.0, 222.0)
    src.get_settings().set(contrast=0.33, brightness=0.66)

    by_copy = CanvasView()
    by_copy.configure_surface(40, 40)
    src.copy_attributes(by_copy, attrlist)

    by_snapshot = CanvasView()
    by_snapshot.configure_surface(40, 40)
    by_snapshot.apply_attributes(src.snapshot_attributes(attrlist))

    keylist, _whence = CanvasView.get_attribute_keys(attrlist)
    for key in keylist:
        assert by_snapshot.get_settings()[key] == by_copy.get_settings()[key], \
            "setting '%s' differs" % (key,)

    # and the values really did come across
    assert by_snapshot.get_settings()['cuts'] == (11.0, 222.0)
    assert by_snapshot.get_settings()['flip_x'] is True
    assert by_snapshot.get_settings()['swap_xy'] is True
    assert by_snapshot.get_settings()['contrast'] == 0.33


def test_snapshot_holds_only_plain_values():
    """It crosses a thread boundary, so it must not carry live objects."""
    src = CanvasView()
    src.configure_surface(40, 40)
    src.set_image(mk_image('src'))

    dct = src.snapshot_attributes(['transforms', 'cutlevels', 'rgbmap',
                                   'icc', 'interpolation'])
    assert len(dct) > 0
    for key, val in dct.items():
        assert isinstance(val, (bool, int, float, str, tuple, list,
                                type(None))), \
            "setting '%s' is a %s" % (key, type(val))


if __name__ == '__main__':
    pytest.main([__file__])
