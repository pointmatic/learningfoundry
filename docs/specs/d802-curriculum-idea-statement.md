# Curriculum Concept Statement
## Deep Learning Essentials: Modern Practices with Classic Data
### D802 – Deep Learning | WGU MSCS, AI & Machine Learning

**Author:** Michael Smith | April 2026
**Document Type:** Curriculum Design Concept Statement
**Version:** 1.0 – Draft

---

## 1. Curriculum Philosophy

This curriculum teaches deep learning fundamentals through a modern, 2026 lens using the CIFAR-10 dataset — a classic benchmark that is small enough for rapid iteration on consumer hardware yet rich enough to demonstrate every concept from raw pixel ingestion through robustness evaluation. The deliberate use of a well-understood dataset shifts the learner's focus from data wrangling heroics to the core discipline: understanding *why* architectural and optimization choices produce the results they do.

The curriculum treats CIFAR-10 not as a competition to be won, but as a controlled laboratory. Accuracy ceilings are intentionally constrained by a small training subset (2,000 images), making optimization decisions consequential and visible. The learner's goal is not to chase state-of-the-art numbers but to develop intuition for the levers that move model performance — and to articulate that intuition clearly.

## 2. Target Audience & Prerequisites

**Audience:** Graduate-level learners in computer science, data science, or adjacent technical fields who are approaching deep learning as a new specialization.

**Assumed knowledge:**

- Python programming (comfortable writing functions, classes, and using third-party packages)
- Machine learning fundamentals (supervised learning, train/test splits, bias-variance tradeoff)
- Mathematical foundations (linear algebra: matrix operations, dot products; calculus: partial derivatives, chain rule)
- Basic statistics (mean, variance, distributions, probability)
- Jupyter Notebooks (cell execution, markdown, kernel management)
- Command line / shell basics (navigation, package installation, script execution)

## 3. Learning Objectives

The curriculum addresses three core competencies, mapped to D802 course standards:

| Competency | Description | Curriculum Coverage |
|---|---|---|
| 4125.1.1 | Applies Neural Network Architectures | Modules 3–8: Progressive architecture building from MLP through CNN across three frameworks |
| 4125.1.2 | Analyzes Deep Learning Models | Modules 9–11: Evaluation strategy, error analysis, robustness testing, and visualization |
| 4125.1.3 | Applies Techniques to Optimize Deep Learning | Modules 7–8, 10: Hyperparameter tuning, data augmentation, regularization, imbalance mitigation |

## 4. Dataset Strategy

### 4.1 CIFAR-10 Training Subset

**Source:** Kaggle CIFAR-10 competition dataset, `train` split only (50,000 labeled images, 10 classes).

**Working subset:** 2,000 images — 200 per class, stratified random sample. This size is chosen to:

- Enable full training runs on CPU in under 5 minutes per experiment
- Make optimization choices visually impactful (small data amplifies the effect of augmentation, regularization, and architecture changes)
- Keep data preparation tractable as a learning exercise, not a logistics exercise

**Held-out evaluation set:** From the remaining 48,000 labeled images, a separate 1,000-image balanced evaluation set (100 per class) serves as the "unseen" test data. This avoids the Kaggle test split's obfuscation issue entirely.

**Imbalance experiment set:** A deliberately skewed variant of the 2,000-image subset where 2–3 classes are undersampled (e.g., 50 images instead of 200). Used exclusively in the imbalance mitigation module.

### 4.2 CIFAR-10-C Corruption Subset

Rather than generating all 20 corruption types at 5 severity levels, the curriculum uses a representative slice:

| Category | Corruption | Rationale |
|---|---|---|
| Noise | Gaussian noise | Most common sensor noise; intuitive to learners |
| Blur | Motion blur | Strong real-world analogy (moving cameras, vehicles) |
| Weather | Fog | Connects to autonomous systems, outdoor deployment |
| Digital | JPEG compression | Universal in web/mobile image pipelines |

