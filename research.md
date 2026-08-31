---
layout: page
title: "Research"
permalink: /research/
stripes: bangladesh
eyebrow: "What I work on"
lede: "Climate geoengineering, climate extremes, regional modelling and impacts, tropical meteorology, monsoon dynamics, and the data-analytic machinery that holds it together."
description: "Research interests of Kwesi A. Quagraine: stratospheric aerosol injection and climate extremes, regionally refined CESM downscaling, subtropical high-pressure indices, co-behaviour of climate processes, and West African monsoon dynamics."
---

My work is committed to **bridging advanced climate science** and **practical solutions for sustainable
development in a changing climate**. In practice that means five threads, each of which feeds the others.

## Stratospheric aerosol injection and climate extremes
{: #sai-extremes}

As a Visiting Scientist at the [NSF National Center for Atmospheric Research](https://ncar.ucar.edu/){:target="_blank"},
I work on what solar geoengineering does to climate extremes — not to the global mean, which is the easy
part, but to the tails that actually cause harm. It is also the question I am most often asked about in
my role as Chief Scientist of the CVF-V20, by governments that would be living with the consequences of
a deployment decision taken elsewhere.

The question I keep returning to is a comparative one: how does the *baseline* climate differ from a
geoengineering scenario, and how does that difference propagate into extremes? A deployment that
restores global-mean temperature can still redistribute heavy rainfall, lengthen dry spells, or move
the moisture that a monsoon depends on. Using the ARISE-SAI ensemble and CESM2, I have shown that
precipitation extremes across Africa respond in ways that a global-mean framing simply does not reveal.

> Cooling the planet and restoring its climate are not the same intervention. The difference lives in
> the extremes.

## Improving CESM-SAI models with regional refinement
{: #regional-refinement}

Imagine trying to understand the detail of a painting from a hundred metres away. That is roughly the
position we are in with current geoengineering models, which typically run at grid spacings around
100&nbsp;km. At that resolution the nuanced regional dynamics and localised impacts of stratospheric
aerosol injection are not so much uncertain as invisible.

To close the gap I use **dynamical downscaling via CESM regional refinement**, which raises spatial and
vertical resolution over a chosen region while keeping the global circulation coupled and consistent.
Refining the model this way lets us ask what an intervention would do to a specific district rather
than a continent — which is the only form in which the answer is any use to the people making
decisions about it. Getting this right is what turns climate intervention research from a global
thought experiment into something a national planner can interrogate.

## Subtropical high-pressure systems, and how to measure them
{: #high-pressure-index}

The subtropical highs sitting over the South Atlantic and the South Indian Ocean are among the
features that set where moisture goes over southern Africa. They are also awkward to talk about
precisely: descriptions of them are often qualitative, which makes it hard to say whether two
seasons, two decades or two models differ, and by how much.

So I have spent several years building indices that put a number on them. The first,
[a simple subtropical high-pressure system index over the South Atlantic](https://doi.org/10.1002/asl.1266){:target="_blank"}
(*Atmospheric Science Letters*, 2024), was deliberately simple: something reproducible from standard
fields rather than a bespoke diagnostic only its authors can compute. A companion study then applied
the same thinking on the other side of the continent,
[assessing the impact of the South Indian Ocean high-pressure system using a novel index](https://doi.org/10.1002/joc.70031){:target="_blank"}
(*International Journal of Climatology*, 2025), led by Kwesi T. Quagraine. Most recently,
[an index to characterize the South Indian Ocean high-pressure system and its variability](https://doi.org/10.1002/asl2.70056){:target="_blank"}
(*Atmospheric Science Letters*, 2026) turns the same instrument on how that system varies.

The point of an index is that it makes a system arguable. Once a high can be reduced to a defensible
number, you can track it through a reanalysis, test whether a model reproduces it, and ask what a
climate intervention would do to it — which is where this thread meets the geoengineering work
above.

## The co-behaviour of climate processes
{: #co-behaviour}

My PhD thesis asked how large-scale climate processes influence regional climate variability, and it
started from a frustration: we routinely evaluate processes one at a time, when the climate presents
them together.

Working with [Prof. Bruce Hewitson](https://tinyurl.com/Bruce-Hewitson){:target="_blank"},
[Dr Chris Jack](https://www.csag.uct.ac.za/author/cjack/){:target="_blank"} and [Dr Chris Lennard](https://www.csag.uct.ac.za/author/clennard/){:target="_blank"}, my
[thesis](http://hdl.handle.net/11427/33916){:target="_blank"} developed a novel approach to describe the
co-behaviour of climate processes over Southern Africa. It produced two papers in the *Journal of
Climate* — [a methodology to assess co-behaviour](https://doi.org/10.1175/JCLI-D-18-0689.1){:target="_blank"}
and an [interrogation of how well CMIP5 GCMs reproduce it](https://doi.org/10.1175/JCLI-D-19-0472.1){:target="_blank"} —
and, in time, the pressure-system indices above.

## The West African monsoon and rain-fed agriculture
{: #monsoon}

Before the PhD, [Prof. Nana Ama Browne Klutse](https://tinyurl.com/Ama-Browne){:target="_blank"}
supervised my MPhil, which sought [to understand the West African Monsoon jump and its implications
for rain-fed agriculture](https://tinyurl.com/quagraine-thesis){:target="_blank"}. The monsoon jump is a sharp
northward shift in the rainband, and its timing sets the planting season for a very large number of
farmers. That work is the reason I still care about onset, cessation and the reanalysis products we
use to characterise them — and why several of my papers land in journals that agronomists read.

![Regional climate change, flattened](/assets/img/climate-banner.jpg)

## Methods and tools

Across all of it: CESM2 and CESM regional refinement, CMIP5/CMIP6 and CORDEX ensembles, ARISE-SAI and
GLENS, reanalysis intercomparison, extreme-value and ETCCDI indices, clustering and self-organising
maps for circulation typing, and a lot of Python. Code lives on [GitHub](https://github.com/Akumenyi){:target="_blank"}.
