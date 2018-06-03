class Node(object):
    """
   The Node is the main building block in bt's tree structure design.
   Both StrategyBase and SecurityBase inherit Node. It contains the
   core functionality of a tree node.

   Args:
       * name (str): The Node name
       * parent (Node): The parent Node
       * children (dict, list): A collection of children. If dict,
           the format is {name: child}, if list then list of children.

   Attributes:
       * name (str): Node name
       * parent (Node): Node parent
       * root (Node): Root node of the tree (topmost node)
       * children (dict): Node's children
       * now (datetime): Used when backtesting to store current date
       * stale (bool): Flag used to determine if Node is stale and need
           updating
       * prices (TimeSeries): Prices of the Node. Prices for a security will
           be the security's price, for a strategy it will be an index that
           reflects the value of the strategy over time.
       * price (float): last price
       * value (float): last value
       * weight (float): weight in parent
       * full_name (str): Name including parents' names
       * members (list): Current Node + node's children

   """

    def __init__(self, name, parent=None, children=None):

        self.name = name

        # strategy children helpers
        self._has_strat_children = False
        self._strat_children = []

        # if children is not None, we assume that we want to limit the
        # available children space to the provided list.
        if children is not None:
            if isinstance(children, list):
                # if all strings - just save as universe_filter
                if all(isinstance(x, str) for x in children):
                    self._universe_tickers = children
                    # empty dict - don't want to uselessly create
                    # tons of children when they might not be needed
                    children = {}
                else:
                    # this will be case if we pass in children
                    # (say a bunch of sub-strategies)
                    tmp = {}
                    ut = []
                    for c in children:
                        if type(c) == str:
                            tmp[c] = SecurityBase(c)
                            ut.append(c)
                        else:
                            # deepcopy object for possible later reuse
                            tmp[c.name] = deepcopy(c)

                            # if strategy, turn on flag and add name to list
                            # strategy children have special treatment
                            if isinstance(c, StrategyBase):
                                self._has_strat_children = True
                                self._strat_children.append(c.name)
                            # if not strategy, then we will want to add this to
                            # universe_tickers to filter on setup
                            else:
                                ut.append(c.name)

                    children = tmp
                    # we want to keep whole universe in this case
                    # so set to None
                    self._universe_tickers = ut

        if parent is None:
            self.parent = self
            self.root = self
            # by default all positions are integer
            self.integer_positions = True
        else:
            self.parent = parent
            self.root = parent.root
            parent._add_child(self)

        # default children
        if children is None:
            children = {}
            self._universe_tickers = None
        self.children = children

        self._childrenv = list(children.values())
        for c in self._childrenv:
            c.parent = self
            c.root = self.root

        # set default value for now
        self.now = 0
        # make sure root has stale flag
        # used to avoid unnecessary update
        # sometimes we change values in the tree and we know that we will need
        # to update if another node tries to access a given value (say weight).
        # This avoid calling the update until it is actually needed.
        self.root.stale = False

        # helper vars
        self._price = 0
        self._value = 0
        self._weight = 0

        # is security flag - used to avoid updating 0 pos securities
        self._issec = False

    def __getitem__(self, key):
        return self.children[key]


class StrategyBase(Node):
    """
   Strategy Node. Used to define strategy logic within a tree.
   A Strategy's role is to allocate capital to it's children
   based on a function.

   Args:
       * name (str): Strategy name
       * children (dict, list): A collection of children. If dict,
           the format is {name: child}, if list then list of children.
           Children can be any type of Node.
       * parent (Node): The parent Node

   Attributes:
       * name (str): Strategy name
       * parent (Strategy): Strategy parent
       * root (Strategy): Root node of the tree (topmost node)
       * children (dict): Strategy's children
       * now (datetime): Used when backtesting to store current date
       * stale (bool): Flag used to determine if Strategy is stale and need
           updating
       * prices (TimeSeries): Prices of the Strategy - basically an index that
           reflects the value of the strategy over time.
       * outlays (DataFrame): Outlays for each SecurityBase child
       * price (float): last price
       * value (float): last value
       * weight (float): weight in parent
       * full_name (str): Name including parents' names
       * members (list): Current Strategy + strategy's children
       * securities (list): List of strategy children that are of type
           SecurityBase
       * commission_fn (fn(quantity, price)): A function used to determine the
           commission (transaction fee) amount. Could be used to model
           slippage (implementation shortfall). Note that often fees are
           symmetric for buy and sell and absolute value of quantity should
           be used for calculation.
       * capital (float): Capital amount in Strategy - cash
       * universe (DataFrame): Data universe available at the current time.
           Universe contains the data passed in when creating a Backtest. Use
           this data to determine strategy logic.

   """

    def __init__(self, name, children=None, parent=None):
        Node.__init__(self, name, children=children, parent=parent)
        self._capital = 0
        self._weight = 1
        self._value = 0
        self._price = 100

        # helper vars
        self._net_flows = 0
        self._last_value = 0
        self._last_price = 100
        self._last_fee = 0

        # default commission function
        self.commission_fn = self._dflt_comm_fn

        self._paper_trade = False
        self._positions = None
        self.bankrupt = False


class Strategy(StrategyBase):
    """
   Strategy expands on the StrategyBase and incorporates Algos.

   Basically, a Strategy is built by passing in a set of algos. These algos
   will be placed in an Algo stack and the run function will call the stack.

   Furthermore, two class attributes are created to pass data between algos.
   perm for permanent data, temp for temporary data.

   Args:
       * name (str): Strategy name
       * algos (list): List of Algos to be passed into an AlgoStack
       * children (dict, list): Children - useful when you want to create
           strategies of strategies

   Attributes:
       * stack (AlgoStack): The stack
       * temp (dict): A dict containing temporary data - cleared on each call
           to run. This can be used to pass info to other algos.
       * perm (dict): Permanent data used to pass info from one algo to
           another. Not cleared on each pass.

   """

    def __init__(self, name, algos=None, children=None):
        super(Strategy, self).__init__(name, children=children)
        if algos is None:
            algos = []
        self.stack = AlgoStack(*algos)
        self.temp = {}
        self.perm = {}
