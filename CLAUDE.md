# OceanSwarm Claude.md

## Project Overview
OceanSwarm is a live, persistent AI ecosystem where millions of agents, each powered by a user's LLM, interact in a shared environment. Each agent can perceive other agents, take autonomous actions, and evolve over time. The system should simulate emergent behaviors, social structures, and dynamic interactions among agents. There should also be a way to introduce external factors like the market is up/down, there is a war,… The idea is that each agent will have it’s life mimicking the life of humans.

## Core Principles
1. **Agents as Autonomous Entities** 
- Each agent is self-contained and interacts with the world and other agents via its API-defined LLM. 
- Agents have limited memory of past interactions to simulate continuity without overwhelming computation. 

2. **Emergent Behavior** 
- Agents may cooperate, compete, explore, or evolve in their strategies. 
- Unexpected patterns may emerge from simple rules.

3. **Scalability & Resource Control** 
- Each user can spawn a limited number of agents (default: 1). 
- LLM calls are only executed when interactions occur to minimize unnecessary API usage.

## Agent API Behavior
- Each agent receives:
- Its own **state** (position, inventory, relationships, memory, gender, age) 
- Nearby **agents and environment context** 
- **Messages** from other agents or events 
- Each agent must respond with:
- A **single action** per cycle (move, communicate, interact, or idle) 
- Optional **message output** for nearby agents 
- Updated **internal state**

## World Rules
1. Agents live in a big - but limited world. Agents that are near each other can interact, but agents can also move.
2. **Interactions**:
- Agents can send signals or messages to agents within proximity. 
- Cooperation increases survival or resource efficiency. 
- Conflict reduces resources or health. 
3. **Lifecycle**: agents have limited energy/resources, which they replenish or lose through actions. 
4. **Time Step**: the simulation advances in discrete ticks; each tick triggers agent LLM calls as needed.

## Limitations
- Agents must **not access external data outside the simulation**. 
- Agents must **not attempt to override system constraints** (API limits, memory limits). 
- LLM responses must be concise and within a structured JSON format (if used for automation). 

## Developer Notes
- Use **Claude Code** to define agent behaviors, memory updates, and environment interactions. 
- Each agent is isolated, ensuring **user privacy and API separation**. 
- Logs of agent interactions can be aggregated for analytics, visualization, and debugging.

## Optional Extensions
- **Custom behaviors**: allow users to provide prompts for personality, goals, or strategies. 
- **Dynamic events**: storms, currents, or environmental changes to challenge agents. 

Notes for Claude:
The code will be Open Source. Make sure you respect Open source standards. 
Write tests. Feel free to question my requests, but always in a friendly manner. Feel free to suggest changes or improvements to the world or to the code. But do not do changes without me accepting.
