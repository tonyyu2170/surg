# Advisor Meeting Agenda — 2026-08-24

## Current Status

Diving deeper into the sub second fluctuations, trying to chase down where these claim’s data and models come from. Starting final report requirements

## Findings This Week

[Large Loads Task Force Meeting and Workshop](https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/llwg/lltf_april_meeting__technical_workshop_presentations_.pdf)

### Where the sub-second number actually comes from

* **Source \#1:** Tesla's slides in the Large Loads Task Force Meeting and Workshop slides.   
  * Nothing published, no data released, and **they are selling the battery pack** that supposedly fixes this  
  * Musk said “**10-20 MW shifts several times per second**” on a podcast once

![][image1]

* Google technical lead manager said “in batch-synchronous ML workloads running on dedicated ML clusters, we observed **power fluctuations in the tens of megawatts**”![][image2]  
* **Source \#2**: Academic paper ([Power Stabilization for AI Training Datacenters](https://arxiv.org/pdf/2508.14318))  
  * Aug 2025, **Microsoft \+ OpenAI \+ NVIDIA**, \~50 authors. Not a neutral study  
  * Each iteration in the training process has  
    * **Compute phase**, GPUs run at maximum capacity, high power  
    * **Communication phase**, GPUs stop calculating to share data across the network or write checkpoints, low power  
    * Stopping and starting causes swings   
  * The data: production telemetry   
    * Every single figure is normalised 0–1 with no absolute MW (or W) axis**.** You cannot read an amplitude off any plot in the paper  
    * Written by the operators themselves, no raw data released  
  * Findings:  
    * **FFT energy concentrated 0.2–3 Hz.**   
    * Swing amplitude grows **proportionally with GPU count** × per-GPU peak power → “tens of megawatts” inside one datacentre  
    * **GPUs are \>50% of server provisioned power** (their GB200 breakdown), so the GPU swing isn't much diluted by the rest of the server  
    * Participating nodes are co-located to form “**a majority of a datacenter, or even multiple datacenters in the same grid**”  
* **Source \#3:** paper released data in a github repo ([link](https://github.com/Ahmed-Elsayed95/High-resolution-AI-Data-Center-Training-Workloads-Dataset/tree/main))  
  * Data set has 32 real **AI training runs on H100/B200 nodes,** per-GPU power measured at at an effective \~10 Hz (the file says 50 Hz, but the sensor itself only updates every \~103 ms)  
    * H100 nodes:  
      * Intel Xeon 208 vCPU  
      * 8x H100 SXM (80GB VRAM)  
      * 1800 GB RAM  
    * B200 nodes:  
      * Intel Xeon 208 vCPU  
      * 8x B200 (180GB VRAM)  
      * 2900 GB RAM  
    * Fine tuned 1B, 3B, 8B param LLMs through LLaMA factory built on pytorch  
  * No data showed 0.2–3 Hz "measured" band from the section above, they all **cycle *slower*** (8.5–15.9 second periods, i.e. 0.06–0.12 Hz) analysis done with periodogram  
  * That's one 8-GPU node, one parallelism strategy, and also fine tuning a much smaller model (frontier models are trillions of parameters now)  
  * **Cross-GPU coherence within a node: p ≈ 0.994–0.995**,  independent confirmation that GPUs in a synchronized job move together   
* **Source \#4:** The [Annual and Peak Electricity Use: History and Future Projections](https://powering-intelligence.epri.com/annual-peak-use.html) EPRI paper  
  * Has a footnote saying “Despite relatively constant levels of output across minutes and hours, abrupt and large changes in load at second and sub-second timescales (that result from coordinated computing tasks stopping and starting) can have significant implications for operational reliability of the grid”  
  * Links to [**this 25k usd paper**](https://www.epri.com/research/products/3002033303) **😂😂😂**

### Does it average out with enough GPUs/across facility? 

* Kind of depends lol  
* AI training  
  * If GPUs are **synchronized** (like they typically are in training), aggregate load swing **amplitude increases**  
  * Same thing for across facility, ai training runs can **take a majority of a datacenter** or even multiple datacenters in the same grid  
* During **inference** though, requests **aren’t synchronized**, so both constructive and destructive interference can occur  
  * In this case across GPUs/across facility I’m guessing it **could** aggregate out with enough users. No real evidence about this though just my thoughts  
  * I’m wondering if MoE has an effect on this  
    * MoE took off late 2023-2024, now basically all frontier models/chinese models use MoE  
    * Every request doesn’t trigger all billions/trillions of params, only ones that fall under specific “experts” are fired  
    * More cause for variability in inference

### Does it average out with HVAC? 

* Nah  
* Isn’t exactly known what % of energy in a datacenter goes to hvac, storage, ai training, inference, daily utility, other cloud services etc. This also differs for different data centers  
  * But general idea can come from PUE (Power Usage Effectiveness) aggregates \= Total facility energy / IT Equipment energy  
  * Google ([link](https://datacenters.google/efficiency/)): **PUE \= 1.10** for 2026 2nd quarter, meaning \~91% goes to IT, \~9% goes to overhead  
  * Meta ([link](https://sustainability.atmeta.com/wp-content/uploads/2024/08/Meta-2024-Responsible-Business-Practices-Report-Index.pdf)): **PUE \= 1.08** for 2023, similar  
* Cooling has minutes-scale thermal inertia, so it physically **cannot track a 0.2–3 Hz swing**. It just sits there as a smooth baseline (compared to ai workloads).  
* Even if it could cooling uses too little energy of the data enter to have a reasonable impact

### Would a battery be fast enough?

* Yah  
* The band is 0.2–3 Hz, i.e. periods of **0.33 to 5 seconds**. Battery power electronics respond in **tens of milliseconds**; a full grid-forming response is \~250 ms.   
* Also tesla’s battery (Megapack) that they were selling literally handles this. Used at the xAI/SpaceX data center (Colossus supercluster) in Memphis, Tennessee

## Notes from meeting

* 