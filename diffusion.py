# -*- coding: utf-8 -*-
"""
Created on Tue May 05 08:16:08 2015
@author: Ferriss

Diffusion in 1 and 3 dimensions with and without path-integration
Uses lmfit library to set up and pass parameters

THIS MODULE ASSUMES THAT ALL CONCENCENTRATIONS ARE ALREADY NORMALIZED TO 1.
Another option will be available at some point.

### 1-dimensional diffusion ###
Simplest function call is diffusion1D(length, diffusivity, time)
    Step 1. Create lmfit parameters with params = params_setup1D
            (Here is where you set what to vary when fitting)
    Step 2. Pass these parameters into diffusion1D_params(params)
    Step 3. Plot with plot_diffusion1D
With profiles in pynams, use profile.plot_diffusion() and fitDiffusivity()

### 3-dimensional diffusion without path integration: 3Dnpi ###
Simplest: diffusion3Dnpi(lengths, D's, time) to get a figure
    Step 1. Create parameters with params = params_setup3D
    Step 2. Pass parameters into diffusion3Dnpi_params(params) to get profiles
            Returns full 3D matrix v, sliceprofiles, then slice positions
    Step 3. Plot with pynams.plot_3panels(slice positions, slice profiles)

### Whole-Block: 3-dimensional diffusion with path integration: 3Dwb ###

    Step 1. Create parameters with params = params_setup3D 
            Same as for non-path integrated 3D.
    Step 2. Pass parameters into diffusion3Dwb(params)

### pynams module Profile and WholeBlock classes have bound functions to 
plot and fit diffusivities using these functions: plot_diffusion,
fitDiffusivity, and fitD

### Arrhenius diagrams ###
class Diffusivities() groups together temperatures and diffusivities
for use in plotting directly onto Arrhenius diagrams


"""
import lmfit
import numpy as np
import scipy
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from mpl_toolkits.axes_grid1.parasite_axes import SubplotHost
import pynams

#%% 1D diffusion
def params_setup1D(microns, log10D_m2s, time_seconds, init=1., fin=0.,
                   vD=True, vinit=False, vfin=False):
    """Takes required info for diffusion in 1D - length, diffusivity, time,
    and whether or not to vary them - vD, vinit, vfin. 
    Return appropriate lmfit params to pass into diffusion1D_params"""
    params = lmfit.Parameters()
    params.add('microns', microns, False, None, None, None)
    params.add('log10D_m2s', log10D_m2s, vD, None, None, None)
    params.add('time_seconds', time_seconds, False, None, None, None)
    params.add('initial_unit_value', init, vinit, None, None, None)
    params.add('final_unit_value', fin, vfin, None, None, None)
    return params

