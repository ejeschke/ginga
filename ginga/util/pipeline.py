#
# pipeline.py -- Base classes for pipelines in Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Bunch, Callback

__all__ = ['Pipeline']


class Pipeline(Callback.Callbacks):

    def __init__(self, logger, stages):
        super(Pipeline, self).__init__()
        self.logger = logger
        self.cur_stage = None
        self.bboard = Bunch.Bunch()

        self.pipeline = list(stages)

        for stage in self.pipeline:
            stage.pipeline = self

        for name in ['pipeline-start',
                     'stage-executing', 'stage-errored', 'stage-done']:
            self.enable_callback(name)

    def insert(self, i, stage):
        self.pipeline.insert(i, stage)
        stage.pipeline = self

    def append(self, stage):
        self.pipeline.append(stage)
        stage.pipeline = self

    def remove(self, stage):
        stage.pipeline = None
        self.pipeline.remove(stage)

    def run_stage(self, i):
        if i < 0 or i >= len(self.pipeline):
            raise ValueError("No stage at index {}".format(i))

        stage = self.pipeline[i]
        prev_stage = None if i == 0 else self.pipeline[i - 1]
        self.cur_stage = stage
        self.make_callback('stage-executing', stage)
        try:
            stage.run(prev_stage)
            self.make_callback('stage-done', stage)

        except Exception as e:
            self.logger.error("Error running stage %d (%s): %s" % (
                i, str(stage), e), exc_info=True)
            self.make_callback('stage-errored', stage)

    def run_from(self, stage):
        self.make_callback('pipeline-start', stage)
        idx = self.pipeline.index(stage)
        for i in range(idx, len(self.pipeline)):
            self.run_stage(i)

    def run_all(self):
        self.run_from(self.pipeline[0])

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

    def __getitem__(self, idx):
        return self.pipeline[idx]

    def __contains__(self, stage):
        return stage in self.pipeline

    def index(self, stage):
        return self.pipeline.index(stage)

    def __len__(self):
        return len(self.pipeline)
