from unittest import TestCase

from optopsy.options.option import Option
from optopsy.options.option_query import OptionQuery
from optopsy.options.option_strategy import OptionStrategy

from optopsy.core.options.option_strategies import OptionStrategies
from optopsy.datafeeds.sqlite_adapter import SQLiteDataFeed
from optopsy.globals import OptionType


class TestOptionStrategy(TestCase):
    def setUp(self):
        self.op_test = OptionStrategy(chains=None)

    def test_max_strike_width_one_strike(self):
        self.op_test.strikes = [1]
        max_width = self.op_test._max_strike_width()
        self.assertEqual(0, max_width)

    def test_max_strike_width_two_strikes(self):
        self.op_test.strikes = [1, 2.5]
        max_width = self.op_test._max_strike_width()
        self.assertEqual(1.5, max_width)

    def test_max_strike_width_three_strikes(self):
        self.op_test.strikes = [1, 2.5, 4]
        max_width = self.op_test._max_strike_width()
        self.assertEqual(1.5, max_width)

        self.op_test.strikes = [1, 2.5, 5]
        max_width = self.op_test._max_strike_width()
        self.assertEqual(2.5, max_width)

    def test_max_strike_width_four_strikes(self):
        self.op_test.strikes = [1, 2.5, 7, 5.5]
        max_width = self.op_test._max_strike_width()
        self.assertEqual(1.5, max_width)

        self.op_test.strikes = [1, 2.5, 7.5, 5.5]
        max_width = self.op_test._max_strike_width()
        self.assertEqual(2, max_width)

    def test_max_strike_width_invalid_strikes(self):
        self.op_test.strikes = [1, 2.5, 4, 5.5, 5]
        self.assertRaises(ValueError, lambda: self.op_test._max_strike_width())

        self.op_test.strikes = []
        self.assertRaises(ValueError, lambda: self.op_test._max_strike_width())

    def test_map_vertical(self):
        # test case for call spread
        sym_1 = ".VXX160219C00030000-.VXX160219C00035000"
        self.op_test.legs = self.op_test._map(sym_1)

        # expected value
        s_option = Option("VXX", "160219", "C", "00030000")
        l_option = Option("VXX", "160219", "C", "00035000")

        # test option leg
        self.assertEqual(len(self.op_test.legs), 2)
        self.assertEqual(1, self.op_test.legs[0]['quantity'])
        self.assertEqual(-1, self.op_test.legs[1]['quantity'])

        # test option in option legs
        self.assertEqual("VXX160219C00030000", self.op_test.legs[0]['contract'].symbol)
        self.assertEqual("VXX160219C00035000", self.op_test.legs[1]['contract'].symbol)

        self.assertEqual("2016-02-19", self.op_test.legs[0]['contract'].expiration)
        self.assertEqual("2016-02-19", self.op_test.legs[1]['contract'].expiration)

        self.assertEqual("C", self.op_test.legs[0]['contract'].option_type)
        self.assertEqual("C", self.op_test.legs[1]['contract'].option_type)

        self.assertEqual(30.0, self.op_test.legs[0]['contract'].strike)
        self.assertEqual(35.0, self.op_test.legs[1]['contract'].strike)

    def test_map_butterfly(self):
        # test case for call spread
        sym_1 = ".VXX160219C00030000-2*.VXX160219C00035000+.VXX160219C00040000"
        self.op_test.legs = self.op_test._map(sym_1)

        # expected value
        l1_option = Option("VXX", "160219", "C", "00030000")
        s_option = Option("VXX", "160219", "C", "00035000")
        l2_option = Option("VXX", "160219", "C", "00040000")

        # test option leg
        self.assertEqual(len(self.op_test.legs), 3)
        self.assertEqual(1, self.op_test.legs[0]['quantity'])
        self.assertEqual(-2, self.op_test.legs[1]['quantity'])
        self.assertEqual(1, self.op_test.legs[2]['quantity'])

        # test option in option legs
        self.assertEqual("VXX160219C00030000", self.op_test.legs[0]['contract'].symbol)
        self.assertEqual("VXX160219C00035000", self.op_test.legs[1]['contract'].symbol)
        self.assertEqual("VXX160219C00040000", self.op_test.legs[2]['contract'].symbol)

        self.assertEqual("2016-02-19", self.op_test.legs[0]['contract'].expiration)
        self.assertEqual("2016-02-19", self.op_test.legs[1]['contract'].expiration)
        self.assertEqual("2016-02-19", self.op_test.legs[2]['contract'].expiration)

        self.assertEqual("C", self.op_test.legs[0]['contract'].option_type)
        self.assertEqual("C", self.op_test.legs[1]['contract'].option_type)
        self.assertEqual("C", self.op_test.legs[2]['contract'].option_type)

        self.assertEqual(30.0, self.op_test.legs[0]['contract'].strike)
        self.assertEqual(35.0, self.op_test.legs[1]['contract'].strike)
        self.assertEqual(40.0, self.op_test.legs[2]['contract'].strike)

    def test_map_iron_condor(self):
        # test case for call spread
        sym_1 = ".VXX160219C00030000-.VXX160219C00035000+.VXX160219P00045000-.VXX160219P00040000"
        self.op_test.legs = self.op_test._map(sym_1)

        # expected value
        l1_option = Option("VXX", "160219", "C", "00030000")
        s1_option = Option("VXX", "160219", "C", "00035000")
        l2_option = Option("VXX", "160219", "P", "00045000")
        s2_option = Option("VXX", "160219", "P", "00040000")

        # test option leg
        self.assertEqual(len(self.op_test.legs), 4)

        self.assertEqual(1, self.op_test.legs[0]['quantity'])
        self.assertEqual(-1, self.op_test.legs[1]['quantity'])
        self.assertEqual(1, self.op_test.legs[2]['quantity'])
        self.assertEqual(-1, self.op_test.legs[3]['quantity'])

        # test option in option legs
        self.assertEqual("VXX160219C00030000", self.op_test.legs[0]['contract'].symbol)
        self.assertEqual("VXX160219C00035000", self.op_test.legs[1]['contract'].symbol)
        self.assertEqual("VXX160219P00045000", self.op_test.legs[2]['contract'].symbol)
        self.assertEqual("VXX160219P00040000", self.op_test.legs[3]['contract'].symbol)

        self.assertEqual("2016-02-19", self.op_test.legs[0]['contract'].expiration)
        self.assertEqual("2016-02-19", self.op_test.legs[1]['contract'].expiration)
        self.assertEqual("2016-02-19", self.op_test.legs[2]['contract'].expiration)
        self.assertEqual("2016-02-19", self.op_test.legs[3]['contract'].expiration)

        self.assertEqual("C", self.op_test.legs[0]['contract'].option_type)
        self.assertEqual("C", self.op_test.legs[1]['contract'].option_type)
        self.assertEqual("P", self.op_test.legs[2]['contract'].option_type)
        self.assertEqual("P", self.op_test.legs[3]['contract'].option_type)

        self.assertEqual(30.0, self.op_test.legs[0]['contract'].strike)
        self.assertEqual(35.0, self.op_test.legs[1]['contract'].strike)
        self.assertEqual(45.0, self.op_test.legs[2]['contract'].strike)
        self.assertEqual(40.0, self.op_test.legs[3]['contract'].strike)

    def test_nearest_mark_vertical(self):
        self.datafeed = SQLiteDataFeed()
        self.data = self.datafeed.get("VXX", start="2016-02-19", end="2016-02-19")

        # filter the data for one quote date
        data = self.data.loc[self.data['quote_date'] == "2016-02-19"]
        chains = OptionStrategies.vertical(OptionQuery(data), width=2, option_type=OptionType.CALL)
        result = chains.nearest_mark(0.5)

        self.assertEqual(result.expirations, ["2016-02-19"])
        self.assertEqual(result.strikes, [25.0, 27.0])
        self.assertEqual(result.underlying_symbol, "VXX")
        self.assertEqual(result.name, "Vertical")

    def test_nearest_mark_iron_condor(self):
        # initialize OptionStrategy class
        datafeed = SQLiteDataFeed()
        data = datafeed.get("VXX", start="2016-02-19", end="2016-02-19")

        # filter the data for one quote date
        data = data.loc[data['quote_date'] == "2016-02-19"]
        chains = OptionStrategies.iron_condor(OptionQuery(data), width=2, c_width=2, p_width=2)
        result = chains.nearest_mark(0.5)

        self.assertEqual(result.expirations, ["2016-02-19"])
        self.assertEqual(result.strikes, [25.0, 27.0, 23.0, 21.0])
        self.assertEqual(result.underlying_symbol, "VXX")
        self.assertEqual(result.name, "Iron Condor")
