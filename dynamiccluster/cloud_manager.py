"""
interface of cloud managers
"""
from dynamiccluster.utilities import get_unique_string, load_template_with_jinja, getLogger, hostname_lookup, unix_time
from dynamiccluster.data import Instance
from dynamiccluster.exceptions import CloudNotAvailableException, FlavorNotFoundException

log = getLogger(__name__)

class CloudManager(object):
    def __init__(self, name, config, max_attempt_time=5):
        self.name=name
        self.config=config
        self.max_attempt_time=max_attempt_time
        
    def list(self, **kwargs):
        assert 0, 'Must define list'
    def boot(self, **kwargs):
        assert 0, 'Must define boot'
    def destroy(self, **kwargs):
        assert 0, 'Must define destroy'
    def update(self, **kwargs):
        assert 0, 'Must define destroy'
    
    
        