def diffusion1D_params(params, data_x_microns=None, data_y_unit_areas=None, 
                 erf_or_sum='erf', need_to_center_x_data=True,
                 infinity=100, points=100):
    """Function set up to follow lmfit fitting requirements.
    Requires input as lmfit parameters value dictionary 
    passing in key information as 'length_microns',
    'time_seconds', 'log10D_m2s', and 'initial_unit_value'. 

    If data are None (default), returns 1D unit diffusion profile 
    x_microns and y as vectors of length points (default 50). 

    Optional keywords:    
     - erf_or_sum: whether to use python's error functions (default) 
       or infinite sums
     - whether to center x data
     - points sets how many points to calculate in profile. Default is 50.
     - what 'infinity' is if using infinite sum approximation
     
    If not including data, returns the x vector and model y values.
    With data, return the residual for use in fitting.

    Visualize results with plot_diffusion1D
    """
    # extract important values from parameter dictionary passed in
    p = params.valuesdict()
    L_meters = p['microns'] / 1e6
    t = p['time_seconds']
    D = 10.**p['log10D_m2s']
    initial_value = p['initial_unit_value']
    final_value = p['final_unit_value']

    if initial_value > final_value:
        going_out = True
        solubility = initial_value
        minimum_value = final_value
    else:
        going_out = False        
        solubility = final_value
        minimum_value = initial_value
    
    a_meters = L_meters / 2.
    twoA = L_meters

    if t < 0:
        print 'no negative time'
        return           

    # Fitting to data or not? Default is not
    fitting = False
    if (data_x_microns is not None) and (data_y_unit_areas is not None):
        if len(data_x_microns) == len(data_y_unit_areas):
            fitting = True
        else:
            print 'x and y data must be the same length'
            print 'x', len(data_x_microns)
            print 'y', len(data_y_unit_areas)
        
    # x is in meters and assumed centered around 0
    if fitting is True:
        # Change x to meters and center it
        x = np.array(data_x_microns) / 1e6
        if need_to_center_x_data is True:
            x = x - a_meters
    else:
        x = np.linspace(-a_meters, a_meters, points)
    
    if erf_or_sum == 'infsum':
        xsum = np.zeros_like(x)
        for n in range(infinity):
           # positive number that converges to 1
            xadd1 = ((-1.)**n) / ((2.*n)+1.)        
            # time conponent
            xadd2 = np.exp(
                            (-D * (((2.*n)+1.)**2.) * (np.pi**2.) * t) / 
                            (twoA**2.) 
                            )                        
            # There the position values come in to create the profile
            xadd3 = np.cos(
                            ((2.*n)+1.) * np.pi * x / twoA
                            )        
            xadd = xadd1 * xadd2 * xadd3
            xsum = xsum + xadd
            
        model = xsum * 4. / np.pi
    

    elif erf_or_sum == 'erf':
        sqrtDt = (D*t)**0.5
        model = ((scipy.special.erf((a_meters+x)/(2*sqrtDt))) + 
                   (scipy.special.erf((a_meters-x)/(2*sqrtDt))) - 1) 

    else:
        print ('erf_or_sum must be set to either "erf" for python built-in ' +
               'error function approximation (defaul) or "sum" for infinite ' +
               'sum approximation with infinity=whatever, defaulting to ' + 
               str(infinity))
        return False

    if going_out is False:
        model = np.ones_like(model) - model

    concentration_range = solubility - minimum_value
    model = (model * concentration_range) + minimum_value

    x_microns = x * 1e6

    # If not including data, just return the model values
    # With data, return the residual for use in fitting.
    if fitting is False:
        return x_microns, model
    return model-data_y_unit_areas

def plot_diffusion1D(x_microns, model, initial_value=None,
                     fighandle=None, axishandle=None, top=1.2,
                     style=None, fitting=False, show_km_scale=False):
    """Takes x and y diffusion data and plots 1D diffusion profile input"""
    a_microns = (max(x_microns) - min(x_microns)) / 2.
    a_meters = a_microns / 1e3
    
    if fighandle is None and axishandle is not None:
        print 'Remember to pass in handles for both figure and axis'
    if fighandle is None or axishandle is None:
        fig = plt.figure()          
        ax  = SubplotHost(fig, 1,1,1)
        ax.grid()
        ax.set_ylim(0, top)
    else:
        fig = fighandle
        ax = axishandle

    if style is None:
        if fitting is True:
            style = {'linestyle' : 'none', 'marker' : 'o'}
        else:
            style = pynams.style_lightgreen

    if show_km_scale is True:
        ax.set_xlabel('Distance (km)')
        ax.set_xlim(0., 2.*a_meters/1e3)
        x_km = x_microns / 1e6
        ax.plot((x_km) + a_meters/1e3, model, **style)
    else:                
        ax.set_xlabel('position ($\mu$m)')
        ax.set_xlim(-a_microns, a_microns)
        ax.plot(x_microns, model, **style)

    if initial_value is not None:
        ax.plot(ax.get_xlim(), [initial_value, initial_value], '--k')

    ax.set_ylabel('Unit concentration or final/initial')
    fig.add_subplot(ax)

    return fig, ax

def diffusion1D(length_microns, log10D_m2s, time_seconds, init=1., fin=0.,
                erf_or_sum='erf', show_plot=True, 
                fighandle=None, axishandle=None,
                style=None, need_to_center_x_data=True,
                infinity=100, points=100, top=1.2, show_km_scale=False):
    """Simplest implementation.
    Takes required inputs length, diffusivity, and time 
    and plots diffusion curve on new or specified figure. 
    Optional inputs are unit initial value and final values. 
    Defaults assume diffusion 
    out, so init=1. and fin=0. Reverse these for diffusion in.
    Returns figure, axis, x vector in microns, and model y data."""
    params = params_setup1D(length_microns, log10D_m2s, time_seconds, 
                            init, fin,
                            vD=None, vinit=None, vfin=None)
                            
    x_microns, model = diffusion1D_params(params, None, None, 
                                          erf_or_sum, need_to_center_x_data, 
                                          infinity, points)

    fig, ax = plot_diffusion1D(x_microns, model, initial_value=init, 
                               fighandle=fighandle, axishandle=axishandle,
                               style=style, fitting=False, 
                               show_km_scale=show_km_scale)
    
    return fig, ax, x_microns, model


