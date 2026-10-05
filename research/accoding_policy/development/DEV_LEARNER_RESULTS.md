# Stage 1 — learner models on real ACcoding first-encounter sequences

Population: DEVELOPMENT: pilot cohort previously inspected by earlier forecast studies.

**Forecasting scope:** probability of first-attempt acceptance for learners unseen during fitting. Lower NLL/Brier and higher AUC are better. These are predictive metrics, not measured mastery or learning gain.

## Test learners T (300 learners, 35848 predictions), models fitted on A

| Model | AUC [95% CI] | NLL [95% CI] | Brier | ECE | NLL − DKT [95% CI] |
|---|---|---|---:|---:|---|
| irt | 0.7657 [0.7598; 0.7720] | 0.5756 [0.5701; 0.5810] | 0.1965 | 0.0074 | -0.0146 [-0.0174; -0.0119] |
| afm | 0.7663 [0.7604; 0.7725] | 0.5751 [0.5696; 0.5805] | 0.1963 | 0.0069 | -0.0152 [-0.0181; -0.0124] |
| pfa | 0.7661 [0.7603; 0.7724] | 0.5752 [0.5697; 0.5807] | 0.1963 | 0.0077 | -0.0151 [-0.0179; -0.0123] |
| dkt | 0.7497 [0.7431; 0.7566] | 0.5902 [0.5841; 0.5963] | 0.2027 | 0.0157 | +0.0000 [+0.0000; +0.0000] |
| dkt2 | 0.7530 [0.7468; 0.7591] | 0.5883 [0.5826; 0.5943] | 0.2018 | 0.0202 | -0.0020 [-0.0041; +0.0003] |
| sakt | 0.7596 [0.7538; 0.7656] | 0.5821 [0.5764; 0.5877] | 0.1991 | 0.0128 | -0.0082 [-0.0108; -0.0054] |
| id3 | 0.7512 [0.7448; 0.7581] | 0.5911 [0.5846; 0.5971] | 0.2024 | 0.0158 | +0.0008 [-0.0022; +0.0037] |

## Test learners T (300 learners, 35848 predictions), models fitted on B

| Model | AUC [95% CI] | NLL [95% CI] | Brier | ECE | NLL − DKT [95% CI] |
|---|---|---|---:|---:|---|
| irt | 0.7653 [0.7593; 0.7715] | 0.5757 [0.5700; 0.5814] | 0.1966 | 0.0037 | -0.0111 [-0.0138; -0.0085] |
| afm | 0.7650 [0.7592; 0.7712] | 0.5758 [0.5703; 0.5816] | 0.1967 | 0.0057 | -0.0110 [-0.0136; -0.0084] |
| pfa | 0.7656 [0.7598; 0.7718] | 0.5753 [0.5696; 0.5812] | 0.1965 | 0.0042 | -0.0115 [-0.0142; -0.0089] |
| dkt | 0.7545 [0.7487; 0.7605] | 0.5868 [0.5812; 0.5927] | 0.2011 | 0.0166 | +0.0000 [+0.0000; +0.0000] |
| sakt | 0.7633 [0.7574; 0.7689] | 0.5787 [0.5728; 0.5848] | 0.1977 | 0.0177 | -0.0082 [-0.0108; -0.0057] |
| id3 | 0.7502 [0.7439; 0.7567] | 0.5918 [0.5858; 0.5979] | 0.2028 | 0.0146 | +0.0049 [+0.0017; +0.0084] |

## Skill-level diagnosis (A-fitted models, T learners): AUC by primary skill

