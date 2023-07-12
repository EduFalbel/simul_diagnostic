Workflows
=========

There are many ways in which to integrate simul_diagnostic into your simulation workflow, some examples will be given here.


*A priori* matching
-------------------

If your pipeline relies on converting a base network (such as OSM) into a network specific to your simulator (SUMO, MATSim) or if you use the same network repeatedly, then it might be worth it to run the detector map-matching *a priori*. This means that the matching is done on the base network, adding to it the tags 'forward_detector' and 'backward_detector', so it can then be passed throug the conversion process while retaining those attributes and/or be used repeatedly without having to re-run the matching process.

.. mermaid:: mermaid/a_priori.mmd

.. ATTENTION::
    Some conversion procedures may make it impossible to infer which way is 'forwards' and which is 'backwards' and thus demand more processing on the user's side. For example, going from an OSM network to a MATSim one using the `SupersonicOsmNetworkReader <https://github.com/matsim-org/matsim-libs/blob/master/contribs/osm/src/main/java/org/matsim/contrib/osm/networkReader/SupersonicOsmNetworkReader.java>`_  or `PT2MATSim <https://github.com/matsim-org/pt2matsim>`_ converters: OSM networks have only one link for two-way roads (denoted by setting the 'oneway' attribute to 0/False) while MATSim has one link per way. Unfortunately, the converters simply duplicate the link along with its attributes and then reverse the geometry of the duplicated link to indicate the flow goes the other way. This means that both links will contain the 'forward_detector' and 'backward_detector' attributes, and thus we cannot tell which is which. To overcome this particular issue, one could use the `SNMan tool <https://github.com/lukasballo/snman/>`_'s `export_to_xml` method with the `as_oneway_links` parameter set to `True` before feeding the OSM network to the converter, for example.

*A posteriori* matching
-----------------------
For one-off networks or simulations in which you want the size of the network file to be as small as possible, then it might be worth it to run the map-matching after the simulation or to simply output a detector-link lookup table as opposed to adding attributes to the network.
Another case where this is desirable is when you already have an established pipeline for building the network and/or running the simulation and don't want to mess with it by adding the map-matching in the middle.

.. mermaid:: mermaid/matsim_workflow.mmd