import os
from subprocess import Popen, CalledProcessError
import time
xdisplay = ':99'

import hashlib
import subprocess
import logging
from PIL import Image
import datetime
import threading
import resource
import tempfile

class TimeoutError(RuntimeError):
    pass

class CaptureInProgress(Exception):
    pass

DEFAULT_WAIT_SECONDS = 60

class ProcessorThread(threading.Thread):
    def __init__(self, callback, *args, **kwargs):
        super(ProcessorThread, self).__init__(*args, **kwargs)
        self.notifier = threading.Condition()
        self.callback = callback
    
    def run(self):
        while True:
            with self.notifier:
                self.notifier.wait()
            while self.callback():
                pass
    
    def notify(self):
        with self.notifier:
            self.notifier.notify()

def setlimits():
    # Set maximum CPU time to 60 seconds in child process, after fork() but before exec()
    resource.setrlimit(resource.RLIMIT_CPU, (DEFAULT_WAIT_SECONDS,DEFAULT_WAIT_SECONDS))

class ThumbProcessor(object):
    def __init__(self, work_path, cuty_path):
        self.work_path = work_path
        self.queue = []
        self.errors = {}
        self.thread = ProcessorThread(self._process_next)
        self.thread.daemon = True
        self.thread.start()
        self.cuty_path = cuty_path
        self.lock = threading.Lock()
    
    def start(self):
        tempdir = tempfile.mkdtemp()
        self.xvfb = subprocess.Popen(['Xvfb', xdisplay, '-screen', '0', '1024x768x24', '-fbdir', tempdir])
        os.environ["DISPLAY"]=xdisplay
        
    def stop(self):
        self.xvfb.terminate()
        # At this point, `ps -C Xvfb` may still show a running process
        # (because signal delivery is asynchronous) or a zombie.
        self.xvfb.wait()
        # Now the child is dead and reaped (assuming it didn't catch SIGTERM).
    
    def _queuecapture(self, url, outfilename):
        with self.lock:
            item = (url, outfilename)
            try:
                return self.queue.index(item)
            except ValueError:
                self.queue.append(item)
                self.thread.notify()
                return len(self.queue) - 1
        
    def _process_next(self):
        if not self.queue:
            return False
        with self.lock:
            url, outfilename = self.queue[0]
            del self.queue[0]
        if os.path.exists(outfilename):
            return True
        error = self._get_error(url)
        if error:
            return True
        try:
            self._capture(url, outfilename)
        except Exception, e:
            logging.exception(str(e))
            self.errors[url] = (str(e), datetime.datetime.utcnow())
        return True
        
    def _wait_timeout(self, args, seconds=DEFAULT_WAIT_SECONDS):
        start = time.time()
        end = start + seconds
        interval = min(seconds / 1000.0, .25)
        try:
            proc = Popen(args, preexec_fn=setlimits)
            while True:
                result = proc.poll()
                if result is not None:
                    cmd = args[0]
                    if result:
                        raise CalledProcessError(result, cmd)
                    return result
                if time.time() >= end:
                    raise TimeoutError("Process timed out")
                time.sleep(interval)
        except TimeoutError:
            proc.kill()
            raise        
    
    def _capture(self, url, outfilename):
        try:
            args = [self.cuty_path,\
                '--url=' + url,\
                '--plugins=on',\
                '--min-width=800',\
                '--min-height=600',\
                '--out=' + outfilename]
            try: 
                self._wait_timeout(args)
                #subprocess.check_call(args, preexec_fn=setlimits)
            except subprocess.CalledProcessError, e:
                logging.error(str(args))
                logging.error(str(e))
                raise
            
            im = Image.open(outfilename)
            width, height = im.size
            #Rescale to 400x300, ratio = 4:3
            ratio = (width / (height + 0.0))
            if (ratio > 1.334) or (ratio < 1.33):
                newheight = int(((width * 4.0)/3.0)+0.5)
                im = im.crop((0, 0, width-1, newheight))
            im.thumbnail((400,300), Image.ANTIALIAS)
            im.save(outfilename)
        except Exception, e:
            if os.path.exists(outfilename):
                os.remove(outfilename)
            raise
    
    def _get_error(self, url):
        error, last_error_time = self.errors.get(url, (None, None))
        if error:
            del self.errors[url]
            if last_error_time > (datetime.datetime.utcnow() - datetime.timedelta(hours=2)):
                return error
    
    def process(self, url):
        h = hashlib.sha1()
        h.update(url)
        filename = '%s.png' % h.hexdigest()
        outfilename = os.path.join(self.work_path, filename)
        if os.path.exists(outfilename):
            #If file over 23 hours old, we'll ditch it so we can harvest another one
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=23)
            if datetime.datetime.utcfromtimestamp(os.path.getctime(outfilename)) > cutoff:
                return open(outfilename, 'rb')
            os.remove(outfilename)
        error = self._get_error(url)
        if error:
            raise Exception(error)
        i = self._queuecapture(url, outfilename)
        raise CaptureInProgress("Capture in progress (len:%d,pos:%d)" % (len(self.queue), i))
