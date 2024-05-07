##############################
# Uitilities to create grids for RIST and run plot
##############################


import numpy as np
import pandas as pd
import os

from bokeh.plotting import figure
from bokeh.models.formatters import BasicTickFormatter
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import Slider, Select, Div
from bokeh.models.annotations import Title
from bokeh.layouts import column, row, layout
from bokeh.io import show, output_notebook# enables plot interface in the Jupyter notebook
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.palettes import Sunset

output_notebook()



class plot_rist():

    def __init__(self):
        '''
        Creates a new instance for RIST and generate a new plot

        '''

        # Initial setup with default inputs to initiate RIST plot
        # self.grid_date = '2024-04-26'
        self.master_grid, self.colors = self.load_grid()


        self.magnitude = 20
        self.ymin = 1e-2        # Setting the y-axis min and max for plotting
        self.ymax = 1e3
        self.ma_table = 'hlwas_imaging'
        self.nresultant = 5
        self.background = 'minzodi_benchmark'

        self.grid_properties = self.retrieve_grid_properties()
        self.source = self.initial_setup()

        self.plot = self.create_plot()
        self.widgets = self.create_widgets()
        self.usage_note = self.create_notes()
        self.layout_with_note = layout([
                                        [[self.widgets], [self.plot]], 
                                        [self.usage_note]
                                        ], width=1600)


    def create_plot(self):
        '''
        Creates a new plot window with proper axis labels, title, and legend

        Returns:
        --------
            plot: the bokeh figure

        '''       
        tooltips = [('Filter', '@desc'),
                    ('SNR', '@snr{int}')]       

        plot = figure(height=450, width=900, title='  ',
                      tools='crosshair,pan,reset,save,box_zoom,hover',
                      x_range=[0.5, 2.5], y_range=[self.ymin, self.ymax],
                      x_axis_type='log', y_axis_type='log',
                      tooltips=tooltips)

    
        axis_formatter = BasicTickFormatter(power_limit_low=-4, power_limit_high=4)
        
        plot.title.text_font_size = '16pt'
        plot.title.align = 'center'
        plot.xaxis.axis_label = 'Wavelength [micron]'
        plot.xaxis.axis_label_text_font_size = '16pt'
        plot.xaxis.major_label_text_font_size = '12pt'
        plot.xaxis.axis_label_text_font_style = 'normal'
        plot.xaxis[0].formatter = axis_formatter

        plot.yaxis.axis_label = 'Signal-to-noise ratio'
        plot.yaxis.axis_label_text_font_size = '16pt'
        plot.yaxis.major_label_text_font_size = '12pt'
        plot.yaxis.axis_label_text_font_style = 'normal'
        plot.yaxis[0].formatter = axis_formatter

        # Plot the initial values across the filters
        # This takes whatever information that is in the 'source' that is defined above
        plot.scatter('wvl', 'snr', source=self.source, size=12, alpha=0.9, marker='circle',
                     fill_color='color', line_color='#b3b3cc',
                     hover_color='#b3b3cc', hover_alpha=0.5, legend_field='desc') 

        plot.scatter('wvl', 'snr_saturated', source=self.source, size=12, alpha=0.9, marker='triangle',
                     fill_color='color', line_color='#b3b3cc',
                     hover_color='#b3b3cc', hover_alpha=0.5)

        # Legend
        legend = plot.legend[0]
        legend.location = 'center'
        legend.label_text_font_size = '12pt'
        legend.label_width = 60
        plot.add_layout(legend, 'right')

        # Title
        title = Title(text='Roman Interactive Sensitivity Tool (RIST)', align='center', text_font_size='15pt')
        plot.add_layout(title, 'above')

        return plot

    
    def create_widgets(self):
        '''
        Creates widgets for the bokeh plot

        Returns:
        --------
        widgets: bokeh column layout that conatins the followings:
                one slider for target magntidue, 
                3 drop-down selecters for background, MA table, and # of resultants

        '''             
        # Set up widgets
        mags = np.array(self.master_grid[0].coords['magnitude']) # Using the first Xarray's attribute to set the coordinates
        magnitude_slider_min = min(mags)
        magnitude_slider_max = max(mags)

        self.magnitude_slider = Slider(start=magnitude_slider_min, end=magnitude_slider_max, value=20, step=.1, title='Magnitude (ABmag)', direction="rtl")

        background_options = ['ecliptic & low', 'ecliptic & medium', 'ecliptic & high', 'zodiacal & 120%min', 'none']
        self.background_select = Select(title='Background & Level', options=background_options, value='zodiacal & 120%min')
        
        matable_options = ['hlwas_imaging', 'hltds_imaging1', 'hltds_imaging2', 'hltds_imaging3', 'hltds_imaging4', 'gbtds'] # 'defocus_mod', 'defocus_lrg'
        self.matable_select = Select(title='MA Table', options=matable_options, value='hlwas_imaging')
        
        # nresultant_options = ['1', '2', '3(Rec. Min)', '4', '5', '6', '7', '8(Max)']    # macthing nresultant options for hlwas 
        nresultant_options = ['2', '3(Rec. Min)', '4', '5', '6', '7', '8(Max)']    
        self.nresultant_select = Select(title='# of Resultant', options=nresultant_options, value= '5')

        for w in [self.magnitude_slider, self.background_select, self.matable_select, self.nresultant_select]:
            w.on_change('value', self.update_data)
        
        # Set up layouts and add to document
        widgets = column(self.magnitude_slider, self.background_select, self.matable_select, self.nresultant_select)
        

        return widgets
    

    def create_notes(self):
        '''
        Creates notes for the bokeh plot

        Returns:
        --------
        usage_note: bokeh widget that conatins the usage notes
        '''       

        # Annotation
        message = ''
        message += '<h2>Notes</h2>'  
        message += '<ul>'
        message += '<li> RIST assumes a flat spectrum point source target. For extended sources or targets with different spectral shapes, '
        message += ' please use Pandeia for more accurate results. </li>'
        message += '<li> Current version of the RIST only supports the imaging mode of the WFI. </li>'
        message += '<li> RIST uses a pre-computed grid of Pandeia spanning a set of the following inputs: source brightness, '
        message += ' background and level, MA table, and number of resultants. </li>'
        message += '<ul><li> The target magnitude is in ABmag. </ul></li>'        
        message += '<ul><li> For the background spectrums: </ul></li>'
        message += '<ul><ul><li> The zodiacal background spectrum is set to 120% of the minimum zodiacal background with  assumed date of January 16, 2020'
        message += ' and RA & DEC of ' + r'17$$^h$$26$$^m$$44$$^s$$ & -73$$^\circ$$19$$^m$$56$$^s$$ </ul></ul></li>' 
        message += '<ul><li>For the MA tables: </li>'
        message += '<ul><li> HLWAS: High Latitude Wide Area Survey </li></ul>'
        message += '<ul><li> HLTDS: High Latitude Time Domain Survey </li></ul>'
        message += '<ul><li> GBTDS: Galactic Bulge Time Domain Survey </li></ul></ul>'
        message += '<li> Computed values for the SNR can be seen by hovering the mouse over the points. </li>'
        message += '<li> Pandeia sets SNR to zero for saturated points and hence the RIST  '
        message += '-- the saturated points are marked with triangles in the plot</li>'        
        message += '<li> The x-axis shows the central wavelength of each Roman filter. </li>'
        message += '<li> Please see the <a href="https://roman-docs.stsci.edu/">RDox</a>'
        message += ' for the detailed references of'
        message += ' RIST (to be linked) '
        message += ' and <a href="https://roman-docs.stsci.edu/simulation-tools-handbook-home/pandeia-for-roman/overview-of-pandeia">Pandeia</a>. </li>'
        message += '</ul>'

        usage_note = Div(text=message, styles = {'font-size': '12pt'}, 
                         width=1050, height=500, width_policy = 'fixed', align='center')

        return usage_note
    

    def update_data(self, attrname, old, new):
        '''
        Updates the bokeh plot for newly computed SNR based on the user inputs

        Inputs:
        --------
        attrname: name of the widget to take new input -- in this case, it's eiter one of the 4:
                  target magnitude, background, MA table, and # of resultant
        old: old value
        new: new value to compute SNR

        '''  

        # New target magnitude selection
        new_magnitude = self.magnitude_slider.value

        # New background selection
        # Insert '_' to match the formatting
        if self.background_select.value == 'zodiacal & 120%min':
            new_background = 'minzodi_benchmark'
        elif self.background_select.value == 'ecliptic & low':
            new_background = 'ecliptic_low'         
        elif self.background_select.value == 'ecliptic & medium':
            new_background = 'ecliptic_medium'
        elif self.background_select.value == 'ecliptic & high':
            new_background = 'ecliptic_high'              
        elif self.background_select.value == 'none':
            new_background = 'none_'            
        else:
            new_background = self.background_select.value
            
        # New MA table selection    
        new_matable = self.matable_select.value

        # Update the nresultant select option based on the MA table selection
        if (self.matable_select.value == 'hlwas_imaging' or 
            self.matable_select.value == 'hltds_imaging1'):
            dynamic_nresultant_options = ['2', '3(Rec. Min)', '4', '5', '6', '7', '8(Max)']
            # dynamic_nresultant_options = ['1', '2', '3(Rec. Min)', '4', '5', '6', '7', '8(Max)']               
        elif self.matable_select.value == 'hltds_imaging2':
            dynamic_nresultant_options = ['2(Rec. Min)', '3', '4', '5', '6', '7', '8(Max)']        
        elif self.matable_select.value == 'hltds_imaging3':
            dynamic_nresultant_options = ['2', '3', '4(Rec. Min)', '5', '6', '7', '8', '9', '10(Max)']   
        elif self.matable_select.value == 'hltds_imaging4':
            dynamic_nresultant_options = ['2', '3', '4', '5', '6(Rec. Min)', '7', '8', '9', '10(Max)'] 
        elif self.matable_select.value == 'gbtds':
            dynamic_nresultant_options = ['2(Rec. Min)', '3', '4', '5', '6(Max)']   

        # New # of resultant selection
        self.nresultant_select.options = dynamic_nresultant_options
            
        # If the exact text for nresultant doesn't belong to the option, give them a special treatment
        if self.nresultant_select.value not in dynamic_nresultant_options:
            # Split the text to further examine
            nresultant_text_handle = str.split(self.nresultant_select.value, '(')
    
            if (self.matable_select.value == 'hlwas_imaging' or
                self.matable_select.value == 'hltds_imaging1'): 
                if int(nresultant_text_handle[0]) == 3:
                    self.nresultant_select.value = '3(Rec. Min)'
                elif int(nresultant_text_handle[0]) >= 8:
                    self.nresultant_select.value = '8(Max)' # If the input value is greater than the max, set it back to max
                else:
                    self.nresultant_select.value = nresultant_text_handle[0]                                     
            elif self.matable_select.value == 'hltds_imaging2':
                if int(nresultant_text_handle[0]) == 2:
                    self.nresultant_select.value = '2(Rec. Min)'
                elif int(nresultant_text_handle[0]) >= 8:
                    self.nresultant_select.value = '8(Max)' # If the input value is greater than the max, set it back to max
                else:
                    self.nresultant_select.value = nresultant_text_handle[0]
            elif self.matable_select.value == 'hltds_imaging3':
                if int(nresultant_text_handle[0]) == 4:
                    self.nresultant_select.value = '4(Rec. Min)'
                elif int(nresultant_text_handle[0]) == 10:
                    self.nresultant_select.value = '10(Max)' # If the input value is greater than the max, set it back to max   
                else:
                    self.nresultant_select.value = nresultant_text_handle[0]                         
            elif self.matable_select.value == 'hltds_imaging4':
                if int(nresultant_text_handle[0]) == 6:
                    self.nresultant_select.value = '6(Rec. Min)'
                elif int(nresultant_text_handle[0]) == 10:
                    self.nresultant_select.value = '10(Max)' # If the input value is greater than the max, set it back to max   
                else:
                    self.nresultant_select.value = nresultant_text_handle[0]                         
            elif self.matable_select.value == 'gbtds':
                if int(nresultant_text_handle[0]) == 2:
                    self.nresultant_select.value = '2(Rec. Min)'
                elif int(nresultant_text_handle[0]) >= 6:
                    self.nresultant_select.value = '6(Max)' # If the input value is greater than the max, set it back to max 
                else:
                    self.nresultant_select.value = nresultant_text_handle[0]                  
                        
        # To assign the selection to nresultant, I need to drop the (Rec. Min) and (Max) text 
        if self.nresultant_select.value in ['2(Rec. Min)', '3(Rec. Min)', '4(Rec. Min)', '6(Rec. Min)', '6(Max)', '8(Max)', '10(Max)']:
            new_nresultant = str.split(self.nresultant_select.value, '(')[0]
        else:
            new_nresultant = self.nresultant_select.value

        self.ma_table = new_matable
        self.nresultant = new_nresultant
        self.background = new_background

        # For testing purpose only
        # new_values = new_matable + '_' + new_nresultant + '_' + new_background
        # print('New Values:' + new_values)

        # Search the grid that matches the selection
        lookup = self.lookup_grid()
        new_result = self.master_grid[lookup]
    
        # Generate the new data points
        # wvl = new_result.attrs['central_wvl']
        snr = new_result.interp(magnitude = new_magnitude) 
        snr_saturated = new_result.interp(magnitude = new_magnitude) 

        # Create array of saturated points
        snr_saturated = snr_saturated.where(snr_saturated != 0, self.ymin*1.1)
        snr_saturated = snr_saturated.where(snr_saturated <= self.ymin*1.1, 0)

        self.source.data['snr'] = snr
        self.source.data['snr_saturated'] = snr_saturated
        # For testing purpose only
        # print('New SNR delivered: ' + str(self.source.data['snr'].values) + ' for mag =  ' + str(new_magnitude) + ' and '+ new_background)
        # print('Lingering nresultant value: ' + str(self.nresultant_select.value))        



    def load_grid(self):

        '''
        Loads the pre-computed Pandeia grid

        Returns:
        --------
        master_grid: the loaded pre-computed Pandeia grid
        colors: color scheme for plotting

        '''

        # Load the master grid
        # module_dir = os.path.dirname(os.path.realpath(__file__))
        # rist_data_dir = os.path.join(os.path.dirname(module_dir), 'data')
        # master_grid = pd.read_pickle(rist_data_dir+'/grid_wfi_{}.pkl'.format(self.grid_date))
        master_grid = pd.read_pickle('grid_wfi.pkl')

        # Use color scheme of Sunset for plotting each filters
        # WFI has 8 filters
        num_colors = len(master_grid[0].coords['filters'].values)
        colors = Sunset[num_colors]

        return master_grid, colors



    def lookup_grid(self):
        '''
        Searches the pre-computed grid to find the matching input request for (MA table, # of resultant, and background)

        Returns:
        --------
        lookup: index number that corresponds to the requested inputs

        '''
 
        grid_name = self.ma_table + '_' + str(self.nresultant) + '_' + self.background
        lookup = np.where(grid_name == self.grid_properties)[0][0]

        return lookup

    def initial_setup(self):
        '''
        Sets up the initial data source to initiate the bokeh plot

        Returns:
        --------
        source: the data source that conatins computed SNR for a set of default values that were assigned withing __init__
                magnitude = 20
                MA table = hlwas_imaging
                nresultant = 5
                background = minzodi_benchmark

        '''
     
        initial_lookup = self.lookup_grid()
        initial_result = self.master_grid[initial_lookup].interp(magnitude = self.magnitude) 
        initial_data = {'wvl': initial_result.attrs['central_wvl'], 'snr': initial_result.values, 
                        'snr_saturated': np.zeros(len((initial_result.values))), 
                        'color': self.colors, 'desc': initial_result.coords['filters'].values}
        
        # create a ColumnDataSource by passing the dict
        source = ColumnDataSource(data=initial_data)

        return source 
    

    def retrieve_grid_properties(self):
        '''
        Retrieves information for the loaded pre-computed Pandeia grid

        Returns:
        --------
        grid_properties: numpy array containing the information regarding MA table, # of resultants, and background

        '''

        # Get the grid properties
        grid_properties = []
        for gp, grid_property in enumerate(self.master_grid):
            grid_properties.append(self.master_grid[gp].attrs['ma_table']['name'] + '_' + str(self.master_grid[gp].attrs['ma_table']['nresultant'])
                                + '_' + self.master_grid[gp].attrs['background'])

        # Convert the list to numpy array
        grid_properties = np.asarray(grid_properties)

        return grid_properties


    def modify_doc(doc):
        '''
        Packages the bokeh plot in the document

        Returns:
        --------
        doc: document contatining the bokeh plots and its neccessaries

        '''        
        layout_with_note = plot_rist().layout_with_note
        doc.add_root(row(layout_with_note, width=800))
        doc.title = "Roman Interactive Sensitivity Tool (RIST)"

        return doc
    
    
    handler = FunctionHandler(modify_doc)
    app = Application(handler)
    show(app)
    # show(app, notebook_url='http://localhost:7324')
