# -*- coding: utf-8 -*-
"""
Created on Sat Mar  6 20:54:33 2021

"""
import multiprocessing as mp
import os
from time import sleep, time
import queue
import logging, logging.handlers
import tkinter as tk
from tkinter import ttk
import datetime
from tkinter import font, filedialog
import tkinter.messagebox
import atexit

from functools import partial

''' Import pyALD file - contains classes + functions to operate sequencer '''
import pyALD

''' Define variables '''
NUM_VALVES = 16
STOP = False
P_STOP = False
LOG_FILEPATH = r'C:\tmp\LogFiles'
VALVE_INTERLOCKS = [[1,2,3],[2,7,15]]

def listener_log_configurer():
    root = logging.getLogger()
    h = logging.StreamHandler()
    f = logging.Formatter('%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s')
    h.setFormatter(f)
    root.addHandler(h)
    now = datetime.datetime.now()
    logfilehandler = logging.handlers.TimedRotatingFileHandler(LOG_FILEPATH + str(now.year) + str(now.month) + str(now.day) + str(now.hour) + str(now.minute) + str(now.second) + '.txt', when='midnight', backupCount=180)
    logfilehandler.setFormatter(f)
    root.addHandler(logfilehandler)
    
def worker_log_configurer(queue):
    h = logging.handlers.QueueHandler(queue)
    root = logging.getLogger()
    root.addHandler(h)
    root.setLevel(logging.info)
        
    
