import logging
from subprocess import Popen, PIPE

__author__ = "Marius Lindauer"
__copyright__ = "Copyright 2015, ML4AAD"
__license__ = "GPLv3"
__maintainer__ = "Marius Lindauer"
__email__ = "lindauer@cs.uni-freiburg.de"
__version__ = "0.0.1"


class StatusType(object):

    """
        class to define numbers for status types
    """
    UNKNOWN = -1  # only used in db setting
    SUCCESS = 1
    TIMEOUT = 2
    CRASHED = 3
    ABORT = 4
    MEMOUT = 5


class ExecuteTARun(object):

    """
        executes a target algorithm run with a given configuration
        on a given instance and some resource limitations

        Attributes
        ----------
        ta : string
            the command line call to the target algorithm (wrapper)
    """

    def __init__(self, ta, run_obj="runtime", par_factor=1, logger=logging.getLogger("ExecuteTARun")):
        """
        Constructor

        Parameters
        ----------
            ta : list
                target algorithm command line as list of arguments
            run_obj: str
                run objective of SMAC
            par_factor: int
                penalized average runtime factor
            logger: Logger from logging
                logger object
        """
        self.ta = ta
        self.logger = logging.getLogger("ExecuteTARun")
        pass

    def run(self, config, instance,
            cutoff=99999999999999.,
            seed=12345,
            instance_specific="0"):
        """
            runs target algorithm <self.ta> with configuration <config> on
            instance <instance> with instance specifics <specifics>
            for at most <cutoff> seconds and random seed <seed>

            Parameters
            ----------
                config : dictionary
                    dictionary param -> value
                instance : string
                    problem instance
                cutoff : double
                    runtime cutoff
                seed : int
                    random seed
                instance_specific: str
                    instance specific information (e.g., domain file or solution)

            Returns
            -------
                status: enum of StatusType (int)
                    {SUCCESS, TIMEOUT, CRASHED, ABORT}
                cost: float
                    cost/regret/quality (float) 
                runtime: float
                    runtime (None if not returned by TA)
                additional_info: dict
                    all further additional run information
        """
        return StatusType.SUCCESS, 12345.0, 1.2345, {}
