
from bottle import route, run, static_file, abort, request, HTTPError, HTTPResponse
import threading
from dynamiccluster.utilities import getLogger
from dynamiccluster.exceptions import *
import os

log = getLogger(__name__)
engine = None
root_path = ""

class AdminServer(threading.Thread):
    
    @route('/dashboard', method='GET')
    def get_admin_index():
        global root_path
        log.debug("get dashboard index page. %s" % root_path+os.sep+'html')
        return static_file("index.html", root=root_path+os.sep+'html')

    @route('/js/:page', method='GET')
    def get_js_page(page):
        global root_path
        log.debug("static js page to return %s"%(page))
        return static_file(page, root=root_path+os.sep+'html'+os.sep+'js')
    @route('/css/:page', method='GET')
    def get_js_page(page):
        global root_path
        log.debug("static css page to return %s"%(page))
        return static_file(page, root=root_path+os.sep+'html'+os.sep+'css')
    @route('/fonts/:page', method='GET')
    def get_fonts_page(page):
        global root_path
        log.debug("static fonts page to return %s"%(page))
        return static_file(page, root=root_path+os.sep+'html'+os.sep+'fonts')
    
    @route('/workernode')
    def get_workernodes():
        state = request.query.state
        log.debug("only whose state=%s" % state)
        global engine
        #log.debug(data.__dict__)
        if len(state)>0:
            return repr([w for w in engine.info.worker_nodes if w.state==int(state)])
        return repr(engine.info.worker_nodes)

    @route('/workernode/<hostname>')
    def get_workernodes(hostname):
        global engine
        #log.debug(data.__dict__)
        list=[w for w in engine.info.worker_nodes if w.hostname==hostname]
        if len(list)==0:
            return HTTPResponse(status=404, body="worker node %s not found" % hostname)
        return repr(list[0])
    
    @route('/workernode/:hostname/:action', method="PUT")
    def manipulate_worker_node(hostname, action):
        global engine
        list=[w for w in engine.info.worker_nodes if w.hostname==hostname]
        if len(list)==0:
            return HTTPResponse(status=404, body="worker node %s not found" % hostname)
        if action=="hold":
            engine.hold_worker_node(hostname)
        elif action=="unload":
            engine.unhold_worker_node(hostname)
        elif action=="vocate":
            engine.vocate_worker_node(hostname)
        else:
            return HTTPResponse(status=404, body="action not supported")
        return {"success":True}
    
    @route('/workernode/:hostname', method="DELETE")
    def delete_worker_node(hostname):
        global engine
        try:
            engine.delete_worker_node(hostname)
        except WorkerNodeNotFoundException:
            return HTTPResponse(status=404, body="worker node %s not found" % hostname)
        except InvalidStateWhenDeleteWorkerNodeException:
            log.debug("can't delete %s in current state."%hostname)
            return HTTPResponse(status=400, body="worker node %s cannot be deleted in current state" % hostname)
        except:
            return HTTPResponse(status=500, body="server error")
        return {"success":True}
    
    @route('/job')
    def get_jobs():
        global engine
        #log.debug(data.__dict__)
        return repr(engine.info.queued_jobs)

    @route('/job/:id')
    def get_jobs(id):
        global engine
        #log.debug(data.__dict__)
        list=[j for j in engine.info.queued_jobs if j.jobid==id]
        if len(list)==0:
            abort(404, "job not found")
        return repr(list[0])
    
    @route('/server/config')
    def get_server_config():
        global engine
        log.debug(engine.config)
        return engine.config
    
    @route('/server/status')
    def get_server_status():
        global engine
        return engine.get_status()
    
    @route('/server/auto', method="PUT")
    def get_server_auto():
        global engine
        engine.set_auto()
        return {"success":True}
    
    @route('/server/auto', method="DELETE")
    def unset_server_auto():
        global engine
        engine.unset_auto()
        return {"success":True}
    
    @route('/resource', method="GET")
    def get_resources():
        global engine
        res_list=engine.resources
        if len(res_list)==0:
            abort(404, "resource %s not found" % res_name)
        for res in res_list:
            res.worker_nodes=[w for w in engine.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name]
        return repr(engine.resources)
 
    @route('/resource/:res_name', method="GET")
    def get_resource(res_name):
        global engine
        res_list=[r for r in engine.resources if r.name==res_name]
        for res in res_list:
            res.worker_nodes=[w for w in engine.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name]
        return repr(res_list[0])
   
    @route('/resource/:res', method="PUT")
    def add_instace_to_res(res):
        num_string = request.query.num
        number=1
        if len(num_string)>0 and num_string.isdigit():
            number=int(num_string)
        log.debug("launch %s instance in %s" % (number,res))
        global engine
        try:
            engine.launch_new_instance(res, number)
            return {"success":True}
        except NoCloudResourceException:
            abort(404, "Cloud resource not found")
        except InsufficientResourceException:
            abort(400, "Resource limit exceeded.")
        abort(500, "Unknown error")
    
    def __init__(self, dynaimc_engine=None, working_path=""):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        global engine
        engine=dynaimc_engine
        global root_path
        root_path=working_path
        self.__port=engine.config['dynamic-cluster']['admin-server']['port']
        self.__debug=engine.config['dynamic-cluster']['admin-server'].get('debug', True)
        
    def run(self):
        run(host='0.0.0.0', port=self.__port, debug=self.__debug)
