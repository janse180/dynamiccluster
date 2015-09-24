
from bottle import route, run, static_file, request, HTTPError, HTTPResponse
import threading
from dynamiccluster.utilities import getLogger, get_prefix
from dynamiccluster.exceptions import *
from dynamiccluster.data import CloudResource
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

    @route('/js/<page>', method='GET')
    def get_js_page(page):
        global root_path
        log.debug("static js page to return %s"%(page))
        if page=="config.js":
            if 'plugins' in engine.config and 'graphite' in engine.config['plugins']:
                graph_view=True
                graphite_prefix=engine.config['plugins']['graphite']['arguments']['prefix']
                graphite_hostname=engine.config['plugins']['graphite']['arguments']['hostname']
                wn_prefix=get_prefix([r.config['instance_name_prefix'] for r in engine.resources])
                return "var graph_view=true;\nvar graphite_prefix='"+graphite_prefix+"';\nvar graphite_hostname='"+graphite_hostname+"';\nvar wn_prefix='"+wn_prefix+"';"
            return "var graph_view=false;"
        return static_file(page, root=root_path+os.sep+'html'+os.sep+'js')
    @route('/css/<page>', method='GET')
    def get_css_page(page):
        global root_path
        log.debug("static css page to return %s"%(page))
        return static_file(page, root=root_path+os.sep+'html'+os.sep+'css')
    @route('/fonts/<page>', method='GET')
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
    
    @route('/workernode/<hostname>/<action>', method="PUT")
    def manipulate_worker_node(hostname, action):
        global engine
        list=[w for w in engine.info.worker_nodes if w.hostname==hostname]
        if len(list)==0:
            return HTTPResponse(status=404, body="worker node %s not found" % hostname)
        log.debug("%s %s"%(action,hostname))
        try:
            if action=="hold":
                engine.hold_worker_node(hostname)
            elif action=="unhold":
                engine.unhold_worker_node(hostname)
            elif action=="vacate":
                engine.vacate_worker_node(hostname)
            else:
                return HTTPResponse(status=404, body="action not supported")
        except WorkerNodeNotFoundException:
            return HTTPResponse(status=404, body="worker node %s not found" % hostname)
        except InvalidStateException:
            return HTTPResponse(status=400, body="You are not allowed to %s worker node %s in current state." % (action, hostname))
        except:
            log.exception("unable to %s worker node %s"%(action, hostname))
            return HTTPResponse(status=500, body="server error")
        return {"success":True}
    
    @route('/workernode/<hostname>', method="DELETE")
    def delete_worker_node(hostname):
        global engine
        try:
            engine.delete_worker_node(hostname)
        except WorkerNodeNotFoundException:
            return HTTPResponse(status=404, body="worker node %s not found" % hostname)
        except InvalidStateException:
            log.debug("can't delete %s in current state."%hostname)
            return HTTPResponse(status=400, body="worker node %s cannot be deleted in current state, please put it on hold first." % hostname)
        except:
            return HTTPResponse(status=500, body="server error")
        return {"success":True}
    
    @route('/job')
    def get_jobs():
        global engine
        #log.debug(data.__dict__)
        return repr(engine.info.queued_jobs)

    @route('/job/<id>')
    def get_jobs(id):
        global engine
        #log.debug(data.__dict__)
        list=[j for j in engine.info.queued_jobs if j.jobid==id]
        if len(list)==0:
            return HTTPResponse(status=404, body="job not found")
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

    @route('/server/queues')
    def get_server_queues():
        global engine
        return engine.get_queues()
    
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
            return HTTPResponse(status=404, body="resource %s not found" % res_name)
        for res in res_list:
            res.worker_nodes=[w for w in engine.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name]
            res_config=engine.config['cloud'][res.name]
            if res.min_num!=res_config['quantity']['min'] or res.max_num!=res_config['quantity']['max']:
                if res.min_num==0 and res.min_num==0:
                    if len(res.worker_nodes)==0:
                        res.flag=CloudResource.Drained
                    else:
                        res.flag=CloudResource.Draining
                elif res.min_num==res.current_num and res.min_num==res.current_num:
                    res.flag=CloudResource.Frozen
            else:
                res.flag=CloudResource.Normal
        return repr(engine.resources)
 
    @route('/resource/<res_name>', method="GET")
    def get_resource(res_name):
        global engine
        try:
            res=engine.get_resource_by_name(res_name)
            res.worker_nodes=[w for w in engine.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name]
            res_config=engine.config['cloud'][res.name]
            if res.min_num!=res_config['quantity']['min'] and res.max_num!=res_config['quantity']['max']:
                if res.min_num==res.current_num and res.min_num==res.current_num:
                    res.flag=CloudResource.Frozen
                elif res.min_num==0 and res.min_num==0:
                    if len(res.worker_nodes)==0:
                        res.flag=CloudResource.Drained
                    else:
                        res.flag=CloudResource.Draining
            else:
                res.flag=CloudResource.Normal
            return repr(res)
        except NoCloudResourceException:
            return HTTPResponse(status=404, body="Cloud resource %s not found"%res)
        return HTTPResponse(status=500, body="Unknown error")
   
    @route('/resource/<res>', method="PUT")
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
            return HTTPResponse(status=404, body="Cloud resource %s not found"%res)
        except InsufficientResourceException:
            return HTTPResponse(status=400, body="You have requested %s worker node(s) in %s but it has exceeded the resource limit."%(num_string,res))
        return HTTPResponse(status=500, body="Unknown error")
    
    @route('/resource/<res>/<action>', method="PUT")
    def manipulate_resource(res, action):
        global engine
        log.debug("%s %s"%(action,res))
        try:
            if action=="freeze":
                engine.freeze_resource(res)
            elif action=="restore":
                engine.restore_resource(res)
            elif action=="drain":
                engine.drain_resource(res)
            else:
                return HTTPResponse(status=404, body="action not supported")
        except NoCloudResourceException:
            return HTTPResponse(status=404, body="Cloud resource %s not found"%res)
        return {"success":True}

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