#%% 3-dimensional diffusion parameter setup
def params_setup3D(microns3, log10D3, time_seconds, 
                   initial=1., final=0.,
                   vD=[True, True, True], vinit=False, vfin=False):
    """Takes required info for diffusion in 3D without path averaging and 
    return appropriate lmfit params.
    
    Returning full matrix and 
    slice profiles in one long list for use in fitting

    """
    params = lmfit.Parameters()
    params.add('microns3', microns3, False, None, None, None)
    params.add('log10Dx', log10D3[0], vD[0], None, None, None)
    params.add('log10Dy', log10D3[1], vD[1], None, None, None)
    params.add('log10Dz', log10D3[2], vD[2], None, None, None)
    params.add('time_seconds', time_seconds, False, None, None, None)
    params.add('initial_unit_value_a', initial, vinit, None, None, None)
    params.add('initial_unit_value_b', initial, vinit, None, None, None)
    params.add('initial_unit_value_c', initial, vinit, None, None, None)
    params.add('final_unit_value_a', final, vfin, None, None, None)
    params.add('final_unit_value_b', final, vfin, None, None, None)
    params.add('final_unit_value_c', final, vfin, None, None, None)
    return params

def diffusion3Dnpi_params(params, data_x_microns=None, data_y_unit_areas=None, 
                 erf_or_sum='erf', need_to_center_x_data=True,
                 infinity=100, points=100):
    """ Diffusion in 3 dimensions in a rectangular parallelipiped.
    Takes params - Setup parameters with params_setup3D.
    General setup and options similar to diffusion1D_params.
    
    Returns complete 3D concentration
    matrix v, slice profiles, and 
    positions of slice profiles.
    
    ### NOT COMPLETELY SET UP FOR FITTING JUST YET ###
    """   
    fitting = False
    if (data_x_microns is not None) and (data_y_unit_areas is not None):
        x_data = np.array(data_x_microns)
        y_data = np.array(data_y_unit_areas)
        if np.shape(x_data) == np.shape(y_data):
            fitting = True
            print 'fitting to data'
        else:
            print 'x and y data must be the same shape'
            print 'x', np.shape(x_data)
            print 'y', np.shape(y_data)

    p = params.valuesdict()
    L3_microns = np.array(p['microns3'])
    t = p['time_seconds']
    init = p['initial_unit_value_a']
    vary_init = [params['initial_unit_value_a'].vary, 
                 params['initial_unit_value_b'].vary,
                 params['initial_unit_value_c'].vary]
    fin = p['final_unit_value_a']
    vary_fin = [params['final_unit_value_a'].vary, 
                 params['final_unit_value_b'].vary,
                 params['final_unit_value_c'].vary]
    log10D3 = [p['log10Dx'], p['log10Dy'], p['log10Dz']]
    vary_D = [params['log10Dx'].vary, 
              params['log10Dy'].vary, 
              params['log10Dz'].vary]

    # If initial values > 1, scale down to 1 to avoid blow-ups later
    going_out = True
    scale = 1.
    for k in range(3):
        if init > 1.0:
            scale = init
            init = 1.
        if init < fin:
            going_out = False
    
    if init > fin:
        minimum_value = fin
    else:
        minimum_value = init
    
    if going_out is False:        
        # I'm having trouble getting diffusion in to work simply, so this
        # is a workaround. The main effort happens as diffusion going in, then
        # I subtract it all from 1.
        init, fin = fin, init
        
    # First create 3 1D profiles, 1 in each direction
    xprofiles = []    
    yprofiles = []
    kwdict = {'points' : points}
    
    for k in range(3):
        p1D = lmfit.Parameters()
        p1D.add('microns', L3_microns[k], False)
        p1D.add('time_seconds', t, params['time_seconds'].vary)
        p1D.add('log10D_m2s', log10D3[k], vary_D[k])
        p1D.add('initial_unit_value', init, vary_init[k])
        p1D.add('final_unit_value', fin, vary_fin[k])
        
        x, y = diffusion1D_params(p1D, **kwdict)

        xprofiles.append(x)
        yprofiles.append(y)
                                      
    # Then multiply them together to get a 3D matrix
    # I should figure out how to do this without the for-loops
    v = np.ones((points, points, points))
    for d in range(0, points):
        for e in range(0, points):
            for f in range(0, points):
                v[d][e][f] = yprofiles[0][d]*yprofiles[1][e]*yprofiles[2][f]

    v = v * scale

    if going_out is False:
        v = np.ones((points, points, points)) - v
        v = v + np.ones_like(v)*minimum_value

    mid = points/2.
    
    aslice = v[:, mid][:, mid]
    bslice = v[mid][:, mid]
    cslice = v[mid][mid]
    sliceprofiles = [aslice, bslice, cslice]

    slice_positions_microns = []
    for k in range(3):
        a = L3_microns[k] / 2.
        x = np.linspace(0, a*2., points)
        slice_positions_microns.append(x)
          
    # Returning full matrix and 
    # slice profiles in one long list for use in fitting
    sliceprofiles = [aslice, bslice, cslice]
    
    if fitting is False:
        return v, sliceprofiles, slice_positions_microns
    else:
        ### Still need to set up residuals! ###
        residuals = np.zeros_like(sliceprofiles)
        return residuals