Each corruption is applied at 3 severity levels (1, 3, 5 — mild, moderate, severe), providing 12 corruption variants per image. Applied to the 1,000-image evaluation set, this yields 12,000 corrupted evaluation images — enough to chart degradation curves without excessive generation time.

The curriculum acknowledges the full CIFAR-10-C scope (20 types × 5 levels) and frames the subset as a principled sampling strategy, not a shortcut.

### 4.3 Data Splits Summary

| Split | Size | Source | Purpose |
|---|---|---|---|
| Training | 2,000 (200/class) | CIFAR-10 train | Model training |
| Validation | Split from training (e.g., 80/20) | CIFAR-10 train | Training-time monitoring |
| Test | 1,000 (100/class) | CIFAR-10 train (held out) | Final evaluation |
| Test-C | 12,000 | Generated from test set | Robustness evaluation |
| Imbalanced variant | 2,000 (skewed) | CIFAR-10 train | Imbalance experiment |

## 5. Framework Progression

The curriculum builds the same classification task three times, using three frameworks in deliberate sequence. Each repetition reinforces abstract concepts while exposing the learner to tools they will encounter in different professional contexts.

### Phase 1: Scikit-learn — The Glass Ceiling

**Tool:** `sklearn.neural_network.MLPClassifier`

The learner builds a basic multi-layer perceptron with minimal code. The model hits a performance ceiling quickly (~55% accuracy on the 2K subset) because Scikit-learn offers no convolutional layers, no GPU acceleration, and limited control over training dynamics. This ceiling is the point: it creates a felt need for more expressive tools.

**Professional context:** Rapid prototyping, baseline establishment, integration with Scikit-learn's broader ML pipeline (preprocessing, metrics, cross-validation).

### Phase 2: PyTorch — Full Control

**Tool:** PyTorch (standalone, no higher-level wrapper)

The learner rebuilds the model from tensors up: defining layers, writing a training loop, managing the optimizer, and computing loss manually. This is where the curriculum's core deep learning content lives — backpropagation, gradient descent, computation graphs, and architecture design are all tangible here.

The progression within PyTorch: simple MLP (~55–60%) → basic CNN (~70–75%) → deeper CNN with augmentation and tuning (~80–85%).

**Professional context:** Research, experimentation, custom architectures, the dominant framework in academia and increasingly in industry.

### Phase 3: Keras — Backend Flexibility & Enterprise Readiness

**Tool:** Keras 3.x with configurable backend (PyTorch or TensorFlow)

The learner rebuilds the same CNN using Keras's high-level API, then switches backends to observe that the same model definition runs on either PyTorch or TensorFlow. This demystifies the framework landscape and prepares the learner for enterprise environments where framework choice may be dictated by infrastructure.

**Professional context:** Production deployment, Google Cloud ML pipelines, team environments where readability and standardization matter, legacy Keras 2 → 3 migration scenarios.

## 6. Module Overview

The curriculum is organized into 12 modules across four phases. Modules within a phase share thematic continuity, and each module is self-contained enough to be entered independently (with pre-assessment gating).

### Phase A: Foundations (Modules 1–3)

| # | Title | Core Topic | Framework | D802 Task Alignment |
|---|---|---|---|---|
| 1 | The Deep Learning Landscape | What deep learning is, where it's used, how to scope a project | — | Task 1 |
| 2 | Meeting the Data | CIFAR-10 exploration, cleaning, normalization, train/val/test splitting | NumPy, Pandas, Matplotlib | Task 2 |
| 3 | Your First Neural Network | MLP with Scikit-learn; hitting the ceiling; motivating CNNs | Scikit-learn | Tasks 1, 3 |

### Phase B: Architecture (Modules 4–6)

| # | Title | Core Topic | Framework | D802 Task Alignment |
|---|---|---|---|---|
| 4 | Tensors, Gradients, and Training Loops | PyTorch fundamentals; autograd; building an MLP from scratch | PyTorch | Task 3 |
| 5 | Seeing with Convolutions | Conv layers, pooling, feature maps; why spatial structure matters | PyTorch | Task 3 |
| 6 | Building a CNN That Learns | Full CNN implementation; model summary interpretation; parameter counting | PyTorch | Task 3 |

