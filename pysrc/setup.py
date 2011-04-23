#!/usr/bin/env python

from distutils.core import setup

setup(
        name="embedvm",
        description="Python tools for working with the embedvm virtual machine",
        author="chrysn",
        author_email="chrysn@fsfe.org",
        #url="", # FIXME
        license="GPL-3+",
        packages=[
            'embedvm',
            ],
        scripts=[
            'evm-disasm',
            'evm-asm',
            'evm-pycomp',
            ],
        )