def diffusion3Dnpi(lengths_microns, log10Ds_m2s, time_seconds, 
                    initial=1, final=0., top=1.2):
        """Takes list of 3 lengths, list of 3 diffusivities, and time 
        Returns plot of 3D non-path-averaged diffusion profiles"""
        params = params_setup3D(lengths_microns, log10Ds_m2s, time_seconds,
                                initial=initial, final=final)
        v, y, x = diffusion3Dnpi_params(params)
        
        f, ax = pynams.plot_3panels(x, y, top=top)
        return f, ax, v, x, y

#%% 3D whole-block: 3-dimensional diffusion with path integration
def diffusion3Dwb_params(params, data_x_microns=None, data_y_unit_areas=None, 
                          raypaths=None, erf_or_sum='erf', show_plot=True, 
                          fig_ax=None, style=None, need_to_center_x_data=True,
                          infinity=100, points=100, show_1Dplots=False):
    """ Diffusion in 3 dimensions with path integration.
    Requires setup with params_setup3Dwb
    """
    if raypaths is None:
        print 'raypaths must be in the form of a list of three abc directions'
        return

    # v is the model 3D array of internal concentrations
    ### Need to add in all the keywords ###
    v, sliceprofiles, slicepositions = diffusion3Dnpi_params(params, 
                    points=points, erf_or_sum=erf_or_sum,
                    need_to_center_x_data=need_to_center_x_data)

    
    # Fitting to data or not? Default is not
    # Add appropriate x and y data to fit
    fitting = False
    if (data_x_microns is not None) and (data_y_unit_areas is not None):
        x_array = np.array(data_x_microns)
        y_array = np.array(data_y_unit_areas)
        if np.shape(x_array) == np.shape(y_array):
            print 'fitting to data'
            fitting = True
        else:
            print 'x and y data must be the same shape'
            print 'x', np.shape(x_array)
            print 'y', np.shape(y_array)
            
    # Whole-block measurements can be obtained through any of the three 
    # planes of the whole-block, so profiles can come from one of two ray path
    # directions. These are the planes.
    raypathA = v.mean(axis=0)
    raypathB = v.mean(axis=1)
    raypathC = v.mean(axis=2)

    # Specify whole-block profiles in model
    mid = points/2
    if raypaths[0] == 'b':
        wbA = raypathB[:, mid]
    elif raypaths[0] == 'c':
        wbA = raypathC[:, mid]       
    else:
        print 'raypaths[0] for profile || a must be "b" or "c"'
        return
        
    if raypaths[1] == 'a':
        wbB = raypathA[:, mid]
    elif raypaths[1] == 'c':
        wbB = raypathC[mid]       
    else:
        print 'raypaths[1] for profile || b must be "a" or "c"'
        return

    if raypaths[2] == 'a':
        wbC = raypathA[mid]
    elif raypaths[2] == 'b':
        wbC = raypathB[mid]       
    else:
        print 'raypaths[2] for profile || c must be "a" or "b"'
        return

    p = params.valuesdict()
    L3 = p['microns3']
    
    wb_profiles = [wbA, wbB, wbC]
    wb_positions = []
    for k in range(3):
        a = L3[k] / 2.
        x_microns = np.linspace(0., 2.*a, points)
        wb_positions.append(x_microns)
        
    if show_plot is True:
        if style is None:
            style = [None, None, None]
            for k in range(3):
                style[k] = pynams.style_lightgreen

        if fig_ax is None:
            f, fig_ax = pynams.plot_3panels(wb_positions, wb_profiles, L3, style)
        else:
            pynams.plot_3panels(wb_positions, wb_profiles, L3, style, 
                         figaxis3=fig_ax)                         

    if fitting is False:        
        return wb_positions, wb_profiles
    
    if fitting is True:
        # Return residuals 
        y_model = []
        y_data = []
        residuals = []
        for k in range(3):
            for pos in range(len(x_array[k])):
                # wb_positions are centered, data are not
                microns = x_array[k][pos]
                # Find the index of the full model whole-block value 
                # closest to the data positions
                idx = (np.abs(wb_positions[k]-microns).argmin())
                
                model = wb_profiles[k][idx]
                data = y_array[k][pos]
                res = model - data
                
                y_model.append(model)
                y_data.append(data)
                residuals.append(res)                
        return residuals

