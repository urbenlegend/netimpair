# netimpair
An easy-to-use network impairment script for Linux written in Python

netimpair.py is a CLI tool that simulates bad network conditions on Linux machines. It essentially is a wrapper script around the Linux netem module and the `tc` command. Using `tc` and netem is sometimes difficult, unintuitive or tedious at best, especially if you only want to impair a specific subset of network traffic. netimpair.py automates all of this and provides a simpler CLI interface for basic network impairment needs.

**NOTE:** Fedora users may need to install kernel-modules-extra if they're getting the below error:
```bash
RTNETLINK answers: No such file or directory
Traceback (most recent call last):
  File "./netimpair.py", line 295, in main
    args.toggle)
  File "./netimpair.py", line 175, in netem
    self.nic))
  File "./netimpair.py", line 58, in _check_call
    subprocess.check_call(shlex.split(command))
  File "/usr/lib64/python2.7/subprocess.py", line 541, in check_call
    raise CalledProcessError(retcode, cmd)
CalledProcessError: Command '['tc', 'qdisc', 'add', 'dev', 'wlp3s0', 'parent', '1:3', 'handle', '30:', 'netem']' returned non-zero exit status 2
```
## Features
netimpair.py can do the following things:

* Simulate packet loss, duplication, jitter, reordering, and rate limiting
* Selective impairment based on ip/port
* Inbound or outbound impairment
* Automatically cleans up any impairment on exit or Ctrl-C

netimpair.py supports both Python 2 and 3.

#### Jitter

```bash
# Add 200ms jitter
sudo ./netimpair.py -n eth0 netem --jitter 200
```

#### Delay

```bash
# Add 200ms delay
sudo ./netimpair.py -n eth0 netem --delay 200
```

#### Loss

```bash
# Add 5% loss
sudo ./netimpair.py -n eth0 netem --loss_ratio 5
```

#### Rate Control

```bash
# Limit rate to 1mbit
sudo ./netimpair.py -n eth0 rate --limit 1000
```

#### Impair inbound traffic

```bash
# Append --inbound flag before the impairment keyword to apply inbound impairment
# For example, this applies 5% loss on inbound eth0
sudo ./netimpair.py -n eth0 --inbound netem --loss_ratio 5
```

#### Selectively impair certain traffic

```bash
# Add 5% loss on packets with source IP of 10.194.247.50 and destination port 9001
# NOTE: Specifying include flag overrides the default include, which impairs everything
sudo ./netimpair.py -n eth0 --include src=10.194.247.50,dport=9001 netem --loss_ratio 5
# Exclude packets with destination IP 10.194.247.50 and source port 10000
sudo ./netimpair.py -n eth0 --exclude dst=10.194.247.50,sport=10000 netem --loss_ratio 5
# Exclude SSH 
sudo ./netimpair.py -n eth0 --exclude dport=22 netem --loss_ratio 5
# Exclude a certain source IP on all ports
sudo ./netimpair.py -n eth0 --exclude src=10.194.247.50 netem --loss_ratio 5
```

#### Additional parameters can be found with the help option
```bash
# Basic help
./netimpair.py -h
# Help for the netem subcommand
./netimpair.py netem -h
# Help for the rate subcommand
./netimpair.py rate -h
```
