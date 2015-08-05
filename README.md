# netimpair
An easy-to-use network impairment script for Linux written in Python

netimpair.py is a CLI tool that runs network impairment commands for you. It is located in the ta folder.
It can do the following things:

* Simulate packet loss, duplication, jitter, reordering, and rate limiting
* Selective impairment based on ip/port
* Inbound or outbound impairment
* Automatically cleans up any impairment on exit or Ctrl-C

netimpair.py is a Python 3 script. For systems that only support Python 2 in its default repositories (i.e. CentOS 6), you can use netimpair2.py

####Jitter

```bash
# Add 200ms jitter
sudo ./netimpair.py -n eth0 netem --jitter 200
```

####Delay

```bash
# Add 200ms delay
sudo ./netimpair.py -n eth0 netem --delay 200
```

####Loss

```bash
# Add 5% loss
sudo ./netimpair.py -n eth0 netem --loss_ratio 5
```

####Rate Control

```bash
# Limit rate to 1mbit
sudo ./netimpair.py -n eth0 rate --limit 1000
```

####Impair inbound traffic

```bash
# Append --inbound flag before the impairment keyword to apply inbound impairment
# For example, this applies 5% loss on inbound eth0
sudo ./netimpair.py -n eth0 --inbound netem --loss_ratio 5
```

Selectively impair certain traffic

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
