class Algo(object):
    """
    Algos are used to modularize strategy logic so that strategy logic becomes
    modular, composable, more testable and less error prone. Basically, the
    Algo should follow the unix philosophy - do one thing well.
    In practice, algos are simply a function that receives one argument, the
    Strategy (referred to as target) and are expected to return a bool.
    When some state preservation is necessary between calls, the Algo
    object can be used (this object). The __call___ method should be
    implemented and logic defined therein to mimic a function call. A
    simple function may also be used if no state preservation is necessary.
    Args:
        * name (str): Algo name
    """

    def __init__(self, name=None):
        self._name = name

    @property
    def name(self):
        """
        Algo name.
        """
        if self._name is None:
            self._name = self.__class__.__name__
        return self._name

    def __call__(self, target):
        raise NotImplementedError("%s not implemented!" % self.name)


class AlgoStack(Algo):
    """
    An AlgoStack derives from Algo runs multiple Algos until a
    failure is encountered.

    The purpose of an AlgoStack is to group a logic set of Algos together. Each
    Algo in the stack is run. Execution stops if one Algo returns False.

    Args:
        * algos (list): List of algos.

    """

    def __init__(self, *algos):
        super(AlgoStack, self).__init__()
        self.algos = algos
        self.check_run_always = any(hasattr(x, 'run_always')
                                    for x in self.algos)

    def __call__(self, target):
        # normal running mode
        if not self.check_run_always:
            for algo in self.algos:
                if not algo(target):
                    return False
            return True
        # run mode when at least one algo has a run_always attribute
        else:
            # store result in res
            # allows continuation to check for and run
            # algos that have run_always set to True
            res = True
            for algo in self.algos:
                if res:
                    res = algo(target)
                elif hasattr(algo, 'run_always'):
                    if algo.run_always:
                        algo(target)
            return res
