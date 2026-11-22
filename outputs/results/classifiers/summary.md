# Aspect-level sentiment: class-imbalance study

Test pairs: 5,479 (all five domains). Values are mean ± standard deviation over seeds.

| Method | Seeds | Accuracy | Macro-F1 | Neutral F1 | Conflicting acc | ECE | ECE after T-scaling (T) | Models | Train (min) | ms/pair |
|---|---|---|---|---|---|---|---|---|---|---|
| No handling | 3 | 0.929 ± 0.005 | 0.746 ± 0.011 | 0.410 ± 0.027 | 0.734 ± 0.003 | 0.050 | 0.021 (1.90) | 1 | 8.1 | 0.77 |
| Class weights | 3 | 0.930 ± 0.000 | 0.756 ± 0.007 | 0.438 ± 0.019 | 0.737 ± 0.015 | 0.053 | 0.024 (2.00) | 1 | 8.1 | 0.78 |
| Random oversampling | 3 | 0.928 ± 0.001 | 0.750 ± 0.004 | 0.426 ± 0.016 | 0.743 ± 0.005 | 0.056 | 0.032 (2.20) | 1 | 10.1 | 0.78 |
| Focal loss | 3 | 0.932 ± 0.002 | 0.759 ± 0.013 | 0.445 ± 0.035 | 0.742 ± 0.008 | 0.025 | 0.014 (0.89) | 1 | 8.1 | 0.78 |
| Balanced bagging (ensemble) | 3 | 0.911 ± 0.001 | 0.725 ± 0.002 | 0.381 ± 0.005 | 0.682 ± 0.008 | 0.038 | 0.012 (1.42) | 5 | 13.6 | 2.97 |
| Balanced bagging (one member) | 3 | 0.902 ± 0.007 | 0.709 ± 0.010 | 0.349 ± 0.021 | 0.668 ± 0.022 | 0.064 | 0.031 (1.72) | 1 | 2.7 | 0.59 |
| LLM synthetic Neutral (verified) | 3 | 0.925 ± 0.004 | 0.736 ± 0.018 | 0.388 ± 0.051 | 0.724 ± 0.016 | 0.054 | 0.022 (1.88) | 1 | 12.5 | 1.18 |
| LLM synthetic Neutral (not verified) | 3 | 0.924 ± 0.001 | 0.723 ± 0.003 | 0.346 ± 0.009 | 0.718 ± 0.008 | 0.054 | 0.021 (1.94) | 1 | 13.0 | 1.19 |

Temperature scaling: one temperature T per model, fitted on the Dev set by minimising negative log-likelihood; predictions are unchanged, only confidences.

## Macro-F1 per domain (mean over seeds)

| Method | Books | Clothing | Hotel | Laptop | Restaurant |
|---|---|---|---|---|---|
| No handling | 0.696 | 0.708 | 0.910 | 0.764 | 0.762 |
| Class weights | 0.712 | 0.682 | 0.931 | 0.768 | 0.780 |
| Random oversampling | 0.705 | 0.663 | 0.920 | 0.768 | 0.771 |
| Focal loss | 0.712 | 0.690 | 0.926 | 0.771 | 0.785 |
| Balanced bagging (ensemble) | 0.696 | 0.680 | 0.906 | 0.727 | 0.747 |
| Balanced bagging (one member) | 0.659 | 0.669 | 0.900 | 0.719 | 0.731 |
| LLM synthetic Neutral (verified) | 0.669 | 0.679 | 0.902 | 0.770 | 0.757 |
| LLM synthetic Neutral (not verified) | 0.647 | 0.654 | 0.915 | 0.759 | 0.757 |

## McNemar test against Class weights (per seed)

| Method | Seed | Only this method correct | Only class weights correct | p |
|---|---|---|---|---|
| LLM synthetic Neutral (verified) | 42 | 77 | 107 | 0.0322 |
| LLM synthetic Neutral (verified) | 153 | 84 | 87 | 0.879 |
| LLM synthetic Neutral (verified) | 650 | 71 | 120 | 0.000482 |
| LLM synthetic Neutral (not verified) | 42 | 69 | 104 | 0.00954 |
| LLM synthetic Neutral (not verified) | 153 | 83 | 107 | 0.0949 |
| LLM synthetic Neutral (not verified) | 650 | 80 | 115 | 0.0147 |
| Balanced bagging (ensemble) | 42 | 53 | 161 | 7.47e-14 |
| Balanced bagging (ensemble) | 153 | 90 | 194 | 6.39e-10 |
| Balanced bagging (ensemble) | 650 | 64 | 163 | 3.83e-11 |
| Balanced bagging (one member) | 42 | 71 | 204 | 4.49e-16 |
| Balanced bagging (one member) | 153 | 93 | 211 | 1.07e-11 |
| Balanced bagging (one member) | 650 | 74 | 226 | 4.72e-19 |
| Focal loss | 42 | 70 | 45 | 0.0248 |
| Focal loss | 153 | 74 | 69 | 0.738 |
| Focal loss | 650 | 62 | 64 | 0.929 |
| No handling | 42 | 87 | 80 | 0.643 |
| No handling | 153 | 82 | 72 | 0.468 |
| No handling | 650 | 63 | 100 | 0.00466 |
| Random oversampling | 42 | 89 | 105 | 0.281 |
| Random oversampling | 153 | 92 | 100 | 0.614 |
| Random oversampling | 650 | 75 | 89 | 0.31 |

## 95% bootstrap intervals (seed 42)

| Method | Macro-F1 | Neutral F1 |
|---|---|---|
| No handling | 0.740 [0.709, 0.769] | 0.390 [0.305, 0.471] |
| Class weights | 0.764 [0.736, 0.790] | 0.459 [0.373, 0.536] |
| Random oversampling | 0.754 [0.723, 0.782] | 0.443 [0.357, 0.523] |
| Focal loss | 0.773 [0.742, 0.803] | 0.484 [0.393, 0.564] |
| Balanced bagging (ensemble) | 0.724 [0.695, 0.750] | 0.380 [0.298, 0.455] |
| Balanced bagging (one member) | 0.718 [0.688, 0.749] | 0.379 [0.291, 0.465] |
| LLM synthetic Neutral (verified) | 0.742 [0.713, 0.772] | 0.411 [0.324, 0.493] |
| LLM synthetic Neutral (not verified) | 0.727 [0.700, 0.754] | 0.356 [0.278, 0.436] |