### Phase C: Optimization (Modules 7–9)

| # | Title | Core Topic | Framework | D802 Task Alignment |
|---|---|---|---|---|
| 7 | The Optimization Toolkit | Loss functions, optimizers (SGD → Adam), learning rate scheduling, batch size effects | PyTorch | Tasks 3, 4 |
| 8 | Tuning and Regularization | Hyperparameter search (grid, random, Bayesian); dropout; weight decay; early stopping | PyTorch | Tasks 3, 4 |
| 9 | Data Augmentation and the Imbalance Problem | Augmentation pipelines; deliberate imbalance experiment; mitigation techniques | PyTorch | Tasks 2, 4 |

### Phase D: Evaluation & Deployment (Modules 10–12)

| # | Title | Core Topic | Framework | D802 Task Alignment |
|---|---|---|---|---|
| 10 | Evaluating What You Built | Metrics, confusion matrices, loss/accuracy curves, error analysis | PyTorch | Task 4 |
| 11 | Robustness Under Pressure | CIFAR-10-C corruptions; degradation curves; real-world reliability framing | PyTorch | Task 4 |
| 12 | Keras, Deployment, and the Bigger Picture | Keras 3 rebuild; backend switching; deployment considerations; ethics; capstone reflection | Keras | Tasks 3, 4 |

## 7. Module Structure Template

Every module follows a consistent structure:

### Pre-Module Assessment (5 minutes)
3–5 targeted questions probing the module's core concepts. Learners who score above a threshold (e.g., 80%) may skip the didactic portion and proceed directly to the experiential section. This respects the time of learners with prior knowledge while ensuring coverage for those who need it.

### Didactic Portion (15–20 minutes, or 45–60 minutes for dense topics)
A guided narrative combining:

- **Reading:** Concise explanatory text with inline code snippets and mathematical notation where appropriate
- **Visual:** Diagrams, architecture illustrations, and annotated matplotlib outputs
- **Audio-visual:** Short embedded video segments (2–5 minutes) demonstrating key concepts — e.g., an animation of gradient descent on a loss surface, or a walkthrough of feature map activations
- **Interactive:** Inline widgets or notebook cells where the learner manipulates a parameter and observes the effect in real time (e.g., slider for learning rate, toggle for augmentation on/off)

Dense topics (backpropagation, optimization landscapes, the convolution operation) are split across multiple modules using a "divide and conquer" approach: each module addresses one facet, and integration happens in a subsequent module. For example, Module 4 introduces autograd mechanically, Module 5 applies it to convolutions, and Module 7 examines how optimizer choice interacts with gradient flow.

### Experiential Portion (20–40 minutes)
A Jupyter notebook exercise where the learner:

1. Modifies and runs code (not just reads it)
2. Answers embedded checkpoint questions
3. Produces a specific artifact (a plot, a trained model, a comparison table)

### Post-Module Assessment (5 minutes)
3–5 questions mirroring the pre-assessment in structure but testing for deeper understanding. Comparison of pre/post scores provides a self-reported learning signal.

## 8. Real-World Application Threads

Each module connects its technical content to at least one concrete application scenario. These are woven through the curriculum as recurring narrative threads, not isolated anecdotes:

- **Manufacturing quality inspection:** A factory floor camera system classifying parts as defective or acceptable. Connects to data augmentation (varying lighting/angles), robustness (fog = dust, motion blur = conveyor speed), and imbalance (defects are rare).
- **Wildlife monitoring:** Trail cameras classifying animal species. Connects to CIFAR-10's animal classes directly, plus robustness under weather corruptions.
- **Content moderation at scale:** Automated image categorization for a media platform. Connects to deployment, ethical considerations, bias in classification errors, and the business cost of false positives vs. false negatives.
- **Mobile/edge deployment:** Running a model on a phone or IoT device. Connects to model complexity, parameter counts, and the tradeoff between accuracy and inference speed.

