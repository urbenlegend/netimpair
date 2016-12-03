#!/usr/bin/env python

'''
The MIT License (MIT)

Copyright (c) 2015 Benjamin Xiao

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from __future__ import print_function

import datetime
import shlex
import subprocess
import sys
from contextlib import contextmanager


class Netem(object):
    '''Wrapper around netem module and the ``tc`` command.
    '''
    def __init__(self, nic, inbound, include, exclude, subproc=subprocess):
        self.inbound = inbound
        self.include = include if include else ['src=0/0', 'src=::/0']
        self.exclude = exclude
        self.subproc = subproc
        self.nic = 'ifb1' if inbound else nic
        self.real_nic = nic

    def _call(self, command):
        '''Run command.'''
        self.subproc.call(shlex.split(command))

    def _check_call(self, command):
        '''Run command, raising CalledProcessError if it fails.'''
        self.subproc.check_call(shlex.split(command))

    @staticmethod
    def _generate_filters(filter_list):
        filter_strings = []
        filter_strings_ipv6 = []
        for tcfilter in filter_list:
            filter_tokens = tcfilter.split(',')
            try:
                filter_string = ''
                filter_string_ipv6 = ''
                for token in filter_tokens:
                    token_split = token.split('=')
                    key = token_split[0]
                    value = token_split[1]
                    # Check for ipv6 addresses and add them to the appropriate
                    # filter string
                    if key == 'src' or key == 'dst':
                        if '::' in value:
                            filter_string_ipv6 += 'match ip6 {0} {1} '.format(
                                key, value)
                        else:
                            filter_string += 'match ip {0} {1} '.format(
                                key, value)
                    else:
                        filter_string += 'match ip {0} {1} '.format(key, value)
                        filter_string_ipv6 += 'match ip6 {0} {1} '.format(
                            key, value)
                    if key == 'sport' or key == 'dport':
                        filter_string += '0xffff '
                        filter_string_ipv6 += '0xffff '
            except IndexError:
                print('ERROR: Invalid filter parameters', file=sys.stderr)

            if filter_string:
                filter_strings.append(filter_string)
            if filter_string_ipv6:
                filter_strings_ipv6.append(filter_string_ipv6)

        return filter_strings, filter_strings_ipv6

    def initialize(self):
        '''Set up traffic control.'''
        if self.inbound:
            # Create virtual ifb device to do inbound impairment on
            self._check_call('modprobe ifb')
            self._check_call('ip link set dev {0} up'.format(self.nic))
            # Delete ingress device before trying to add
            self._call('tc qdisc del dev {0} ingress'.format(self.real_nic))
            # Add ingress device
            self._check_call(
                'tc qdisc replace dev {0} ingress'.format(self.real_nic))
            # Add filter to redirect ingress to virtual ifb device
            self._check_call(
                'tc filter replace dev {0} parent ffff: protocol ip prio 1 '
                'u32 match u32 0 0 flowid 1:1 action mirred egress redirect '
                'dev {1}'.format(self.real_nic, self.nic))

        # Delete network impairments from any previous runs of this script
        self._call('tc qdisc del root dev {0}'.format(self.nic))

        # Create prio qdisc so we can redirect some traffic to be unimpaired
        self._check_call(
            'tc qdisc add dev {0} root handle 1: prio'.format(self.nic))

        # Apply selective impairment based on include and exclude parameters
        print('Including the following for network impairment:')
        include_filters, include_filters_ipv6 = self._generate_filters(
            self.include)
        for filter_string in include_filters:
            include_filter = 'tc filter add dev {0} protocol ip parent 1:0 ' \
                'prio 3 u32 {1}flowid 1:3'.format(self.nic, filter_string)
            print(include_filter)
            self._check_call(include_filter)

        for filter_string_ipv6 in include_filters_ipv6:
            include_filter_ipv6 = 'tc filter add dev {0} protocol ipv6 ' \
                'parent 1:0 prio 4 u32 {1}flowid 1:3'.format(
                    self.nic, filter_string_ipv6)
            print(include_filter_ipv6)
            self._check_call(include_filter_ipv6)
        print()

        print('Excluding the following from network impairment:')
        exclude_filters, exclude_filters_ipv6 = self._generate_filters(
            self.exclude)
        for filter_string in exclude_filters:
            exclude_filter = 'tc filter add dev {0} protocol ip parent 1:0 ' \
                'prio 1 u32 {1}flowid 1:2'.format(self.nic, filter_string)
            print(exclude_filter)
            self._check_call(exclude_filter)

        for filter_string_ipv6 in exclude_filters_ipv6:
            exclude_filter_ipv6 = 'tc filter add dev {0} protocol ipv6 ' \
                'parent 1:0 prio 2 u32 {1}flowid 1:2'.format(
                    self.nic, filter_string_ipv6)
            print(exclude_filter_ipv6)
            self._check_call(exclude_filter_ipv6)
        print()

    # pylint: disable=too-many-arguments
    @contextmanager
    def emulate(
            self,
            loss_ratio=0,
            loss_corr=0,
            dup_ratio=0,
            delay=0,
            jitter=0,
            delay_jitter_corr=0,
            reorder_ratio=0,
            reorder_corr=0,
    ):
        '''Enable packet loss using the ``netem`` subcommand to ``tc``.
        '''
        self._check_call(
            'tc qdisc add dev {0} parent 1:3 handle 30: netem'
            .format(self.nic)
        )
        impair_cmd = 'tc qdisc change dev {0} parent 1:3 handle 30: ' \
            'netem loss {1}% {2}% duplicate {3}% delay {4}ms {5}ms {6}% ' \
            'reorder {7}% {8}%'.format(
                self.nic, loss_ratio, loss_corr, dup_ratio, delay, jitter,
                delay_jitter_corr, reorder_ratio, reorder_corr)
        print('Setting network impairment:')
        print(impair_cmd)
        # Set network impairment
        self._check_call(impair_cmd)
        print('Impairment timestamp: {0}'.format(datetime.datetime.today()))

        yield

        self._check_call(
            'tc qdisc change dev {0} parent 1:3 handle 30: netem'.format(
                self.nic))
        print('Impairment stopped timestamp: {0}'.format(
                datetime.datetime.today()))

    @contextmanager
    def rate(self, limit=0, buffer_length=2000, latency=20):
        '''Enable packet reorder and rate limting using the ``rate`` subcommand
        to ``tc``.
        '''
        self._check_call(
            'tc qdisc add dev {0} parent 1:3 handle 30: tbf rate 1000mbit '
            'buffer {1} latency {2}ms'.format(
                self.nic, buffer_length, latency)
        )
        impair_cmd = 'tc qdisc change dev {0} parent 1:3 handle 30: tbf ' \
            'rate {1}kbit buffer {2} latency {3}ms'.format(
                self.nic, limit, buffer_length, latency)
        print('Setting network impairment:')
        print(impair_cmd)
        # Set network impairment
        self._check_call(impair_cmd)
        print('Impairment timestamp: {0}'.format(datetime.datetime.today()))

        yield

        self._check_call(
            'tc qdisc change dev {0} parent 1:3 handle 30: tbf rate '
            '1000mbit buffer {1} latency {2}ms'.format(
                self.nic, buffer_length, latency)
        )
        print('Impairment stopped timestamp: {0}'.format(
            datetime.datetime.today()))

    def teardown(self):
        '''Reset traffic control rules.'''
        if self.inbound:
            self._call(
                'tc filter del dev {0} parent ffff: protocol ip prio 1'.format(
                    self.real_nic))
            self._call('tc qdisc del dev {0} ingress'.format(self.real_nic))
            self._call('ip link set dev ifb0 down')
        self._call('tc qdisc del root dev {0}'.format(self.nic))
        print('Network impairment teardown complete.')
