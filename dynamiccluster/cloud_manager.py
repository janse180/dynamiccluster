


class CloudManager(object):
    def __init__(self, config):
        self.config=config
        
    def list(self):
        assert 0, 'Must define list'
    def boot(self):
        assert 0, 'Must define boot'
    def destroy(self):
        assert 0, 'Must define boot'
    def get(self):
        assert 0, 'Must define get'
    
    
class OpenStackManager(CloudManager):
    def __init__(self, config):
        CloudManager.__init__(self, config)
        
    