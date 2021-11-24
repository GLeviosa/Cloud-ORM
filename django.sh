#!/bin/bash
cd /home/ubuntu
sudo apt update
git clone https://github.com/raulikeda/tasks.git

sudo sed -i "s/node1/postgres_ip/g" /home/ubuntu/tasks/portfolio/settings.py

cd tasks
./install.sh

sudo reboot
