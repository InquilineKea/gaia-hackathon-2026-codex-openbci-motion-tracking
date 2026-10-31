# Preliminary source-checked findings for Gemini review

This follow-up audits336 prior graph treatment variants and adds384 numerical controls of the same old graph specimens. No new seed replication, chemistry simulation, physical calibration or stationary-ensemble validation. The source scope and acceptance criteria are in PROTOCOL.md; raw output and retrieved-source hashes are checked before analysis.

## Execution and exact reproduction

{
  "graphs_audited": 336,
  "mechanical_cases": 384,
  "all_converged": true,
  "eligible_cases": 376,
  "max_force_residual": 3.717536851272074e-10,
  "maximum_uncapped_rate_argument": 1.0460191265713112,
  "total_cap_steps": 0,
  "total_cap_edge_updates": 0,
  "elapsed_graph_audit": 503.57369901399943,
  "elapsed_controls": 857.4447686720014,
  "four_seeds_not_new_replication": true
}

{
  "reference_rows_checked": 144,
  "unique_case_keys": 128,
  "maximum_G0_difference": 0.0,
  "maximum_retention_difference": 0.0
}

## Time-step gate

{
  "comparisons": 96,
  "eligible_comparisons": 96,
  "ineligible_comparisons": 0,
  "eligible_failures": 0,
  "threshold_retention": 0.0001,
  "max_fine_difference": 9.605113592991987e-05,
  "max_coarse_difference": 0.0002938491225478179,
  "worst_eligible": [
    {
      "L": 24,
      "z_target": 3.2,
      "seed": 74003,
      "arm": 0,
      "kappa": 0.03,
      "r": 0.5,
      "rate_beta": 10.0,
      "G0": 0.013998711261744349,
      "eligible": true,
      "retention_dt1": 0.8033468686120276,
      "retention_dt05": 0.8031490706254097,
      "retention_dt025": 0.8030530194894798,
      "fine_difference": 9.605113592991987e-05,
      "coarse_difference": 0.0002938491225478179,
      "meets_predeclared_0001": true
    },
    {
      "L": 24,
      "z_target": 3.2,
      "seed": 74003,
      "arm": 2,
      "kappa": 0.03,
      "r": 0.5,
      "rate_beta": 10.0,
      "G0": 0.014396930148296164,
      "eligible": true,
      "retention_dt1": 0.7983128936876095,
      "retention_dt05": 0.7981162082441078,
      "retention_dt025": 0.7980207103705074,
      "fine_difference": 9.549787360041417e-05,
      "coarse_difference": 0.00029218331710212375,
      "meets_predeclared_0001": true
    },
    {
      "L": 24,
      "z_target": 3.2,
      "seed": 74002,
      "arm": 1,
      "kappa": 0.03,
      "r": 0.5,
      "rate_beta": 10.0,
      "G0": 0.01657894847737342,
      "eligible": true,
      "retention_dt1": 0.7835420654346436,
      "retention_dt05": 0.7833464523332195,
      "retention_dt025": 0.7832515116299757,
      "fine_difference": 9.494070324378434e-05,
      "coarse_difference": 0.00029055380466780356,
      "meets_predeclared_0001": true
    },
    {
      "L": 24,
      "z_target": 3.2,
      "seed": 74001,
      "arm": 1,
      "kappa": 0.03,
      "r": 0.5,
      "rate_beta": 10.0,
      "G0": 0.011090523154047635,
      "eligible": true,
      "retention_dt1": 0.7831255864026136,
      "retention_dt05": 0.7829314273493554,
      "retention_dt025": 0.7828371951810051,
      "fine_difference": 9.423216835025006e-05,
      "coarse_difference": 0.0002883912216085083,
      "meets_predeclared_0001": true
    },
    {
      "L": 24,
      "z_target": 3.2,
      "seed": 74001,
      "arm": 0,
      "kappa": 0.03,
      "r": 0.5,
      "rate_beta": 10.0,
      "G0": 0.012739031757562932,
      "eligible": true,
      "retention_dt1": 0.7769804391621846,
      "retention_dt05": 0.7767866082819752,
      "retention_dt025": 0.7766925437415314,
      "fine_difference": 9.406454044380563e-05,
      "coarse_difference": 0.00028789542065321694,
      "meets_predeclared_0001": true
    },
    {
      "L": 24,
      "z_target": 3.2,
      "seed": 74003,
      "arm": 1,
      "kappa": 0.03,
      "r": 0.5,
      "rate_beta": 10.0,
      "G0": 0.014425943950115207,
      "eligible": true,
      "retention_dt1": 0.784691833222347,
      "retention_dt05": 0.7845004738170219,
      "retention_dt025": 0.7844075774667815,
      "fine_difference": 9.289635024045673e-05,
      "coarse_difference": 0.0002842557555655656,
      "meets_predeclared_0001": true
    },
    {
      "L": 24,
      "z_target": 3.2,
      "seed": 74002,
      "arm": 0,
      "kappa": 0.03,
      "r": 0.5,
      "rate_beta": 10.0,
      "G0": 0.017481388205876306,
      "eligible": true,
      "retention_dt1": 0.7731441222717432,
      "retention_dt05": 0.7729529024005277,
      "retention_dt025": 0.7728601100031545,
      "fine_difference": 9.279239737325362e-05,
      "coarse_difference": 0.0002840122685887625,
      "meets_predeclared_0001": true
    },
    {
      "L": 24,
      "z_target": 3.2,
      "seed": 74001,
      "arm": 2,
      "kappa": 0.03,
      "r": 0.5,
      "rate_beta": 10.0,
      "G0": 0.015391407223675395,
      "eligible": true,
      "retention_dt1": 0.7754336134659144,
      "retention_dt05": 0.7752488570306388,
      "retention_dt025": 0.7751591876519107,
      "fine_difference": 8.966937872811886e-05,
      "coarse_difference": 0.00027442581400372035,
      "meets_predeclared_0001": true
    }
  ]
}

