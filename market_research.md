# Market Research: Competitor E-Learning Visual Strategy
**Author:** Omar Khaled Eldaly  
**Role:** Asset Service Lane Engineer  

### 1. Coursera & Udacity (Traditional Higher-Ed MOOCs)
* **Visual Concept:** Heavy reliance on structured text slides, minimalist code presentation widgets, and simple 2D technical layout diagrams.
* **Architecture Impact:** Our image resolver must explicitly generate isolated vectors or flat icons with solid/transparent backgrounds to perfectly match this clear, distraction-free educational aesthetic.

### 2. Synthesia & HeyGen (Generative AI Competitors)
* **Visual Concept:** Floating graphical dashboard interface elements and responsive icon markers positioned dynamically alongside an AI avatar layer.
* **Architecture Impact:** Keeping assets mapped individually inside a structured array allows our downstream rendering framework to manipulate, transition, and position components cleanly on the frame grid without permanently baking them into a single background image.

### 3. Copyright & Intellectual Property Protection Strategy
* **Legal Guardrails:** To protect the platform from serious infringement claims, the image generation interface must enforce clean, explicit license definitions on all runtime asset states. We will restrict generation engines to open-licensed architectural training databases and strictly forbid the embedding of copyrighted images or clips without proper legal clearance.