def diffusion3Dwb(lengths_microns, log10Ds_m2s, time_seconds, raypaths,
                   initial=1., final=0., top=1.2):
        """Takes list of 3 lengths, list of 3 diffusivities, and time.
        Returns plot of 3D path-averaged (whole-block) diffusion profiles"""
        params = params_setup3D(lengths_microns, log10Ds_m2s, time_seconds,
                                initial=initial, final=final)
        x, y = diffusion3Dwb_params(params, raypaths=raypaths, show_plot=False)
        f, ax = pynams.plot_3panels(x, y, top=top)
        return f, ax, x, y

        
#%% Arrhenius diagram
def make_Arrhenius_line(celcius_list, logD_list, lowD=6.0, highD=10.0):
    """Takes lists of log10D and temperatures in Celcius
    Returns 100-point vectors of log10D and 1e4/T in K for plotting as lines"""
    if len(celcius_list) != len(logD_list):
        print 'List of temperatures not equal to list of diffusivities'
        return
    Tx = []
    for k in celcius_list:
        Tx.append(1.0e4 / (k+273.15))  
    p = np.polyfit(Tx, logD_list, 1)
    x = np.linspace(lowD, highD, 100) 
    y = np.polyval(p, x)
    return x, y

def Arrhenius_outline(low=6., high=11., bottom=-18., top=-8.,
                      Celcius_labels = np.arange(0, 2000, 100),
                      figsize_inches = (6, 4), shrinker_for_legend = 0.3,
                      generic_legend=True, sunk=-2.):
    """Make Arrhenius diagram outline"""
    fig = plt.figure(figsize=figsize_inches)
    ax = SubplotHost(fig, 1,1,1)
    ax_Celcius = ax.twin()
    parasite_tick_locations = 1e4/(Celcius_labels + 273.15)
    ax_Celcius.set_xticks(parasite_tick_locations)
    ax_Celcius.set_xticklabels(Celcius_labels)
    fig.add_subplot(ax)
    ax.axis["bottom"].set_label("10$^{-4}$/Temperature (K$^{-1}$)")
    ax.axis["left"].set_label("log$_{10}$D (m$^{2}$/s)")
    ax_Celcius.axis["top"].set_label("Temperature ($\degree$C)")
    ax_Celcius.axis["top"].label.set_visible(True)
    ax_Celcius.axis["right"].major_ticklabels.set_visible(False)
    ax.set_xlim(low, high)
    ax.set_ylim(bottom, top)
    ax.grid()
    
    # main legend below
    legend_handles_main = []
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height*shrinker_for_legend, 
                     box.width, box.height*(1.0-shrinker_for_legend)])
    main_legend = plt.legend(handles=legend_handles_main, numpoints=1, ncol=3, 
                             bbox_to_anchor=(low, bottom, high-low, sunk),
                             bbox_transform=ax.transData, mode='expand')
    plt.gca().add_artist(main_legend)
    
