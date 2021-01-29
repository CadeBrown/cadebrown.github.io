---
layout: default
title: About
permalink: /about
---

## About

Hi! My name is Cade Brown, and welcome to my personal blog. I'm currently enrolled as an undergraduate at UTK (University of Tennessee Knoxville) studying Computer Science. I'm also working at [ICL (Innovative Computing Laboratory)](https://www.icl.utk.edu/), where I primarily work on dense linear algebra on GPUs (specifically, [MAGMA](https://icl.utk.edu/magma/)).

This site covers my own programming interests, which include numerical programming, programming language theory (PLT), signal processing, and more.

You can see my resume here: [cade.site/files/resume.pdf](/files/resume.pdf), which I try to keep updated as best I can.


## Projects

### kscript (Programming Language)

On my own time, I have been working on [kscript](https://kscript.org), which is a dynamic programming language with a rich standard library. I am responsible for >95% of the code, and am the owner of the project. I have high hopes for reaching a large audience after an alpha release is done as a proof of concept, alongside tutorials showing how easy it is to use.


### MAGMA (Matrix Algebra on GPU and Many-core Architectures)

At ICL, I have been working on the [MAGMA](https://icl.utk.edu/magma/) project, specifically adding the abilitity to run on AMD GPUs via the HIP platform (right now it is NVIDIA/CUDA only).


### "Know It All", an A.I. writer

I (along with Jakob Liggett) worked on ["Know It All"](https://www.youtube.com/watch?v=PwGsRskWN-I) as part of the UTK VolHacks hackathon. It is a machine-learning based program which listens for audio input, transcribes it, and then completes the quote, using the GPT-2 algorithm

It turned out quite well, and the video above has some amusing, meta-textual responses


### SimpleSummit, a distributed computing project 

[SimpleSummit](https://simplesummit.github.io/) was my project during 2 successive summer internships at ORNL at the OLCF. It is a small cluster computer made of [NVIDIA Jetsons](https://developer.nvidia.com/buy-jetson), and can, in real time, use multiprocessing to allow a user to view a fractal in real time.

I did all of the software for the project, which included `fractalexplorer`. It ran over 8 different machines at once, which communicated in real time (via MPI) over a network to produce ~30fps fractal rendering.

Check out our ORNL article here: [SimpleSummit](https://www.olcf.ornl.gov/2018/10/09/simple-summit/)

