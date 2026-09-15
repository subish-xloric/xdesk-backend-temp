import _pickle as cPickle
import datetime
import celery
from celery.beat import Scheduler
import celery.utils.log
import redis as redisServer
from django.conf import settings

from CorePlatform.Common.Utility import Utility


class SharedScheduler(Scheduler):

    def __init__(self, *args, **kwargs):
        Scheduler.__init__(self, *args, **kwargs)
        self.merge_inplace(self.app.conf.CELERY_BEAT_SCHEDULE)

        # a redis server
        pool = redisServer.ConnectionPool(
            host=settings.SHARED_LOCKER_HOST,
            port=settings.SHARED_LOCKER_PORT,
            db=0,
            password=settings.SHARED_LOCKER_PWD
        )
        self.redis = redisServer.Redis(connection_pool=pool)
        self.protocal = cPickle
        self.moduleName = 'CeleryScheduler'

    def tick(self):
        """Run a tick, that is one iteration of the scheduler.

        Executes all due tasks.

        """
        remaining_times = []
        try:
            for entry_name, entry in self.schedule.items():
                pipe = self.redis.pipeline()
                try:
                    key = 'celery:scheduler:%s' % entry_name
                    pipe.watch(key)

                    # after WATCHing, the pipeline is put into immediate execution
                    # mode until we tell it to start buffering commands again.
                    # this allows us to get the current value of our sequence
                    entry_value = pipe.get(key)

                    if entry_value:
                        try:
                            entry = self.protocal.loads(entry_value)
                        except:
                            msg = 'Error: SharedScheduler-tick, Load entry from db failed. %s' % str(
                                entry_name)
                            Utility().writeLog(msg)

                    is_due, next_time_to_run = entry.is_due()

                    if next_time_to_run:
                        remaining_times.append(next_time_to_run)

                    if is_due:
                        msg = ' Info: Scheduler sending due task %s, %s' % (
                            str(entry_name), str(entry.task))
                        Utility().writeLog(msg)
                        old_entry = entry
                        entry = old_entry.next()
                        entry_value = self.protocal.dumps(entry)

                        # now we can put the pipeline back into buffered mode with MULTI
                        pipe.multi()
                        pipe.set(key, entry_value)
                        # and finally, execute the pipeline (the set command)
                        pipe.execute()

                        # if a WatchError wasn't raised during execution, everything
                        # we just did happened atomically.
                        try:
                            result = self.apply_async(old_entry)
                            result_id = result.id
                        except Exception as exc:
                            msg = 'Error : Message %s' % (str(exc))
                            Utility().writeLog(msg)

                        else:
                            msg = 'Info : %s sent. id->%s' % (
                                str(entry.task), str(result_id))
                            Utility().writeLog(msg)

                except self.redis.WatchError:
                    # another client must have changed 'OUR-SEQUENCE-KEY' between
                    # the time we started WATCHing it and the pipeline's execution.
                    # our best bet is to just retry.
                    continue
                except Exception as e:
                    msg = 'Error : Task Scheduler Failed. %s. Error is %s' % (
                        entry_name, str(e))
                    Utility().writeLog(msg)
                finally:
                    pipe.reset()

        except RuntimeError:
            pass
        next_time = min(remaining_times + [self.max_interval])
        #msg= 'Info : wait for %s' % next_time
        # utility.writeLog(content=msg,moduleName=self.moduleName)
        return next_time

    def reserve(self, entry):
        new_entry = entry.next()
        return new_entry