#    if generic_legend is True:
#        leg2 = []
#        print 'Still working on generic legend'
#        generic.add_to_legend(ax, leg2, descript='// [100]*', orientation='x', 
#                              addline=True)
#        generic.add_to_legend(ax, leg2, descript='// [010]', orientation='y', 
#                              addline=True)
#        generic.add_to_legend(ax, leg2, descript= '// [001]', orientation='z',
#                              addline=True)
#        generic.add_to_legend(ax, leg2, descript='not oriented', orientation='u')
#        plt.legend(handles=leg2, loc=3, numpoints=1, frameon=True)

    return fig, ax, legend_handles_main

class Diffusivities():
    description = None
    celcius_all = []
    celcius_unoriented = []
    celcius_x = []
    celcius_y = []
    celcius_z = []
    logD_unoriented = []
    logDx = []
    logDy = []
    logDz = []
    logDx_error = []
    logDy_error = []
    logDz_error = []
    logDu_error = []
    basestyle = []
    wholeblocks = []

    def get_from_wholeblock(self, peak_idx=None, print_diffusivities=False):
        """Grab diffusivities from whole-block"""
        self.celcius_all = []
        self.logDx = []
        self.logDy = []
        self.logDz = []
        self.logDx_error = []
        self.logDy_error = []
        self.logDz_error = []
        
        for wb in self.wholeblocks:
            if wb.temperature_celcius is None:
                print wb.name, 'needs temperature_celcius attribute'
                return

            wb.get_diffusivities()
            
            if print_diffusivities is True:
                wb.print_diffusivities()
            
            self.celcius_all.append(wb.temperature_celcius)

            if peak_idx is None:
                self.logDx.append(wb.profiles[0].diffusivity_log10m2s)
                self.logDy.append(wb.profiles[1].diffusivity_log10m2s)
                self.logDz.append(wb.profiles[2].diffusivity_log10m2s)
                self.logDx_error.append(wb.profiles[0].diff_error)
                self.logDy_error.append(wb.profiles[1].diff_error)
                self.logDz_error.append(wb.profiles[2].diff_error)
            else:
                self.logDx.append(wb.profiles[0].peak_diffusivities[peak_idx])
                self.logDy.append(wb.profiles[1].peak_diffusivities[peak_idx])
                self.logDz.append(wb.profiles[2].peak_diffusivities[peak_idx])
                self.logDx_error.append(wb.profiles[0].peak_diff_error[peak_idx])
                self.logDy_error.append(wb.profiles[1].peak_diff_error[peak_idx])
                self.logDz_error.append(wb.profiles[2].peak_diff_error[peak_idx])
            
    def plotloop(self, fig_axis, celcius, logD, style, legendlabel=None, 
                  offset_celcius=0, show_error=True, Derror = None):
        """Where the checks and actual plotting gets done"""
        # checks
        if len(celcius) == 0:
            if self.celcius_all is not None:
                celcius = self.celcius_all
            else:
                return
        if logD is None:
            return            
        if len(celcius) != len(logD):
            print 'temp and logD not the same length'
            print 'Celcius:', celcius
            print 'logD:', logD            
            return

        # change temperature scale
        x = []
        for k in range(len(celcius)):
            x.append(1.0e4 / (celcius[k] + offset_celcius + 273.15))

        if show_error is True:
            if Derror is not None:
                fig_axis.errorbar(x, logD, yerr=Derror, ecolor=style['color'],
                                  fmt=None)
               
        fig_axis.plot(x, logD, label=legendlabel, **style)


    def plotDx(self, fig_axis, llabel='// [100]', offset_celsius=0, er=True):
#        style_x = dict(self.basestyle.items() + pynams.style_Dx.items())
        style_x = self.basestyle
        style_x['fillstyle'] = pynams.style_Dx['fillstyle']
        self.plotloop(fig_axis, self.celcius_x, self.logDx, style_x, llabel, 
                       offset_celsius, Derror=self.logDx_error,
                       show_error=er)
        
    def plotDy(self, fig_axis, llabel='// [010]', offset_celsius=0, er=True):