## 9. Assessment Design

### Pre/Post Module Assessments
- Format: Multiple choice, fill-in-the-blank, short conceptual explanations
- Delivery: Embedded in the Jupyter notebook or a companion quiz interface
- Skip logic: Pre-assessment score ≥ 80% unlocks the option to skip the didactic portion

### Experiential Checkpoints
- Embedded in notebooks as assertions, visual comparisons, or short-answer cells
- Designed to catch misunderstandings before they compound in later modules

### Stretch Goal: LLM-as-Judge "Teach Me" Exercises
Selected modules include an optional "explain this concept in your own words" prompt where the learner's explanation is evaluated against a rubric by an LLM. Noted as a design feature for future implementation; not included in the initial deliverable due to the requirement for a locally-runnable open-weights model, which is out of scope for the current timeline.

## 10. Technical Requirements

### Minimum System
- Python 3.10+
- CPU with 8GB RAM
- 2GB disk space for datasets and environments

### Recommended
- NVIDIA GPU with CUDA support (any modern consumer GPU)
- 16GB RAM

### Software Stack
- **Environment:** Jupyter Lab
- **Core frameworks:** Scikit-learn, PyTorch, Keras 3.x, TensorFlow (as Keras backend option)
- **Data & visualization:** NumPy, Pandas, Matplotlib
- **Interpretability (optional/stretch):** pytorch-grad-cam (jacobgil)
- **Package management:** pip with requirements.txt; optional conda environment file

### CPU Accommodation
All training exercises are designed to complete in under 5 minutes on CPU with the 2K subset. Modules note where GPU acceleration would matter at production scale and provide optional "try it bigger" exercises for learners with GPU access (e.g., training on 10K or 50K images to observe the accuracy difference).

## 11. Performance Expectations

Given the 2K training subset, approximate accuracy targets across the curriculum arc:

| Stage | Architecture | Expected Accuracy (2K) | Notes |
|---|---|---|---|
| Baseline | Scikit-learn MLP | ~45–55% | Ceiling demonstration |
| First CNN | Basic 2-layer CNN (PyTorch) | ~60–70% | Architecture improvement |
| Optimized CNN | Deeper CNN + augmentation + tuning | ~75–85% | Optimization payoff |
| Keras rebuild | Same architecture in Keras | ~75–85% | Framework equivalence |
| Full dataset comparison | Same optimized CNN on 50K | ~88–92% | Data volume impact |

These ranges are approximate and intentionally wide. The curriculum frames the *trajectory* (each stage meaningfully better than the last) as the learning outcome, not any specific number.

## 12. Stretch Goals & Future Work

- **LLM-as-judge assessments:** Integrate a locally-runnable model for "teach me" evaluation exercises
- **pytorch-grad-cam integration:** Add an interpretability module using Grad-CAM visualizations to show *what* the model attends to, connecting to error analysis and debugging
- **Transfer learning module:** Fine-tuning a pretrained model (e.g., ResNet-18) on the CIFAR-10 subset to demonstrate modern practice and contrast with training from scratch
- **Interactive corruption explorer:** A notebook widget where learners apply corruptions in real time to individual images and observe classification confidence changes

## 13. Alignment to D802 Task Requirements

| D802 Task | Key Requirements | Curriculum Modules |
|---|---|---|
| Task 1 | Introduction, objectives, architecture justification, end goal | 1, 3, 5 |
| Task 2 | Data cleaning, preprocessing, normalization, augmentation, splits, GitLab | 2, 9 |
| Task 3 | Neural network creation, model summary, layers, parameters, hyperparameter tuning | 4, 5, 6, 7, 8, 12 |
| Task 4 | Evaluation, early stopping, visualizations, overfitting, metrics, augmentation impact, imbalance, error analysis, deployment, ethics | 7, 8, 9, 10, 11, 12 |

---

*This concept statement serves as the guiding design document for curriculum development. Individual module designs, notebook content, and assessment items will be developed in subsequent iterations.*
