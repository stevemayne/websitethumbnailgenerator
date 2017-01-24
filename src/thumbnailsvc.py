#!/usr/bin/env python
import sys
import os
our_path = os.path.abspath(os.path.dirname(__file__))
import signal
from BaseHTTPServer import HTTPServer
import ConfigParser
import thumb_processor
from handler import ThumbnailHandler

terminate = False

def TERMHandler(signum, frame):
    global terminate
    terminate = True

def GetArgs():
    runAsDaemon = False
    for i in range(1, len(sys.argv)):
        if sys.argv[i] == '-D':
            runAsDaemon = 1
    return runAsDaemon

# Start here
runAsDaemon = GetArgs()

try:
    # Signal handling
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, TERMHandler)
    
    conf_file = '/etc/opt/thumbnailsvc.cfg'
    if not os.path.exists(conf_file):
        conf_file = os.path.join(our_path, 'thumbnailsvc.cfg')
    config = ConfigParser.RawConfigParser()
    config.read(conf_file)    
    
    CUTYCAPT_PATH = os.path.join(our_path, config.get('Config', 'CutyCaptPath'))
    TEMP_PATH = os.path.join(our_path, config.get('Config', 'TempPath'))
    PORT = int(config.get('Config', 'Port'))
    
    ThumbnailHandler.processor = thumb_processor.ThumbProcessor(TEMP_PATH, CUTYCAPT_PATH)
    ThumbnailHandler.processor.start()
    try:
        server = HTTPServer(('', PORT), ThumbnailHandler)
        while not terminate:
            try:
                server.handle_request()
            except KeyboardInterrupt:
                server.socket.close()
                break
    finally:
        ThumbnailHandler.processor.stop()
except Exception, e:
    sys.stderr.write("\n%s\n" % str(e))
    raise