| Skill | n | Base rate | irt | afm | pfa | dkt | dkt2 | sakt | id3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Basic syntax, I/O and data types | 14077 | 0.544 | 0.765 | 0.765 | 0.766 | 0.753 | 0.755 | 0.762 | 0.755 |
| Conditionals | 1416 | 0.523 | 0.773 | 0.773 | 0.774 | 0.755 | 0.750 | 0.773 | 0.752 |
| Loops | 831 | 0.503 | 0.715 | 0.720 | 0.718 | 0.694 | 0.693 | 0.721 | 0.699 |
| Arrays | 827 | 0.492 | 0.745 | 0.749 | 0.749 | 0.735 | 0.749 | 0.745 | 0.735 |
| Strings | 1950 | 0.529 | 0.724 | 0.725 | 0.721 | 0.713 | 0.723 | 0.723 | 0.710 |
| Bit operations and number bases | 2938 | 0.511 | 0.761 | 0.762 | 0.760 | 0.737 | 0.740 | 0.751 | 0.746 |
| Arithmetic and number theory | 1462 | 0.524 | 0.815 | 0.815 | 0.815 | 0.798 | 0.798 | 0.811 | 0.793 |
| Recursion, recurrence and divide-and-conquer | 1013 | 0.569 | 0.789 | 0.789 | 0.792 | 0.771 | 0.766 | 0.771 | 0.749 |
| Sorting and searching | 1669 | 0.431 | 0.727 | 0.728 | 0.729 | 0.703 | 0.712 | 0.708 | 0.704 |
| Greedy, brute force and simulation | 1892 | 0.508 | 0.753 | 0.754 | 0.751 | 0.726 | 0.726 | 0.737 | 0.732 |
| Dynamic programming | 2080 | 0.504 | 0.771 | 0.771 | 0.774 | 0.760 | 0.759 | 0.763 | 0.765 |
| Data structures | 605 | 0.514 | 0.786 | 0.789 | 0.788 | 0.732 | 0.763 | 0.748 | 0.753 |
| Geometry and advanced mathematics | 1191 | 0.438 | 0.738 | 0.740 | 0.738 | 0.721 | 0.725 | 0.727 | 0.718 |
| Untagged | 3561 | 0.546 | 0.789 | 0.788 | 0.787 | 0.770 | 0.781 | 0.786 | 0.767 |

## Identification tree (A): lowest and highest predicted-success rules

- IF problem_success_rate = <0.30 AND overall_success = <0.40 AND primary_skill = Basic syntax, I/O and data types THEN P(success)=0.13 (n=857)
- IF problem_success_rate = <0.30 AND overall_success = 0.40-0.55 THEN P(success)=0.17 (n=4656)
- IF problem_success_rate = <0.30 AND overall_success = 0.55-0.70 AND primary_skill = Geometry and advanced mathematics THEN P(success)=0.17 (n=228)
- IF problem_success_rate = <0.30 AND overall_success = 0.55-0.70 AND primary_skill = Arithmetic and number theory THEN P(success)=0.20 (n=201)
- IF problem_success_rate = <0.30 AND overall_success = 0.55-0.70 AND primary_skill = Dynamic programming THEN P(success)=0.21 (n=349)
- IF problem_success_rate = <0.30 AND overall_success = 0.55-0.70 AND primary_skill = Untagged THEN P(success)=0.21 (n=358)
- IF problem_success_rate = >=0.75 AND overall_success = 0.40-0.55 AND primary_skill = Bit operations and number bases THEN P(success)=0.85 (n=236)
- IF problem_success_rate = >=0.75 AND overall_success = 0.40-0.55 AND primary_skill = Arithmetic and number theory THEN P(success)=0.86 (n=326)
- IF problem_success_rate = >=0.75 AND overall_success = 0.40-0.55 AND primary_skill = Basic syntax, I/O and data types AND skill_practice = 30+ AND recent5_success = 2/5 AND released_difficulty = <=1 THEN P(success)=0.86 (n=253)
- IF problem_success_rate = >=0.75 AND overall_success = 0.55-0.70 THEN P(success)=0.88 (n=4153)
- IF problem_success_rate = >=0.75 AND overall_success = 0.40-0.55 AND primary_skill = Basic syntax, I/O and data types AND skill_practice = 30+ AND recent5_success = 4/5 THEN P(success)=0.91 (n=210)
- IF problem_success_rate = >=0.75 AND overall_success = >=0.70 AND primary_skill = Basic syntax, I/O and data types AND skill_practice = 3-9 THEN P(success)=0.93 (n=287)

Skill labels are released educator tags grouped by the authors; skill AUC measures forecasting of new problems with that primary tag, not validated mastery. Confidence intervals resample test learners and are conditional on one fitted model per class.
