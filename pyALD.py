# -*- coding: utf-8 -*-
"""
Created on Wed Mar 17 20:31:59 2021

@author: mfusc
"""
import tkinter as tk
from tkinter import font, filedialog
from tkinter import ttk
import tkinter.messagebox
from datetime import datetime
import logging
import os

# Import function 'partial' from 'functools'
from functools import partial

logger = logging.getLogger()


class GUI():
    
    def __init__(self, nValves=16, nCycles=3, nLaminates=1, vInterlocks=None):
        #self.createWindow()
        self.logger = logging.getLogger()
        self.logger.info('GUI Initializing...')
        self.logDir = ''
        self.STOP = False
        self.P_STOP = False
        self.NUM_VALVES = nValves
        #self.NUM_CYCLES = nCycles
        #self.NUM_LAMINATES = nLaminates
        #self.VALVE_INTERLOCKS = vInterlocks
    
    def setQueues(self, rCQ=None, rIQ=None, vQ=None, gQ=None):
        self.rCQueue = rCQ
        self.rIQueue = rIQ
        self.vQueue = vQ
        self.gQueue = gQ
        
    def setConfig(self, d):
        self.configDict = d
        
    def setLogger(self, a):
        
        self.root=a
        
    def setInitialization(self, initDict):
        
        self.NUM_CYCLES = initDict['nCycles']
        self.NUM_LAMINATES = initDict['nLaminates']
        self.VALVE_INTERLOCKS = initDict['valveInterlocks']
        self.VALVE_LABELS = initDict['valveLabels']
        
    def ask_quit(self):
        
        if tkinter.messagebox.askokcancel('Quit', 'Do you want to quit? Note that all valves will be reset'):
            # Reset all valves and close Tkinter window
            self.STOP = True
            self.vQueue.put_nowait(['Reset'])
            self.vQueue.put_nowait(['Shutdown'])
            self.rQueue.put_nowait(['Shutdown'])
            self.gQueue.put_nowait(['Shutdown'])
            self.logger.info('Shutting down...')
            self.app.destroy()
            #server.shutdown()
            
    def estop_click(self):
        """
        Determines what happens when the emergency stop button is clicked. Valves are reset to 'OFF', and an error
        message is displayed
        """
        #global stop
        self.logger.info('Emergency Stop Button Clicked')
        self.STOP = True
        # Resets all valves and stops recipe from running
        self.vQueue.put_nowait(['Reset'])
        # Resets all valve buttons to 'OFF'
        self.resetValveButtons()
        self.featureDict['Button']['Recipe']['Play'].config(text='Play', bg='green2', fg='black', state='normal')
        self.featureDict['Button']['Recipe']['Manual'].config(state='normal')
        tkinter.messagebox.showerror('Emergency Stop', "Emergency stop engaged. Valves have been reset. Please resolve"
                                                       " issues before continuing.")
    
    def valveButtonClick(self, v_num):
        """
        Function handling valve button clicks. Clicking a valve button will change its state to 'ON' or 'OFF'
        depending on its current state. A corresponding signal will also be sent to the control card, causing the
        valve to turn on or off.
        :param v_num: The number of the valve that was clicked
        """
        if self.featureDict['Button']['Valve']['ValveButtons'][v_num]['text'].replace(' ','') == 'OFF':
            on_num = []
            # Check which valves are currently actuated
            for i in range(self.NUM_VALVES):
                if self.featureDict['Button']['Valve']['ValveButtons'][i]['text'].replace(" ", "") == 'ON':
                    on_num.append(i)
                    
            self.vQueue.put_nowait(['On', v_num, on_num])
            #proceed = self.checkInterlock(self.featureDict['Button']['Valve']['ValveButtons'], v_num)
            """
            if proceed:
                self.featureDict['Button']['Valve']['ValveButtons'][v_num].config(text=' ON ', bg='green')
                # Call valve_on function from ValveOperation.py
                self.vQueue.put_nowait(['On',v_num])
            else:
                # Trigger interlock - shut all valves and provide error
                error_msg = trigger_interlock()
                reset_valve_buttons()
                tkinter.messagebox.showerror('Valve Interlock', error_msg)
            """
            
        else:
            #self.featureDict['Button']['Valve']['ValveButtons'][v_num].config(text='OFF', bg='red')
            # Call valve_off function from ValveOperation.py
            self.vQueue.put_nowait(['Off',v_num])
            
    def playButtonClick(self):
        if self.featureDict['Button']['Recipe']['Play']['text'] == 'Play':
            
            self.logger.info('Play Button Clicked')
            ''' Get recipe steps and cycle / laminate entries '''
            recipeDict = self.getRecipeSteps()
            lamEntryDict, cycleEntryDict = self.getLamCycleEntryValues()
            
            ''' Send start signal to recipe thread '''
            self.rCQueue.put_nowait(['Start', recipeDict, lamEntryDict, cycleEntryDict])
            self.STOP = False
            
            ''' Get recipe length and set labels '''
            self.getRecipeLength()
            
            ''' Reset current step/cycle/laminate labels '''
            self.featureDict['Label']['Recipe']['StartStepName'].config(text=' ')
            self.featureDict['Label']['Recipe']['EndStepName'].config(text=' ')
            
            for j in range(len(self.featureDict['Label']['Recipe']['CurrLamDisp'])):
                self.featureDict['Label']['Recipe']['CurrLamDisp'][j].config(text='0')
            for j in range(len(self.featureDict['Label']['Recipe']['CurrStepDisp'])):
                self.featureDict['Label']['Recipe']['CurrStepDisp'].config(text='0')
                self.featureDict['Label']['Recipe']['CurrStepName'].config(text=' ')
                
            ''' Disable buttons during recipe '''
            self.featureDict['Button']['Recipe']['Play'].config(state='disabled',fg='red',text='Running',bg='yellow')
            self.featureDict['Button']['Recipe']['Manual'].config(state='disabled',bg='green', relief=tk.RAISED)
            self.featureDict['Button']['Recipe']['Load'].config(state='disabled')
            self.featureDict['Button']['Recipe']['Save'].config(state='disabled')
            self.featureDict['Button']['Recipe']['AddLine'].config(state='disabled')
            self.featureDict['Button']['Recipe']['Preview'].config(state='disabled')
            self.featureDict['Button']['Recipe']['CalcLength'].config(state='disabled')
            [self.featureDict['Button']['Recipe']['ValveButtons'][j].config(state='disabled') for j in range(self.NUM_VALVES)]
                    
            # Create log file --------------------------------------------
            date = datetime.datetime.now().date()
            h = 0
            while True:
                h += 1
                log_file_name = str(date) + "_" + str(h) + ".txt"
                log_file_path = os.path.join(self.logDir, log_file_name)
                if os.path.exists(log_file_path):
                    pass
                else:
                    break
            self.log_file = open(log_file_path, 'w')
            self.log_file.write("Recipe: \n \n")
            for j in range(len(self.featureDict['Entry']['Recipe']['Time'])):
                if not self.featureDict['Entry']['Recipe']['Time'][j].get():
                    pass
                else:
                    self.log_file.write(self.featureDict['Entry']['Recipe']['Time'][j].get() + 
                                        "\t" + self.featureDict['Entry']['Recipe']['StepName'][j].get() +
                                        "\t" + self.featureDict['Combobox']['Recipe']['StepType'][j].get() + 
                                        "\t" + self.featureDict['Combobox']['Recipe']['Laminate'] + 
                                        "\t" + self.featureDict['Entry']['Recipe']['Actuator'][j].get()+"\n")
            self.log_file.write("\n")
            cycle_str = ''.join(str(cycleEntryDict[x])+"\t" for x in cycleEntryDict.keys())
            lam_str = ''.join(str(lamEntryDict[x])+"\t" for x in lamEntryDict.keys())
            self.log_file.write("Cycles: \t" + cycle_str + "\n")
            self.log_file.write("Laminates: \t" + lam_str + "\n \n")
            self.log_file.write('Experiment Comment: ' + self.featureDict['Entry']['Recipe']['ExpComment'].get() + "\n \n")
            # ----------------------------------------------------------------------------------
            # Write recipe start and timestamp to log file
            self.log_file.write('Recipe Start' + '\t\t\t' + str(datetime.datetime.now()) + '\n')
            self.logger.info('Recipe started')
            
            
        return
            
    
    def stopButtonClick(self):
        
        if self.featureDict['Button']['Recipe']['Play']['text'] == 'Running':
            self.STOP = True
            self.rQueue.put_nowait(['Stop'])
            self.vQueue.put_nowait(['Reset'])
            self.resetValveButtons()
        
    def resetValveButtons(self):
        for i in range(self.NUM_VALVES):
            self.featureDict['Button']['Valve']['ValveButtons'][i].config(text='OFF', bg='red', state='disabled')
        self.featureDict['Button']['Recipe']['Manual'].config(bg='green', relief=tk.RAISED)    
        
    def getLamCycleEntryValues(self):
        
        lamEntryDict = {}
        cycleEntryDict = {}
        for j in range(len(self.featureDict['Entry']['Recipe']['LamEntry'])):
            try:
                lamEntryDict[j] = int(self.featureDict['Entry']['Recipe']['LamEntry'][j].get())
            except ValueError:
                lamEntryDict[j] = 1
                self.featureDict['Entry']['Recipe']['LamEntry'][j].delete(0, 'end')
                self.featureDict['Entry']['Recipe']['LamEntry'][j].insert(0, 1)
        
        for j in range(len(self.featureDict['Entry']['Recipe']['CycleNumEntry'])):
            try:
                cycleEntryDict[j] = int(self.featureDict['Entry']['Recipe']['CycleNumEntry'][j].get())
            except ValueError:
                lamEntryDict[j] = 1
                self.featureDict['Entry']['Recipe']['CycleNumEntry'][j].delete(0, 'end')
                self.featureDict['Entry']['Recipe']['CycleNumEntry'][j].insert(0, 1)
                
        return lamEntryDict, cycleEntryDict
        
    def manualControlClick(self):
        """
        Function that handles when the manual control button is clicked. Clicking the button either enables or disables
        manual control of valve buttons, depending on the current state of the button. When manual control is enabled,
        valve buttons may be clicked to actuate valves. Otherwise, the buttons remain disabled.
        """
        #global p_stop
        if self.featureDict['Button']['Recipe']['Manual']['bg'] == 'green':
            self.featureDict['Button']['Recipe']['Manual'].config(bg='lime green', relief=tk.SUNKEN)
            if self.P_STOP:
                for i in range(len(self.NUM_VALVES)):
                    for j in self.VALVE_INTERLOCKS:
                        if i in self.VALVE_INTERLOCKS[j]:
                            break
                    else:
                        self.featureDict['Button']['Valve']['ValveButtons'][i].config(state='normal')
            else:
                for i in range(len(self.NUM_VALVES)):
                    self.featureDict['Button']['Valve']['ValveButtons'][i].config(state='normal')

        elif self.featureDict['Button']['Recipe']['Manual']['bg'] == 'lime green':
            self.featureDict['Button']['Recipe']['Manual'].config(bg='green', relief=tk.RAISED)
            for i in range(len(self.NUM_VALVES)):
                self.featureDict['Button']['Valve']['ValveButtons'][i].config(state='disabled')
                
    def load_recipe(self):
        """
        Function to load a recipe from a file. Columns must be tab separated, defaults to .txt
        Columns are arranged as: Step time, Step Name, Step type, Actuator list
        Recipe parameters are passed to their appropriate entry fields in the main window
        """
        global recipe_window_len

        self.app.filename = filedialog.askopenfilename(initialdir=self.recipe_dir,
                                                           title="Select File",
                                                           filetypes=(('text files', '*.txt'), ('all files',  '*.*')))
        if not self.app.filename:
            return
        g = 0
        for i in range(recipe_window_len):
            self.featureDict['Entry']['Recipe']['Time'][i].delete(0, 'end')
            self.featureDict['Entry']['Recipe']['StepName'][i].delete(0, 'end')
            self.featureDict['Combobox']['Recipe']['StepType'][i].delete(0, 'end')
            self.featureDict['Combobox']['Recipe']['Laminate'][i].delete(0, 'end')
            self.featureDict['Entry']['Recipe']['Actuator'][i].delete(0, 'end')

        if recipe_window_len >= 12:
            self.delete_recipe_lines(12)

        with open(self.app.filename, 'r') as z:
            for x in z.readlines():
                # Check if there are enough recipe lines
                if (g + 1) > recipe_window_len:
                    self.add_recipe_line()

                y = x.split("\t")
                try:
                    self.featureDict['Entry']['Recipe']['Time'][g].insert(0, float(y[0].replace(" ", "")))
                    self.featureDict['Entry']['Recipe']['StepName'][g].insert(0, y[1])
                    self.featureDict['Combobox']['Recipe']['StepType'][g].insert(0, y[2].replace(" ", ""))
                    self.featureDict['Combobox']['Recipe']['Laminate'][g].insert(0, y[3].replace(" ", ""))
                    self.featureDict['Entry']['Recipe']['Actuator'][g].insert(0, y[4].replace(" ", "").replace("\n", "").ljust(self.NUM_VALVES, '0'))
                    g += 1
                except ValueError:
                    pass
        short_filename = self.app.filename.split('/')
        self.recipe_filename.config(text=short_filename[-1])

    def save_recipe(self):
        """
        Function to save current recipe to a file. Saves as a tab separated file, defaults to .txt
        Columns are arranged as: Step time, Step Name, Step type, Actuator list
        Recipe parameters are taken from their appropriate entry fields in the main window
        """
        #global recipe_window_len

        self.app.filename = filedialog.asksaveasfile(mode="w", initialdir=self.recipe_dir,
                                                         title='Save File As', defaultextension=".txt",
                                                         filetypes=(("text file", "*.txt"), ("all files", "*.*")))
        if self.app.filename is None:
            return

        for i in range(self.recipe_window_len):
            # Check if step time field is empty
            if not self.featureDict['Entry']['Recipe']['Time'][i].get():
                pass
            # If not, write time, step name, step type, and actuator list to file
            else:
                self.app.filename.write(self.featureDict['Entry']['Recipe']['Time'][i].get().replace(" ", "") + "\t" +
                                    self.featureDict['Entry']['Recipe']['StepName'][i].get() + "\t" +
                                    self.featureDict['Combobox']['Recipe']['StepType'][i].get().replace(" ", "") + "\t" +
                                    self.featureDict['Combobox']['Recipe']['Laminate'][i].get().replace(" ", "") + "\t" +
                                    self.featureDict['Entry']['Recipe']['Actuator'][i].get().replace(" ", "").ljust(self.NUM_VALVES, '0') + "\n")
        self.app.filename.close()
        
        
    def getRecipeSteps(self):
        """
        Function to collect and parse recipe steps from the recipe entry fields. This function gets the timing, name,
        step type, and actuator string for each recipe step, placing them in separate lists to be accessed by other
        functions.
        :return: recipe_time, actuators, step_type, step_name [lists]
        """

        recipe_time = []
        actuators = []
        step_type = []
        step_name = []
        laminate = []
        lamDict = {}
        # Loop through recipe steps
        for i in range(self.recipe_window_len):
            # Check if step time field is empty
            if not self.featureDict['Entry']['Recipe']['Time'][i].get():
                pass
            # If not, add time, step type, and actuators to lists
            else:
                recipe_time.append(float(self.featureDict['Entry']['Recipe']['Time'][i].get().replace(" ", "")))
                step_name.append(self.featureDict['Entry']['Recipe']['StepName'][i].get())
                step_type.append(self.featureDict['Combobox']['Recipe']['StepType'][i].get().replace(" ", ""))
                laminate.append(self.featureDict['Combobox']['Recipe']['Laminate'][i].get().replace(" ", ""))
                actuators.append(self.featureDict['Entry']['Recipe']['Actuator'][i].get().replace(" ", ""))
                
                if 'start' in step_type[i].lower() or 'end' in step_type[i].lower():
                    pass
                else:
                    cNum = int(step_type[i].split('Cycle')[-1])
                    if laminate[i] not in lamDict:
                        lamDict[laminate[i]] = []
                    if cNum not in lamDict[laminate[i]]:
                        lamDict[laminate[i]].append(cNum)
                
        recipeDict = {'Time':recipe_time, 'Actuators':actuators, 'StepName':step_name, 'StepType':step_type, 'Laminate':laminate, 'Lam_Cycle':lamDict}
        return recipeDict
    
    def getActuatorList(self, actuators):
        """
        Function to get an integer list of valves to actuate from a string of 1's and 0's
        :param actuators: String of 1's and 0's indicating which valves should be actuated
        :return actuator_list: Integer list of valves to be actuated for each recipe step
        """
        actuator_list = []
        # Create integer list of engaged valves during each step
        for i in range(len(actuators)):
            if actuators[i] == '1':
                actuator_list.append(int(i))
    
        return actuator_list
    
    def recipePreview(self):
        """
        Function to preview valves actuated during recipe steps. Creates an overlay window to control
        recipe preview. Click through recipe steps to see which valves will be on and off during each step.
        """
        # Function to handle click events on next step button
        def next_click():
            global STEP
            STEP += 1
            curr_step_lab.config(text=str(STEP + 1) + ":  " + recipeDict['StepName'][STEP])
            show_valves()
            if STEP >= 1 and STEP + 1 == len(actuator_list):
                previous_step_button.config(state='normal')
                next_step_button.config(state='disabled')
            elif STEP >= 1:
                previous_step_button.config(state='normal')
            elif STEP + 1 == len(actuator_list):
                next_step_button.config(state='disabled')

        # Function to handle click events on previous step button
        def previous_click():
            global STEP
            STEP -= 1
            curr_step_lab.config(text=str(STEP + 1) + ':  ' + recipeDict['StepName'][STEP])
            show_valves()
            if STEP == 0:
                previous_step_button.config(state='disabled')
                next_step_button.config(state='normal')
            elif STEP + 1 < len(actuator_list) and STEP > 0:
                next_step_button.config(state='normal')

        # Function to handle click events on end preview button
        def end_click():
            # Enable buttons once preview_window has closed
            self.featureDict['Button']['Recipe']['Play'].config(state='normal')
            self.featureDict['Button']['Recipe']['Stop'].config(state='normal')
            self.featureDict['Button']['Recipe']['Manual'].config(state='normal')
            self.featureDict['Button']['Recipe']['Load'].config(state='normal')
            self.featureDict['Button']['Recipe']['Save'].config(state='normal')
            self.featureDict['Button']['Recipe']['AddLine'].config(state='normal')
            self.featureDict['Button']['Recipe']['DelLine'].config(state='normal')
            self.featureDict['Button']['Recipe']['Preview'].config(state='normal')
            self.featureDict['Button']['Recipe']['CalcLen'].config(state='normal')
            for i in range(self.NUM_VALVES):
                if i in curr_act_list:
                    self.featureDict['Button']['Valve']['ValveButtons'][i].config(text=' ON ', bg='green')
                else:
                    self.featureDict['Button']['Valve']['ValveButtons'][i].config(text='OFF', bg='red')
            win.destroy()

        # Function to show valves that will be acutated during current recipe step on main window
        def show_valves():
            global STEP
            for i in range(self.NUM_VALVES):
                if i in actuator_list[STEP]:
                    valve_buttons[i].config(text=' ON ', bg='green')
                else:
                    valve_buttons[i].config(text='OFF', bg='red')
            win.update()
            
            return
            
        def buttonClick(v):
            
            if valve_buttons[v]['text'].replace(" ", "") == "ON":
                valve_buttons[v].config(text='OFF', bg='red')
            else:
                valve_buttons[v].config(text=' ON ', bg='green')
            win.update()
            
            return
            
        def updateValves():
            global STEP
            actList = []
            for i in range(self.NUM_VALVES):
                if valve_buttons[i]['text'].replace(' ','') == 'ON':
                    actList.append(i)
                    
            self.featureDict['Entry']['Recipe']['Actuators'][STEP].delete(0, 'end')
            self.featureDict['Entry']['Recipe']['Actuators'][STEP].insert(0, ''.join(str(j)+',' if i < len(actList)-1 else str(j) for i, j in enumerate(actList)))
            
            return

        # Disable other buttons when recipe preview button is clicked
        for i in range(len(self.featureDict['Button']['Valve']['ValveButtons'])):
            self.featureDict['Button']['Valve']['ValveButtons'][i].config(state='disabled')
        self.featureDict['Button']['Recipe']['Play'].config(state='disabled')
        self.featureDict['Button']['Recipe']['Stop'].config(state='disabled')
        self.featureDict['Button']['Recipe']['Manual'].config(state='disabled', bg='green', relief=tk.RAISED)
        self.featureDict['Button']['Recipe']['Load'].config(state='disabled')
        self.featureDict['Button']['Recipe']['Save'].config(state='disabled')
        self.featureDict['Button']['Recipe']['AddLine'].config(state='disabled')
        self.featureDict['Button']['Recipe']['DelLine'].config(state='disabled')
        self.featureDict['Button']['Recipe']['Preview'].config(state='disabled')
        self.featureDict['Button']['Recipe']['CalcLen'].config(state='disabled')

        # Create preview window
        win = tk.Toplevel()
        win.geometry("250x200")
        win.title('Recipe Preview')

        # Get actuator strings from get_recipe_steps function
        recipeDict = self.getRecipeSteps()
        global STEP
        STEP = 0
        actuator_list = []

        # Create widgets in preview window
        
        mainFrame = tk.Frame(win, highlightbackground='black', borderwidth=0, relief=tk.SOLID)
        valveFrame = tk.Frame(win, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
        
        tk.Label(mainFrame, text='Current Step: ').pack(pady=5, padx=10)
        curr_step_lab = tk.Label(mainFrame, text='1:  ' + recipeDict['StepName'][0], font=self.fontDict['Label'])
        next_step_button = tk.Button(mainFrame, text='Next Step', state='disabled', command=next_click)
        previous_step_button = tk.Button(mainFrame, text='Previous Step', state='disabled', command=previous_click)
        end_preview_button = tk.Button(mainFrame, text='End Preview', command=end_click)
        update_valves_button = tk.Button(mainFrame, text='Edit Valves', command=updateValves)
        
        valve_num_labels = [tk.Label(valveFrame, text='V'+str(j),font=self.fontDict['Valve']) for j in range(self.NUM_VALVES)]
        valve_desc_labels = [tk.Label(valveFrame, text=self.VALVE_LABELS[j], font=self.fontDict['Valve'], justify='center') for j in range(self.NUM_VALVES)]
        valve_buttons = [tk.Button(valveFrame, text='OFF', bg='red', font=self.fontDict['Button'], state='normal', command=partial(buttonClick, j)) for j in range(self.NUM_VALVES)]
        
        mainFrame.grid(row=0, column=0, rowspan=5, ipadx=5, ipady=5)
        #recipe_control_frame.grid(row=0, column=0, rowspan=1, ipadx=5, ipady=5)
        valveFrame.grid(row=0, column=1, rowspan=8, ipadx=1, ipady=1, padx=1)

        # Pack widgets in preview window
        curr_step_lab.pack(padx=15, pady=5)
        next_step_button.pack(pady=5)
        previous_step_button.pack(pady=5)
        end_preview_button.pack(pady=5)
        update_valves_button.pack(pady=5)
        
        for i in range(self.NUM_VALVES):
            if i <= 15:
                valve_num_labels[i].grid(row=i, column=0, ipadx=2.5, padx=2.5, sticky='e')
                valve_desc_labels[i].grid(row=i, column=2, pady=5, padx=2.5, sticky='w')
                valve_buttons[i].grid(row=i, column=1, ipadx=5, ipady=0, padx=2.5, pady=2.5)
                valveFrame.grid_rowconfigure(i, weight = 1)

        valveFrame.grid_columnconfigure(0, weight=1)
        valveFrame.grid_columnconfigure(1, weight=1)
        valveFrame.grid_columnconfigure(2, weight=1)
        
        ''' End window creation '''

        # Get current actuator list
        curr_act_list = []
        for i in range(self.NUM_VALVES):
            if self.featureDict['Button']['Valve']['ValveButtons'][i]['text'].replace(" ", "") == 'ON':
                curr_act_list.append(i)

        # Populate actuator list from get_actuator_list function
        for j in recipeDict['Actuators']:
            actuator_list.append(self.getActuatorList(j))

        # Enable next step button if there is more than 1 recipe step
        if len(actuator_list) > 1:
            next_step_button.config(state='normal')

        # Show valves for initial recipe step (step=0)
        try:
            show_valves()
        except IndexError:
            pass

        # Handle delete window event (click x in upper right)
        win.protocol('WM_DELETE_WINDOW', end_click)

        # Loop the window until it is destroyed
        win.mainloop()
        
        return
    
    
    def sortRecipeSteps(self, step_type):
        """
        Function to sort recipe steps into type (start, end, cycles, etc.) and organize them.
        :param step_type: string containing the type of recipe step
        :param cycle_entries: number of cycles to be run
        :return: integer lists of numbered start steps, end steps, cycle steps, and cycles
        """
        start_steps = []
        end_steps = []
        cyc_steps = {}
        cyc_num = []
        cycles = []

        # Sort recipe steps into categories: 'start', 'cycle', or 'end'
        g = 0
        for i in range(len(step_type)):
            if step_type[i].replace(" ", "").lower() == 'start':
                start_steps.append(i)
            elif step_type[i].replace(" ", "").lower() == 'end':
                end_steps.append(i)
            elif 'cycle' in step_type[i].replace(" ", "").lower():
                try:
                    cyc_num.append(int(step_type[i].split('Cycle')[-1]))
                except ValueError:
                    cyc_num.append(1)
    
                if cyc_num[g] in cyc_steps:
                    cyc_steps[cyc_num[g]].append(i)
                else:
                    cyc_steps[cyc_num[g]] = [i]
                g += 1
    
        if len(cyc_num) > 0:
            num_cycles = max(cyc_num)
        else:
            num_cycles = 0
        for m in range(num_cycles):
            try:
                cycles.append(int(self.featureDict['Entry']['Recipe']['CycleNumEntry'][m].get()))  # Get number of cycles from entry field)
            except ValueError:
                cycles.append(0)
    
        return start_steps, end_steps, cyc_steps, cycles
    
    def calculateRecipeLength(self, recipeDict):
        """
        Function designed to calculate the length of a given recipe.
        :param recipe_time: list of times (in seconds) of recipe steps
        :param step_type: list of step types (start, end, cycle1, cycle2, etc.)
        :param cycle_entries: list of integer values determining number of cycles for each cycle number
        :param num_laminates: integer value denoting the number of laminates to be used
        :param lam_cycles: list of integer values denoting which cycle types (cycle1, cycle2, etc.) correspond with which
        laminate(s)
        :return: three strings: start time, end time, and recipe length
        """
        start_steps, end_steps, cyc_steps, cycles = self.sortRecipeSteps(recipeDict['StepType'])
    
        # Calculate recipe end date / time
        now = datetime.datetime.now()
        now_str = datetime.datetime.strptime(now.strftime('%m/%d/%Y %H:%M:%S'), '%m/%d/%Y %H:%M:%S') \
            .strftime('%m/%d/%Y %I:%M:%S %p')
    
        total_time = 0
        cyc_time = []
    
        for k in start_steps:
            total_time += recipeDict['Time'][k]
        for k in end_steps:
            total_time += recipeDict['Time'][k]
        for m in range(len(self.featureDict['Entry']['Recipe']['LamEntry'])):
            cyc_time.append(0)
            for n in range(len(recipeDict['Lam_Cycle'][m])):
                if recipeDict['Lam_Cycle'][m][n] in cyc_steps:
                    for j in cyc_steps[recipeDict['Lam_Cycle'][m][n]]:
                        cyc_time[m] += recipeDict['Time'][j] * cycles[recipeDict['Lam_Cycle'][m][n] - 1]
            total_time += cyc_time[m] * self.featureDict['Entry']['Recipe']['LamEntry'][m]
    
        end = now + datetime.timedelta(seconds=total_time)
        end_str = datetime.datetime.strptime(end.strftime('%m/%d/%Y %H:%M:%S'), '%m/%d/%Y %H:%M:%S') \
            .strftime('%m/%d/%Y %I:%M:%S %p')
        minutes, seconds = divmod(total_time, 60)
        hours, minutes = divmod(minutes, 60)
        rec_len_str = '{}h : {}m : {}s'.format(hours, minutes, round(seconds, 2))
    
        return now_str, end_str, rec_len_str
    
    def getRecipeLength(self):
        """
        Function to calculate length of current recipe. Uses the calculate_recipe_length function from the Recipe.py
        script in the Valve_Sequencer folder
        """
        recipeDict = self.getRecipeSteps()
        num_laminates = []
        for i in range(len(self.featureDict['Entry']['Recipe']['LamEntry'])):
            try:
                num_laminates.append(int(self.featureDict['Entry']['Recipe']['LamEntry'][i].get()))
            except ValueError:
                num_laminates.append(1)
                self.featureDict['Entry']['Recipe']['LamEntry'][i].delete(0, 'end')
                self.featureDict['Entry']['Recipe']['LamEntry'][i].insert(0, 1)

        now_str, end_str, rec_len_str = self.calculateRecipeLength(recipeDict)
        self.featureDict['Label']['Recipe']['RecipeLenTime'].config(text=rec_len_str)
        self.featureDict['Label']['Recipe']['RecipeStartTime'].config(text=now_str)
        self.featureDict['Label']['Recipe']['RecipeEndTimeLab'].config(text=end_str)
        
        return
        
    def addRecipeLine(self):
        if self.recipe_window_len == len(self.featureDict['Label']['Recipe']['Row']):
            # Create new entry and label fields
            self.featureDict['Label']['Recipe']['Row'].append(tk.Label(self.frameDict['RecipeEdit'], text=str(self.recipe_window_len + 1)))
            self.featureDict['Entry']['Recipe']['Time'].append(tk.Entry(self.frameDict['RecipeEdit'], justify='center', width=7))
            self.featureDict['Entry']['Recipe']['StepName'].append(tk.Entry(self.frameDict['RecipeEdit'], justify='center', width=15))
            self.featureDict['Combobox']['Recipe']['StepType'].append(ttk.combobox(self.frameDict['RecipeEdit'], justify='center', width=8))
            self.featureDict['Combobox']['Recipe']['Laminate'].append(ttk.combobox(self.frameDict['RecipeEdit'], justify='center', width=8))
            self.featureDict['Entry']['Recipe']['Actuator'].append(tk.Entry(self.frameDict['RecipeEdit'], justify='center', width=15))

        # Add newly-created fields to interface
        self.featureDict['Label']['Recipe']['Row'][self.recipe_window_len].grid(row=self.recipe_window_len + 2, column=0, sticky='ew')
        self.featureDict['Entry']['Recipe']['Time'][self.recipe_window_len].grid(row=self.recipe_window_len + 2, column=1, sticky='ew', padx=5, pady=2)
        self.featureDict['Entry']['Recipe']['StepName'][self.recipe_window_len].grid(row=self.recipe_window_len + 2, column=2, sticky='ew', padx=5, pady=2)
        self.featureDict['Combobox']['Recipe']['StepType'][self.recipe_window_len].grid(row=self.recipe_window_len + 2, column=3, sticky='ew', padx=5, pady=2)
        self.featureDict['Combobox']['Recipe']['Laminate'][self.recipe_window_len].grid(row=self.recipe_window_len + 2, column=4, sticky='ew', padx=5, pady=2)
        self.featureDict['Entry']['Recipe']['Actuator'][self.recipe_window_len].grid(row=self.recipe_window_len + 2, column=5, sticky='ew', padx=5, pady=2)

        self.recipe_window_len += 1
        return
        
    def deleteRecipeLine(self):

        while self.recipe_window_len > self.num_recipe_lines:
            self.featureDict['Entry']['Recipe']['Time'][self.recipe_window_len - 1].delete(0, 'end')
            self.featureDict['Entry']['Recipe']['StepName'][self.recipe_window_len - 1].delete(0, 'end')
            self.featureDict['Combobox']['Recipe']['StepType'][self.recipe_window_len - 1].delete(0, 'end')
            self.featureDict['Combobox']['Recipe']['Laminate'][self.recipe_window_len - 1].delete(0, 'end')
            self.featureDict['Entry']['Recipe']['Actuator'][self.recipe_window_len - 1].delete(0, 'end')

            self.featureDict['Label']['Recipe']['Row'][self.recipe_window_len - 1].grid_forget()
            self.featureDict['Entry']['Recipe']['Time'][self.recipe_window_len - 1].grid_forget()
            self.featureDict['Entry']['Recipe']['StepName'][self.recipe_window_len - 1].grid_forget()
            self.featureDict['Combobox']['Recipe']['StepType'][self.recipe_window_len - 1].grid_forget()
            self.featureDict['Combobox']['Recipe']['Laminate'][self.recipe_window_len - 1].grid_forget()
            self.featureDict['Entry']['Recipe']['Actuator'][self.recipe_window_len - 1].grid_forget()

            self.recipe_window_len -= 1
        return
            
    def deleteSingleLine(self):

        if self.recipe_window_len > 1:
            self.featureDict['Entry']['Recipe']['Time'][self.recipe_window_len - 1].delete(0, 'end')
            self.featureDict['Entry']['Recipe']['StepName'][self.recipe_window_len - 1].delete(0, 'end')
            self.featureDict['Combobox']['Recipe']['StepType'][self.recipe_window_len - 1].delete(0, 'end')
            self.featureDict['Combobox']['Recipe']['Laminate'][self.recipe_window_len - 1].delete(0, 'end')
            self.featureDict['Entry']['Recipe']['Actuator'][self.recipe_window_len - 1].delete(0, 'end')

            self.featureDict['Label']['Recipe']['Row'][self.recipe_window_len - 1].grid_forget()
            self.featureDict['Entry']['Recipe']['Time'][self.recipe_window_len - 1].grid_forget()
            self.featureDict['Entry']['Recipe']['StepName'][self.recipe_window_len - 1].grid_forget()
            self.featureDict['Combobox']['Recipe']['StepType'][self.recipe_window_len - 1].grid_forget()
            self.featureDict['Combobox']['Recipe']['Laminate'][self.recipe_window_len - 1].grid_forget()
            self.featureDict['Entry']['Recipe']['Actuator'][self.recipe_window_len - 1].grid_forget()

            self.recipe_window_len -= 1
        return
    
    def on_frame_config(self, canvas):
        """
        Configures canvas scrolling for the recipe entry region
        :param canvas: Canvas on which the scroll bar is located
        """
        # Configure scroll region in recipe canvas
        canvas.config(scrollregion=canvas.bbox("all"))
        
    def createWindow(self):
        self.app = tk.Tk()
        self.app.title('Control Box Operation Window')
        screenWidth = self.app.winfo_screenwidth()
        screenHeight = self.app.winfo_screenheight()
        geom = '%dx%d' %(screenWidth*0.85, screenHeight*0.85)
        self.app.geometry(geom)
    
        ''' Define Dictionaries '''
        self.fontDict = {}
        self.frameDict = {}
        self.featureDict = {}
        
        ''' Fonts '''
        self.fontDict['Button'] = font.Font(size=14, weight='bold')
        self.fontDict['Label'] = font.Font(size=14)
        self.fontDict['Valve'] = font.Font(size=12)
    
        ''' Frame Creation '''
        self.frameDict['RecipeControl'] = tk.Frame(self.app, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
        self.frameDict['Recipe'] = tk.Frame(self.app, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
        self.frameDict['RecipeHeaders'] = tk.Frame(self.frameDict['Recipe'])
        self.recipe_canvas = tk.Canvas(self.frameDict['Recipe'], borderwidth=0)
        self.frameDict['RecipeEdit'] = tk.Frame(self.recipe_canvas, highlightbackground='black', borderwidth=0, relief=tk.SOLID)
        self.frameDict['RecipeDetails'] = tk.Frame(self.app, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
        self.frameDict['RecipeLength'] = tk.Frame(self.app, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
        self.frameDict['Valve'] = tk.Frame(self.app, highlightbackground='black', borderwidth=1, relief=tk.SOLID)
        
        ''' Recipe Frame '''
        self.featureDict['Label'] = {}
        self.featureDict['Entry'] = {}
        self.featureDict['Button'] = {}
        
        self.featureDict['Label']['Recipe'] = {}
        self.featureDict['Entry']['Recipe'] = {}
        self.featureDict['Button']['Recipe'] = {}
        
        self.featureDict['Label']['Recipe']['Row'] = []
        #featureDict['Label']['Recipe']['Col'] = []
    
        recipe_col_text = ['Row', 'Time', 'Step Name', 'Step Type', 'Laminate', 'Actuators']
        self.featureDict['Label']['Recipe']['CurrentRecipe'] = tk.Label(self.frameDict['RecipeHeaders'], text='Current Recipe: ')
        
        self.featureDict['Label']['Recipe']['Col'] = [tk.Label(self.frameDict['RecipeHeaders'], text=recipe_col_text[j]) for j in range(6)]
        #for j in range(5):
        #    featureDict['Label']['Recipe']['Col'].append(tk.Label(frameDict['RecipeHeaders'], text=recipe_col_text[j]))
        self.featureDict['Label']['Recipe']['Col'][0].config(width=3)
        self.featureDict['Label']['Recipe']['Col'][1].config(width=6)
        self.featureDict['Label']['Recipe']['Col'][2].config(width=12)
        self.featureDict['Label']['Recipe']['Col'][3].config(width=8)
        self.featureDict['Label']['Recipe']['Col'][4].config(width=8)
        self.featureDict['Label']['Recipe']['Col'][5].config(width=12)
    
        self.vsb = tk.Scrollbar(self.frameDict['Recipe'], orient='vertical', command=self.recipe_canvas.yview)
        self.recipe_canvas.config(yscrollcommand=self.vsb.set)
    
        self.featureDict['Button']['Recipe']['AddLine'] = tk.Button(self.frameDict['Recipe'], text='Add Recipe Line', command=self.addRecipeLine)
        self.featureDict['Button']['Recipe']['DelLine'] = tk.Button(self.frameDict['Recipe'], text='Delete Recipe Line', command=self.deleteSingleLine)
        self.featureDict['Button']['Recipe']['CalcLen'] = tk.Button(self.frameDict['Recipe'], text='Calculate Recipe Length', command=self.getRecipeLength)
        self.featureDict['Button']['Recipe']['Preview']= tk.Button(self.frameDict['Recipe'], text='Preview Recipe Steps', command=self.recipePreview)
        #self.featureDict['Button']['Recipe']['EditRecipeValves'] = tk.Button(self.frameDict['Recipe'], text='Edit Recipe Valves', command=self.editRecipeValves)
        
        ''' Create recipe region '''
        self.recipe_window_len = 12
        self.featureDict['Label']['Recipe']['Row'] = [tk.Label(self.frameDict['RecipeEdit'], text=str(i+1)) for i in range(self.recipe_window_len)]
        self.featureDict['Entry']['Recipe']['Time'] = [tk.Entry(self.frameDict['RecipeEdit'], justify='center', width=7) for i in range(self.recipe_window_len)]
        self.featureDict['Entry']['Recipe']['StepName'] = [tk.Label(self.frameDict['RecipeEdit'], justify='center', width=15) for i in range(self.recipe_window_len)]
        self.featureDict['Combobox']['Recipe']['StepType'] = [ttk.combobox(self.frameDict['RecipeEdit'], justify='center', width=8) for i in range(self.recipe_window_len)]
        self.featureDict['Combobox']['Recipe']['Laminate'] = [ttk.combobox(self.frameDict['RecipeEdit'], justify='center', width=8) for i in range(self.recipe_window_len)]
        self.featureDict['Entry']['Recipe']['Actuator'] = [tk.Label(self.frameDict['RecipeEdit'], justify='center', width=17) for i in range(self.recipe_window_len)]
    
        self.numLams = self.configDict['Laminates']
        self.numCycles = self.configDict['Cycles']
        
        self.stepTypes = ['Start', 'End']
        for i in range(self.numCycles):
            self.stepTypes.append('Cycle'+str(i+1))
        
        for i in range(self.recipe_window_len):
            self.featureDict['Combobox']['Recipe']['Laminate']['values'] = [str(j+1) for j in range(self.numLam)]
            self.featureDict['Combobox']['Recipe']['Laminate']['values'] = [self.stepTypes[j] for j in range(len(self.stepTypes))]
    
        ''' Recipe Control Frame '''
        self.featureDict['Button']['Recipe']['Load'] = tk.Button(self.frameDict['RecipeControl'], text='Load Recipe', font=self.fontDict['Button'], bg='bisque',
                                       command=self.loadRecipe)
        self.featureDict['Button']['Recipe']['Save'] = tk.Button(self.frameDict['RecipeControl'], text='Save Recipe', font=self.fontDict['Button'], bg='light goldenrod',
                                       command=self.saveRecipe)
        self.featureDict['Button']['Recipe']['Manual'] = tk.Button(self.frameDict['RecipeControl'], text='Manual Control', font=self.fontDict['Button'], width=12, bg='green',
                                       fg='white', command=self.manualControlClick)
        self.featureDict['Button']['Recipe']['Play'] = tk.Button(self.frameDict['RecipeControl'], text='Play', bg='green2', font=self.fontDict['Button'], width=6,
                                command=self.playButtonClick)
        self.featureDict['Button']['Recipe']['Stop'] = tk.Button(self.frameDict['RecipeControl'], text='Stop', bg='red3', font=self.fontDict['Button'], width=6,
                                command=self.stopButtonClick)
        
        self.featureDict['Label']['Recipe']['FilenameLabel'] = tk.Label(self.frameDict['RecipeControl'], text='Recipe Filename', justify='right')
        self.featureDict['Label']['Recipe']['Filename'] = tk.Label(self.frameDict['RecipeControl'], text=' ', width=18, relief=tk.SUNKEN, bg='white')
        self.featureDict['Label']['Recipe']['ExpComment'] = tk.Label(self.frameDict['RecipeControl'], text='Experiment Comment: ', justify='right')
        self.featureDict['Entry']['Recipe']['ExpComment'] = tk.Entry(self.frameDict['RecipeControl'], text=' ', width=30, relief=tk.SUNKEN, bg='white')
    
        ''' Recipe Details Frame '''
    
        ''' Create widgets for recipe details frame '''
        self.featureDict['Label']['Recipe']['StepTimeRem'] = tk.Label(self.frameDict['RecipeDetails'], text=' 0.00 ', relief=tk.SUNKEN, width=7, bg='white', anchor='w')
        self.featureDict['Label']['Recipe']['StepTimeRem_Lab'] = tk.Label(self.frameDict['RecipeDetails'], text='Time Remaining in Current Step')
        self.featureDict['Label']['Recipe']['StartStepName'] = tk.Label(self.frameDict['RecipeDetails'], text=' ', relief=tk.SUNKEN, width=15, bg='white')
        self.featureDict['Label']['Recipe']['EndStepName'] = tk.Label(self.frameDict['RecipeDetails'], text=' ', relief=tk.SUNKEN, width=15, bg='white')
        self.featureDict['Button']['Recipe']['EStop'] = tk.Button(self.frameDict['RecipeDetails'], text="EMERGENCY STOP", bg="red", font=self.fontDict['Button'], width=20,
                                 command=self.estop_click)
        
        self.featureDict['Label']['Recipe']['LamLabel'] = [tk.Label(self.frameDict['RecipeDetails'], text='Laminate # '+str(j+1)) for j in range(self.numLams)]
        self.featureDict['Entry']['Recipe']['LamEntry'] = [tk.Entry(self.frameDict['RecipeDetails'], relief=tk.SUNKEN, width=7, justify='center', bg='white') for j in range(self.numLams)]
        self.featureDict['Label']['Recipe']['CurrLamLab'] = [tk.Label(self.frameDict['RecipeDetails'], text='Current Lam. \n # '+str(j+1)) for j in range(self.numLams)]
        self.featureDict['Label']['Recipe']['CurrLamDisp'] = [tk.Label(self.frameDict['RecipeDetails'], relief = tk.SUNKEN, width=7, justify='center', bg='white') for j in range(self.numLams)]
        
        for j in range(self.numLams):
            self.featureDict['Entry']['Recipe']['LamEntry'][j].insert(0, 1)

        self.featureDict['Entry']['Recipe']['CycleNumEntry'] = [tk.Entry(self.frameDict['RecipeDetails'], justify='center', width=7) for j in range(self.numCycles)]
        self.featureDict['Label']['Recipe']['CycleLab'] = [tk.Label(self.frameDict['RecipeDetails'], text='Cycle '+str(j + 1)) for j in range(self.numCycles)]
        self.featureDict['Label']['Recipe']['CurrStepDisp'] = [tk.Label(self.frameDict['RecipeDetails'], text=' ', relief=tk.SUNKEN, width=7, bg='white') for j in range(self.numCycles)]
        self.featureDict['Label']['Recipe']['CurrStepLab'] = [tk.Label(self.frameDict['RecipeDetails'], text='Current ' +str(j+1)) for j in range(self.numCycles)]
        self.featureDict['Label']['Recipe']['CurrStepName'] = [tk.Label(self.frameDict['RecipeDetails'], text=' ', relief=tk.SUNKEN, width=15, bg='white') for j in range(self.numCycles)]
        
        for j in range(self.numCycles):
            self.featureDict['Entry']['Recipe']['CycleNumEntry'][j].insert(0, 0)

        ''' Recipe Length Frame '''
        self.featureDict['Label']['Recipe']['RecipeLenLab'] = tk.Label(self.frameDict['RecipeLength'], text='Recipe Length: ')
        self.featureDict['Label']['Recipe']['RecipeLenTime'] = tk.Label(self.frameDict['RecipeLength'], text='0h : 0m : 0s', width=20, bg='white', relief=tk.SUNKEN)
        self.featureDict['Label']['Recipe']['RecipeStartTimeLab'] = tk.Label(self.frameDict['RecipeLength'], text='Recipe Start Time: ')
        self.featureDict['Label']['Recipe']['RecipeStartTime'] = tk.Label(self.frameDict['RecipeLength'], text=' ', width=25, bg='white', relief=tk.SUNKEN)
        self.featureDict['Label']['Recipe']['RecipeEndTimeLab'] = tk.Label(self.frameDict['RecipeLength'], text='Recipe End Time: ')
        self.featureDict['Label']['Recipe']['RecipeEndTime'] = tk.Label(self.frameDict['RecipeLength'], text=' ', width=25, bg='white', relief=tk.SUNKEN)
    
        ''' Valve Frame '''
        self.featureDict['Label']['Valve'] = {}
        self.featureDict['Entry']['Valve'] = {}
        self.featureDict['Button']['Valve'] = {}
        #valve_num_labels = []
        #valve_desc_labels = []
        #valve_buttons = []
    
        #self.numValves = 16
        self.valveLabels = self.configDict['ValveLabels']

        # Add extra labels if not enough are specified
        if len(self.valveLabels) < self.NUM_VALVES:
            xtra = self.NUM_VALVES - len(self.valveLabels)
            for k in range(xtra):
                self.valveLabels.append('Not Specified')
    
        ''' Create two sets of valve labels and valve buttons '''
        self.featureDict['Label']['Valve']['ValveNum'] = [tk.Label(self.frameDict['Valve'], text='V'+str(j),font=self.fontDict['Valve']) for j in range(self.NUM_VALVES)]
        self.featureDict['Label']['Valve']['ValveDesc'] = [tk.Label(self.frameDict['Valve'], text=self.valveLabels[j], font=self.fontDict['Valve'], justify='center') for j in range(self.NUM_VALVES)]
        self.featureDict['Button']['Valve']['ValveButtons'] = [tk.Button(self.frameDict['Valve'], text='OFF', bg='red', font=self.fontDict['Button'], state='disabled',command=partial(self.valveButtonClick, j)) for j in range(self.NUM_VALVES)]
    
        ''' --------------------- Widget Layout -----------------------------'''
    
        self.frameDict['RecipeControl'].grid(row=0, column=0, rowspan=1, ipadx=5, ipady=5)
        #recipe_control_frame.grid(row=0, column=0, rowspan=1, ipadx=5, ipady=5)
        self.frameDict['Recipe'].grid(row=1, column=0, rowspan=5, ipadx=1, ipady=1, padx=1)
        #recipe_frame.grid(row=1, column=0, rowspan=5, ipadx=1, ipady=1, padx=1)
        self.frameDict['RecipeDetails'].grid(row=0, column=1, rowspan=4, ipadx=5, ipady=5, padx=5, pady=5)
        #recipe_details_frame.grid(row=0, column=1, rowspan=4, ipadx=5, ipady=5, padx=5, pady=5)
        self.frameDict['RecipeLength'].grid(row=6, column=0, rowspan=1, ipadx=5, ipady=5, padx=5)
        #recipe_length_frame.grid(row=6, column=0, rowspan=1, ipadx=5, ipady=5, padx=5)
        self.frameDict['Valve'].grid(row=0, column=2, rowspan=8, padx=5, pady=5)
        #valve_frame.grid(row=0, column=2, rowspan=8, padx=5, pady=5)
        
        for i in range(10):
           self.app.grid_rowconfigure(i, weight=1)
        
        self.app.grid_columnconfigure(0, weight=1)
        self.app.grid_columnconfigure(1, weight=1)
        self.app.grid_columnconfigure(2, weight=1)
    
        #if num_valves > 16:
        #    valve_frame2.grid(row=0, column=3, rowspan=8, padx=5, pady=5)
        
        self.frameDict['RecipeHeaders'].pack(fill='both') # Pack this frame in recipe_frame
        #recipe_headers_frame.pack(fill='both')      
        self.featureDict['Button']['Recipe']['CalcLen'].pack(side=tk.BOTTOM, pady=2)
        #calc_len_button.pack(side=tk.BOTTOM, pady=2)     # Pack this button in recipe_frame
        self.featureDict['Button']['Recipe']['DelLine'].pack(side=tk.BOTTOM, pady=2)
        self.featureDict['Button']['Recipe']['AddLine'].pack(side=tk.BOTTOM, pady=2)
        self.featureDict['Button']['Recipe']['Preview'].pack(side=tk.BOTTOM, pady=2)
        #del_line_button.pack(side=tk.BOTTOM, pady=2)     # Pack this button in recipe_frame
        #add_line_button.pack(side=tk.BOTTOM, pady=2)     # Pack this button in recipe_frame
        #recipe_prev_button.pack(side=tk.BOTTOM, pady=2)  # Pack this button in recipe_frame
        
        
        self.recipe_canvas.pack(side=tk.LEFT, fill='y', expand=True)     # Pack this canvas in recipe_frame
        self.frameDict['RecipeEdit'].pack(fill='both')     # Pack this frame in recipe_canvas
    
        self.vsb.pack(side=tk.LEFT, fill='y')  # Pack this vertical scrollbar in recipe_frame
        
        self.frameDict['RecipeEdit'].bind("<Configure>", lambda event, canvas=self.recipe_canvas: self.on_frame_config(canvas))
        self.recipe_canvas.create_window((5, 5), window=self.frameDict['RecipeEdit'], anchor='ne')
    
        ''' Edit recipe frame '''
        self.featureDict['Label']['Recipe']['CurrentRecipe'].grid(row=0, column=0, columnspan=2)
        #curr_recipe_label.grid(row=0, column=0, columnspan=2)
        for j in range(6):
            self.featureDict['Label']['Recipe']['Col'][j].grid(row=1, column=j)
            self.frameDict['RecipeEdit'].grid_columnconfigure(j, weight=1)
        for i in range(self.recipe_window_len):
            self.featureDict['Label']['Recipe']['Row'][i].grid(row=i+2, column=0, sticky='ew')
            self.featureDict['Entry']['Recipe']['Time'][i].grid(row=i+2, column=1, sticky='ew', padx=5, pady=2)

            self.featureDict['Entry']['Recipe']['StepName'][i].grid(row=i+2, column=2, sticky='ew', padx=5, pady=2)
            self.featureDict['Combobox']['Recipe']['StepType'][i].grid(row=i+2, column=3, sticky='ew', padx=5, pady=2)
            self.featureDict['Combobox']['Recipe']['Laminate'][i].grid(row=i+2, column=4, sticky='ew', padx=5, pady=2)
            self.featureDict['Entry']['Recipe']['Actuator'][i].grid(row=i+2, column=5, sticky='ew', padx=5, pady=2)
            self.frameDict['RecipeEdit'].grid_rowconfigure(i+2, weight=1)
    
        ''' Edit recipe frame '''
        self.featureDict['Button']['Recipe']['Load'].grid(row=0, column=0, padx=5, pady=5)
        self.featureDict['Button']['Recipe']['Save'].grid(row=0, column=1, padx=5, pady=5, sticky='e')
        self.featureDict['Button']['Recipe']['Manual'].grid(row=3, column=0, columnspan=2, pady=15, sticky='ew', padx=10)
        self.featureDict['Button']['Recipe']['Play'].grid(row=4, column=0, padx=2, pady=1, sticky='w')
        self.featureDict['Button']['Recipe']['Stop'].grid(row=4, column=1, padx=2, pady=1, sticky='e')
        self.featureDict['Label']['Recipe']['FilenameLabel'].grid(row=1, column=0)
        self.featureDict['Label']['Recipe']['Filename'].grid(row=1, column=1, padx=2, pady=5)
        self.featureDict['Label']['Recipe']['ExpComment'].grid(row=2, column=0, padx=5, pady=5)
        self.featureDict['Entry']['Recipe']['ExpComment'].grid(row=2, column=1, padx=5, pady=5)
        
        self.frameDict['RecipeEdit'].grid_rowconfigure(0, weight=1)
        self.frameDict['RecipeEdit'].grid_rowconfigure(1, weight=1)
        self.frameDict['RecipeEdit'].grid_rowconfigure(2, weight=1)
        self.frameDict['RecipeEdit'].grid_rowconfigure(3, weight=1)
        
        self.frameDict['RecipeEdit'].grid_columnconfigure(0, weight=1)
        self.frameDict['RecipeEdit'].grid_columnconfigure(1, weight=1)
    
        ''' Recipe Details Frame '''
        self.featureDict['Button']['Recipe']['EStop'].grid(row=0, column=0, rowspan=2, columnspan=3, pady=5)
        self.featureDict['Label']['Recipe']['StepTimeRem_Lab'].grid(row=2, column=0, columnspan=3, ipadx=5)
        self.featureDict['Label']['Recipe']['StepTimeRem'].grid(row=3, column=1, ipadx=5, pady=5)
        self.featureDict['Label']['Recipe']['StartStepName'].grid(row=5, column=1, ipadx=5, pady=5)
        
        self.featureDict['RecipeDetail'].grid_rowconfigure(0, weight=1)
        self.featureDict['RecipeDetail'].grid_rowconfigure(1, weight=1)
        self.featureDict['RecipeDetail'].grid_rowconfigure(2, weight=1)
        self.featureDict['RecipeDetail'].grid_rowconfigure(3, weight=1)
        self.featureDict['RecipeDetail'].grid_rowconfigure(4, weight=1)
        self.featureDict['RecipeDetail'].grid_rowconfigure(5, weight=1)
        self.featureDict['RecipeDetail'].grid_rowconfigure(6, weight=1)
        
        
        self.featureDict['RecipeDetail'].grid_columnconfigure(0, weight=1)
        self.featureDict['RecipeDetail'].grid_columnconfigure(1, weight=1)
        self.featureDict['RecipeDetail'].grid_columnconfigure(2, weight=1)
    
        for i in range(self.numCycles):
            self.featureDict['Entry']['Recipe']['CycleNumEntry'][i].grid(row=2*i+7, column=0, padx=1)
            self.featureDict['Label']['Recipe']['CycleLab'][i].grid(row=2*i+6, column=0, padx=1)
            self.featureDict['Label']['Recipe']['CurrStepDisp'][i].grid(row=2*i+7, column=2, padx=1)
            self.featureDict['Label']['Recipe']['CurrStepLab'][i].grid(row=2*i+6, column=2, padx=1)
            self.featureDict['Label']['Recipe']['CurrStepName'][i].grid(row=2*i+7, column=1, ipadx=5, padx=1)
            
            self.frameDict['RecipeDetail'].grid_rowconfigure(2*i+6, weight=1)
            self.frameDict['RecipeDetail'].grid_rowconfigure(2*i+7, weight=1)
    
        self.featureDict['Label']['Recipe']['EndStepName'].grid(row=2*i+8, column=1, ipadx=5, padx=0, pady=8)
        self.frameDict['RecipeDetail'].grid_rowconfigure(2*i+8, weight=1)
        self.frameDict['RecipeDetail'].grid_rowconfigure(2*i+9, weight=1)
    
        for m in range(self.numLams):
            self.featureDict['Label']['Recipe']['LamLabel'][m].grid(row=2*i+10+(2*m), column=0, padx=1)
            self.featureDict['Entry']['Recipe']['LamEntry'][m].grid(row=2*i+11+2*m, column=0, padx=1)
            self.featureDict['Label']['Recipe']['CurrLamLab'][m].grid(row=2*i+10+2*m, column=2, padx=1)
            self.featureDict['Label']['Recipe']['CurrLamDisp'][m].grid(row=2*i+11+2*m, column=2, padx=1)
            
            self.frameDict['RecipeDetail'].grid_rowconfigure(2*i+10+2*m, weight=1)
            self.frameDict['RecipeDetail'].grid_rowconfigure(2*i+11+2*m, weight=1)
    
        ''' Recipe Length Frame '''
        self.featureDict['Label']['Recipe']['RecipeLenLab'].grid(row=0, column=0, padx=10, pady=5)
        self.featureDict['Label']['Recipe']['RecipeLenTime'].grid(row=0, column=1, padx=10, pady=5)
        self.featureDict['Label']['Recipe']['RecipeStartTimeLab'].grid(row=1, column=0, padx=10, pady=5)
        self.featureDict['Label']['Recipe']['RecipeStartTime'].grid(row=1, column=1, padx=10, pady=5)
        self.featureDict['Label']['Recipe']['RecipeEndTimeLab'].grid(row=2, column=0, padx=10, pady=5)
        self.featureDict['Label']['Recipe']['RecipeEndTime'].grid(row=2, column=1, padx=10, pady=5)
        
        self.frameDict['RecipeLength'].grid_rowconfigure(0, weight=1)
        self.frameDict['RecipeLength'].grid_rowconfigure(1, weight=1)
        self.frameDict['RecipeLength'].grid_rowconfigure(2, weight=1)
        
        self.frameDict['RecipeLength'].grid_columnconfigure(0, weight=1)
        self.frameDict['RecipeLength'].grid_columnconfigure(1, weight=1)
    
        ''' Valve Frame '''
        for i in range(self.NUM_VALVES):
            if i <= 15:
                self.featureDict['Label']['Valve']['ValveNum'][i].grid(row=i, column=0, ipadx=2.5, padx=2.5, sticky='e')
                self.featureDict['Label']['Valve']['ValveDesc'][i].grid(row=i, column=2, pady=5, padx=2.5, sticky='w')
                self.featureDict['Button']['Valve']['ValveButtons'][i].grid(row=i, column=1, ipadx=5, ipady=0, padx=2.5, pady=2.5)
                self.frameDict['Valve'].grid_rowconfigure(i, weight = 1)
            #else:
            #    valve_num_labels[i].grid(row=i-16, column=0, ipadx=2.5, padx=2.5, sticky='e')
            #    valve_desc_labels[i].grid(row=i-16, column=2, pady=5, padx=2.5, sticky='w')
            #    valve_buttons[i].grid(row=i-16, column=1, ipadx=5, ipady=0, padx=2.5, pady=2.5)
            #    valve_frame2.grid_rowconfigure(i-16, weight = 1)
        self.frameDict['Valve'].grid_columnconfigure(0, weight=1)
        self.frameDict['Valve'].grid_columnconfigure(1, weight=1)
        self.frameDict['Valve'].grid_columnconfigure(2, weight=1)
        
        #if num_valves > 16:
        #    valve_frame2.grid_columnconfigure(0, weight=1)
        #    valve_frame2.grid_columnconfigure(1, weight=1)
        #    valve_frame2.grid_columnconfigure(2, weight=1)
        
        # Check if instrument was found
        #if my_inst == 0:
        #    tkinter.messagebox.showinfo('Warning', 'No Instrument Detected! Check COM port.')
    
            # Focus_force entry widgets to allow interactivity after messagebox pops up
        for i in range(self.recipe_window_len):
            self.featureDict['Entry']['Recipe']['Time'][i].focus_force()
            self.featureDict['Entry']['Recipe']['StepName'][i].focus_force()
            self.featureDict['Combobox']['Recipe']['StepType'][i].focus_force()
            self.featureDict['Combobox']['Recipe']['Laminate'][i].focus_force()
            self.featureDict['Entry']['Recipe']['Actuator'][i].focus_force()

        for i in range(self.numLams):
            self.featureDict['Entry']['Recipe']['LamEntry'][i].focus_force()

        for i in range(self.numCycles):
            self.featureDict['Entry']['Recipe']['CycleNumEntry'][i].focus_force()
    
        ''' function to check queue for gui actions '''
        def updateStatus():
            if not self.gQueue.empty():

                guiTask = self.gQueue.get()

                if guiTask[0] == 'Config':
                    self.configDict = guiTask[1]
                elif guiTask[0] == 'Set_Interlocks':
                    self.VALVE_INTERLOCKS = guiTask[1]
                elif guiTask[0] == 'Reset_Valves':
                    self.resetValveButtons()
                elif guiTask[0] == 'Edit':
                    labs = guiTask[1]
                    d = guiTask[2]
                    for key in d:
                        #pyGui.featureDict[labs[0]][labs[1]][labs[2]].config(key=d[key])
                        if key == 'text':
                            if len(labs)>3:
                                if len(labs[3])>1:
                                    for j in range(len(labs[3])):
                                        self.featureDict[labs[0]][labs[1]][labs[2]][labs[3][j]].config(text=d[key])
                                    else:
                                        self.featureDict[labs[0]][labs[1]][labs[2]][labs[3]].config(text=d[key])
                            else:
                                self.featureDict[labs[0]][labs[1]][labs[2]].config(text=d[key])
                                    
                        elif key == 'state':
                            if len(labs)>3:
                                if len(labs[3])>1:
                                    for j in range(len(labs[3])):
                                        self.featureDict[labs[0]][labs[1]][labs[2]][labs[3][j]].config(state=d[key])
                                    else:
                                        self.featureDict[labs[0]][labs[1]][labs[2]][labs[3]].config(state=d[key])
                            else:
                                self.featureDict[labs[0]][labs[1]][labs[2]].config(state=d[key])
                                    
                        elif key == 'bg':
                            if len(labs)>3:
                                if len(labs[3])>1:
                                    for j in range(len(labs[3])):
                                        self.featureDict[labs[0]][labs[1]][labs[2]][labs[3][j]].config(bg=d[key])
                                    else:
                                        self.featureDict[labs[0]][labs[1]][labs[2]][labs[3]].config(bg=d[key])
                            else:
                                self.featureDict[labs[0]][labs[1]][labs[2]].config(bg=d[key])
                                    
                        elif key == 'fg':
                            if len(labs)>3:
                                if len(labs[3])>1:
                                    for j in range(len(labs[3])):
                                        self.featureDict[labs[0]][labs[1]][labs[2]][labs[3][j]].config(fg=d[key])
                                    else:
                                        self.featureDict[labs[0]][labs[1]][labs[2]][labs[3]].config(fg=d[key])
                            else:
                                self.featureDict[labs[0]][labs[1]][labs[2]].config(fg=d[key])
                        elif key == 'relief':
                            if len(labs)>3:
                                if len(labs[3])>1:
                                    for j in range(len(labs[3])):
                                        self.featureDict[labs[0]][labs[1]][labs[2]][labs[3][j]].config(relief=d[key])
                                    else:
                                        self.featureDict[labs[0]][labs[1]][labs[2]][labs[3]].config(relief=d[key])
                            else:
                                self.featureDict[labs[0]][labs[1]][labs[2]].config(relief=d[key])

            self.app.after(1, updateStatus())
    
        self.app.after(1, updateStatus())
        self.app.protocol('WM_DELETE_WINDOW', self.ask_quit)
        self.app.mainloop()
        
class ValveOp():
    
    def __init__(self, nValves=16, vInterlocks=[]):
        self.NUM_VALVES = nValves
        #self.VALVE_INTERLOCKS = vInterlocks
        ''' initiate communication with instrument here '''
    
    def setQueues(self, rCQ=None, rIQ=None, vQ=None, gQ=None):
        self.rCQueue = rCQ
        self.rIQueue = rIQ
        self.vQueue = vQ
        self.gQueue = gQ
    
    def setInitialization(self, initDict):
        
        #self.NUM_CYCLES = initDict['nCycles']
        #self.NUM_LAMINATES = initDict['nLaminates']
        self.VALVE_INTERLOCKS = initDict['valveInterlocks']
        #self.VALVE_LABELS = initDict['valveLabels']
    
    def reset_valves(self):
        """
        Function to reset all relays (valves) to de-energized (closed)
        :return: Nothing
        """
        # Write sequence to reset all actuators
        #valve_seq = '0'*self.NUM_VALVES
        self.multi_valve_op([])
        
    def trigger_interlock(self, event, step_num=None):
        """
        Function to trigger interlock condition. Will reset all valves and return an error message
        :return error_msg: Error message to show up as a tkinter message box
        """
        #valve_seq = '0'*self.NUM_VALVES
        self.multi_valve_op([])
        self.gQueue.put_nowait(['Reset_Valves'])
        self.tQueue.put_nowait(['Reset'])
        if event == 'recipe':
            error_msg = \
                'Interlock triggered in step {} of recipe. All valves have been reset. Please correct before proceeding'.format(step_num + 1)
        elif event == 'button':
            error_msg = 'Interlock Triggered! All valves have been reset.'
    
        return error_msg


    def check_interlock(self, valves, eventType = 'button', on_valves=None, step_num=None):
            """
            Function to check if a valve interlock has been triggered
            :param valve_buttons: list of valve buttons from TkWindow.py script
            :param valves: either a single valve number that has been clicked or a list of valves
            :return proceed: Boolean that is True if no interlocks have been triggered and False if an interlock condition was
            met
            """
            if eventType == 'button':
                # Check if the valve that was clicked is in the interlocks list
                for x in self.VALVE_INTERLOCKS:
                    if valves in self.VALVE_INTERLOCKS[x]:
                        for j in on_valves:
                            if j in self.VALVE_INTERLOCKS[x]:
                                #return False    # Interlock triggered!
                                error_msg = self.trigger_interlock(event='button')    # Interlock triggered!
                                tkinter.messagebox.showerror('Valve Interlock', error_msg)
                                return False
                return True
        
            else:
                for x in self.VALVE_INTERLOCKS:
                    for j in range(len(valves)):
                        # Check if any valves to be actuated in the recipe step are in the interlocks list
                        if valves[j] in self.VALVE_INTERLOCKS[x]:
                            # Check if any remaining valves in list show up in the interlocks list
                            for k in range(j+1, len(valves)):
                                if valves[k] in self.VALVE_INTERLOCKS[x]:
                                    #return False    # Interlock Triggered!
                                    if eventType == 'recipe_check':
                                        error_msg = \
                                        'Interlock alert in step {} of recipe. Please correct before proceeding'.format(step_num + 1) 
                                    else:
                                        error_msg = self.trigger_interlock(event='recipe', step_num=step_num)    # Interlock triggered!
                                        tkinter.messagebox.showerror('Valve Interlock', error_msg)
                                        return False
                return True
                
                
    def valve_on(self, v_num, on_valves=None):
        """
        Function to turn on (energize) selected relay (valves) when an action is performed (i.e. button click)
        :param v_num: valve number - defined when button is clicked
        """
        proceed = self.check_interlock(v_num, on_valves=on_valves, eventType='button')
        
        if proceed:
            self.gQueue.put_nowait(['Edit',['Button','Valve','ValveButtons', v_num],{'text':' ON ', 'bg':'green'}])
            # Energizes relay (actuates valve)
            relay_on = "SK"
        
            if v_num <= 7:
                sig = '0'+relay_on+str(v_num)
                my_inst.write(sig)
                self.logger.info('Sent valve on signal '+sig+' to controller')
            elif 8 <= v_num <= 15:
                sig = '1'+relay_on+str(v_num-8)
                my_inst.write(sig)
                self.logger.info('Sent valve on signal '+sig+' to controller')
    
        return
    
    def valve_off(self, v_num):
        """
        Function to turn off (de-energize) selected relays (valves) when an action is performed (i.e. button click)
        :param v_num: valve number - defined when button is clicked
        """
        self.gQueue.put_nowait(['Edit',['Button','Valve','ValveButtons', v_num],{'text':'OFF', 'bg':'red'}])
        # Resets (de-energizes) relay (de-actuates or closes valve)
        relay_off = "RK"
    
        if v_num <= 7:
            sig = '0'+relay_off+str(v_num)
            my_inst.write(sig)
            self.logger.info('Sent valve off signal '+sig+' to controller')
        elif 8 <= v_num <= 15:
            sig = '1'+relay_off+str(v_num-8)
            my_inst.write(sig)
            self.logger.info('Sent valve off signal '+sig+' to controller')
    
        return
    
    def multi_valve_op(self, valves, step=None):
        """
        Function to send command to operate multiple actuators simultaneously
        :param seq: string containing valve command in 1's and 0's
        :param log_file: object denoting the text file where recipe steps are logged.
        """
        multi_relay_write = 'SPK'
        
        if len(valves) == 0:
            if self.NUM_VALVES <= 8:
                valve_seq = '0'*self.NUM_VALVES
                my_inst.write(multi_relay_write + valve_seq)
                self.logger.info('Sent multi valve signal '+valve_seq+' to controller')
            elif 8 < self.NUM_VALVES <= 16:
                valve_seq0 = '0'*self.NUM_VALVES
                valve_seq1 = '0'*self.NUM_VALVES
                my_inst.write(multi_relay_write + valve_seq0)
                my_inst.write('1' + multi_relay_write + valve_seq1)
                self.logger.info('Sent multi valve signal '+valve_seq0+' to controller')
                self.logger.info('Sent multi valve signal '+valve_seq1+' to controller')
        else:
            proceed = self.check_interlock(valves, eventType='recipe', step_num=step)
            
            if proceed:
                self.gQueue.put_nowait(['Edit',['Button','Valve','ValveButtons', valves],{'text':' ON ', 'bg':'green'}])
                v_off = [i for i in range(self.NUM_VALVES) if i not in valves]
                self.gQueue.put_nowait(['Edit',['Button','Valve','ValveButtons', v_off],{'text':'OFF', 'bg':'red'}])
                
                seq = ''.join('1' if i in valves else '0' for i in range(self.NUM_VALVES))
                
                if self.NUM_VALVES <= 8:
            
                    # Reverse sequence to write to controller
                    valve_seq = seq[::-1].replace(" ","")
                    try:
                        # Write valve sequence to instrument
                        my_inst.write(multi_relay_write + valve_seq)
                        self.logger.info('Sent multi valve signal ' +valve_seq+' to controller')
                    except AttributeError:
                        print('No Instrument Detected')
            
                    # Write valve_seq and timestamp to log file
                    #try:
                    #    log_file.write(str(datetime.now()) + "\t" + valve_seq + "\n")
                    #except AttributeError:
                    #    pass
            
                elif 8 < self.NUM_VALVES <= 16:
                    # Split and reverse sequence to write to controller
                    valve_seq0 = seq[7::-1].replace(" ", "")
                    valve_seq1 = seq[15:7:-1].replace(" ", "")
                    try:
                        # Write two valve sequences to instrument, one to each control card
                        my_inst.write(multi_relay_write + valve_seq0)
                        my_inst.write('1' + multi_relay_write + valve_seq1)
                        self.logger.info('Sent multi valve signal ' +valve_seq0+' to controller')
                        self.logger.info('Sent multi valve signal ' +valve_seq1+' to controller')
                    except AttributeError:
                        print('No Instrument Detected')
            
                    # Write valve_seq0, valve_seq1, and timestamp to log file
                    #try:
                    #    log_file.write(str(datetime.now()) + "\t" + valve_seq0 + "\t" + valve_seq1 + "\n")
                    #except AttributeError:
                    #    pass

class RecipeOp():
    def __init__(self, numValves=16):
        
        self.pyV = ValveOp(nValves=numValves)
        self.STOP = False
        self.NUM_VALVES = numValves
        self.STEP_NUM = -1
        self.cycDict = {}
        self.lamDict = {}
        
    def setQueues(self, rCQ=None, rIQ=None, vQ=None, gQ=None, tQ=None):
        self.rCQueue = rCQ
        self.rIQueue = rIQ
        self.vQueue = vQ
        self.gQueue = gQ
        self.tQueue = tQ
        
    def setRecipeParams(self, rd=None, ld=None, cd=None):
        
        self.recipeDict = rd
        self.lamEntryDict = ld
        self.cycleEntryDict = cd
        
    def setInitialization(self, initDict):
        pass
        
    def checkRecipe(self):
        
        ''' Check for interlock trigger in recipe steps '''
        for i in self.recipeDict:
            proceed = self.pyV.check_interlock(self.recipeDict['Actuators'][i], eventType='recipe_check', step_num=i+i)
            if not proceed:
                self.STOP = True
                break
        
        """
        ''' Disable buttons during recipe play '''
        self.gQueue.put_nowait(['Edit',['Button','Recipe','Play'],{'state':'disabled','fg':'red','text':'Running','bg':'yellow'}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','Manual'],{'state':'disabled','bg':'green','relief':tk.RAISED}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','Load'],{'state':'disabled'}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','Save'],{'state':'disabled'}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','AddLine'],{'state':'disabled'}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','Preview'],{'state':'disabled'}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','CalcLength'],{'state':'disabled'}])
        self.gQueue.put_nowait(['Edit',['Button','Valve','ValveButtons',[j for j in range(self.NUM_VALVES)]],{'state':'disabled'}])
        """
    
    def startRecipe(self):
        if not self.STOP:
            self.logger.info('Generating recipe list...')
            '''
            Create list w/ dictionaries  for all steps in recipe
            i.e. 
            Start
            Cycle1 step1 - cycle, lam, actuators
            Cycle1 step2
            Cycle1 step3
            repeat...
            Cycle2 step1
            Cycle2 step2
            repeat...
            end
            
            then just increment the step counter each time and finish when 
            '''
            self.recipeList = []
            #step = -1
            #while True:
            ''' Start steps '''
            for i, sType in enumerate(self.recipeDict['StepType']):
                if 'start' in sType.lower():
                    
            #step += 1
                #if 'start' in self.recipeDict['StepType'][step].lower():
                    self.recipeList.append({'StepType':sType, 
                                            'StepName':self.recipeDict['StepName'][i],
                                            'Time':self.recipeDict['Time'][i],
                                            'Actuators':self.recipeDict['Actuators'][i],
                                            'CycNum':0,
                                            'LamNum':0
                                            })
                #else:
                #    break
            ''' Cycle / laminate steps '''
            for i, nLam in enumerate(sorted(self.lamEntryDict.keys())):
                for j in range(self.lamEntryDict[nLam]):
                    for k, nCyc in enumerate(sorted(self.recipeDict['Lam_Cycle'][nLam])):
                        for p in range(self.cycleEntryDict[nCyc]):
                            if any(['cycle'+str(nCyc) in self.recipeDict['StepType'].lower()]):
                                for s, t in enumerate(self.recipeDict['StepType']):
                                    if t.lower() == 'cycle'+str(nCyc):
                                        self.recipeList.append({'StepType':t, 
                                            'StepName':self.recipeDict['StepName'][s],
                                            'Time':self.recipeDict['Time'][s],
                                            'Actuators':self.recipeDict['Actuators'][s],
                                            'CycNum':int(nCyc),
                                            'LamNum':nLam
                                            })
    
            #while True:
            #    step += 1
            ''' End steps '''
            for i, sType in enumerate(self.recipeDict['StepType']):
                if 'end' in sType.lower():
                    self.recipeList.append({'StepType':sType,
                                            'StepName':self.recipeDict['StepName'][i],
                                            'Time':self.recipeDict['Time'][i],
                                            'Actuators':self.recipeDict['Actuators'][i],
                                            'CycNum':0,
                                            'LamNum':0
                                            })
    
        self.rIQueue.put_nowait(['Recipe_Check', self.recipeList])
        
        ''' Disable buttons during recipe play '''
        self.gQueue.put_nowait(['Edit',['Button','Recipe','Play'],{'state':'disabled','fg':'red','text':'Running','bg':'yellow'}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','Manual'],{'state':'disabled','bg':'green','relief':tk.RAISED}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','Load'],{'state':'disabled'}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','Save'],{'state':'disabled'}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','AddLine'],{'state':'disabled'}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','Preview'],{'state':'disabled'}])
        self.gQueue.put_nowait(['Edit',['Button','Recipe','CalcLength'],{'state':'disabled'}])
        self.gQueue.put_nowait(['Edit',['Button','Valve','ValveButtons',[j for j in range(self.NUM_VALVES)]],{'state':'disabled'}])

        
        return
            
            
    def playRecipeStep(self):
        self.STEP_NUM += 1
        self.logger.info('Starting recipe step number: '+str(self.STEP_NUM))
        stepDict = self.recipeList[self.STEP_NUM]
        nLam = stepDict['LamNum']
        nCyc = stepDict['CycNum']
        valvesON = stepDict['Actuators']
        #valvesOFF = [i for i in range(self.NUM_VALVES) if i not in valvesON]
        time = stepDict['Time']
        if nCyc > 0 and nCyc not in self.cycDict:
            self.cycDict[nCyc] = 0
        if nLam > 0 and nLam not in self.lamDict:
            self.lamDict[nLam] = 0
            
        self.cycDict[nCyc] += 1
        self.lamDict[nLam] += 1
        
        if not self.STOP:
            ''' Send commands to gui queue to edit recipe labels '''
            if 'start' in stepDict['StepType'].lower():
                self.gQueue.put_nowait(['Edit',['Label','Recipe','StartStepName'],{'text':stepDict['StepName']}])
                #self.gQueue.put_nowait(['Edit',['Label','Recipe','StepTimeRem'],{'text':str(stepDict['Time'])}])
            elif 'end' in stepDict['StepType'].lower():
                self.gQueue.put_nowait(['Edit',['Label','Recipe','EndStepName'],{'text':stepDict['StepName']}])
                #self.gQueue.put_nowait(['Edit',['Label','Recipe','StepTimeRem'],{'text':str(stepDict['Time'])}])
                #self.gQueue.put_nowait(['Edit',['Button','Valve','ValveButtons', v_num],{'text':' ON ', 'bg':'green'}])
            else:
                self.gQueue.put_nowait(['Edit',['Label','Recipe','CurrStepName',nCyc-1],{'text':stepDict['StepName']}])
                self.gQueue.put_nowait(['Edit',['Label','Recipe','CurrStepDisp',nCyc-1],{'text':str(self.cycDict[nCyc])}])
                
                #self.gQueue.put_nowait(['Edit',['Label','Recipe','StepTimeRem'],{'text':str(stepDict['Time'])}])
                self.gQueue.put_nowait(['Edit',['Label','Recipe','CurrLamDisp',nLam-1],{'text':str(self.lamDict[nLam])}])
                
        if not self.STOP:
            ''' Send commands to gui queue to edit valve buttons --- 
            Actually, the valve Op class does this alread '''
            #self.gQueue.put_nowait(['Edit',['Button', 'Valve', 'ValveButtons', valvesON],{'text':' ON ', 'bg':'green'}])
            #self.gQueue.put_nowait(['Edit',['Button', 'Valve', 'ValveButtons', valvesOFF],{'text':'OFF', 'bg':'red'}])
        
            ''' Send command to valve queue to actuate valves '''
            self.vQueue.put_nowait(['Multi', valvesON, self.STEP_NUM])
            
            ''' Send command to timer queue to start step timer '''
            self.tQueue.put_nowait(['Start',time])

        return
        
        
        
        
        
        
        
        
        
        
        
        
                
    
    