def guiThread(guiQueue, valveQueue, timerQueue, recipeIQueue, recipeCQueue, logQueueIn, configurer, initDict):
    
    configurer(logQueueIn)
    root = logging.getLogger()
    root.info('guiThread started')
    
    pyGui = pyALD.GUI(nValves=16, nCycles=3, nLaminates=1)
    
    pyGui.setQueues(rIQ=recipeIQueue, rCQ=recipeCQueue, vQ=valveQueue, gQ=guiQueue)
    pyGui.setLogger(root)
    pyGui.setInitialization(initDict)
    
    pyGui.app = tk.Tk()
    pyGui.app.title('Control Box Operation Window')
    screenWidth = pyGui.app.winfo_screenwidth()
    screenHeight = pyGui.app.winfo_screenheight()
    geom = '%dx%d' %(screenWidth*0.85, screenHeight*0.85)
    pyGui.app.geometry(geom)

    ''' Define Dictionaries '''
    pyGui.fontDict = {}
    pyGui.frameDict = {}
    pyGui.featureDict = {}
    
    ''' Fonts '''
    pyGui.fontDict['Button'] = font.Font(size=14, weight='bold')
    pyGui.fontDict['Label'] = font.Font(size=14)
    pyGui.fontDict['Valve'] = font.Font(size=12)

    ''' Frame Creation '''
    pyGui.frameDict['RecipeControl'] = tk.Frame(pyGui.app, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
    pyGui.frameDict['Recipe'] = tk.Frame(pyGui.app, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
    pyGui.frameDict['RecipeHeaders'] = tk.Frame(pyGui.frameDict['Recipe'])
    pyGui.recipe_canvas = tk.Canvas(pyGui.frameDict['Recipe'], borderwidth=0)
    pyGui.frameDict['RecipeEdit'] = tk.Frame(pyGui.recipe_canvas, highlightbackground='black', borderwidth=0, relief=tk.SOLID)
    pyGui.frameDict['RecipeDetails'] = tk.Frame(pyGui.app, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
    pyGui.frameDict['RecipeLength'] = tk.Frame(pyGui.app, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
    pyGui.frameDict['Valve'] = tk.Frame(pyGui.app, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
    
    ''' Recipe Frame '''
    pyGui.featureDict['Label'] = {}
    pyGui.featureDict['Entry'] = {}
    pyGui.featureDict['Button'] = {}
    
    pyGui.featureDict['Label']['Recipe'] = {}
    pyGui.featureDict['Entry']['Recipe'] = {}
    pyGui.featureDict['Button']['Recipe'] = {}
    
    pyGui.featureDict['Label']['Recipe']['Row'] = []
    #featureDict['Label']['Recipe']['Col'] = []

    recipe_col_text = ['Row', 'Time', 'Step Name', 'Step Type', 'Laminate', 'Actuators']
    pyGui.featureDict['Label']['Recipe']['CurrentRecipe'] = tk.Label(pyGui.frameDict['RecipeHeaders'], text='Current Recipe: ')
    
    pyGui.featureDict['Label']['Recipe']['Col'] = [tk.Label(pyGui.frameDict['RecipeHeaders'], text=recipe_col_text[j]) for j in range(6)]
    #for j in range(5):
    #    featureDict['Label']['Recipe']['Col'].append(tk.Label(frameDict['RecipeHeaders'], text=recipe_col_text[j]))
    pyGui.featureDict['Label']['Recipe']['Col'][0].config(width=3)
    pyGui.featureDict['Label']['Recipe']['Col'][1].config(width=6)
    pyGui.featureDict['Label']['Recipe']['Col'][2].config(width=12)
    pyGui.featureDict['Label']['Recipe']['Col'][3].config(width=8)
    pyGui.featureDict['Label']['Recipe']['Col'][4].config(width=8)
    pyGui.featureDict['Label']['Recipe']['Col'][5].config(width=12)

    pyGui.vsb = tk.Scrollbar(pyGui.frameDict['Recipe'], orient='vertical', command=pyGui.recipe_canvas.yview)
    pyGui.recipe_canvas.config(yscrollcommand=pyGui.vsb.set)

    pyGui.featureDict['Button']['Recipe']['AddLine'] = tk.Button(pyGui.frameDict['Recipe'], text='Add Recipe Line', command=pyGui.addRecipeLine)
    pyGui.featureDict['Button']['Recipe']['DelLine'] = tk.Button(pyGui.frameDict['Recipe'], text='Delete Recipe Line', command=pyGui.deleteSingleLine)
    pyGui.featureDict['Button']['Recipe']['CalcLen'] = tk.Button(pyGui.frameDict['Recipe'], text='Calculate Recipe Length', command=pyGui.getRecipeLength)
    pyGui.featureDict['Button']['Recipe']['Preview']= tk.Button(pyGui.frameDict['Recipe'], text='Preview Recipe Steps', command=pyGui.recipePreview)
    #pyGui.featureDict['Button']['Recipe']['EditRecipeValves'] = tk.Button(pyGui.frameDict['Recipe'], text='Edit Recipe Valves', command=pyGui.editRecipeValves)
    
    ''' Create recipe region '''
    pyGui.recipe_window_len = 12
    pyGui.featureDict['Label']['Recipe']['Row'] = [tk.Label(pyGui.frameDict['RecipeEdit'], text=str(i+1)) for i in range(pyGui.recipe_window_len)]
    pyGui.featureDict['Entry']['Recipe']['Time'] = [tk.Entry(pyGui.frameDict['RecipeEdit'], justify='center', width=7) for i in range(pyGui.recipe_window_len)]
    pyGui.featureDict['Entry']['Recipe']['StepName'] = [tk.Label(pyGui.frameDict['RecipeEdit'], justify='center', width=15) for i in range(pyGui.recipe_window_len)]
    pyGui.featureDict['Combobox']['Recipe']['StepType'] = [ttk.combobox(pyGui.frameDict['RecipeEdit'], justify='center', width=8) for i in range(pyGui.recipe_window_len)]
    pyGui.featureDict['Combobox']['Recipe']['Laminate'] = [ttk.combobox(pyGui.frameDict['RecipeEdit'], justify='center', width=8) for i in range(pyGui.recipe_window_len)]
    pyGui.featureDict['Entry']['Recipe']['Actuator'] = [tk.Label(pyGui.frameDict['RecipeEdit'], justify='center', width=17) for i in range(pyGui.recipe_window_len)]

    pyGui.numLams = pyGui.configDict['Laminates']
    pyGui.numCycles = pyGui.configDict['Cycles']
    
    pyGui.stepTypes = ['Start', 'End']
    for i in range(pyGui.numCycles):
        pyGui.stepTypes.append('Cycle'+str(i+1))
    
    for i in range(pyGui.recipe_window_len):
        pyGui.featureDict['Combobox']['Recipe']['Laminate']['values'] = [str(j+1) for j in range(pyGui.numLam)]
        pyGui.featureDict['Combobox']['Recipe']['Laminate']['values'] = [pyGui.stepTypes[j] for j in range(len(pyGui.stepTypes))]

    ''' Recipe Control Frame '''
    pyGui.featureDict['Button']['Recipe']['Load'] = tk.Button(pyGui.frameDict['RecipeControl'], text='Load Recipe', font=pyGui.fontDict['Button'], bg='bisque',
                                   command=pyGui.loadRecipe)
    pyGui.featureDict['Button']['Recipe']['Save'] = tk.Button(pyGui.frameDict['RecipeControl'], text='Save Recipe', font=pyGui.fontDict['Button'], bg='light goldenrod',
                                   command=pyGui.saveRecipe)
    pyGui.featureDict['Button']['Recipe']['Manual'] = tk.Button(pyGui.frameDict['RecipeControl'], text='Manual Control', font=pyGui.fontDict['Button'], width=12, bg='green',
                                   fg='white', command=pyGui.manualControlClick)
    pyGui.featureDict['Button']['Recipe']['Play'] = tk.Button(pyGui.frameDict['RecipeControl'], text='Play', bg='green2', font=pyGui.fontDict['Button'], width=6,
                            command=pyGui.playButtonClick)
    pyGui.featureDict['Button']['Recipe']['Stop'] = tk.Button(pyGui.frameDict['RecipeControl'], text='Stop', bg='red3', font=pyGui.fontDict['Button'], width=6,
                            command=pyGui.stopButtonClick)
    
    pyGui.featureDict['Label']['Recipe']['FilenameLabel'] = tk.Label(pyGui.frameDict['RecipeControl'], text='Recipe Filename', justify='right')
    pyGui.featureDict['Label']['Recipe']['Filename'] = tk.Label(pyGui.frameDict['RecipeControl'], text=' ', width=18, relief=tk.SUNKEN, bg='white')
    pyGui.featureDict['Label']['Recipe']['ExpComment'] = tk.Label(pyGui.frameDict['RecipeControl'], text='Experiment Comment: ', justify='right')
    pyGui.featureDict['Entry']['Recipe']['ExpComment'] = tk.Entry(pyGui.frameDict['RecipeControl'], text=' ', width=30, relief=tk.SUNKEN, bg='white')

    ''' Recipe Details Frame '''

    ''' Create widgets for recipe details frame '''
    pyGui.featureDict['Label']['Recipe']['StepTimeRem'] = tk.Label(pyGui.frameDict['RecipeDetails'], text=' 0.00 ', relief=tk.SUNKEN, width=7, bg='white', anchor='w')
    pyGui.featureDict['Label']['Recipe']['StepTimeRem_Lab'] = tk.Label(pyGui.frameDict['RecipeDetails'], text='Time Remaining in Current Step')
    pyGui.featureDict['Label']['Recipe']['StartStepName'] = tk.Label(pyGui.frameDict['RecipeDetails'], text=' ', relief=tk.SUNKEN, width=15, bg='white')
    pyGui.featureDict['Label']['Recipe']['EndStepName'] = tk.Label(pyGui.frameDict['RecipeDetails'], text=' ', relief=tk.SUNKEN, width=15, bg='white')
    pyGui.featureDict['Button']['Recipe']['EStop'] = tk.Button(pyGui.frameDict['RecipeDetails'], text="EMERGENCY STOP", bg="red", font=pyGui.fontDict['Button'], width=20,
                             command=pyGui.estop_click)
    
    pyGui.featureDict['Label']['Recipe']['LamLabel'] = [tk.Label(pyGui.frameDict['RecipeDetails'], text='Laminate # '+str(j+1)) for j in range(pyGui.numLams)]
    pyGui.featureDict['Entry']['Recipe']['LamEntry'] = [tk.Entry(pyGui.frameDict['RecipeDetails'], relief=tk.SUNKEN, width=7, justify='center', bg='white') for j in range(pyGui.numLams)]
    pyGui.featureDict['Label']['Recipe']['CurrLamLab'] = [tk.Label(pyGui.frameDict['RecipeDetails'], text='Current Lam. \n # '+str(j+1)) for j in range(pyGui.numLams)]
    pyGui.featureDict['Label']['Recipe']['CurrLamDisp'] = [tk.Label(pyGui.frameDict['RecipeDetails'], relief = tk.SUNKEN, width=7, justify='center', bg='white') for j in range(pyGui.numLams)]
    
    for j in range(pyGui.numLams):
        pyGui.featureDict['Entry']['Recipe']['LamEntry'][j].insert(0, 1)

    pyGui.featureDict['Entry']['Recipe']['CycleNumEntry'] = [tk.Entry(pyGui.frameDict['RecipeDetails'], justify='center', width=7) for j in range(pyGui.numCycles)]
    pyGui.featureDict['Label']['Recipe']['CycleLab'] = [tk.Label(pyGui.frameDict['RecipeDetails'], text='Cycle '+str(j + 1)) for j in range(pyGui.numCycles)]
    pyGui.featureDict['Label']['Recipe']['CurrStepDisp'] = [tk.Label(pyGui.frameDict['RecipeDetails'], text=' ', relief=tk.SUNKEN, width=7, bg='white') for j in range(pyGui.numCycles)]
    pyGui.featureDict['Label']['Recipe']['CurrStepLab'] = [tk.Label(pyGui.frameDict['RecipeDetails'], text='Current ' +str(j+1)) for j in range(pyGui.numCycles)]
    pyGui.featureDict['Label']['Recipe']['CurrStepName'] = [tk.Label(pyGui.frameDict['RecipeDetails'], text=' ', relief=tk.SUNKEN, width=15, bg='white') for j in range(pyGui.numCycles)]
    
    for j in range(pyGui.numCycles):
        pyGui.featureDict['Entry']['Recipe']['CycleNumEntry'][j].insert(0, 0)

    ''' Recipe Length Frame '''
    pyGui.featureDict['Label']['Recipe']['RecipeLenLab'] = tk.Label(pyGui.frameDict['RecipeLength'], text='Recipe Length: ')
    pyGui.featureDict['Label']['Recipe']['RecipeLenTime'] = tk.Label(pyGui.frameDict['RecipeLength'], text='0h : 0m : 0s', width=20, bg='white', relief=tk.SUNKEN)
    pyGui.featureDict['Label']['Recipe']['RecipeStartTimeLab'] = tk.Label(pyGui.frameDict['RecipeLength'], text='Recipe Start Time: ')
    pyGui.featureDict['Label']['Recipe']['RecipeStartTime'] = tk.Label(pyGui.frameDict['RecipeLength'], text=' ', width=25, bg='white', relief=tk.SUNKEN)
    pyGui.featureDict['Label']['Recipe']['RecipeEndTimeLab'] = tk.Label(pyGui.frameDict['RecipeLength'], text='Recipe End Time: ')
    pyGui.featureDict['Label']['Recipe']['RecipeEndTime'] = tk.Label(pyGui.frameDict['RecipeLength'], text=' ', width=25, bg='white', relief=tk.SUNKEN)

    ''' Valve Frame '''
    pyGui.featureDict['Label']['Valve'] = {}
    pyGui.featureDict['Entry']['Valve'] = {}
    pyGui.featureDict['Button']['Valve'] = {}
    #valve_num_labels = []
    #valve_desc_labels = []
    #valve_buttons = []

    #pyGui.numValves = 16
    pyGui.valveLabels = pyGui.configDict['ValveLabels']

    # Add extra labels if not enough are specified
    if len(pyGui.valveLabels) < pyGui.NUM_VALVES:
        xtra = pyGui.NUM_VALVES - len(pyGui.valveLabels)
        for k in range(xtra):
            pyGui.valveLabels.append('Not Specified')

    ''' Create two sets of valve labels and valve buttons '''
    pyGui.featureDict['Label']['Valve']['ValveNum'] = [tk.Label(pyGui.frameDict['Valve'], text='V'+str(j),font=pyGui.fontDict['Valve']) for j in range(pyGui.NUM_VALVES)]
    pyGui.featureDict['Label']['Valve']['ValveDesc'] = [tk.Label(pyGui.frameDict['Valve'], text=pyGui.valveLabels[j], font=pyGui.fontDict['Valve'], justify='center') for j in range(pyGui.NUM_VALVES)]
    pyGui.featureDict['Button']['Valve']['ValveButtons'] = [tk.Button(pyGui.frameDict['Valve'], text='OFF', bg='red', font=pyGui.fontDict['Button'], state='disabled',command=partial(pyGui.valveButtonClick, j)) for j in range(pyGui.NUM_VALVES)]

    ''' --------------------- Widget Layout -----------------------------'''

    pyGui.frameDict['RecipeControl'].grid(row=0, column=0, rowspan=1, ipadx=5, ipady=5)
    #recipe_control_frame.grid(row=0, column=0, rowspan=1, ipadx=5, ipady=5)
    pyGui.frameDict['Recipe'].grid(row=1, column=0, rowspan=5, ipadx=1, ipady=1, padx=1)
    #recipe_frame.grid(row=1, column=0, rowspan=5, ipadx=1, ipady=1, padx=1)
    pyGui.frameDict['RecipeDetails'].grid(row=0, column=1, rowspan=4, ipadx=5, ipady=5, padx=5, pady=5)
    #recipe_details_frame.grid(row=0, column=1, rowspan=4, ipadx=5, ipady=5, padx=5, pady=5)
    pyGui.frameDict['RecipeLength'].grid(row=6, column=0, rowspan=1, ipadx=5, ipady=5, padx=5)
    #recipe_length_frame.grid(row=6, column=0, rowspan=1, ipadx=5, ipady=5, padx=5)
    pyGui.frameDict['Valve'].grid(row=0, column=2, rowspan=8, padx=5, pady=5)
    #valve_frame.grid(row=0, column=2, rowspan=8, padx=5, pady=5)
    
    for i in range(10):
       pyGui.app.grid_rowconfigure(i, weight=1)
    
    pyGui.app.grid_columnconfigure(0, weight=1)
    pyGui.app.grid_columnconfigure(1, weight=1)
    pyGui.app.grid_columnconfigure(2, weight=1)

    #if num_valves > 16:
    #    valve_frame2.grid(row=0, column=3, rowspan=8, padx=5, pady=5)
    
    pyGui.frameDict['RecipeHeaders'].pack(fill='both') # Pack this frame in recipe_frame
    #recipe_headers_frame.pack(fill='both')      
    pyGui.featureDict['Button']['Recipe']['CalcLen'].pack(side=tk.BOTTOM, pady=2)
    #calc_len_button.pack(side=tk.BOTTOM, pady=2)     # Pack this button in recipe_frame
    pyGui.featureDict['Button']['Recipe']['DelLine'].pack(side=tk.BOTTOM, pady=2)
    pyGui.featureDict['Button']['Recipe']['AddLine'].pack(side=tk.BOTTOM, pady=2)
    pyGui.featureDict['Button']['Recipe']['Preview'].pack(side=tk.BOTTOM, pady=2)
    #del_line_button.pack(side=tk.BOTTOM, pady=2)     # Pack this button in recipe_frame
    #add_line_button.pack(side=tk.BOTTOM, pady=2)     # Pack this button in recipe_frame
    #recipe_prev_button.pack(side=tk.BOTTOM, pady=2)  # Pack this button in recipe_frame
    
    
    pyGui.recipe_canvas.pack(side=tk.LEFT, fill='y', expand=True)     # Pack this canvas in recipe_frame
    pyGui.frameDict['RecipeEdit'].pack(fill='both')     # Pack this frame in recipe_canvas

    pyGui.vsb.pack(side=tk.LEFT, fill='y')  # Pack this vertical scrollbar in recipe_frame
    
    pyGui.frameDict['RecipeEdit'].bind("<Configure>", lambda event, canvas=pyGui.recipe_canvas: pyGui.on_frame_config(canvas))
    pyGui.recipe_canvas.create_window((5, 5), window=pyGui.frameDict['RecipeEdit'], anchor='ne')

    ''' Edit recipe frame '''
    pyGui.featureDict['Label']['Recipe']['CurrentRecipe'].grid(row=0, column=0, columnspan=2)
    #curr_recipe_label.grid(row=0, column=0, columnspan=2)
    for j in range(6):
        pyGui.featureDict['Label']['Recipe']['Col'][j].grid(row=1, column=j)
        pyGui.frameDict['RecipeEdit'].grid_columnconfigure(j, weight=1)
    for i in range(pyGui.recipe_window_len):
        pyGui.featureDict['Label']['Recipe']['Row'][i].grid(row=i+2, column=0, sticky='ew')
        pyGui.featureDict['Entry']['Recipe']['Time'][i].grid(row=i+2, column=1, sticky='ew', padx=5, pady=2)

        pyGui.featureDict['Entry']['Recipe']['StepName'][i].grid(row=i+2, column=2, sticky='ew', padx=5, pady=2)
        pyGui.featureDict['Combobox']['Recipe']['StepType'][i].grid(row=i+2, column=3, sticky='ew', padx=5, pady=2)
        pyGui.featureDict['Combobox']['Recipe']['Laminate'][i].grid(row=i+2, column=4, sticky='ew', padx=5, pady=2)
        pyGui.featureDict['Entry']['Recipe']['Actuator'][i].grid(row=i+2, column=5, sticky='ew', padx=5, pady=2)
        pyGui.frameDict['RecipeEdit'].grid_rowconfigure(i+2, weight=1)

    ''' Edit recipe frame '''
    pyGui.featureDict['Button']['Recipe']['Load'].grid(row=0, column=0, padx=5, pady=5)
    pyGui.featureDict['Button']['Recipe']['Save'].grid(row=0, column=1, padx=5, pady=5, sticky='e')
    pyGui.featureDict['Button']['Recipe']['Manual'].grid(row=3, column=0, columnspan=2, pady=15, sticky='ew', padx=10)
    pyGui.featureDict['Button']['Recipe']['Play'].grid(row=4, column=0, padx=2, pady=1, sticky='w')
    pyGui.featureDict['Button']['Recipe']['Stop'].grid(row=4, column=1, padx=2, pady=1, sticky='e')
    pyGui.featureDict['Label']['Recipe']['FilenameLabel'].grid(row=1, column=0)
    pyGui.featureDict['Label']['Recipe']['Filename'].grid(row=1, column=1, padx=2, pady=5)
    pyGui.featureDict['Label']['Recipe']['ExpComment'].grid(row=2, column=0, padx=5, pady=5)
    pyGui.featureDict['Entry']['Recipe']['ExpComment'].grid(row=2, column=1, padx=5, pady=5)
    
    pyGui.frameDict['RecipeEdit'].grid_rowconfigure(0, weight=1)
    pyGui.frameDict['RecipeEdit'].grid_rowconfigure(1, weight=1)
    pyGui.frameDict['RecipeEdit'].grid_rowconfigure(2, weight=1)
    pyGui.frameDict['RecipeEdit'].grid_rowconfigure(3, weight=1)
    
    pyGui.frameDict['RecipeEdit'].grid_columnconfigure(0, weight=1)
    pyGui.frameDict['RecipeEdit'].grid_columnconfigure(1, weight=1)

    ''' Recipe Details Frame '''
    pyGui.featureDict['Button']['Recipe']['EStop'].grid(row=0, column=0, rowspan=2, columnspan=3, pady=5)
    pyGui.featureDict['Label']['Recipe']['StepTimeRem_Lab'].grid(row=2, column=0, columnspan=3, ipadx=5)
    pyGui.featureDict['Label']['Recipe']['StepTimeRem'].grid(row=3, column=1, ipadx=5, pady=5)
    pyGui.featureDict['Label']['Recipe']['StartStepName'].grid(row=5, column=1, ipadx=5, pady=5)
    
    pyGui.featureDict['RecipeDetail'].grid_rowconfigure(0, weight=1)
    pyGui.featureDict['RecipeDetail'].grid_rowconfigure(1, weight=1)
    pyGui.featureDict['RecipeDetail'].grid_rowconfigure(2, weight=1)
    pyGui.featureDict['RecipeDetail'].grid_rowconfigure(3, weight=1)
    pyGui.featureDict['RecipeDetail'].grid_rowconfigure(4, weight=1)
    pyGui.featureDict['RecipeDetail'].grid_rowconfigure(5, weight=1)
    pyGui.featureDict['RecipeDetail'].grid_rowconfigure(6, weight=1)
    
    
    pyGui.featureDict['RecipeDetail'].grid_columnconfigure(0, weight=1)
    pyGui.featureDict['RecipeDetail'].grid_columnconfigure(1, weight=1)
    pyGui.featureDict['RecipeDetail'].grid_columnconfigure(2, weight=1)

    for i in range(pyGui.numCycles):
        pyGui.featureDict['Entry']['Recipe']['CycleNumEntry'][i].grid(row=2*i+7, column=0, padx=1)
        pyGui.featureDict['Label']['Recipe']['CycleLab'][i].grid(row=2*i+6, column=0, padx=1)
        pyGui.featureDict['Label']['Recipe']['CurrStepDisp'][i].grid(row=2*i+7, column=2, padx=1)
        pyGui.featureDict['Label']['Recipe']['CurrStepLab'][i].grid(row=2*i+6, column=2, padx=1)
        pyGui.featureDict['Label']['Recipe']['CurrStepName'][i].grid(row=2*i+7, column=1, ipadx=5, padx=1)
        
        pyGui.frameDict['RecipeDetail'].grid_rowconfigure(2*i+6, weight=1)
        pyGui.frameDict['RecipeDetail'].grid_rowconfigure(2*i+7, weight=1)

    pyGui.featureDict['Label']['Recipe']['EndStepName'].grid(row=2*i+8, column=1, ipadx=5, padx=0, pady=8)
    pyGui.frameDict['RecipeDetail'].grid_rowconfigure(2*i+8, weight=1)
    pyGui.frameDict['RecipeDetail'].grid_rowconfigure(2*i+9, weight=1)

    for m in range(pyGui.numLams):
        pyGui.featureDict['Label']['Recipe']['LamLabel'][m].grid(row=2*i+10+(2*m), column=0, padx=1)
        pyGui.featureDict['Entry']['Recipe']['LamEntry'][m].grid(row=2*i+11+2*m, column=0, padx=1)
        pyGui.featureDict['Label']['Recipe']['CurrLamLab'][m].grid(row=2*i+10+2*m, column=2, padx=1)
        pyGui.featureDict['Label']['Recipe']['CurrLamDisp'][m].grid(row=2*i+11+2*m, column=2, padx=1)
        
        pyGui.frameDict['RecipeDetail'].grid_rowconfigure(2*i+10+2*m, weight=1)
        pyGui.frameDict['RecipeDetail'].grid_rowconfigure(2*i+11+2*m, weight=1)

    ''' Recipe Length Frame '''
    pyGui.featureDict['Label']['Recipe']['RecipeLenLab'].grid(row=0, column=0, padx=10, pady=5)
    pyGui.featureDict['Label']['Recipe']['RecipeLenTime'].grid(row=0, column=1, padx=10, pady=5)
    pyGui.featureDict['Label']['Recipe']['RecipeStartTimeLab'].grid(row=1, column=0, padx=10, pady=5)
    pyGui.featureDict['Label']['Recipe']['RecipeStartTime'].grid(row=1, column=1, padx=10, pady=5)
    pyGui.featureDict['Label']['Recipe']['RecipeEndTimeLab'].grid(row=2, column=0, padx=10, pady=5)
    pyGui.featureDict['Label']['Recipe']['RecipeEndTime'].grid(row=2, column=1, padx=10, pady=5)
    
    pyGui.frameDict['RecipeLength'].grid_rowconfigure(0, weight=1)
    pyGui.frameDict['RecipeLength'].grid_rowconfigure(1, weight=1)
    pyGui.frameDict['RecipeLength'].grid_rowconfigure(2, weight=1)
    
    pyGui.frameDict['RecipeLength'].grid_columnconfigure(0, weight=1)
    pyGui.frameDict['RecipeLength'].grid_columnconfigure(1, weight=1)

    ''' Valve Frame '''
    for i in range(pyGui.NUM_VALVES):
        if i <= 15:
            pyGui.featureDict['Label']['Valve']['ValveNum'][i].grid(row=i, column=0, ipadx=2.5, padx=2.5, sticky='e')
            pyGui.featureDict['Label']['Valve']['ValveDesc'][i].grid(row=i, column=2, pady=5, padx=2.5, sticky='w')
            pyGui.featureDict['Button']['Valve']['ValveButtons'][i].grid(row=i, column=1, ipadx=5, ipady=0, padx=2.5, pady=2.5)
            pyGui.frameDict['Valve'].grid_rowconfigure(i, weight = 1)
        #else:
        #    valve_num_labels[i].grid(row=i-16, column=0, ipadx=2.5, padx=2.5, sticky='e')
        #    valve_desc_labels[i].grid(row=i-16, column=2, pady=5, padx=2.5, sticky='w')
        #    valve_buttons[i].grid(row=i-16, column=1, ipadx=5, ipady=0, padx=2.5, pady=2.5)
        #    valve_frame2.grid_rowconfigure(i-16, weight = 1)
    pyGui.frameDict['Valve'].grid_columnconfigure(0, weight=1)
    pyGui.frameDict['Valve'].grid_columnconfigure(1, weight=1)
    pyGui.frameDict['Valve'].grid_columnconfigure(2, weight=1)
    
    #if num_valves > 16:
    #    valve_frame2.grid_columnconfigure(0, weight=1)
    #    valve_frame2.grid_columnconfigure(1, weight=1)
    #    valve_frame2.grid_columnconfigure(2, weight=1)
    
    # Check if instrument was found
    #if my_inst == 0:
    #    tkinter.messagebox.showinfo('Warning', 'No Instrument Detected! Check COM port.')

        # Focus_force entry widgets to allow interactivity after messagebox pops up
    for i in range(pyGui.recipe_window_len):
        pyGui.featureDict['Entry']['Recipe']['Time'][i].focus_force()
        pyGui.featureDict['Entry']['Recipe']['StepName'][i].focus_force()
        pyGui.featureDict['Combobox']['Recipe']['StepType'][i].focus_force()
        pyGui.featureDict['Combobox']['Recipe']['Laminate'][i].focus_force()
        pyGui.featureDict['Entry']['Recipe']['Actuator'][i].focus_force()

    for i in range(pyGui.numLams):
        pyGui.featureDict['Entry']['Recipe']['LamEntry'][i].focus_force()

    for i in range(pyGui.numCycles):
        pyGui.featureDict['Entry']['Recipe']['CycleNumEntry'][i].focus_force()

    ''' function to check queue for gui actions '''
    def updateStatus():
        #if not pyGui.gQueue.empty():
        try:   
            guiTask = pyGui.gQueue.get_nowait()

            if guiTask[0] == 'Config':
                pyGui.configDict = guiTask[1]
            elif guiTask[0] == 'Set_Interlocks':
                pyGui.VALVE_INTERLOCKS = guiTask[1]
            elif guiTask[0] == 'Reset_Valves':
                pyGui.resetValveButtons()
            elif guiTask[0] == 'Edit':
                labs = guiTask[1]
                d = guiTask[2]
                for key in d:
                    #pyGui.featureDict[labs[0]][labs[1]][labs[2]].config(key=d[key])
                    if key == 'text':
                        if len(labs)>3:
                            if len(labs[3])>1:
                                for j in range(len(labs[3])):
                                    pyGui.featureDict[labs[0]][labs[1]][labs[2]][labs[3][j]].config(text=d[key])
                                else:
                                    pyGui.featureDict[labs[0]][labs[1]][labs[2]][labs[3]].config(text=d[key])
                        else:
                            pyGui.featureDict[labs[0]][labs[1]][labs[2]].config(text=d[key])
                                
                    elif key == 'state':
                        if len(labs)>3:
                            if len(labs[3])>1:
                                for j in range(len(labs[3])):
                                    pyGui.featureDict[labs[0]][labs[1]][labs[2]][labs[3][j]].config(state=d[key])
                                else:
                                    pyGui.featureDict[labs[0]][labs[1]][labs[2]][labs[3]].config(state=d[key])
                        else:
                            pyGui.featureDict[labs[0]][labs[1]][labs[2]].config(state=d[key])
                                
                    elif key == 'bg':
                        if len(labs)>3:
                            if len(labs[3])>1:
                                for j in range(len(labs[3])):
                                    pyGui.featureDict[labs[0]][labs[1]][labs[2]][labs[3][j]].config(bg=d[key])
                                else:
                                    pyGui.featureDict[labs[0]][labs[1]][labs[2]][labs[3]].config(bg=d[key])
                        else:
                            pyGui.featureDict[labs[0]][labs[1]][labs[2]].config(bg=d[key])
                                
                    elif key == 'fg':
                        if len(labs)>3:
                            if len(labs[3])>1:
                                for j in range(len(labs[3])):
                                    pyGui.featureDict[labs[0]][labs[1]][labs[2]][labs[3][j]].config(fg=d[key])
                                else:
                                    pyGui.featureDict[labs[0]][labs[1]][labs[2]][labs[3]].config(fg=d[key])
                        else:
                            pyGui.featureDict[labs[0]][labs[1]][labs[2]].config(fg=d[key])
                    elif key == 'relief':
                        if len(labs)>3:
                            if len(labs[3])>1:
                                for j in range(len(labs[3])):
                                    pyGui.featureDict[labs[0]][labs[1]][labs[2]][labs[3][j]].config(relief=d[key])
                                else:
                                    pyGui.featureDict[labs[0]][labs[1]][labs[2]][labs[3]].config(relief=d[key])
                        else:
                            pyGui.featureDict[labs[0]][labs[1]][labs[2]].config(relief=d[key])
        except queue.Empty():
            root.info('No tasks in GUI queue')

        pyGui.app.update()
        pyGui.app.after(25, updateStatus())
        

    pyGui.app.after(1, updateStatus())
    pyGui.app.protocol('WM_DELETE_WINDOW', pyGui.ask_quit)
    pyGui.app.mainloop()
    #pyGui.createWindow()
    valveQueue.put_nowait(['Shutdown'])
    timerQueue.put_nowait(['Shutdown'])
    recipeIQueue.put_nowait(['Shutdown'])
    recipeCQueue.put_nowait(['Shutdown'])
    
    
    
def valveThread(guiQueue, valveQueue, timerQueue, recipeIQueue, recipeCQueue, logQueueIn, configurer, pyV):
    
    configurer(logQueueIn)
    root = logging.getLogger()
    root.info('valveThread started')
    
    #pyV = pyALD.ValveOp(nValves=16)
    #pyV.setInitialization(initDict)
    
    while True:
        try:
            valveTask = valveQueue.get()
            if valveTask[0] == 'Reset':
                pyV.reset_valves()
                root.info('Resetting valves')
            elif valveTask[0] == 'On':
                vNum = valveTask[1]
                onList = valveTask[2]
                pyV.valve_on(vNum, on_valves=onList)
                root.info('Valve # {} ON'.format(vNum))
            elif valveTask[0] == 'Off':
                vNum = valveTask[1]
                pyV.valve_off(vNum)
                root.info('Valve # {} OFF'.format(vNum))
            elif valveTask[0] == 'Multi':
                valvesON = valveTask[1]
                step = valveTask[2]
                pyV.multi_valve_op(valvesON, step=step)
                root.info('Valve sequence {} submitted'.format(seq))
            elif valveTask[0] == 'Check':
                valves, event, stepNum = valveTask[1]
                root.info('Checking valve interlocks')
                flag = pyV.check_interlock(pyGui.featureDict['Button']['Valve']['ValveButtons'], valves)
                if flag:
                    msg = pyV.trigger_interlock(event, stepNum)
                    root.info('Interlock triggered! ' + msg)
            elif valveTask[0] == 'Set_Interlocks':
                pyV.VALVE_INTERLOCKS = valveTask[1]
            elif valveTask[0] == 'Shutdown':
                root.info('Shutting down valve thread')
                break
        except queue.Empty:
            root.info('No tasks in valve queue')


def timerThread(guiQueue, valveQueue, timerQueue, recipeIQueue, recipeCQueue, logQueueIn, configurer):
    
    configurer(logQueueIn)
    root = logging.getLogger()
    root.info('timerThread started')
    while True:
        try:
            timeTask = timerQueue.get_nowait()
        
            if timeTask[0] == 'Start':
                root.info('Starting timer')
                STOP = False
                stepTime = timeTask[1]
                guiQueue.put_nowait(['Update', ['Label','Recipe','StepTimeRem'], {'text':str(stepTime)}])
                time_start = time()
                time_rem = stepTime
                
                while time_rem > 0.1 and not STOP:
                    if timerQueue.empty():
                        time_rem = stepTime -(time() - time_start)
                        guiQueue.put(['Edit', ['Label','Recipe','StepTimeRem'], {'text':str(time_rem)}])
                        guiQueue.put(['Update'])
                    else:
                        tt = timerQueue.get()
                        if tt[0] == 'STOP':
                            STOP = True
                else:
                    guiQueue.put(['Edit',['Label','Recipe','StepTimeRem'], {'text':'0.00'}])
                    #guiQueue.put(['Update',time_rem])
                    time_rem = stepTime - (time() - time_start)
                    #recipeQueue.put_nowait(['Next'])
                
                    recipeIQueue.put(['Next'])
                    root.info('Finish step timer')
                    
            elif timeTask[0] == 'Shutdown':
                root.info('Shutting down timer thread')
                break
        
        except queue.Empty:
            root.info('No tasks in timer queue')
            
def recipeInterfaceThread(guiQueue, valveQueue, timerQueue, recipeIQueue, recipeCQueue, logQueueIn, configurer, pyR):
    
    configurer(logQueueIn)
    root = logging.getLogger()
    root.info('recipeThread started')
    
    while True:
        try:
            recipeTask = recipeIQueue.get_nowait()
            
            if recipeTask[0] == 'Start':
                #pyR.playRecipe(recipeTask[1], recipeTask[2], recipeTask[3])
                pass
            elif recipeTask[0] == 'Stop':
                pyR.STOP = True
            elif recipeTask[0] == 'Next':
                pass
            elif recipeTask[0] == 'Shutdown':
                root.info('Shutting down recipe thread')
                break
            
        except queue.Empty:
            root.info('No tasks in recipe interface queue')

         
def recipeControlThread(guiQueue, valveQueue, timerQueue, recipeIQueue, recipeCQueue, logQueueIn, configurer, pyR):
    
    configurer(logQueueIn)
    root = logging.getLogger()
    root.info('recipeThread started')
    
    while True:
        try:
            recipeTask = recipeCQueue.get_nowait()
            
            if recipeTask[0] == 'Start':
                pyR.setRecipeParams(rd=recipeTask[1], ld=recipeTask[2], cd=recipeTask[3])
                pyR.checkRecipe()
                pyR.startRecipe()
            elif recipeTask[0] == 'Stop':
                pyR.STOP = True
            elif recipeTask[0] == 'Next':
                pass
            elif recipeTask[0] == 'Shutdown':
                root.info('Shutting down recipe thread')
                break
            
        except queue.Empty:
            root.info('No tasks in recipe control queue')
    
            
            
def loggerThread(logQueueIn, logReadyEventIn, configurer):
    configurer()
    logReadyEventIn.set()
    while True:
        try:
            record = logQueueIn.get()
            if record is None:
                break
            logger = logging.getLogger(record.name)
            logger.handle(record)
        except Exception:
            import sys, traceback
            print('Problem: ', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            
def exit_handler(valveQueue):
    # Reset all valves if python exits
    #pyV.reset_valves()
    valveQueue.put_nowait(['Reset'])
    

def initializationGui():
    
    def setValveInterlocks():
        
        def complete_interlocks():
            global interlockDict
            
            for j in range(c):
                interlockDict[j] = []
                for i in range(r):
                    if len(entryDict[i][j].get()) != 0:
                        interlockDict[j].append(int(entryDict[i][j].get().replace(' ','')))
            return
                    
            for i in range(r):
                
                colLabels[i].grid(row=i+1,column=0)
            for j in range(c):
                rowLabels[j].grid(row=0, column=j+1)
                entryDict[i][j].grid(row=i+1,column=j+1) 
            win.destroy()
            
        
        global interlockDict
        
        win = tk.Toplevel()
        win.geometry("250x200")
        win.title('Valve Interlocks')
        r = 8
        c = 5
        
        interlockDict = {}
        
        button_set = tk.Button(win, text='Set Interlocks', command=complete_interlocks)
        rowLabels = [tk.Label(win, text='Interlock Column '+str(i)) for i in range(c)]
        colLabels = [tk.Label(win, text='Row '+str(i)) for i in range(r)]
        entryDict = {}
        for i in range(r):
            entryDict[i] = [tk.Entry(win, justify='center',width=7) for j in range(c)]
            
        for i in range(r):
            colLabels[i].grid(row=i+1,column=0)
            for j in range(c):
                rowLabels[j].grid(row=0, column=j+1)
                entryDict[i][j].grid(row=i+1,column=j+1)
                
        button_set.grid(row=r+2, column=0, columnspan=2)
        
        win.mainloop()
        
        return

    
    def setValveLabels():
        
        def complete_labels():
            global valveLabels
            #valveLabels = []
            for i in range(NUM_VALVES):
                valveLabels.append(entries[i].get())
            
            win.destroy()
            
            return
        
        win = tk.Toplevel()
        win.geometry("250x200")
        win.title('Valve Labels')
        #r = 8
        #c = 5
        
        global valveLabels
        
        #interlockDict = {}
        NUM_VALVES = 16
        valveLabels = []
        
        button_set = tk.Button(win, text='Set labels', command=complete_labels)
        rowLabels = [tk.Label(win, text='Valve '+str(i)) for i in range(NUM_VALVES)]
        entries = [tk.Entry(win, justify='center', width=7) for i in range(NUM_VALVES)]
                
        for i in range(NUM_VALVES):
            rowLabels[i].grid(row=i, column=0)
            entries[i].grid(row=i, column=1)
            
        button_set.grid(row=NUM_VALVES+1, column=0, columnspan=2)
        
        win.mainloop()
    
    def complete():
        global initDict
        if len(entry_cycleNum) == 0:
            nC = 3
        else:
            nC = int(entry_cycleNum.get().replace(' ',''))
        
        if len(entry_lamNum) == 0:
            nL = 1
        else:
            nL = int(entry_lamNum.get().replace(' ',''))
            
        if len(entry_valveCOM) == 0:
            vC = 0
        else:
            vC = int(entry_valveCOM.get().replace(' ',''))
            
        initDict['nCycles'] = nC
        initDict['nLaminates'] = nL
        initDict['valveCOM'] = vC
        
        app.destroy()
    
    initDict = {}
    
    ''' Create GUI to allow user to input initialization parameters '''
    app = tk.Tk()
    app.title('Control Box Initialization Parameters')
    screenWidth = app.winfo_screenwidth()
    screenHeight = app.winfo_screenheight()
    geom = '%dx%d' %(screenWidth*0.85, screenHeight*0.85)
    app.geometry(geom)
    
    font_button = font.Font(size=14, weight='bold')
    font_label = font.Font(size=14)
    
    button_valveInterlock = tk.Button(app, text='Set Valve Interlocks', font=font_button,command=setValveInterlocks)
    button_valveLabels = tk.Button(app, text='Set Valve Labels', font=font_button, command=setValveLabels)
    button_complete = tk.Button(app, text='Complete Initialization', font=font_button, command=complete)
    
    label_valveCOM = tk.Label(app, text='Valve COM Port', font=font_label)
    label_cycleNum = tk.Label(app, text='Number of Cycles:',font=font_label)
    label_lamNum = tk.Label(app, text='Number of Laminates:',font=font_label)
    
    entry_valveCOM = tk.Entry(app, justify='center',width=7)
    entry_cycleNum = tk.Entry(app, justify='center', width=7)
    entry_lamNum = tk.Entry(app, justify='center', width=7)
    
    label_valveCOM.grid(row=0,column=0)
    entry_valveCOM.grid(row=0,column=1)
    
    label_cycleNum.grid(row=1,column=0)
    entry_cycleNum.grid(row=1,column=1)
    
    label_lamNum.grid(row=2,column=0)
    entry_lamNum.grid(row=2,column=1)

    button_valveInterlock.grid(row=3,column=0)
    button_valveLabels.grid(row=3,column=1)
    button_complete.grid(row=4,column=0,columnspan=2)
    
    app.mainloop()
    
    initDict['ValveLabels'] = valveLabels
    initDict['ValveInterlocks'] = interlockDict
    
    return initDict

def getValveCOM():
    pass
    

if __name__ == "__main__":
    
    ''' Startup steps
       - Initiate communication w/ hardware
       - Reset valves
       - Set exit handler
       - Initiate mp and threads
    '''
    pyV = pyALD.ValveOp(nValves=16)
    #pyGui = pyALD.GUI(nValves=16, nCycles=3, nLaminates=1)
    #pySeq = pyALD.sequencerOperations()
    pyR = pyALD.RecipeOp(nValves=16)
    
    # Reset valves on startup
    #seq = '0' * NUM_VALVES
    pyV.reset_valves()
    
    # Call function exit_handler at python exit
    atexit.register(exit_handler)
    
    ''' Initialization GUI '''
    initDict = initializationGui()
    
    pyV.setInitialization(initDict)
    pyR.setInitialization(initDict)
    
    ''' Initiate communication with valve controller '''
    inst = getValveCOM()
    
    ''' Multiprocessing manager '''
    manager = mp.Manager()
    
    ''' Logger setup '''
    logQueue = manager.Queue()
    logReadyEvent = manager.Event()
    loggerProcess = mp.Process(target=loggerThread, args=(logQueue, logReadyEvent, listener_log_configurer))
    loggerProcess.start()
    logReadyEvent.wait()

    ''' Queue setup '''
    guiQueue = manager.Queue()
    recipeIQueue = manager.Queue()
    recipeCQueue = manager.Queue()
    valveQueue = manager.Queue()
    timerQueue = manager.Queue()
    
    #pyGui.setQueues(rIQ=recipeIQueue, rCQ=recipeCQueue, vQ=valveQueue, gQ=guiQueue)
    pyV.setQueues(rIQ=recipeIQueue, rCQ=recipeCQueue, vQ=valveQueue, gQ=guiQueue)
    pyR.setQueues(rIQ=recipeIQueue, rCQ=recipeCQueue, vQ=valveQueue, gQ=guiQueue, tQ=timerQueue)
    #pySeq.setQueues(rQ=recipeQueue, vQ=valveQueue, gQ=guiQueue)
    
    ''' Gui process '''
    guiProcess = mp.Process(target=guiThread, args=(guiQueue, valveQueue, timerQueue, recipeIQueue, recipeCQueue, logQueue, worker_log_configurer, initDict))
    guiProcess.start()
    
    ''' valve process '''
    valveProcess = mp.Process(target=valveThread, args=(guiQueue, valveQueue, timerQueue, recipeIQueue, recipeCQueue, logQueue, worker_log_configurer, pyV, initDict))
    valveProcess.start()
    
    ''' timer process '''
    timerProcess = mp.Process(target=timerThread, args=(guiQueue, valveQueue, timerQueue, recipeIQueue, recipeCQueue, logQueue, worker_log_configurer))
    timerProcess.start()
    
    ''' recipe interface process '''
    recipeInterfaceProcess = mp.Process(target=recipeInterfaceThread, args=(guiQueue, valveQueue, timerQueue, recipeIQueue, recipeCQueue, logQueue, worker_log_configurer, pyR))
    recipeInterfaceProcess.start()
    
    ''' recipe control process '''
    recipeControlProcess = mp.Process(target=recipeControlThread, args=(guiQueue, valveQueue, timerQueue, recipeIQueue, recipeCQueue, logQueue, worker_log_configurer, pyR))
    recipeControlProcess.start()
    
    ''' Ask to select config file '''
    r = tk.Tk()
    r.withdraw()
    #fname = tk.filedialog.askopenfilename(initialdir='/', title='Select config file')
    #configDict = readConfigFile(fname)
    #guiQueue.put_nowait(['Config', configDict])
    #guiQueue.put_nowait(['Initialization',initDict])
    #valveQueue.put_nowait(['Initialization', initDict])
    #guiQueue.put_nowait(['Create'])
    
    guiProcess.join()
    valveProcess.join()
    timerProcess.join()
    recipeInterfaceProcess.join()
    recipeControlProcess.join()
    