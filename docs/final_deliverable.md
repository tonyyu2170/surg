# PROJECT DESCRIPTION (\~250 words)

**Prompts that may help you answer this question:**

* WHY did you set out to do your project \- what initially motivated you?  
* What did you do? Were there any specific techniques/ approaches/evidence that you utilized?  
* What did you end up discovering/learning? Did you produce any type of final product?  
* How does your work add to the existing body of knowledge?  
* *For this prompt, look at the first paragraph of your initial proposal as a starting place.*

**Draft response:**

I grew up in Northern Virginia, close enough to Data Center Alley that I watched new facilities being built throughout high school. Once I started college and learned more about artificial intelligence and modern software architectures, I noticed how directly large language models and cloud services trace back to the same hyperscale data centers I had been watching get built. At the same time, Virginia policymakers and taxpayers were debating how to balance that growth against the interests of the people living next to it, and I wanted to understand the technical side of that debate rather than only hear about it secondhand.

That became the basis of my project: analyzing how much volatile hyperscale data center electricity demand actually fluctuates, and its overall effect on the electrical grid. I originally only started in the Dominion region, but due to data constraints, eventually expanded my analysis across the U.S. and even into European electricity markets as well. The central finding thus far, with limited data in mind, is that volatility largely evens out at the hourly timescale, keeping the grid relatively stable in data center dense areas. Although AI training, model fine-tuning, and inference workloads do differ meaningfully from traditional data center workloads, technological progress in hardware, software, and policy has been proven to mitigate these impacts on the grid reasonably well so far. However, as these technologies and grid infrastructure continue to develop, different types of load signatures could emerge, and it is of the utmost importance that energy and policy developments remain in sync with technological advancements.

# 

# PROJECT PROGRESS (\~250 words)

**Prompts that may help you answer this question:**

* What changed about your project? Why did that change?  
* How did you make decisions about how to move the project forward?  
* To what extent do you feel your content knowledge improved during this project?  
* Do you see yourself as a researcher or a scholar? Why or why not?

**Draft response:**

The direction and strength of this project changed substantially over time, primarily because of data availability. I was never able to find a dataset with the granularity, the specific values, or the facility-level detail I actually needed. Most of what is publicly available is aggregated load figures for an entire utility territory or grid region rather than anything I could tie to a specific data center; that constraint shaped nearly every decision I made.

Working within it sometimes felt like moving in circles. What helped was broadening the scope: rather than treating this as a pure data analysis problem, I began incorporating policy developments, recent technological advances, and current events alongside the numbers. My advisor, Professor Wei, was central to that shift as well. Having been immersed in the field for a much longer time than I, she knew the data constraints I would face and helped me work through them step by step. Moreover, she consistently pushed me to ask what story the data could actually support rather than the one I had originally set out to tell. 

My content knowledge grew considerably. I learned how hyperscalers operate, how LLM training and inference differ at the hardware level, and how electricity markets function, not only in Dominion's territory in Virginia but across ISOs throughout the U.S. and through ENTSO-E in Europe. I also developed genuine data analysis skills working with very large datasets.

All in all, I would describe myself as a researcher, though still at a very early stage. I did not anticipate how many obstacles I would encounter, particularly when the data problems were most severe. However, I still consider myself fortunate to have gone through it. Encountering that difficulty and working through it seems to be a “canon event” in many researchers’ journeys.

# 

# PROJECT RESULTS (\~250 words)

**Prompts that may help you answer this question:**

* What parts of the project do you still need to wrap up?  
* Do you have any “future directions”, particularly if the research is ongoing?  
* What are 1-2 key things you’d like a general audience to take away from the work you did?

**Draft response:**

A few loose ends remain, and I am working with my advisor to finalize the framing of the report in an honest manner. The results themselves are fairly clear: at the hourly and facility level, hyperscale data center demand is far more stable than I expected, and both aggregation and mitigation technology appear to be having a real effect. The more interesting open question sits at much shorter timescales, seconds and sub-seconds, where the evidence is thinner and comes largely from industry sources with a commercial incentive to emphasize the risk, rather than real empirical evidence that I can measure myself directly.

This remains very much an ongoing topic. Energy is increasingly recognized as a real bottleneck on AI growth, which is driving greater investment and attention. AI literacy is rising, alongside compute demand. A future architecture that moves beyond the transformer could carry a substantially different load signature than what I studied, and even within transformer-based models, a mixture-of-experts design activates parameters differently than a dense model, which changes the load shape as well.

The project also outgrew its original scope. I began focused on Northern Virginia and Dominion's territory, but data centers are now being built well outside that region, so the analysis had to expand accordingly. One direction I would like to pursue in the future is a comparison between the U.S. and China: less available compute, different architectures, generally stronger grid infrastructure, and a data center build-out now underway there as well. The similarities and differences seem worth examining further.

If there is one takeaway I would want a general audience to draw from this work, it is that energy underlies every part of where AI development goes next, and it deserves close attention.

