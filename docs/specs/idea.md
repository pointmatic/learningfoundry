# learningfoundry - A knowledge learning generator

## Overview

I need a system that can generate learning content based on a given topic or set of topics. This system should be able to support curation of existing content as well as generation of new content, with assets in various formats (text, markdown,images, videos, and html pages).

The system should be configurable with learning pipeline templates that define the structure and content of the learning material, and content templates that define the format and flow of the content assets.

## Constraints
Learning foundry will be a PyPI package. The implementation of any curriculum will be done in its own application repository. 

### Curriculum Format
The system will support an ad hoc YAML format for defining learning pipelines and content templates. 

### Libraries
The system should integrate the following libraries (some are WIP):
- **lmentry**: unified interface for various LLM providers (see [features.md](lmentry/features.md))
- **quizazz**: generates quizzes and assessments (see [concept.md](quizazz/concept.md), [features.md](quizazz/features.md), [tech-spec.md](quizazz/tech-spec.md))
- **modelfoundry**: manages the mechanics of data preparation, model training, optimization, and evaluation and will be loosely based on a prior project (see [concept.md](modelfoundry/concept.md), [features.md](modelfoundry/features.md), [tech-spec.md](modelfoundry/tech-spec.md))
- **nbfoundry**: generates Marimo notebooks for experiential learning with Python, machine learning models, and data analysis (not implemented)
- **d3foundry**: generates D3.js visualizations for data exploration and analysis (not implemented)

### Stack
- Pyve (`brew install pointmatic/tap/pyve`, https://pointmatic.gihub.io/pyve)
  - Python 3.12 (latest stable)
  - micromamba backend
- SvelteKit (for frontend)

See [d802-curriculum-idea-statement.md](d802-curriculum-idea-statement.md) for a detailed use case for a deep learning curriculum.

### Dependency Specs
- Write dependency specs for each of the libraries listed above that will facilitate being able to orchestrate a cohesive learning experience.
- Identify complexity challenges that may need to be abstracted into additional libraries. 