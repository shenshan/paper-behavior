#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  3 11:28:01 2019
Generates learning rate figurre 4b. Boxplots of learning rates per mouse 
divided by lab

@author: alejandropan
"""

#Import some general packages

import time, re, datetime, os, glob
from datetime import timedelta
import seaborn as sns
import sys
import matplotlib as mpl
import matplotlib.pyplot as plt
import scipy
import math as m

import numpy as np
import pandas as pd
from IPython import embed as shell
from scipy import stats

## CONNECT TO datajoint

import datajoint as dj
dj.config['database.host'] = 'datajoint.internationalbrainlab.org'
sys.path.insert(0, '/Users/alex/Documents/PYTHON/analysis/python/')
sys.path.insert(0, '/Users/alex/Documents/PYTHON/analysis/paper-behavior/')
sys.path.insert(0, '/Users/alex/Documents/PYTHON/analysis/paper-behavior/figure8/')

from dj_tools import *

import datajoint as dj
from ibl_pipeline.analyses import behavior as behavior_analysis
from ibl_pipeline import reference, subject, action, acquisition, data, behavior
from ibl_pipeline.analyses import behavior as behavior_analysis
from alexfigs_datajoint_functions import *  # this has all plotting functions


#Collect all all data 
use_subjects = subject.Subject * subject.SubjectLab * subject.SubjectProject & 'subject_project="ibl_neuropixel_brainwide_01"'
sess = (acquisition.Session & (behavior.TrialSet.Trial() & 'ABS(trial_stim_contrast_left-0)<0.0001' \
	& 'ABS(trial_stim_contrast_right-0)<0.0001') & 'task_protocol like "%trainingChoiceWorld%"') \
	* use_subjects
b 		= (behavior.TrialSet.Trial & sess) * subject.Subject() * subject.SubjectLab()
bdat 	= pd.DataFrame(b.fetch(order_by='subject_nickname, session_start_time, trial_id'))
allsubjects 	= dj2pandas(bdat)


#Drop unnecesary weight 

allsubjects= allsubjects.drop([
 'session_start_time',
 'trial_id',
 'trial_start_time',
 'trial_end_time',
 'trial_response_time',
 'trial_response_choice',
 'trial_stim_on_time',
 'trial_stim_contrast_left',
 'trial_stim_contrast_right',
 'trial_go_cue_time',
 'trial_go_cue_trigger_time',
 'trial_feedback_time',
 'trial_feedback_type',
 'trial_rep_num',
 'probabilityLeft',
 'trial_reward_volume',
 'trial_iti_duration',
 'trial_included',
 'subject_birth_date',
 'ear_mark',
 'subject_line',
 'subject_source',
 'protocol_number',
 'subject_description',
 'subject_ts',
 'subjectlab_ts',
 'signed_contrast',
 'trial',
 'choice',
 'correct',
 'choice_right',
 'choice2',
 'correct_easy',
 'rt',
 'previous_choice',
 'previous_outcome',
 'previous_contrast',
 'previous_choice_name',
 'previous_outcome_name',
 'repeat'], axis=1)

allsubjects = allsubjects.drop_duplicates(['subject_nickname'])

#Add learning rate columns
allsubjects['training_status'] =np.nan
allsubjects['days_to_trained'] = np.nan
allsubjects['trials_to_trained'] = np.nan
allsubjects['days_to_ephys'] = np.nan
allsubjects['trials_to_ephys'] = np.nan

#Summary trial weight
allsubjects['average_weight'] = np.nan
allsubjects['average_trialspsession'] = np.nan


#Add bias (level2) columns
allsubjects['average_bias08'] =np.nan
allsubjects['average_bias02'] =np.nan
allsubjects['average_threshold'] =np.nan
allsubjects['average_lapse_high'] =np.nan
allsubjects['average_lapse_low'] =np.nan



users  =  allsubjects['lab_name'].unique()

for labname in users:
    for mouse in allsubjects['subject_nickname']:
        try:
            # TRIAL COUNTS AND SESSION DURATION
            behav = get_behavior(mouse, labname)
            # check whether the subject is trained based the the lastest session and get average weight
            subj = subject.Subject & 'subject_nickname="{}"'.format(mouse)
            last_session = subj.aggr(behavior.TrialSet, session_start_time
                                     ='max(session_start_time)')
            training_status = (behavior_analysis.SessionTrainingStatus & 
                               last_session).fetch1('training_status')
            average_weight , _ = get_weights(mouse, labname).mean()
            average_trialspsession  =  behav.groupby('days').count()['trial_id'].mean()
                
            if training_status in ['trained_1a', 'trained_1b', 'ready4ephysrig', 'ready4recording']:
                first_trained_session_1a = subj.aggr(behavior_analysis.SessionTrainingStatus & 'training_status="trained_1a"', first_trained='min(session_start_time)')
                    
                first_trained_session_1b = subj.aggr(behavior_analysis.SessionTrainingStatus & 'training_status="trained_1b"', first_trained='min(session_start_time)')
                    
                    
                #Exceptions for animals that jumped from 1a or 1b to biased choice world
                if not first_trained_session_1b:
                    first_trained_session_time = first_trained_session_1a.fetch1('first_trained')
                    
                if not first_trained_session_1a:
                    first_trained_session_time = first_trained_session_1b.fetch1('first_trained')
                        
                else:
                    first_trained_session_time = min([first_trained_session_1a.fetch('first_trained'),first_trained_session_1b.fetch('first_trained')])
                    
                    #Fetch training critierion that was reached earlier 
                    # convert to timestamp
                    trained_date = pd.DatetimeIndex([first_trained_session_time][0])[0]
                    # how many days to training?
                    days_to_trained = sum(behav['date'].unique() < trained_date.to_datetime64())
                    # how many trials to trained?
                    trials_to_trained = sum(behav['date'] < trained_date.to_datetime64())
                       
                    #average threshold
                    pars = pd.DataFrame((behavior_analysis.BehavioralSummaryByDate.PsychResults * subject.Subject * subject.SubjectLab & \
                                         'subject_nickname="%s"'%mouse & 'lab_name="%s"'%labname).fetch(as_dict=True))
                    average_threshold  = pars.loc[(pars['prob_left'] == 0.5) & (pars['session_date'] \
                                                >= first_trained_session_time[0].date()), 'threshold'].mean()
                    average_lapse_high  = pars.loc[(pars['prob_left'] == 0.5) & (pars['session_date'] \
                                                >= first_trained_session_time[0].date()), 'lapse_high'].mean()
                    average_lapse_low  = pars.loc[(pars['prob_left'] == 0.5) & (pars['session_date'] \
                                                >= first_trained_session_time[0].date()), 'lapse_low'].mean()
            else:   
                 days_to_trained = np.nan
                 trials_to_trained = np.nan
                 average_threshold = np.nan
                 average_lapse_high = np.nan
                 average_lapse_low = np.nan
    
            if training_status in ['ready4recording', 'ready4ephysrig']:
                #Only counting from ready to ephys status
                first_ephystrained_session = subj.aggr(behavior_analysis.SessionTrainingStatus & \
                                                           'training_status="ready4ephysrig"', first_ephystrained='min(session_start_time)')
                first_ephystrained_session_time = first_ephystrained_session.fetch1('first_ephystrained')
                # trials to ready for ephys
                ephys_date = pd.DatetimeIndex([first_ephystrained_session_time])[0]
                days_to_ephys = sum((behav['date'].unique() < ephys_date.to_datetime64()) & (behav['date'].unique() > trained_date.to_datetime64()))
                trials_to_ephys = sum((behav['date'] < ephys_date.to_datetime64()) & (behav['date'] > trained_date.to_datetime64()))
                    
                #Bias analysis
                pars = pd.DataFrame((behavior_analysis.BehavioralSummaryByDate.PsychResults * \
                                     subject.Subject * subject.SubjectLab & 'subject_nickname="%s"'%mouse & \
                                     'lab_name="%s"'%labname).fetch(as_dict=True))
                average_bias_08  = pars.loc[(pars['prob_left'] == 0.8) & (pars['session_date'] \
                                            >= first_ephystrained_session_time.date()), 'bias'].mean()
                average_bias_02  = pars.loc[(pars['prob_left'] == 0.2) & (pars['session_date'] \
                                                >= first_ephystrained_session_time.date()), 'bias'].mean()
                    
            else:
                average_bias_08 = np.nan
                average_bias_02= np.nan
                days_to_ephys = np.nan
                trials_to_ephys= np.nan
                    
                # keep track
                
            allsubjects.loc[allsubjects['subject_nickname'] == mouse, ['days_to_trained','trials_to_trained','days_to_ephys','trials_to_ephys', 'training_status',\
                                'average_threshold','average_lapse_high', 'average_lapse_low', 'average_bias08', 'average_bias02', 'average_weight', 'average_trialspsession']] = days_to_trained, \
                                trials_to_trained,days_to_ephys, trials_to_ephys, training_status,\
                                average_threshold, average_lapse_high, average_lapse_low, average_bias_08, average_bias_02, average_weight, average_trialspsession
                
        except:
            pass


##########
###Figure1
##########

sns.set('paper')
fig, ax = plt.subplots(3,2,figsize=[13,15])
#
plt.sca(ax[0,0])
sns.boxplot(y="sex", x="days_to_trained", data=allsubjects, color = "yellow", width=0.5)
sns.swarmplot(y="sex", x="days_to_trained", data=allsubjects,hue="lab_name", edgecolor="white", )
plt.ylabel('Sex')
plt.xlabel('Length of training (sessions)')
ax[0,0].set_yticklabels(['Male \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='M']), 'Female \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='F']) ], rotation = 45)
ax[0,0].legend(loc='upper right', bbox_to_anchor=(0.75, 1.2), ncol=3)
# replace labels
new_labels = ['CSHL', 'UC Berkeley', 'NYU', 'SWC - 1', 'Princeton','UCL', 'SWC - 2','CCU']
for t, l in zip(ax[0,0].legend_.texts, new_labels): t.set_text(l)
#Stats
_ ,p_sessions  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'days_to_trained'], allsubjects.loc[allsubjects['sex']=='F', 'days_to_trained'], use_continuity=True)
lim = max(allsubjects['days_to_trained']) +  5
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_sessions<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_sessions)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=16)

plt.sca(ax[0,1])
sns.boxplot(y="sex", x="trials_to_trained", data=allsubjects,  color = "yellow" , width=0.5)
sns.swarmplot(y="sex", x="trials_to_trained", data=allsubjects,hue="lab_name", edgecolor="white")
plt.ylabel('Sex')
plt.xlabel('Length of training (trials)')
ax[0,1].legend_.remove()
ax[0,1].set_yticklabels(['Male \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='M']), 'Female \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='F']) ], rotation = 45)

#Stats
_ ,p_trials  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'trials_to_trained'], allsubjects.loc[allsubjects['sex']=='F', 'trials_to_trained'], use_continuity=True)
lim = max(allsubjects['trials_to_trained']) +  5000
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_trials<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_trials)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=16)

#####
plt.sca(ax[1,0])
sns.boxplot(y="sex", x="average_weight", data=allsubjects,  color = "yellow" , width=0.5)
sns.swarmplot(y="sex", x="average_weight", data=allsubjects,hue="lab_name", edgecolor="white")
plt.ylabel('Sex')
plt.xlabel('Weight (g)')
ax[1,0].legend_.remove()
ax[1,0].set_yticklabels(['Male \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='M']), 'Female \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='F']) ], rotation = 45)

#Stats
_ ,p_weight  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'average_weight'], allsubjects.loc[allsubjects['sex']=='F', 'average_weight'], use_continuity=True)
lim = max(allsubjects['average_weight']) +  2
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_weight<0.05:
    plt.text(lim*1.0, 0.65, '*'*m.floor(m.log10(p_weight)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.45, 'n.s', ha='center', rotation = -90, fontsize=16)


######
allsubjects  = allsubjects.dropna(subset=['average_trialspsession'])
plt.sca(ax[1,1])
sns.scatterplot(y="average_trialspsession", x="average_weight", data=allsubjects, hue = 'lab_name')
sns.regplot(y="average_trialspsession", x="average_weight", data=allsubjects, scatter=False, ax=ax[1,1], color='k')
plt.ylabel('Average no trials per sessions')
plt.xlabel('Weight (g)')
ax[1,1].legend_.remove()

pearson  =scipy.stats.pearsonr(allsubjects.average_weight.to_numpy(), allsubjects.average_trialspsession.to_numpy())
spearman  =scipy.stats.spearmanr(allsubjects.average_weight.to_numpy(), allsubjects.average_trialspsession.to_numpy())

if pearson[1]<0.05:
    plt.text(0.9, 0.8,'p<0.01',
         horizontalalignment='center',
         verticalalignment='center',
         transform = ax[1,1].transAxes)

######
    
allsubjects['gsessions_2_trained'] = allsubjects['days_to_trained']/allsubjects['average_weight']
plt.sca(ax[2,0])
sns.boxplot(y="sex", x="gsessions_2_trained", data=allsubjects, color = "yellow", width=0.5)
sns.swarmplot(y="sex", x="gsessions_2_trained", data=allsubjects,hue="lab_name", edgecolor="white", )
plt.ylabel('Sex')
plt.xlabel('Length of training (sessions)/ Weight (g)')
ax[2,0].set_yticklabels(['Male \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='M']), 'Female \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='F']) ], rotation = 45)
ax[2,0].legend_.remove()
#Stats
_ ,p_gsessions  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'gsessions_2_trained'], allsubjects.loc[allsubjects['sex']=='F', 'gsessions_2_trained'], use_continuity=True)
lim = max(allsubjects['gsessions_2_trained']) +  1
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_gsessions<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_gsessions)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=16)

fig.delaxes(ax[2,1])

fig.savefig("weight_sex_training.pdf", bbox_inches='tight')

###########
####Figure2
###########


sns.set('paper')
fig_2ephys, ax = plt.subplots(2,2,figsize=[13,10])
#
plt.sca(ax[0,0])
sns.boxplot(y="sex", x="days_to_ephys", data=allsubjects, color = "yellow", width=0.5)
sns.swarmplot(y="sex", x="days_to_ephys", data=allsubjects,hue="lab_name", edgecolor="white", )
plt.ylabel('Sex')
plt.xlabel('Length of training (sessions)')
ax[0,0].set_yticklabels(['Male \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='M'].dropna(subset=['days_to_ephys'])), 'Female \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='F'].dropna(subset=['days_to_ephys'])) ], rotation = 45)
ax[0,0].legend(loc='upper right', bbox_to_anchor=(0.75, 1.2), ncol=3)
# replace labels
new_labels = ['CSHL', 'UC Berkeley', 'NYU', 'SWC - 1', 'Princeton','UCL', 'SWC - 2','CCU']
for t, l in zip(ax[0,0].legend_.texts, new_labels): t.set_text(l)
#Stats
_ ,p_sessions  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'days_to_ephys'], allsubjects.loc[allsubjects['sex']=='F', 'days_to_ephys'], use_continuity=True)
lim = np.nanmax(allsubjects['days_to_ephys']) +  5
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_sessions<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_sessions)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=12)

plt.sca(ax[0,1])
sns.boxplot(y="sex", x="trials_to_ephys", data=allsubjects,  color = "yellow" , width=0.5)
sns.swarmplot(y="sex", x="trials_to_ephys", data=allsubjects,hue="lab_name", edgecolor="white")
plt.ylabel('Sex')
plt.xlabel('Length of training (trials)')
ax[0,1].legend_.remove()
ax[0,1].set_yticklabels(['Male \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='M'].dropna(subset=['days_to_ephys'])), 'Female \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='F'].dropna(subset=['days_to_ephys'])) ], rotation = 45)
#Stats
_ ,p_trials  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'trials_to_ephys'], allsubjects.loc[allsubjects['sex']=='F', 'trials_to_ephys'], use_continuity=True)
lim = np.nanmax(allsubjects['trials_to_ephys']) +  5000
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_trials<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_trials)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=12)


######
allsubjects['gsessions_2_ephys'] = allsubjects['days_to_ephys']/allsubjects['average_weight']
plt.sca(ax[1,0])
sns.boxplot(y="sex", x="gsessions_2_ephys", data=allsubjects, color = "yellow", width=0.5)
sns.swarmplot(y="sex", x="gsessions_2_ephys", data=allsubjects,hue="lab_name", edgecolor="white", )
plt.ylabel('Sex')
plt.xlabel('Length of training (sessions)/ Weight (g)')
ax[1,0].set_yticklabels(['Male \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='M'].dropna(subset=['days_to_ephys'])), 'Female \n (n = %d)' %len(allsubjects.loc[allsubjects['sex']=='F'].dropna(subset=['days_to_ephys'])) ], rotation = 45)
ax[1,0].legend_.remove()
#Stats
_ ,p_gsessions  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'gsessions_2_ephys'], allsubjects.loc[allsubjects['sex']=='F', 'gsessions_2_ephys'], use_continuity=True)
lim = np.nanmax(allsubjects['gsessions_2_ephys'])+0.1
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_gsessions<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_gsessions)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=12)

fig_2ephys.delaxes(ax[1,1])

fig_2ephys.savefig("weight_sex_ephys.pdf", bbox_inches='tight')


###########
####Figure3
###########

#a
sns.set('paper')
fig_3_psychometrics, ax = plt.subplots(3,2,figsize=[13,15])
plt.sca(ax[0,0])
sns.boxplot(y="sex", x="average_threshold", data=allsubjects, color = "yellow", width=0.5)
sns.swarmplot(y="sex", x="average_threshold", data=allsubjects,hue="lab_name", edgecolor="white", )
plt.ylabel('Sex')
plt.xlabel('Average Threshold')
ax[0,0].set_yticklabels(['Male \n (n = %d)' %allsubjects.loc[allsubjects['sex']=='M','average_threshold'].count(), 'Female \n (n = %d)' %allsubjects.loc[allsubjects['sex']=='F','average_threshold'].count()])
ax[0,0].legend(loc='upper right', bbox_to_anchor=(0.75, 1.2), ncol=3)
#Stats
_ ,p_threshold  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'average_threshold'], allsubjects.loc[allsubjects['sex']=='F', 'average_threshold'], use_continuity=True)
lim = np.nanmax(allsubjects['average_threshold']) +  2
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_threshold<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_threshold)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=16)

#b
plt.sca(ax[0,1])
sns.boxplot(y="sex", x="average_lapse_high", data=allsubjects, color = "yellow", width=0.5)
sns.swarmplot(y="sex", x="average_lapse_high", data=allsubjects,hue="lab_name", edgecolor="white", )
plt.ylabel('Sex')
plt.xlabel('Average Lapse Right')
ax[0,1].set_yticklabels(['Male \n (n = %d)' %allsubjects.loc[allsubjects['sex']=='M','average_lapse_high'].count(), 'Female \n (n = %d)' %allsubjects.loc[allsubjects['sex']=='F','average_lapse_high'].count()])
ax[0,1].legend_.remove()
#Stats
_ ,p_lapse_high  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'average_lapse_high'], allsubjects.loc[allsubjects['sex']=='F', 'average_lapse_high'], use_continuity=True)
lim = np.nanmax(allsubjects['average_lapse_high']) +  0.1
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_lapse_high<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_lapse_high)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=16)

#c
plt.sca(ax[1,0])
sns.boxplot(y="sex", x="average_lapse_low", data=allsubjects, color = "yellow", width=0.5)
sns.swarmplot(y="sex", x="average_lapse_low", data=allsubjects,hue="lab_name", edgecolor="white", )
plt.ylabel('Sex')
plt.xlabel('Average Lapse Left')
ax[1,0].set_yticklabels(['Male \n (n = %d)' %allsubjects.loc[allsubjects['sex']=='M','average_lapse_low'].count(), 'Female \n (n = %d)' %allsubjects.loc[allsubjects['sex']=='F','average_lapse_low'].count()])
ax[1,0].legend_.remove()
#Stats
_ ,p_lapse_low  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'average_lapse_low'], allsubjects.loc[allsubjects['sex']=='F', 'average_lapse_low'], use_continuity=True)
lim = np.nanmax(allsubjects['average_lapse_low']) +  0.1
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_lapse_low<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_lapse_low)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=16)
    
#d
plt.sca(ax[1,1])
sns.boxplot(y="sex", x="average_bias08", data=allsubjects, color = "yellow", width=0.5)
sns.swarmplot(y="sex", x="average_bias08", data=allsubjects,hue="lab_name", edgecolor="white", )
plt.ylabel('Sex')
plt.xlabel('Average Right Bias')
ax[1,1].set_yticklabels(['Male \n (n = %d)' %allsubjects.loc[allsubjects['sex']=='M','average_bias08'].count(), 'Female \n (n = %d)' %allsubjects.loc[allsubjects['sex']=='F','average_bias08'].count()])
ax[1,1].legend_.remove()
#Stats
_ ,p_bias08 = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'average_bias08'], allsubjects.loc[allsubjects['sex']=='F', 'average_bias08'], use_continuity=True)
lim = np.nanmax(allsubjects['average_bias08']) +  2
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_bias08<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_bias08)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=16)
#e    
plt.sca(ax[2,0])
sns.boxplot(y="sex", x="average_bias02", data=allsubjects, color = "yellow", width=0.5)
sns.swarmplot(y="sex", x="average_bias02", data=allsubjects,hue="lab_name", edgecolor="white", )
plt.ylabel('Sex')
plt.xlabel('Average Left Bias')
ax[2,0].set_yticklabels(['Male \n (n = %d)' %allsubjects.loc[allsubjects['sex']=='M','average_bias02'].count(), 'Female \n (n = %d)' %allsubjects.loc[allsubjects['sex']=='F','average_bias02'].count()])
ax[2,0].legend_.remove()
#Stats
_ ,p_bias02  = scipy.stats.mannwhitneyu(allsubjects.loc[allsubjects['sex']=='M', 'average_bias02'], allsubjects.loc[allsubjects['sex']=='F', 'average_bias02'], use_continuity=True)
lim = np.nanmax(allsubjects['average_bias02']) +  2
plt.plot([lim,lim, lim, lim], [0, 0, 1, 1], linewidth=2, color='k')
if p_bias02<0.05:
    plt.text(lim*1.01, 0.5, '*'*m.floor(m.log10(p_bias02)*-1), ha='center', rotation = -90, fontsize=16)
else:
    plt.text(lim*1.01, 0.5, 'n.s', ha='center', rotation = -90, fontsize=16)

fig_3_psychometrics.savefig("fig_3_psychometrics.pdf", bbox_inches='tight')


###########
####Figure4
###########


#Make average "lab"

allsubjects_mean =  allsubjects.copy()
allsubjects_mean['lab_name'] = 'Mean'
allsubjects1 = pd.concat([allsubjects_mean, allsubjects], ignore_index=True)

#Set colours for figure
my_pal = {'churchlandlab':'grey', 'danlab':'grey', 'angelakilab':'grey', 'hoferlab':'grey', 'wittenlab':'grey',
       'cortexlab':'grey', 'mrsicflogellab':'grey', 'mainenlab':'grey', 'Mean':'yellow'}

#Start figure
sns.set('paper')
fig_totrained, ax = plt.subplots(2,2,figsize=[16,13])

##a
plt.sca(ax[0,0])
sns.boxplot(y="lab_name", x="days_to_trained", data=allsubjects1, color = "grey", palette=my_pal)
sns.swarmplot(y="lab_name", x="days_to_trained", data=allsubjects1, edgecolor="white", color='k' ,  size=3)
plt.ylabel('Location')
plt.xlabel('Length of training (sessions)')
# replace labels

new_labels = ['Mean \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='Mean') & ((allsubjects1['training_status']=='trained_1a') | (allsubjects1['training_status']=='ready4ephysrig'))]), 'CSHL \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='churchlandlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]),\
              'UC Berkeley \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='danlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]), 'NYU \n (n = %d)'  %len(allsubjects1.loc[(allsubjects1['lab_name']=='angelakilab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]),\
              'SWC - 1 \n (n = %d)'  %len(allsubjects1.loc[(allsubjects1['lab_name']=='mrsicflogellab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]), 'Princeton \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='wittenlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]),\
              'UCL \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='cortexlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]),'SWC - 2 \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='hoferlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]),\
              'CCU \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='mainenlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))])]

ax[0,0].set_yticklabels(new_labels)

##b
plt.sca(ax[0,1])
sns.boxplot(y="lab_name", x="trials_to_trained", data=allsubjects1, color = "grey", palette=my_pal)
sns.swarmplot(y="lab_name", x="trials_to_trained", data=allsubjects1, edgecolor="white", color='k' ,  size=3)
plt.ylabel('Location')
plt.xlabel('Length of training (trials)')
# replace labels
new_labels = ['Mean \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='Mean') & ((allsubjects1['training_status']=='trained_1a') | (allsubjects1['training_status']=='ready4ephysrig'))]), 'CSHL \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='churchlandlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]),\
              'UC Berkeley \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='danlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]), 'NYU \n (n = %d)'  %len(allsubjects1.loc[(allsubjects1['lab_name']=='angelakilab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]),\
              'SWC - 1 \n (n = %d)'  %len(allsubjects1.loc[(allsubjects1['lab_name']=='mrsicflogellab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]), 'Princeton \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='wittenlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]),\
              'UCL \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='cortexlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]),'SWC - 2 \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='hoferlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))]),\
              'CCU \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='mainenlab') & ((allsubjects1['training_status']=='trained_1a')| (allsubjects1['training_status']=='ready4ephysrig'))])]
ax[0,1].set_yticklabels(new_labels)
##c
plt.sca(ax[1,0])
sns.boxplot(y="lab_name", x="days_to_ephys", data=allsubjects1, color = "grey", palette=my_pal)
sns.swarmplot(y="lab_name", x="days_to_ephys", data=allsubjects1, edgecolor="white", color='k' ,  size=3)
plt.ylabel('Location')
plt.xlabel('Length of training Level 2 (sessions)')
# replace labels
new_labels = ['Mean \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='Mean') & (allsubjects1['training_status']=='ready4ephysrig')]), 'CSHL \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='churchlandlab') & (allsubjects1['training_status']=='ready4ephysrig')]),\
              'UC Berkeley \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='danlab') & (allsubjects1['training_status']=='ready4ephysrig')]), 'NYU \n (n = %d)'  %len(allsubjects1.loc[(allsubjects1['lab_name']=='angelakilab') & (allsubjects1['training_status']=='ready4ephysrig')]),\
              'SWC - 1 \n (n = %d)'  %len(allsubjects1.loc[(allsubjects1['lab_name']=='mrsicflogellab') & (allsubjects1['training_status']=='ready4ephysrig')]), 'Princeton \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='wittenlab') & (allsubjects1['training_status']=='ready4ephysrig')]),\
              'UCL \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='cortexlab') & (allsubjects1['training_status']=='ready4ephysrig')]),'SWC - 2 \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='hoferlab') & (allsubjects1['training_status']=='ready4ephysrig')]),\
              'CCU \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='mainenlab') & (allsubjects1['training_status']=='ready4ephysrig')])]
ax[1,0].set_yticklabels(new_labels)

##d
plt.sca(ax[1,1])
sns.boxplot(y="lab_name", x="trials_to_ephys", data=allsubjects1, color = "grey", palette=my_pal)
sns.swarmplot(y="lab_name", x="trials_to_ephys", data=allsubjects1, edgecolor="white", color='k' ,  size=3)
plt.ylabel('Location')
plt.xlabel('Length of training Level 2 (trials)')
# replace labels
new_labels = ['Mean \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='Mean') & (allsubjects1['training_status']=='ready4ephysrig')]), 'CSHL \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='churchlandlab') & (allsubjects1['training_status']=='ready4ephysrig')]),\
              'UC Berkeley \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='danlab') & (allsubjects1['training_status']=='ready4ephysrig')]), 'NYU \n (n = %d)'  %len(allsubjects1.loc[(allsubjects1['lab_name']=='angelakilab') & (allsubjects1['training_status']=='ready4ephysrig')]),\
              'SWC - 1 \n (n = %d)'  %len(allsubjects1.loc[(allsubjects1['lab_name']=='mrsicflogellab') & (allsubjects1['training_status']=='ready4ephysrig')]), 'Princeton \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='wittenlab') & (allsubjects1['training_status']=='ready4ephysrig')]),\
              'UCL \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='cortexlab') & (allsubjects1['training_status']=='ready4ephysrig')]),'SWC - 2 \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='hoferlab') & (allsubjects1['training_status']=='ready4ephysrig')]),\
              'CCU \n (n = %d)' %len(allsubjects1.loc[(allsubjects1['lab_name']=='mainenlab') & (allsubjects1['training_status']=='ready4ephysrig')])]
ax[1,1].set_yticklabels(new_labels)

fig_totrained.savefig("training_times.pdf", bbox_inches='tight')



