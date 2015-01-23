class NoClusterDefinedException(BaseException):
    pass

class ServerInitializationError(BaseException):
    pass

class NoCloudResourceException(BaseException):
    pass

class WorkerNodeNotFoundException(BaseException):
    pass

class CloudNotAvailableException(BaseException):
    pass

class FlavorNotFoundException(BaseException):
    pass

class CloudNotSupportedException(BaseException):
    pass

class ConfigCheckerNotSupportedException(BaseException):
    pass

