import os
import logging
from BaseHTTPServer import BaseHTTPRequestHandler
from thumb_processor import CaptureInProgress

class ThumbnailHandler(BaseHTTPRequestHandler):
    processor = None
    
    def __init__(self, *args, **kwargs):
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
    
    def do_GET(self):
        #Get get parameters:
        i = self.path.find('?')
        if i > -1:
            try:
                uri = self.path[i+1:]
                raw_params = dict([item.split('=') for item in uri.split('&')])
                file = self.processor.process(raw_params['url'])
                try:
                    size = os.path.getsize(file.name)
                    self.send_response(200)
                    self.send_header('Content-length', str(size))
                    self.send_header('Content-type', 'image/png')
                    self.end_headers()
                    self.wfile.write(file.read())
                finally:
                    file.close()
            except CaptureInProgress, e:
                self.send_response(503, str(e))
            except Exception, e:
                logging.exception(str(e))
                self.send_response(500, str(e))
        else:
            self.send_response(404, 'Not found')
        return