Interpret the threshold in absolute retention fraction; multiply by100 to obtain percentage points. Passing .05 versus.025 does not prove the dt->0 limit or physical validity. Rate-beta0 controls only use dt.1; the new fine-step comparisons cover beta10. Ineligible matched pairs must stay separate from convergence failures. Compare within-seed treatment contrasts at common dt, not individual-case errors from unrelated settings.

## Graph observations

All336 prior hashes and full triangle-arm degree sequences matched. Nine variants (seven distinct edge masks) have both old directional winding flags but no rank-two component. L24/z3.2/seed74000/hub is one example: giant378nodes/921edges with primitive winding vector(1,-1), rank1. The old flags retain their declared meaning; rank differs from biconnectivity and mechanical rigidity. Primitive winding normalization preserves span rank, not integer subgroup index.

At L24,z4.8, mean hub degree histogram k0..6 is[77.25,11.75,15.5,13.5,16,33.25,408.75] nodes out of576. Intermediate degrees remain. Exact giant-component mean degree averages5.546304 compared with uniform4.802083; giant bending counts1310.75 versus1108.75. Changes in isolation, density and bending remain inseparable. No finite histogram proves thermodynamic condensation or a growing preferential-attachment mechanism.

## Paired retention contrasts

[
  {
    "z_target": 3.2,
    "kappa": 0.003,
    "contrast": "hub_minus_uniform",
    "n_dt0.1": 4,
    "mean_dt0.1": -0.42639730740129783,
    "paired_values_dt0.1": [
      -0.40173906925328495,
      -0.43327995833651933,
      -0.42505921951483694,
      -0.4455109825005501
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": -0.4262448412554639,
    "paired_values_dt0.05": [
      -0.4015620623061673,
      -0.43313102308687734,
      -0.42490786890864374,
      -0.44537841072016726
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": -0.4261704718209528,
    "paired_values_dt0.025": [
      -0.4014757984594759,
      -0.4330583638747695,
      -0.42483404981037687,
      -0.44531367513918896
    ],
    "max_paired_fine_change": 8.626384669141451e-05
  },
  {
    "z_target": 3.2,
    "kappa": 0.003,
    "contrast": "triangle_high_minus_low",
    "n_dt0.1": 4,
    "mean_dt0.1": 0.004635314439623672,
    "paired_values_dt0.1": [
      -0.005279443836732067,
      0.005985648079057437,
      0.027429019390774245,
      -0.009593965874604926
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": 0.0046392905288741015,
    "paired_values_dt0.05": [
      -0.005284889421232397,
      0.005996342144024447,
      0.027451660983688564,
      -0.009605951590984207
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": 0.00464123081064402,
    "paired_values_dt0.025": [
      -0.0052875212689666995,
      0.006001588719265927,
      0.02746263335375798,
      -0.009611777561481127
    ],
    "max_paired_fine_change": 1.0972370069417536e-05
  },
  {
    "z_target": 3.2,
    "kappa": 0.03,
    "contrast": "hub_minus_uniform",
    "n_dt0.1": 4,
    "mean_dt0.1": -0.2555360743774774,
    "paired_values_dt0.1": [
      -0.21717379080093835,
      -0.2551658592890359,
      -0.2535923737732395,
      -0.2962122736466958
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": -0.25533207797014923,
    "paired_values_dt0.05": [
      -0.21699520064544475,
      -0.254955918867673,
      -0.2533848303654048,
      -0.29599236200207446
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": -0.2552329362317506,
    "paired_values_dt0.025": [
      -0.2169084458488264,
      -0.2548539149065995,
      -0.2532839679730856,
      -0.29588541619849085
    ],
    "max_paired_fine_change": 0.0001069458035836135
  },
  {
    "z_target": 3.2,
    "kappa": 0.03,
    "contrast": "triangle_high_minus_low",
    "n_dt0.1": 4,
    "mean_dt0.1": 0.0028329075031703066,
    "paired_values_dt0.1": [
      -0.0038748729047295427,
      0.0076919729366992096,
      0.021135590445974017,
      -0.013621060465262458
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": 0.002828996096055858,
    "paired_values_dt0.05": [
      -0.00386856870788288,
      0.007682570318716553,
      0.021117717200475616,
      -0.013615734427085857
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": 0.002827093782586859,
    "paired_values_dt0.025": [
      -0.0038655196363899247,
      0.007678007529094422,
      0.02110902014136884,
      -0.0136131329037259
    ],
    "max_paired_fine_change": 8.697059106776983e-06
  },
  {
    "z_target": 4.0,
    "kappa": 0.003,
    "contrast": "hub_minus_uniform",
    "n_dt0.1": 4,
    "mean_dt0.1": -0.15375163350460472,
    "paired_values_dt0.1": [
      -0.1567886421447593,
      -0.19750324817616915,
      -0.12939818305762374,
      -0.13131646063986668
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": -0.15364162182297944,
    "paired_values_dt0.05": [
      -0.1566768097852299,
      -0.19735099354772423,
      -0.12931021744497262,
      -0.131228466513991
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": -0.15358815373968687,
    "paired_values_dt0.025": [
      -0.15662245684933018,
      -0.19727702511504197,
      -0.1292674449913076,
      -0.13118568800306774
    ],
    "max_paired_fine_change": 7.396843268225872e-05
  },
  {
    "z_target": 4.0,
    "kappa": 0.003,
    "contrast": "triangle_high_minus_low",
    "n_dt0.1": 4,
    "mean_dt0.1": -0.004772503132468492,
    "paired_values_dt0.1": [
      -0.012866458782499146,
      -0.001960763515121533,
      -0.01229273942577358,
      0.008029949193520292
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": -0.004768446998029696,
    "paired_values_dt0.05": [
      -0.012858747029659057,
      -0.0019590128042653587,
      -0.012280564124442894,
      0.008024535966248525
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": -0.004766475968126932,
    "paired_values_dt0.025": [
      -0.012854991808956218,
      -0.0019581635831874555,
      -0.012274654306951294,
      0.008021905826587239
    ],
    "max_paired_fine_change": 5.9098174916005775e-06
  },
  {
    "z_target": 4.0,
    "kappa": 0.03,
    "contrast": "hub_minus_uniform",
    "n_dt0.1": 4,
    "mean_dt0.1": -0.10537589450683216,
    "paired_values_dt0.1": [
      -0.11377467006176623,
      -0.10874185646629109,
      -0.10887473198397968,
      -0.09011231951529164
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": -0.10528675661553585,
    "paired_values_dt0.05": [
      -0.11367877446427876,
      -0.10865341270822204,
      -0.1087826100416247,
      -0.0900322292480179
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": -0.10524348332229957,
    "paired_values_dt0.025": [
      -0.11363222492569558,
      -0.10861046512187567,
      -0.10873787996664608,
      -0.08999336327498098
    ],
    "max_paired_fine_change": 4.654953858318489e-05
  },
  {
    "z_target": 4.0,
    "kappa": 0.03,
    "contrast": "triangle_high_minus_low",
    "n_dt0.1": 4,
    "mean_dt0.1": 0.002851598732679095,
    "paired_values_dt0.1": [
      -0.002956113878072486,
      0.0015284603627784277,
      0.003326601720284872,
      0.009507446725725566
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": 0.0028496267884126625,
    "paired_values_dt0.05": [
      -0.0029531534325173414,
      0.0015278240447444968,
      0.0033236094693037677,
      0.009500227072119727
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": 0.0028486644072363843,
    "paired_values_dt0.025": [
      -0.002951718997061037,
      0.001527513141453718,
      0.0033221521211478366,
      0.00949671136340502
    ],
    "max_paired_fine_change": 3.5157087147075217e-06
  },
  {
    "z_target": 4.8,
    "kappa": 0.003,
    "contrast": "hub_minus_uniform",
    "n_dt0.1": 4,
    "mean_dt0.1": -0.01939098673472542,
    "paired_values_dt0.1": [
      -0.017265310156626135,
      -0.02738154657302383,
      -0.017274128717077675,
      -0.015642961492174035
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": -0.019379228446597896,
    "paired_values_dt0.05": [
      -0.017254488517454813,
      -0.027364632870058858,
      -0.01726402336053301,
      -0.015633769038344902
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": -0.01937351025479575,
    "paired_values_dt0.025": [
      -0.017249224377430705,
      -0.027356405929889305,
      -0.017259100584154474,
      -0.015629310127708518
    ],
    "max_paired_fine_change": 8.226940169553387e-06
  },
  {
    "z_target": 4.8,
    "kappa": 0.003,
    "contrast": "triangle_high_minus_low",
    "n_dt0.1": 4,
    "mean_dt0.1": 0.0005706421524061811,
    "paired_values_dt0.1": [
      -0.00012494860080702885,
      0.002894171288173375,
      -0.0007412384604725819,
      0.0002545843827309602
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": 0.0005704348176399643,
    "paired_values_dt0.05": [
      -0.0001244475412749413,
      0.002892435418121009,
      -0.0007406784911943021,
      0.0002544298849080917
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": 0.000570332551982633,
    "paired_values_dt0.025": [
      -0.00012420681523761523,
      0.0028915884203504216,
      -0.0007404058865256857,
      0.0002543544893434113
    ],
    "max_paired_fine_change": 8.469977705871656e-07
  },
  {
    "z_target": 4.8,
    "kappa": 0.03,
    "contrast": "hub_minus_uniform",
    "n_dt0.1": 4,
    "mean_dt0.1": -0.039155212609988194,
    "paired_values_dt0.1": [
      -0.0350893162087762,
      -0.04928057717220147,
      -0.04130282099720972,
      -0.030948136061765386
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": -0.03911991622511746,
    "paired_values_dt0.05": [
      -0.03505873967801876,
      -0.049236246519273164,
      -0.04126679409873324,
      -0.030917884604444668
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": -0.03910279528485064,
    "paired_values_dt0.025": [
      -0.035043907471133506,
      -0.0492147460663479,
      -0.04124930638154922,
      -0.030903221220371924
    ],
    "max_paired_fine_change": 2.1500452925260483e-05
  },
  {
    "z_target": 4.8,
    "kappa": 0.03,
    "contrast": "triangle_high_minus_low",
    "n_dt0.1": 4,
    "mean_dt0.1": 0.00166624653733366,
    "paired_values_dt0.1": [
      0.0019638556048332534,
      0.004849458423729525,
      -0.0008481311735425434,
      0.000699803294314405
    ],
    "n_dt0.05": 4,
    "mean_dt0.05": 0.0016647368396368045,
    "paired_values_dt0.05": [
      0.0019619581366336902,
      0.00484507441685611,
      -0.0008472937049085472,
      0.0006992085099659651
    ],
    "n_dt0.025": 4,
    "mean_dt0.025": 0.0016640041967001806,
    "paired_values_dt0.025": [
      0.0019610371888482137,
      0.0048429481172993505,
      -0.0008468883783129266,
      0.000698919858966085
    ],
    "max_paired_fine_change": 2.12629955675947e-06
  }
]

## Rate controls

[
  {
    "z_target": 3.2,
    "kappa": 0.0,
    "rate_beta": 0.0,
    "eligible_uniform": 0,
    "eligible_hub": 4,
    "eligible_pairs": 0,
    "paired_uniform_mean": null,
    "paired_hub_mean": null,
    "paired_delta_mean": null,
    "pairs": []
  },
  {
    "z_target": 3.2,
    "kappa": 0.0,
    "rate_beta": 10.0,
    "eligible_uniform": 0,
    "eligible_hub": 4,
    "eligible_pairs": 0,
    "paired_uniform_mean": null,
    "paired_hub_mean": null,
    "paired_delta_mean": null,
    "pairs": []
  },
  {
    "z_target": 3.2,
    "kappa": 0.003,
    "rate_beta": 0.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.9314821026828474,
    "paired_hub_mean": 0.5060050040832552,
    "paired_delta_mean": -0.42547709859959215,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.4010795047298975,
        "uniform": 0.9078810017361736,
        "hub": 0.5068014970062761
      },
      {
        "seed": 74001,
        "delta": -0.4322508786140885,
        "uniform": 0.9385616973330781,
        "hub": 0.5063108187189896
      },
      {
        "seed": 74002,
        "delta": -0.42410120194784173,
        "uniform": 0.9308726854568186,
        "hub": 0.5067714835089768
      },
      {
        "seed": 74003,
        "delta": -0.44447680910654064,
        "uniform": 0.9486130262053192,
        "hub": 0.5041362170987785
      }
    ]
  },
  {
    "z_target": 3.2,
    "kappa": 0.003,
    "rate_beta": 10.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.9313796477036324,
    "paired_hub_mean": 0.5049823403023346,
    "paired_delta_mean": -0.42639730740129783,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.40173906925328495,
        "uniform": 0.907694691255077,
        "hub": 0.505955622001792
      },
      {
        "seed": 74001,
        "delta": -0.43327995833651933,
        "uniform": 0.938485221054808,
        "hub": 0.5052052627182887
      },
      {
        "seed": 74002,
        "delta": -0.42505921951483694,
        "uniform": 0.9307766656386648,
        "hub": 0.5057174461238279
      },
      {
        "seed": 74003,
        "delta": -0.4455109825005501,
        "uniform": 0.9485620128659799,
        "hub": 0.5030510303654298
      }
    ]
  },
  {
    "z_target": 3.2,
    "kappa": 0.03,
    "rate_beta": 0.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.7744636627869987,
    "paired_hub_mean": 0.519220060813843,
    "paired_delta_mean": -0.2552436019731557,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.2171831677855367,
        "uniform": 0.742332819666096,
        "hub": 0.5251496518805593
      },
      {
        "seed": 74001,
        "delta": -0.2548007228590631,
        "uniform": 0.7776976440418183,
        "hub": 0.5228969211827552
      },
      {
        "seed": 74002,
        "delta": -0.25328206328895364,
        "uniform": 0.7738920955246422,
        "hub": 0.5206100322356886
      },
      {
        "seed": 74003,
        "delta": -0.2957084539590694,
        "uniform": 0.8039320919154385,
        "hub": 0.508223637956369
      }
    ]
  },
  {
    "z_target": 3.2,
    "kappa": 0.03,
    "rate_beta": 10.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.7737280956074816,
    "paired_hub_mean": 0.5181920212300042,
    "paired_delta_mean": -0.2555360743774774,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.21717379080093835,
        "uniform": 0.7414409523839711,
        "hub": 0.5242671615830328
      },
      {
        "seed": 74001,
        "delta": -0.2551658592890359,
        "uniform": 0.7769804391621846,
        "hub": 0.5218145798731487
      },
      {
        "seed": 74002,
        "delta": -0.2535923737732395,
        "uniform": 0.7731441222717432,
        "hub": 0.5195517484985037
      },
      {
        "seed": 74003,
        "delta": -0.2962122736466958,
        "uniform": 0.8033468686120276,
        "hub": 0.5071345949653319
      }
    ]
  },
  {
    "z_target": 4.0,
    "kappa": 0.0,
    "rate_beta": 0.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.5033689734995428,
    "paired_hub_mean": 0.5033689734995428,
    "paired_delta_mean": 5.551115123125783e-17,
    "pairs": [
      {
        "seed": 74000,
        "delta": 1.1102230246251565e-16,
        "uniform": 0.5033689734995427,
        "hub": 0.5033689734995428
      },
      {
        "seed": 74001,
        "delta": -1.1102230246251565e-16,
        "uniform": 0.5033689734995428,
        "hub": 0.5033689734995427
      },
      {
        "seed": 74002,
        "delta": 1.1102230246251565e-16,
        "uniform": 0.5033689734995427,
        "hub": 0.5033689734995428
      },
      {
        "seed": 74003,
        "delta": 1.1102230246251565e-16,
        "uniform": 0.5033689734995427,
        "hub": 0.5033689734995428
      }
    ]
  },
  {
    "z_target": 4.0,
    "kappa": 0.0,
    "rate_beta": 10.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.5029604680422377,
    "paired_hub_mean": 0.5023132801817797,
    "paired_delta_mean": -0.0006471878604580872,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.0007491345366701374,
        "uniform": 0.5029626297920226,
        "hub": 0.5022134952553524
      },
      {
        "seed": 74001,
        "delta": -0.0009485524733293671,
        "uniform": 0.5032541323974148,
        "hub": 0.5023055799240854
      },
      {
        "seed": 74002,
        "delta": -0.0004904681072084305,
        "uniform": 0.5027989511594676,
        "hub": 0.5023084830522592
      },
      {
        "seed": 74003,
        "delta": -0.00040059632462441375,
        "uniform": 0.502826158820046,
        "hub": 0.5024255624954216
      }
    ]
  },
  {
    "z_target": 4.0,
    "kappa": 0.003,
    "rate_beta": 0.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.6593386175291261,
    "paired_hub_mean": 0.505819725447568,
    "paired_delta_mean": -0.1535188920815581,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.15645568129652743,
        "uniform": 0.6615375957740947,
        "hub": 0.5050819144775672
      },
      {
        "seed": 74001,
        "delta": -0.19727823224348118,
        "uniform": 0.702295871433006,
        "hub": 0.5050176391895248
      },
      {
        "seed": 74002,
        "delta": -0.12912550407134482,
        "uniform": 0.6341523601341948,
        "hub": 0.50502685606285
      },
      {
        "seed": 74003,
        "delta": -0.13121615071487902,
        "uniform": 0.6393686427752091,
        "hub": 0.5081524920603301
      }
    ]
  },
  {
    "z_target": 4.0,
    "kappa": 0.003,
    "rate_beta": 10.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.6585205158974896,
    "paired_hub_mean": 0.5047688823928849,
    "paired_delta_mean": -0.15375163350460472,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.1567886421447593,
        "uniform": 0.6607220352775925,
        "hub": 0.5039333931328333
      },
      {
        "seed": 74001,
        "delta": -0.19750324817616915,
        "uniform": 0.7014646894847061,
        "hub": 0.5039614413085369
      },
      {
        "seed": 74002,
        "delta": -0.12939818305762374,
        "uniform": 0.6333689068113492,
        "hub": 0.5039707237537254
      },
      {
        "seed": 74003,
        "delta": -0.13131646063986668,
        "uniform": 0.6385264320163108,
        "hub": 0.5072099713764441
      }
    ]
  },
  {
    "z_target": 4.0,
    "kappa": 0.03,
    "rate_beta": 0.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.6232156319250679,
    "paired_hub_mean": 0.5177569369360343,
    "paired_delta_mean": -0.1054586949890336,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.11375632279459191,
        "uniform": 0.6266794181075052,
        "hub": 0.5129230953129132
      },
      {
        "seed": 74001,
        "delta": -0.10886421388927914,
        "uniform": 0.6229183772993406,
        "hub": 0.5140541634100615
      },
      {
        "seed": 74002,
        "delta": -0.10892153625851475,
        "uniform": 0.6230864113507463,
        "hub": 0.5141648750922315
      },
      {
        "seed": 74003,
        "delta": -0.09029270701374859,
        "uniform": 0.6201783209426796,
        "hub": 0.529885613928931
      }
    ]
  },
  {
    "z_target": 4.0,
    "kappa": 0.03,
    "rate_beta": 10.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.62207104526458,
    "paired_hub_mean": 0.5166951507577479,
    "paired_delta_mean": -0.10537589450683216,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.11377467006176623,
        "uniform": 0.6255472507149883,
        "hub": 0.5117725806532221
      },
      {
        "seed": 74001,
        "delta": -0.10874185646629109,
        "uniform": 0.6217470463840021,
        "hub": 0.513005189917711
      },
      {
        "seed": 74002,
        "delta": -0.10887473198397968,
        "uniform": 0.6219802035603367,
        "hub": 0.513105471576357
      },
      {
        "seed": 74003,
        "delta": -0.09011231951529164,
        "uniform": 0.6190096803989928,
        "hub": 0.5288973608837012
      }
    ]
  },
  {
    "z_target": 4.8,
    "kappa": 0.0,
    "rate_beta": 0.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.5033689734995427,
    "paired_hub_mean": 0.5033689734995427,
    "paired_delta_mean": 0.0,
    "pairs": [
      {
        "seed": 74000,
        "delta": 0.0,
        "uniform": 0.5033689734995427,
        "hub": 0.5033689734995427
      },
      {
        "seed": 74001,
        "delta": 0.0,
        "uniform": 0.5033689734995427,
        "hub": 0.5033689734995427
      },
      {
        "seed": 74002,
        "delta": -1.1102230246251565e-16,
        "uniform": 0.5033689734995427,
        "hub": 0.5033689734995426
      },
      {
        "seed": 74003,
        "delta": 1.1102230246251565e-16,
        "uniform": 0.5033689734995427,
        "hub": 0.5033689734995428
      }
    ]
  },
  {
    "z_target": 4.8,
    "kappa": 0.0,
    "rate_beta": 10.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.5023334653840998,
    "paired_hub_mean": 0.502245223302343,
    "paired_delta_mean": -8.824208175681192e-05,
    "pairs": [
      {
        "seed": 74000,
        "delta": -3.181399480778335e-05,
        "uniform": 0.5023033111860545,
        "hub": 0.5022714971912468
      },
      {
        "seed": 74001,
        "delta": -0.00011912844623296337,
        "uniform": 0.5023458135608853,
        "hub": 0.5022266851146523
      },
      {
        "seed": 74002,
        "delta": -0.0001090317078096259,
        "uniform": 0.5023447631031698,
        "hub": 0.5022357313953602
      },
      {
        "seed": 74003,
        "delta": -9.299417817687505e-05,
        "uniform": 0.5023399736862898,
        "hub": 0.5022469795081129
      }
    ]
  },
  {
    "z_target": 4.8,
    "kappa": 0.003,
    "rate_beta": 0.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.5238834835821911,
    "paired_hub_mean": 0.5046069809772263,
    "paired_delta_mean": -0.019276502604964718,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.01719048690984748,
        "uniform": 0.521828631594914,
        "hub": 0.5046381446850665
      },
      {
        "seed": 74001,
        "delta": -0.02722975263105576,
        "uniform": 0.5314670565774474,
        "hub": 0.5042373039463917
      },
      {
        "seed": 74002,
        "delta": -0.017141573864571935,
        "uniform": 0.5213886271462348,
        "hub": 0.5042470532816629
      },
      {
        "seed": 74003,
        "delta": -0.015544197014383698,
        "uniform": 0.520849619010168,
        "hub": 0.5053054219957843
      }
    ]
  },
  {
    "z_target": 4.8,
    "kappa": 0.003,
    "rate_beta": 10.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.5228791621344359,
    "paired_hub_mean": 0.5034881753997105,
    "paired_delta_mean": -0.01939098673472542,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.017265310156626135,
        "uniform": 0.5208119343209726,
        "hub": 0.5035466241643465
      },
      {
        "seed": 74001,
        "delta": -0.02738154657302383,
        "uniform": 0.5304800911540419,
        "hub": 0.5030985445810181
      },
      {
        "seed": 74002,
        "delta": -0.017274128717077675,
        "uniform": 0.5203905536592945,
        "hub": 0.5031164249422169
      },
      {
        "seed": 74003,
        "delta": -0.015642961492174035,
        "uniform": 0.5198340694034342,
        "hub": 0.5041911079112602
      }
    ]
  },
  {
    "z_target": 4.8,
    "kappa": 0.03,
    "rate_beta": 0.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.5502050052372461,
    "paired_hub_mean": 0.5110297339858779,
    "paired_delta_mean": -0.03917527125136824,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.03512225867604535,
        "uniform": 0.5462128754117755,
        "hub": 0.5110906167357302
      },
      {
        "seed": 74001,
        "delta": -0.04932338658401392,
        "uniform": 0.5584848033943675,
        "hub": 0.5091614168103535
      },
      {
        "seed": 74002,
        "delta": -0.041283451236704294,
        "uniform": 0.5497413009159234,
        "hub": 0.5084578496792191
      },
      {
        "seed": 74003,
        "delta": -0.030971988508709414,
        "uniform": 0.546381041226918,
        "hub": 0.5154090527182086
      }
    ]
  },
  {
    "z_target": 4.8,
    "kappa": 0.03,
    "rate_beta": 10.0,
    "eligible_uniform": 4,
    "eligible_hub": 4,
    "eligible_pairs": 4,
    "paired_uniform_mean": 0.549070575057188,
    "paired_hub_mean": 0.5099153624471999,
    "paired_delta_mean": -0.039155212609988194,
    "pairs": [
      {
        "seed": 74000,
        "delta": -0.0350893162087762,
        "uniform": 0.5450962311696945,
        "hub": 0.5100069149609183
      },
      {
        "seed": 74001,
        "delta": -0.04928057717220147,
        "uniform": 0.5573106646237755,
        "hub": 0.5080300874515741
      },
      {
        "seed": 74002,
        "delta": -0.04130282099720972,
        "uniform": 0.5486275131533802,
        "hub": 0.5073246921561705
      },
      {
        "seed": 74003,
        "delta": -0.030948136061765386,
        "uniform": 0.5452478912819021,
        "hub": 0.5142997552201367
      }
    ]
  }
]

Four paired seeds support descriptive comparisons, not confirmatory significance or phase-boundary estimates. Whole-energy stiffness rescaling changes microscopic stiffness as well as topology. Matched_final_stress is .1 times retention and is not independent corroboration. A difference persisting at beta0 rejects a rate-acceleration-only explanation in that tested numerical slice, without establishing a unique bending/fragmentation/degree mechanism. Any finer-step-dependent small triangle effect must be interpreted in light of its actual paired contrast changes and the weak achieved clustering intervention.

## Questions for reviewers

What survives exact graph reconstruction and the predeclared largest-size time-step gate? Which claims remain conditional on shear-bearing graphs? Does the rate-control result generalize across all tested z values? Which single next study best separates topology mechanisms or closes a material numerical uncertainty? Reject unsupported alleged bugs and scope-changing repairs. Literature requests are unverified unless independently checked; no invented references or claims of code execution.
