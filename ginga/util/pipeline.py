#
# pipeline.py -- Base classes for pipelines in Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time

from ginga.misc import Bunch, Callback
from ginga.util import action

__all__ = ['Pipeline']


class PipeError(Exception):
    pass


class Pipeline(Callback.Callbacks):

    def __init__(self, logger, stages, name=None):
        super(Pipeline, self).__init__()
        self.logger = logger
        self.cur_stage = None
        self._i = 0
        self.bboard = Bunch.Bunch()
        if name is None:
            name = 'noname'
        self.name = name
        self.enabled = True
        self.pipeline = list(stages)
        # undo/redo stack
        self.actions = action.ActionStack()

        for stage in self.pipeline:
            self._init_stage(stage)

        for name in ['pipeline-start',
                     'stage-executing', 'stage-errored', 'stage-done']:
            self.enable_callback(name)

    def _init_stage(self, stage):
        stage.pipeline = self
        stage.logger = self.logger
        stage.result = Bunch.Bunch(res_np=None)

    def insert(self, i, stage):
        self.pipeline.insert(i, stage)
        self._init_stage(stage)

    def append(self, stage):
        self.pipeline.append(stage)
        self._init_stage(stage)

    def remove(self, stage):
        stage.pipeline = None
        self.pipeline.remove(stage)

    def enable(self, tf):
        self.enabled = tf

    def run_stage_idx(self, i):
        if not self.enabled:
            self.logger.info("pipeline disabled")

        if i < 0 or i >= len(self.pipeline):
            raise ValueError("No stage at index {}".format(i))

        stage = self.pipeline[i]
        prev_stage = None if i == 0 else self.pipeline[i - 1]
        self.cur_stage = stage
        self.make_callback('stage-executing', stage)
        start_time = time.time()
        try:
            stage.run(prev_stage)
            stop_time = time.time()
            self.make_callback('stage-done', stage)

        except Exception as e:
            stop_time = time.time()
            self.logger.error("Error running stage %d (%s): %s" % (
                i, str(stage), e), exc_info=True)
            self.stop()
            self.make_callback('stage-errored', stage)

        self.logger.debug("stage '%s' took %.4f sec" % (stage._stagename,
                                                        stop_time - start_time))

    def run_from(self, stage):
        self.make_callback('pipeline-start', stage)
        self._i = self.pipeline.index(stage)
        start_time = time.time()

        while self._i < len(self.pipeline):
            self.run_stage_idx(self._i)
            self._i += 1

        stop_time = time.time()
        self.logger.debug("pipeline '%s' total execution %.4f sec" % (
            self.name, stop_time - start_time))

    def run_all(self):
        self.run_from(self.pipeline[0])

    def stop(self):
        self._i = len(self.pipeline)

    def get_data(self, stage):
        return stage.result.res_np

    def send(self, **kwargs):
        self.cur_stage.result = Bunch.Bunch(kwargs)

    def set(self, **kwargs):
        self.bboard.setvals(**kwargs)

    def get(self, *args):
        if len(args) == 1:
            return self.bboard[args[0]]
        if len(args) == 2:
            return self.bboard.get(args[0], args[1])
        raise ValueError("Pass keyword as argument")

    def invalidate(self):
        for stage in self.pipeline:
            stage.invalidate()

    def push(self, act):
        self.actions.push(act)

    def undo(self):
        act = self.actions.undo()
        self.run_from(act.obj)

    def redo(self):
        act = self.actions.redo()
        self.run_from(act.obj)

    def save(self):
        dd = dict(name=self.name)
        d = dict(pipeline=dd)
        l = [stage.export_as_dict() for stage in self.pipeline]
        dd['stages'] = l
        return d

    def load(self, d, cd):
        # reinitialize some things
        self.cur_stage = None
        self._i = 0
        self.bboard = Bunch.Bunch()
        self.actions = action.ActionStack()

        dd = d['pipeline']
        self.name = dd['name']
        l = []
        for sd in dd['stages']:
            # instantiate stage
            stage = cd[sd['type']]()
            self._init_stage(stage)
            stage.import_from_dict(sd)
            l.append(stage)
        self.pipeline = l

        return d

    def __getitem__(self, idx):
        return self.pipeline[idx]

    def __contains__(self, stage):
        return stage in self.pipeline

    def index(self, stage):
        return self.pipeline.index(stage)

    def __len__(self):
        return len(self.pipeline)
