#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='finance-news-scraper',
    version='1.0.0',
    description='同花顺金融快讯爬虫 - 支持快讯获取与投资分析',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    author='galig',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'requests>=2.28.0',
    ],
    entry_points={
        'console_scripts': [
            'finance-news=scraper.__main__:main',
        ],
    },
    package_data={
        'scraper': ['SKILL.md', 'README.md'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Financial and Investment Industry',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
