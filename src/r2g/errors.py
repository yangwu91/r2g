class InputError(Exception):
    """Error raised for checking input arguments"""
    pass


class OutputError(Exception):
    """Error raised for checking outputs"""
    pass


class AssembleError(Exception):
    """Error raised for assemblers, i.e., Trinity"""
    pass


class QueryError(Exception):
    """Couldn't get or parse results from NCBI"""
    pass


class FetchError(Exception):
    """Couldn't fetch Spot in the database SRA"""
    pass


class AlignerError(Exception):
    """Error raised for the aligner engine"""
    pass
