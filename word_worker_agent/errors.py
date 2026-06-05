class WordWorkerRuntimeError(RuntimeError):
    def __init__(self, error_code, detail):
        super().__init__(detail)
        self.error_code = error_code
        self.detail = detail