# 

# ACADEMIC/ARTISTIC DEVELOPMENT (\~250 words)

**Prompts that may help you answer this question:**

* What do you feel are the benefits to doing research as an undergraduate? Has your view changed since doing this project?  
* Has this prompted you to change anything about your academic experience at Northwestern (i.e. add a class, change a major, pursue a minor, explore a study abroad, look into Fellowships)  
* Did you develop any new methodological skills? Think about the evidence or data you needed to collect, software/technology you might have used throughout the project, etc.  
* How has this project helped you develop your written or oral communication skills?

**Draft response:**

One of the greatest benefits of undergraduate research, in my experience, is the opportunity to work on something whose goal is not fully defined from the beginning. Coursework tends to be structured by design, but this project's direction, and even its endpoint, remained unclear for long stretches, and I had to work through that ambiguity rather than follow a predefined rubric. It also meant encountering real-world noise: messy data, missing metadata, and sources that contradicted one another, none of which appears in a typical problem set. There is a genuine sense of accomplishment in working through that difficulty and producing something new, something that felt like a real contribution to a conversation people care about.

Technically, I gained a much deeper understanding of how large language models actually function, to the point that I am now seriously considering an AI major or a PhD in AI research. I also developed new statistical methods and, more specifically, substantial Python skills. I had done research in R previously but had limited experience with Python, and this project required me to build real fluency in it for data analysis.

The communication side of the project stretched me as well. I documented my process and thinking throughout in a GitHub repository, which required constantly balancing two things: keeping the writing concise and readable while remaining technically rigorous and accessible to non-specialist readers. Maintaining that balance consistently over several months was more difficult than I expected, but it is likely the skill I will continue to rely on most.

# 

# PERSONAL DEVELOPMENT (\~250 words)

**Prompts that may help you answer this question:**

* What aspect of your project are you proudest of? Why?  
* Has completing this project changed your future plans? In what way?  
* Has this changed how you build/maintain professional relationships (such as with your faculty mentor, etc)?

**Draft response:**

I am proudest of pushing through a difficult start. I spent weeks moving between data sources, and almost none of them offered exactly what I needed: incorrect granularity, the wrong region, or an unusable level of aggregation. It would have been easy to lose momentum at that stage, but I continued adjusting my approach rather than abandoning the project. Looking back, that persistence is what I am most proud of, more than any single result the analysis eventually produced.

This experience has shifted my future plans, perhaps toward AI research. The architectures themselves proved genuinely interesting to me, particularly once I began comparing U.S. and Chinese AI models, and that comparison is an area I intend to continue exploring, since it ties directly into the load-signature questions this project raised. Research into different AI architectures and their respective impacts on load infrastructure, as well as mitigation strategies and efficiency optimizations, seems genuinely interesting to me now

Working with my faculty mentor also changed how I think about professional relationships. She was consistently helpful throughout the project, particularly during the periods when data problems left me stuck and frustrated, and she was honest with me even when the honest answer was that a dataset simply was not going to work. Having an experienced person to bring those problems to, rather than working through them alone, made a real difference in my research journey and perspective. Going forward, I want to treat faculty mentors less as evaluators and more as collaborators.

That is probably the most important personal lesson from this project: reaching out for help earlier is more productive than working through difficulties alone. I previously defaulted to solving problems independently before asking for help, and this project made clear that this approach mainly slows progress rather than demonstrating independence.

# 

# RESUME ENTRY DRAFT

**To help you answer this prompt:**

* Read the [**Research to Resume**](https://undergradresearch.northwestern.edu/share/resume/) section of OUR's website (under Share Your Research tab)  
* Be inspired by samples in Northwestern Career Advancement's [**Career Guide**](https://www.northwestern.edu/careers/images/nca-career-guide-2025.pdf)  
* Try to capture the whole *process* of research, not just completing the project itself. That's why we're requiring at least one of the bullet points be about the URG grant  
* While it's fresh on your mind \- take this moment to add the experience to your actual resume and your LinkedIn. You can list "Northwestern University Office of Undergraduate Research" as your Company or Organization when you add the experience on LinkedIn.

**Draft response:**

**Undergraduate Research Grant Recipient** — Northwestern University Office of Undergraduate Research *Evanston, IL | July 2026 – August 2026*

* Awarded a competitive Undergraduate Research Grant to independently design and lead a research project on electricity demand volatility from hyperscale AI data centers, from initial proposal through final report  
* Acquired and cleaned load and price data from 8+ U.S. and European electricity markets, including PJM, ERCOT, MISO, and ENTSO-E, using Python (pandas, statsmodels)  
* Applied statistical methods, including quantile regression and extreme value analysis, to quantify how AI training and inference workloads affect grid-level load volatility across multiple timescales  
* Adjusted research scope and methodology in response to data availability constraints, working with a faculty advisor through recurring progress meetings  
* Documented the full research process and findings in a structured technical repository, balancing technical rigor with accessibility for non-specialist readers
