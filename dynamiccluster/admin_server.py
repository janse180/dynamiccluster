
from bottle import route, run, static_file, abort, request
import threading
from dynamiccluster.utilities import getLogger
from dynamiccluster.exceptions import NoCloudResourceException
import os

log = getLogger(__name__)
server = None
root_path = ""

class AdminServer(threading.Thread):
    
    @route('/dashboard', method='GET')
    def get_admin_index():
        global root_path
        log.debug("get dashboard index page")
        return static_file("index.html", root=root_path+os.pathsep+'html')

    @route('/js/:page', method='GET')
    def get_js_page(page):
        global root_path
        log.debug("static js page to return %s"%(page))
        return static_file(page, root=root_path+os.pathsep+'html'+os.pathsep+'js')
    @route('/css/:page', method='GET')
    def get_js_page(page):
        global root_path
        log.debug("static css page to return %s"%(page))
        return static_file(page, root=root_path+os.pathsep+'html'+os.pathsep+'css')
    @route('/fonts/:page', method='GET')
    def get_fonts_page(page):
        global root_path
        log.debug("static fonts page to return %s"%(page))
        return static_file(page, root=root_path+os.pathsep+'html'+os.pathsep+'fonts')
    
    @route('/workernode')
    def get_workernodes():
        state = request.query.state
        log.debug("only whose state=%s" % state)
        global server
        #log.debug(data.__dict__)
        if len(state)>0:
            return repr([w for w in server.info.worker_nodes if w.state==int(state)])
        return repr(server.info.worker_nodes)

    @route('/workernode/:hostname')
    def get_workernodes(hostname):
        global server
        #log.debug(data.__dict__)
        list=[w for w in server.info.worker_nodes if w.hostname==hostname]
        if len(list)==0:
            abort(404, "worker node not found")
        return repr(list[0])
    
    @route('/workernode/:hostname', method="DELETE")
    def delete_worker_node(hostname):
        global server
        list=[w for w in server.info.worker_nodes if w.hostname==hostname]
        if len(list)==0:
            abort(404, "worker node not found")
        server.delete_worker_node(hostname)
        return {"success":True}
    
    @route('/job')
    def get_jobs():
        global server
        #log.debug(data.__dict__)
        return repr(server.info.queued_jobs)

    @route('/job/:id')
    def get_jobs(id):
        global server
        #log.debug(data.__dict__)
        list=[j for j in server.info.queued_jobs if j.jobid==id]
        if len(list)==0:
            abort(404, "job not found")
        return repr(list[0])
    
    @route('/server/config')
    def get_server_config():
        global server
        return server.config
    
    @route('/server/status')
    def get_server_status():
        global server
        return server.get_status()
    
    @route('/server/auto', method="PUT")
    def get_server_auto():
        global server
        server.set_auto()
        return {"success":True}
    
    @route('/server/auto', method="DELETE")
    def unset_server_auto():
        global server
        server.unset_auto()
        return {"success":True}
    
    @route('/resource', method="GET")
    def get_resources():
        global server
        res_list=server.resources
        if len(res_list)==0:
            abort(404, "resource %s not found" % res_name)
        for res in res_list:
            res.worker_nodes=[w for w in server.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name]
        return repr(server.resources)
 
    @route('/resource/:res_name', method="GET")
    def get_resource(res_name):
        global server
        res_list=[r for r in server.resources if r.name==res_name]
        for res in res_list:
            res.worker_nodes=[w for w in server.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name]
        return repr(res_list[0])
   
    @route('/resource/:res', method="PUT")
    def add_instace_to_res(res):
        num_string = request.query.num
        number=1
        if len(num_string)>0 and num_string.isdigit():
            number=int(num_string)
        log.debug("launch %s instance in %s" % (number,res))
        global server
        try:
            server.launch_new_instance(res, number)
            return {"success":True}
        except NoCloudResourceException:
            abort(500, "Cloud resource not found")
        abort(400, "Unknown error")
    
    def __init__(self, srv=None, working_path=""):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        global server
        server=srv
        global root_path
        root_path=working_path
        self.__port=server.config['dynamic-cluster']['admin-server']['port']
        
    def run(self):
        run(host='0.0.0.0', port=self.__port, debug=True)
