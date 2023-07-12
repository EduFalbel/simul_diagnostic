.. simul_diagnostic documentation master file, created by
   sphinx-quickstart on Wed May 24 13:47:48 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to simul_diagnostic's documentation!
============================================

simul_diagnostic is a collection of Python packages designed to help you evaluate the calibration state of your traffic simulation.
Our goal is to help transport researchers and engineers quickly and easily check whether their simulations actually correspond to what is observed in the real world.
To do so we offer a handful of packages, each meant to assist with one part of the process, as well as ways to integrate them into your current pipeline.

As of now, the library comes with two Python subpackages:

- diagnostic
- map_matching

The former is meant to provide users with a quick way to generate the most common analyses when evaluating traffic simulations, such as calculating link-by-link statistics (GEH, SQV, etc.) and aggregated metrics, while the latter seeks to help users that deal with particular loop detector databases know which detector counts should be compared with which network links.

At the highest level, simul_diagnostic is meant to take you from disjointed data to in-depth knowledge regarding where your simulations succeeds in replicating its target network, and where it doesn't.

.. mermaid:: ./mermaid/high_level.mmd

simul_diagnostic is made to be simulator agnostic, meaning as long as your inputs are formatted correctly, then it doesn't matter where they came from, but as of this moment we offer convenience methods for OSM and MATSim networks.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   install
   usage.ipynb
   workflows

.. autosummary::
   :caption: API
   :toctree: _autosummary
   :recursive:

   diagnostic
   map_matching

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
