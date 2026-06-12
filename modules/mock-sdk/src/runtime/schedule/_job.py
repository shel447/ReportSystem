# coding=utf-8

import uuid
import time

NOT_SCHEDULE_TASK = object()


class Job:
    __slots__ = ['func', 'delay', 'interval', 'job_id', 'params', 'next_time']

    def __init__(
            self,
            func,
            *,
            delay=0,
            interval=NOT_SCHEDULE_TASK,
            params=None):

        self.func = func
        self.delay = delay
        self.interval = interval
        self.job_id = uuid.uuid1()
        self.params = params

        # 真正执行时间点
        self.next_time = int(time.time()) + self.delay

    def run(self):
        try:

            self.func(self.params)
        except BaseException:
            pass

        if self.interval is NOT_SCHEDULE_TASK:
            # 仅执行一次
            return False

        if isinstance(self.interval, int) and self.interval != 0:
            # 计算下次支持时间
            self.next_time = int(time.time()) + self.interval
            # 仅执行一次
            return True

        # 其余情况均返回False
        return False

    def __lt__(self, other):
        return self.next_time < other.next_time

    def __eq__(self, other):
        return self.next_time == other.next_time

    def __le__(self, other):
        return self.next_time <= other.next_time

    def __gt__(self, other):
        return self.next_time > other.next_time

    def __ge__(self, other):
        return self.next_time >= other.next_time
