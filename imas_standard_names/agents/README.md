# Workflows

This file is built to explain the different workflows, their design implementations and make notes for further workflows to be developed. These workflows are all designed with a human in the loop approach, with the goal in mind that the end user is to simply give the direction for the name instead of having to develop a standard name from scratch which fits into the data dictionary.

## AI review workflows

These workflows work on a 2 Tiered review system: AI-Review and Human-Review. The generating AI works on a feedback loop with an AI review agent, which gives standard names a preliminary score. When a batch of names has passed they are passed to human review. The human review can approve names for entry into the DD or select names for regeneration.


### Agent Loop Workflow
This workflow is designed to robustly generate a user inputed amount of names, by generating each name individually for the inputed quantity of names. 

### Agent List Generate Workflow
This workflow is designed to give AI more flexibility in generating standard names, allowing for better generation of standard names which are built on top of ScalarStandardNames. The models in this workflow generate the entire batch of standard names at once, allowing for generation of a vector and its components simultaneously.
