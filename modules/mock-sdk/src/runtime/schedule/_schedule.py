# coding=utf-8

import time
import heapq

from threading import RLock
from threading import Event

from concurrent.futures.thread import ThreadPoolExecutor

from ._job import Job
from ._job import NOT_SCHEDULE_TASK


class Schedule:
    def __init__(self, max_threads=10):
        self._jobs = []
        self._lock = RLock()
        self._pools = ThreadPoolExecutor(max_threads)

        # 任务列表由空到非空 触发事件信号
        # 任务列表由非空到空 复位事件信号
        self._event = Event()

    def add_job(self, job):
        # 支持外部自定义job类型
        if not job or not hasattr(job, 'run'):
            return False

        # 线程锁
        with self._lock:
            # 最小堆
            heapq.heappush(self._jobs, job)

        if len(self._jobs) == 1:
            # 发送add事件
            self._event.set()

        return True

    def add(self, *, func=None, delay=0, interval=0, params=None):
        if not func:
            return False

        if delay <= 0:
            delay = 0

        if interval <= 0:
            interval = NOT_SCHEDULE_TASK

        job = Job(func, delay=delay, interval=interval, params=params)

        return self.add_job(job)

    def run(self):
        # 阻塞式函数
        while True:
            if not self._jobs:
                # 等待add事件
                self._event.wait()

            # 线程锁
            with self._lock:
                job = heapq.heappop(self._jobs)
                if len(self._jobs) == 0:
                    # 事件复位
                    self._event.clear()

                now_time = int(time.time())
                delay = job.next_time - now_time
                if delay > 0:
                    time.sleep(delay)

                # 轮询任务，需要加入任务列表, job run函数不能抛异常
                if job.run():
                    self.add_job(job)
