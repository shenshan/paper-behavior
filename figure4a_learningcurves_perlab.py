"""
SIGMOIDAL LEARNING CURVES DURING TRAINING
Anne Urai, CSHL, 2019
"""

import pandas as pd
import numpy as np
import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns
from paper_behavior_functions import query_subjects, seaborn_style
import datajoint as dj
from IPython import embed as shell  # for debugging

# import wrappers etc
from ibl_pipeline import reference, subject, action, acquisition, data, behavior
from ibl_pipeline.utils import psychofit as psy
from ibl_pipeline.analyses import behavior as behavioral_analyses

sys.path.insert(0, '../analysis_IBL/python')
from fit_learning_curves import *

# INITIALIZE A FEW THINGS
seaborn_style()
figpath = os.path.join(os.path.expanduser('~'), 'Data', 'Figures_IBL')
cmap = sns.diverging_palette(20, 220, n=3, center="dark")

# ================================= #
# GET DATA FROM TRAINED ANIMALS
# ================================= #

use_subjects = query_subjects()
b = (behavioral_analyses.BehavioralSummaryByDate * use_subjects)
behav = b.fetch(order_by='lab_name, subject_nickname', format='frame').reset_index()

# ================================= #
# LEARNING CURVES
# ================================= #

# TODO: WAIT FOR SHAN TO ADD training_day to BehavioralSummaryByDate

fig = sns.FacetGrid(behav,
                    col="institution", col_wrap=4, hue='subject_nickname',
                    sharex=True, sharey=True, aspect=1, xlim=[-1, 50.5], ylim=[0.4, 1])
fig.map(plot_learningcurve, "training_day",
        "performance_easy", "subject_nickname")
fig.set_axis_labels('Days in training', 'Performance on easy trials (%)')
# for ax, title in zip(fig.axes.flat, list(lab_names.values())):
#     ax.set_title(title)
fig.despine(trim=True)
fig.savefig(os.path.join(figpath, "figure4e_learningcurves_perlab.pdf"))
fig.savefig(os.path.join(
    figpath, "figure4e_learningcurves_perlab.png"), dpi=600)
plt.close('all')

fig = sns.FacetGrid(behav,
                    col="subject_nickname", col_wrap=8, hue="institution", palette="colorblind",
                    sharex=True, sharey=True, aspect=1)
fig.map(plot_learningcurve, "training_day",
        "performance_easy", "subject_nickname").add_legend()
fig.set_axis_labels('Days in training', 'Performance on easy trials (%)')
fig.set_titles("{col_name}")
fig.despine(trim=True)
fig.savefig(os.path.join(figpath, "figure4e_learningcurves_permouse.pdf"))
plt.close('all')
