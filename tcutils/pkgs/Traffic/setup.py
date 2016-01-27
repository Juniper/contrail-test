#!/usr/bin/env python

from distutils.core import setup

setup(name="traffic",
      version="1.0",
      author="Ignatious Johnson",
      author_email="ijohnson@juniper.net",
      description=("Traffic generator package."),
      packages=['traffic',
                'traffic.core',
                'traffic.utils', ],
      scripts=['traffic/scripts/sendpkts', 'traffic/scripts/recvpkts']
      )