#        style_y = dict(self.basestyle.items() + pynams.style_Dy.items())
        style_y = self.basestyle
        style_y['fillstyle'] = pynams.style_Dy['fillstyle']
        self.plotloop(fig_axis, self.celcius_y, self.logDy, style_y, llabel, 
                       offset_celsius, Derror=self.logDy_error,
                       show_error=er)
        
    def plotDz(self, fig_axis, llabel='// [001]', offset_celsius=0, er=True):
#        style_z = dict(self.basestyle.items() + pynams.style_Dz.items())
        style_z = self.basestyle
        style_z['fillstyle'] = pynams.style_Dz['fillstyle']
        self.plotloop(fig_axis, self.celcius_z, self.logDz, style_z, llabel,
                       offset_celsius, Derror=self.logDz_error,
                       show_error=er)
        
    def plotDu(self, fig_axis, llabel='unoriented', offset_celsius=0, er=True):
#        style_u = dict(self.basestyle.items() +pynams.style_unoriented.items())
        style_u = self.basestyle
#        style_u['fillstyle']
        self.plotloop(fig_axis, self.celcius_unoriented, self.logD_unoriented, 
                      style_u, llabel, offset_celsius, Derror=self.logDu_error,
                      show_error=er)
            
    def plotD(self, fig_axis, xoffset_celsius=0, er=True, legend_add=False,
              legend_handle_list=None):
                  
        if legend_add is True and legend_handle_list is None:
            print self.description
            print 'Need legend_handle_list for legend'
            return
            
        if legend_add is True:
            self.add_to_legend(fig_axis, legend_handle_list)

        self.plotDx(fig_axis, offset_celsius=xoffset_celsius, er=er)
        self.plotDy(fig_axis, offset_celsius=xoffset_celsius, er=er)
        self.plotDz(fig_axis, offset_celsius=xoffset_celsius, er=er)
        self.plotDu(fig_axis, offset_celsius=xoffset_celsius, er=er)
        

    def add_to_legend(self, fig_axis, legend_handle_list, sunk=-2.0,
                      descript=None, orientation=None, addline=False,
                      ncol=2):
        """Take a figure axis and its list of legend handles 
        and adds information to it"""
        if descript is None:
            if self.description is None:
                print 'Need description!'
                return
            else:
               descript = self.description
        
        # set marker style
#        if orientation == 'x':
#            bstyle = dict(self.basestyle.items() + pynams.style_Dx.items())
#        elif orientation == 'y':
#            bstyle = dict(self.basestyle.items() + pynams.style_Dy.items())
#        elif orientation == 'z':
#            bstyle = dict(self.basestyle.items() + pynams.style_Dz.items())
#        elif orientation == 'u':
#            bstyle = dict(self.basestyle.items() + 
#                          pynams.style_unoriented.items())
#        else:
        bstyle = self.basestyle
        bstyle['fillstyle'] = 'full'

        # set line style
        if addline is False:
            bstyleline = bstyle
        elif addline is True:
            if orientation == 'x':
                bstyleline = dict(bstyle.items() +pynams.style_Dx_line.items())
            elif orientation == 'y':
                bstyleline = dict(bstyle.items() +pynams.style_Dy_line.items())
            elif orientation == 'z':
                bstyleline = dict(bstyle.items() +pynams.style_Dz_line.items())
            elif orientation == 'u':
                bstyleline = dict(bstyle.items() + 
                            pynams.style_unoriented_line.items())
            
        add_marker = mlines.Line2D([], [], label=descript, **bstyleline)
        
        legend_handle_list.append(add_marker)
        
        low = fig_axis.get_xlim()[0]
        high = fig_axis.get_xlim()[1]
        bottom = fig_axis.get_ylim()[0]
        main_legend = plt.legend(handles=legend_handle_list, 
                                 numpoints=1, ncol=ncol, 
                                 bbox_to_anchor=(low, bottom, high-low, sunk),
                                 bbox_transform=fig_axis.transData, 
                                 mode='expand')
        plt.gca().add_artist(main_legend)
        return legend_handle_list

generic = Diffusivities()
generic.basestyle = {'marker' : 's', 'color' : 'black', 'alpha' : 0.5,
                     'markersize' : 8, 'linestyle': 'none'}
