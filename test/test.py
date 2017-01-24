import unittest

class ThumbnailTests(unittest):
    
    def testCuty(self):
    
        try:
            args = ['xvfb-run',\
                r'-e', self.cuty_error_log,
                r'--server-args=-screen 0 1024x768x24',
                self.cuty_path,\
                '--url=' + url,\
                '--plugins=on',\
                ('--max-wait=%d' % (MAX_WAIT_SECONDS - 2) * 1000),\
                '--min-width=800',\
                '--min-height=600',\
                '--out=' + outfilename]
            try:
                start_time = time.time()
                process = Popen(args, preexec_fn=setlimits)
                try:
                    if (start_time - time.time()) > MAX_WAIT_SECONDS:
                        raise Exception("Timeout expired") 
                    
                    while process.poll() == None:
                        time.sleep(1)
                except:
                    if not process.returncode:
                        try:
                            process.kill()
                        except:
                            logging.error('Failed to terminate xvfb process')
                            pass
                    raise
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
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()