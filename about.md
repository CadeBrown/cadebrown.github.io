---
layout: default
title: About
permalink: /about/
---

## About

Hi! My name is Cade Brown, and welcome to my personal blog. I'm currently enrolled as an undergraduate at UTK (University of Tennessee Knoxville) studying Computer Science. I'm also working at [ICL (Innovative Computing Laboratory)](https://www.icl.utk.edu/), where I primarily work on dense linear algebra on GPUs (specifically, [MAGMA](https://icl.utk.edu/magma/)).

This site covers my own programming interests, which include numerical programming, programming language theory (PLT), signal processing, and more.


## Projects

### MAGMA (Matrix Algebra on GPU and Many-core Architectures)

At ICL, I have been working on the [MAGMA](https://icl.utk.edu/magma/) project, specifically adding the abilitity to run on AMD GPUs via the HIP platform (right now it is NVIDIA/CUDA only).


### "Know It All", an A.I. writer

I (along with Jakob Liggett) worked on ["Know It All"](https://www.youtube.com/watch?v=PwGsRskWN-I) as part of the UTK VolHacks hackathon. It is a machine-learning based program which listens for audio input, transcribes it, and then completes the quote, using the GPT-2 algorithm

It turned out quite well, and the video above has some amusing, meta-textual responses


### SimpleSummit, a distributed computing project 

[SimpleSummit](https://simplesummit.github.io/) was my project during 2 successive summer internships at ORNL at the OLCF. It is a small cluster computer made of [NVIDIA Jetsons](https://developer.nvidia.com/buy-jetson), and can, in real time, use multiprocessing to allow a user to view a fractal in real time.

I did all of the software for the project, which included `fractalexplorer`. It ran over 8 different machines at once, which communicated in real time (via MPI) over a network to produce ~30fps fractal rendering.

Check out our ORNL article here: [SimpleSummit](https://www.olcf.ornl.gov/2018/10/09/simple-summit/)


## Employment

Additionally, for reference, here is my (approximate) employment record:


### Research Assistant @ ICL (Summer 2019 - Present)

Since I've started attending UTK, I've worked at ICL (Innovative Computing Laboratory). Within ICL, I work under Dr. Stan Tomov in the Linear Algebra (LA) division. Our task has been porting and accelerating common LA operations on the new AMD HIP/ROCm stack.

### Intern @ ORNL (Summer 2016 - Summer 2017)

For 2 summers, I worked as an intern at ORNL (Oak Ridge National Laboratory). There, I helped write SimpleSummit ([https://simplesummit.github.io/](https://simplesummit.github.io/)), including the fractal rendering program, and the website


