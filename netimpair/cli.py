"""
netimpair CLI
"""
import argparse
import os
import signal
import time
import traceback
from functools import partial


def parse_args():
    '''Parse command-line arguments.'''
    argparser = argparse.ArgumentParser(
        description='Network Impairment Test Tool')

    argparser.add_argument(
        '-n', '--nic',
        choices=os.listdir('/sys/class/net'),
        metavar='INTERFACE',
        required=True,
        help='name of the network interface to be impaired')
    argparser.add_argument(
        '--inbound',
        action='store_true',
        help='do inbound impairment on the interface instead of outbound')
    argparser.add_argument(
        '--include',
        action='append',
        default=[],
        help='ip addresses and/or ports to include in network '
        'impairment (example: --include src=ip,sport=portnum '
        '--include dst=ip,dport=portnum)')
    argparser.add_argument(
        '--exclude',
        action='append',
        default=['dport=22', 'sport=22'],
        help='ip addresses and/or ports to exclude from network '
        'impairment (example: --exclude src=ip,sport=portnum '
        '--exclude dst=ip,dport=portnum)')

    subparsers = argparser.add_subparsers(
        title='impairments',
        dest='subparser_name',
        description='specify which impairment to enable',
        help='valid impairments')

    # loss args
    netem_args = subparsers.add_parser('netem', help='enable packet loss')
    netem_args.add_argument(
        '--loss_ratio',
        type=int,
        default=0,
        help='specify percentage of packets that will be lost')
    netem_args.add_argument(
        '--loss_corr',
        type=int,
        default=0,
        help='specify a correlation factor for the random packet loss')
    # dup args
    netem_args.add_argument(
        '--dup_ratio',
        type=int,
        default=0,
        help='specify percentage of packets that will be duplicated')
    # delay/jitter args
    netem_args.add_argument(
        '--delay',
        type=int,
        default=0,
        help='specify an overall delay for each packet')
    netem_args.add_argument(
        '--jitter',
        type=int,
        default=0,
        help='specify amount of jitter in milliseconds')
    netem_args.add_argument(
        '--delay_jitter_corr',
        type=int,
        default=0,
        help='specify a correlation factor for the random jitter')
    # reorder args
    netem_args.add_argument(
        '--reorder_ratio',
        type=int,
        default=0,
        help='specify percentage of packets that will be reordered')
    netem_args.add_argument(
        '--reorder_corr',
        type=int,
        default=0,
        help='specify a correlation factor for the random reordering')
    # toggle parameter
    netem_args.add_argument(
        '--toggle',
        nargs='+',
        type=int,
        default=[1000000],
        help='toggles impairment on and off on specific intervals (example: '
        '--toggle 6 3 5 1 will enable impairment for 6 seconds, turn it off '
        'for 3, turn it on for 5, and turn it off for 1')

    # rate limit args
    rate_args = subparsers.add_parser('rate', help='enable packet reorder')
    rate_args.add_argument(
        '--limit',
        type=int,
        default=0,
        help='specify rate limit in kb')
    rate_args.add_argument(
        '--buffer',
        type=int,
        default=2000,
        help='specify how many tokens in terms of bytes should be available')
    rate_args.add_argument(
        '--latency',
        type=int,
        default=20,
        help='specify the maximum time packets can stay in the '
        'queue before getting dropped')
    rate_args.add_argument(
        '--toggle',
        nargs='+',
        type=int,
        default=[1000000],
        help='toggles impairment on and off on specific intervals (example: '
        '--toggle 6 3 5 1 will enable impairment for 6 seconds, turn it off '
        'for 3, turn it on for 5, and turn it off for 1')

    return argparser.parse_args()


def init_signals(netem):
    '''Catch signals in order to stop network impairment before exiting.'''

    # pylint: disable=unused-argument
    def signal_action(signum, frame):
        '''To be executed upon exit signal.'''
        print()
        netem.teardown()
        # Print blank line before quitting to deal with some crappy
        # terminal behavior
        print()
        exit(5)

    # Catch SIGINT and SIGTERM so that we can clean up
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, signal_action)

    print('Network impairment starting.',
          'Press Ctrl-C to restore normal behavior and quit.\n')


def main():
    '''Start the CLI application.
    '''
    args = parse_args()

    if os.geteuid() != 0:
        print('You need root permissions to enable impairment!'
              'Please run with sudo or as root.', sys.stderr)
        exit(1)

    try:
        # Create Netem instance
        netem = Netem(
            args.nic, args.inbound, args.include, args.exclude)

        # Perform setup
        netem.initialize()

        # Catch signals
        init_signals(netem)

        toggle = args.toggle

        # Do impairment
        if args.subparser_name == 'netem':
            mng = partial(
                    netem.emulate,
                    args.loss_ratio,
                    args.loss_corr,
                    args.dup_ratio,
                    args.delay,
                    args.jitter,
                    args.delay_jitter_corr,
                    args.reorder_ratio,
                    args.reorder_corr
                )

        elif args.subparser_name == 'rate':
            mng = partial(
                netem.rate,
                args.limit,
                args.buffer,
                args.latency
            )

        # perform toggled periods
        while toggle:
            with mng():
                # sleep while enabled
                time.sleep(toggle.pop(0))
                if not toggle:
                    break

            # sleep while disabled
            time.sleep(toggle.pop(0))

        # Shutdown cleanly
        netem.teardown()
    except netem.subproc.CalledProcessError:
        traceback.print_exc()
        netem.teardown()
        exit(5)
