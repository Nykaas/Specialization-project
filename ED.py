import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math

from plot import plot_settings
from CE import get_current_efficiency
from xy_smooth import smooth_xy

def ED_plot(df, excelfile, writer, smooth, markers):
    A_sample = 12.5 # cm^2
    CE_data = []
    ECSA = get_ECSA(df)
    for sheet in df: # Iterate sheet name as key in df dictionary
        if sheet == 'ECSA-cap':
            continue
        print(f'--- {sheet} ---')
        columns = list(df[sheet].columns)
        markers_idx = 0
        xlabel = df[sheet]['Graph_settings'][1]
        ylabel = df[sheet]['Graph_settings'][2]
        CellA5_CE = df[sheet]['Graph_settings'][3]
        
        for i in range(1, len(columns), 3): # Iterate data columns
            x = np.array(df[sheet][columns[i]].tolist())
            y = np.array(df[sheet][columns[i+1]].tolist())
            x, y = smooth_xy(x, y, smooth)
            name = columns[i+2]
            offset_AgCl = get_AgCl_offset(name, sheet)

            if '-' in name and 'V' in name: # Correct Ag/Cl offset in label
                idx = name.find('V')
                E = round(float(name[idx-5:idx-1]) - offset_AgCl, 2) # - offset since float is positive from excel
                name = name.replace(name[idx-5:idx-1], str(E))
                name += ' RHE'
                print(f'Label: AgCl offset {name}')

            if '-' in name and 'A' in name: # Change to current density in label
                idx = name.find('-')
                current_density = (float(name[idx+1:idx+5])/A_sample) * 1000 # A to mA
                name = name.replace(name[idx+1:idx+5],  f'{current_density:.0f}')
                name = name.replace('A', r'mA $\mathdefault{cm^{-2}}$')
                print('Label: Current density')

            if 'mV/s' in name:
                name = name.replace('mV/s', r'mV $\mathdefault{s^{-1}}$')
            
            if 'NiSO4' in name:
                name = name.replace('NiSO4', r'$\mathdefault{NiSO_{4}}$')

            if 'NiCl2' in name:
                name = name.replace('NiCl2', r'$\mathdefault{NiCl_{2}}$')

            if 'H3BO3' in name:
                name = name.replace('H3BO3', r'$\mathdefault{H_{3}}$$\mathdefault{BO_{3}}$')
            
            if CellA5_CE == 'CE': # Current efficiency
                m_t, m_a, CE, loading, I, t = get_current_efficiency(df, sheet, name)
                save_CE_data(m_t, m_a, CE, loading, CE_data, writer, name, I, t)

            if 'GC' in sheet or 'Glassy carbon' in name: # Glassy carbon
                A_sample = 0.196 # cm^2
                print(f'Area GC = {A_sample}')
            
            elif ('NF' in name or 'Nickel felt' in name or 'Carbon paper' in name) and ECSA_norm:
                A_sample = ECSA
                print(f'ECSA NF = {A_sample:.2f}')
           
            else:
                A_sample = 12.5 # cm^2
                print(f'Area "{name}" = {A_sample}')
            
            ### Plot ###
            if 'CV' in sheet: # CV
                xlabel = r'E [V vs. RHE]'
                ylabel = r'Current density [mA $\mathdefault{cm^{-2}}$]'
                plt.plot(x + offset_AgCl, y/A_sample, label = name, marker = markers[markers_idx], markevery = 100, markersize = get_markersize())
                
                if 'Electrolytes' in sheet:
                    plt.xlim(right=-0.4)
                    save_Eeq_data(x, y, writer, name, offset_AgCl, Eeq_data, sheet, A_sample)

            elif 'CP' in sheet: # Constant potential
                xlabel = r'Time [s]'
                ylabel = r'Current density [mA $\mathdefault{cm^{-2}}$]'
                plt.plot(x, y/A_sample, label = name, marker = markers[markers_idx], markevery = 0.3)
            
            elif 'CI' in sheet: # Constant current
                xlabel = r'Time [s]'
                ylabel = r'E [V vs. RHE]'
                plt.plot(x, y + offset_AgCl, label = name, marker = markers[markers_idx], markevery = 0.1)
            
            markers_idx += 1
        plot_settings(xlabel, ylabel, columns, sheet, excelfile, ECSA_norm=False)

def save_Eeq_data(x, y, writer, name, offset_AgCl, Eeq_data, sheet, A_sample):
    y_ = y
    for i, current in enumerate(y):
            if current < -0.2:
                Ieq = current
                Eeq = x[i] + offset_AgCl
                temp = {'Sheet': sheet, 'Sample': name, 'idx': i, 'Eeq [V, RHE]': Eeq, 'Ieq [mA]': Ieq, 'Ip [mA/cm^2]': y_[-1]/A_sample}
                Eeq_data.append(temp)
                Eeq_df = pd.DataFrame(Eeq_data, columns = ['Sheet', 'Sample', 'idx', 'Eeq [V, RHE]', 'Ieq [mA]', 'Ip [mA/cm^2]'])
                Eeq_df.to_excel(writer, index = False, header=True, sheet_name='Eeq')
                writer.save()
                #print(sheet, name, i, Ieq, Eeq)
                break

def get_ECSA(df):
    columns = list(df['ECSA-cap'].columns)
    x = np.array(df['ECSA-cap'][columns[1]].tolist())
    y = np.array(df['ECSA-cap'][columns[2]].tolist())
    cdl, b = np.polyfit(x, y, 1) # cdl [F]
    c = 40e-6 # F/cm^2
    ECSA = cdl / c # ECSA [cm^2]
    return ECSA

def get_AgCl_offset(name, sheet):
    if 'NiSO4' in name:
        pH = 4.1
    elif 'NiCl2' in name:
        pH = 3.9
    elif 'FeCl2' in name:
        pH = 0
    elif 'Watts' in sheet:
        pH = 3.64
    else:
        pH = 4.1
    offset_AgCl = 0.197 + (0.0591 * pH) # V
    print(f'AgCl to RHE offset = {offset_AgCl:.2f} V at pH {pH}')
    return offset_AgCl