#! /usr/bin/python
from __future__ import with_statement   # needed under Python 2.5 (Leopard default)

# see http://wiki.apache.org/couchdb/ExternalProcesses for configuration instructions
class CouchExternal(object):
    def run(self):
        import sys
        import json
        
        line = sys.stdin.readline()
        while line:
            try:
                response = self.process(json.loads(line))
            except Exception:
                response = {'code':500, 'json':{'error':True, 'reason':"Internal error processing request"}}
            sys.stdout.write("%s\n" % json.dumps(response))
            sys.stdout.flush()
            line = sys.stdin.readline()
    
    def process(self, req):
        return {'json':{'ok':True}}


from time import sleep
import os
import json
import uuid



class Importer(object):
    def __init__(self, db_url, source_id, folder):
        self._cancelled = False
        self._files = Queue()
        self._image_docs = Queue(maxsize=32)
        self._imported_ids = []
        
        def find_new_files():
            for (dirpath, dirnames, filenames) in os.walk(folder):
                for filename in filenames:
                    if filename[0] == '.':
                        continue
                    
                    full_path = os.path.join(dirpath, filename)
                    rel_path = os.path.relpath(full_path, folder)
                    identifiers = {'relative_path':{'source':{'_id':source_id}, 'path':rel_path}}
                    if not image_with_identifiers(identifiers):     # TODO: image_with_identifiers
                        self._files.put(full_path)
                
                if self._cancelled:
                    break
        
        def get_file_docs():
            while not self._cancelled:
                file = self._files.get()
                doc = doc_for_file(file)        # TODO: implement doc_for_file, image_with_identifiers
                if doc and not image_with_identifiers(doc['identifiers']):  
                    self._image_docs.put(doc)
                self._files.task_done()
        
        def upload_docs():
            while not self._cancelled:
                doc = self._image_docs.get()
                doc_id = write_new_doc(doc)     # TODO: implement write_new_doc
                self._imported_ids.append(doc_id)
                self._image_docs.task_done()
        
        self._find_files = Thread(target=find_files)
        self._find_files.run()
        self._get_file_docs = Thread(target=get_file_docs)
        self._get_file_docs.run()
        self._upload_docs = Thread(target=upload_docs)
    
    def begin(self):
        self._upload_docs.run()
    
    def cancel(self, remove=True):
        self._cancelled = True
        
        if self._find_files.is_alive():
            self._find_files.join()
        if self._get_file_docs.is_alive():
            self._get_file_docs.join()
        if self._upload_docs.is_alive():
            self._upload_docs.join()
        
        def delete_docs():
            while self._imported_ids:
                doc_id = self._imported_ids.pop()
                delete_doc(doc_id)      # TODO: implement write_new_doc
        Thread(target=delete_docs).run()
    
    def status(self):
        to_implement
        return {'imported':0, 'remaining':42, 'verb':['wait+scan', 'wait', 'import+scan', 'import', 'cancel'][0]}


class ImportManager(CouchExternal):
    def __init__(self):
        self.imports = {}
    
    def process_folder(self, req):
        source_id = req['path'][2]
        token = req['query'].get('token', None)
        helper = req['query'].get('utility', None)
        if not token or not helper or not source_id:
            return {'code':400, 'json':{'error':True, 'reason':"Required parameter(s) missing"}}
        
        # check that the request is not forged
        with open(helper, 'r') as f:
            first_chunk = f.read(4096)  # token required in first 4k
            if first_chunk.find("<!-- SHUTTERSTEM-TOKEN(%s)TOKEN-SHUTTERSTEM -->" % token) == -1:
                raise Exception()
        
        if source_id in self.imports:
            return {'code':409, 'json':{'error':True, 'reason':"An import is already in progress for this source"}}
        
        info = self.imports[source_id] = {}
        info['token'] = uuid.uuid4().hex
        info['folder'] = os.path.dirname(helper)
        
        # TODO: start import of requested folder in background
        return {'code':202, 'json':{'ok':True, 'message':"Import of '%s' may now start." % info['folder'], 'token':info['token']}}
    
    def process(self, req):
        if req['method'] == 'POST' and req['path'][3] == "folder":
            try:
                return self.process_folder(req)
            except Exception:
                sleep(2.5)    # slow down malicious local scanning
                return {'code':400, 'json':{'error':True, 'reason':"Bad request"}}
        
        if req['method'] == 'GET':
            # TODO: return status info (w/long polling?)
            pass
        
        return {'body': "<h1>Hello World!</h1>\n<pre>%s</pre>" % json.dumps(req, indent=4)}
        

if __name__ == "__main__":
    import_server = ImportManager()
    import_server.run()