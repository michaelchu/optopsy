import time
import optopsy as op


def start():
    """
    Main function of program.
    """
    # program timer
    program_starts = time.time()

    # Analyse VXX vertical spreads
    option_chains = op.get("VXX", start="2016-01-29", end="2016-03-12")
    option_strategy = op.OptionStrategies.iron_condor(option_chains, op.Period.SEVEN_WEEKS, 5, 2, 2)

    program_ends = time.time()
    print("The simulation ran for {0} seconds.".format(round(program_ends - program_starts, 2)))

    # option_strategy.surface_plot("2016-02-19")


if __name__ == '__main__':
    start()