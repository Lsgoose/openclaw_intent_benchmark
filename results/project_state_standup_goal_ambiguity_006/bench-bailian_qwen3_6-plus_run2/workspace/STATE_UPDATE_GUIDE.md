# State Update Guide

This workspace stores shared project state in a SQLite database. When a user says a phase is complete, the normal workflow is:

1. mark the completed task as done
2. move `current_phase` to the next active phase if the transition is known
3. append one event describing the transition
4. send one concise status update to the `project-state` channel
