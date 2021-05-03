#!/usr/bin/env python

import sys
import os.path
import os
from os import walk

source_path = sys.argv[1]

_, _, filenames = next(walk(source_path))

filenames.sort()

print(filenames)
