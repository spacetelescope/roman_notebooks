import numpy as np
import pandas as pd
import os

from bokeh.plotting import figure
from bokeh.models.formatters import BasicTickFormatter
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import Slider, Select, Div, RadioButtonGroup
from bokeh.models.annotations import Title
from bokeh.layouts import column, row, layout
from bokeh.io import show, output_notebook # enables plot interface in the Jupyter notebook
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.palettes import Sunset

output_notebook()


# To add or remove any parameter, edit the following functions:
# lookup_grid, retrieve_grid_properties
# create_widgets, update_data


class plot_rist():

    def __init__(self):
        '''
        Creates a new instance for RIST and generate a new plot

        '''

        # Initial setup with default inputs to initiate RIST plot
        self.master_grid, self.colors = self.load_grid()


        self.magnitude = 20
        self.ymin = 1e-2        # Setting the y-axis min and max for plotting
        self.ymax = 1e3
        self.ma_table = 'C2A_IMG_HLWAS'
        self.nresultant = 5
        self.background = 'minzodi_benchmark'
        self.mag_system = 'abmag'
        self.sed_type = 'flat_'

        self.grid_properties = self.retrieve_grid_properties()
        self.source = self.initial_setup()

        self.plot = self.create_plot()
        self.widgets = self.create_widgets()
        self.layout_with_note = layout([
                                        [[self.widgets], [self.plot]]
                                        ], width=1400)


    def create_plot(self):
        '''
        Creates a new plot window with proper axis labels, title, and legend

        Returns:
        --------
            plot: the bokeh figure

        '''       
        tooltips = [('Filter', '@desc'),
                    ('SNR', '@snr{0.00}')]       

        plot = figure(height=450, width=800, title='  ',
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
        legend.label_width = 45
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

        # Choose a magnitude system
        self.magsys_button_group = RadioButtonGroup(labels=['AB Mag', 'Vega Mag'], active=0)

        # Magnitude slider
        mags = np.array(self.master_grid[0].coords['magnitude']) # Using the first Xarray's attribute to set the coordinates
        magnitude_slider_min = min(mags)
        magnitude_slider_max = max(mags)

        self.magnitude_slider = Slider(start=magnitude_slider_min, end=magnitude_slider_max, value=20, step=.1, title='Magnitude', direction="rtl")

        # SED type
        self.sed_type_button_group = RadioButtonGroup(labels=['Flat', 'A0V', 'G2V', 'M5V'], active=0)

        background_options = ['minzodi & benchmark']
        self.background_select = Select(title='Background & Level', options=background_options, value='minzodi & benchmark')
        
        matable_options = ['C1_IMG_MICROLENS', 'C2A_IMG_HLWAS', 'C2B_IMG_HLWAS', 'C2C_IMG_HLWAS', 'C2D_IMG_HLWAS', 'C2E_IMG_HLWAS', 'C2F_IMG_HLWAS', 'C2G_IMG_HLWAS', 'C2H_IMG_HLWAS'] # 'defocus_mod', 'defocus_lrg'
        self.matable_select = Select(title='MA Table', options=matable_options, value='C2A_IMG_HLWAS')
        
        nresultant_options = ['2', '3', '4(Rec. Min)', '5', '6', '7', '8', '9', '10(Max)']    
        self.nresultant_select = Select(title='# of Resultant', options=nresultant_options, value= '5')

        for w1 in [self.magnitude_slider, self.background_select, self.matable_select, self.nresultant_select]:
            w1.on_change('value', self.update_data)

        for w2 in [self.magsys_button_group, self.sed_type_button_group]:
            w2.on_change('active', self.update_data)
        
        # Set up layouts and add to document
        label_magsys = Div(text='Input Magnitude Type')
        label_sedtype = Div(text='Spectrum Type')
        widgets = column(column(label_magsys, self.magsys_button_group), 
                        column(label_sedtype, self.sed_type_button_group), 
                        self.magnitude_slider, self.background_select, self.matable_select, self.nresultant_select)
        

        return widgets
    
    

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
        if self.background_select.value == 'minzodi & benchmark':
            new_background = 'minzodi_benchmark'
        elif self.background_select.value == 'ecliptic & low':
            new_background = 'ecliptic_low'         
        elif self.background_select.value == 'ecliptic & medium':
            new_background = 'ecliptic_medium'
        elif self.background_select.value == 'ecliptic & high':
            new_background = 'ecliptic_high'
        elif self.background_select.value == 'minzodi & low':
            new_background = 'minzodi_low'         
        elif self.background_select.value == 'minzodi & medium':
            new_background = 'minzodi_medium'
        elif self.background_select.value == 'minzodi & high':
            new_background = 'minzodi_high'                      
        elif self.background_select.value == 'none':
            new_background = 'none_'            
        else:
            new_background = self.background_select.value
            
        # New MA table selection    
        new_matable = self.matable_select.value

        # Update the nresultant select option based on the MA table selection
        if self.matable_select.value == 'C1_IMG_MICROLENS':
            dynamic_nresultant_options = ['2', '3', '4(Rec. Min)', '5', '6(Max)']       
        elif self.matable_select.value == 'C2A_IMG_HLWAS':
            dynamic_nresultant_options = ['2', '3', '4(Rec. Min)', '5', '6', '7', '8', '9', '10(Max)']        
        elif self.matable_select.value == 'C2B_IMG_HLWAS':
            dynamic_nresultant_options = ['2', '3', '4(Rec. Min)', '5', '6', '7', '8', '9', '10', '11', '12', '13(Max)']   
        else:
            dynamic_nresultant_options = ['2', '3', '4(Rec. Min)', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16(Max)'] 
 

        # New # of resultant selection
        self.nresultant_select.options = dynamic_nresultant_options
            
        # If the exact text for nresultant doesn't belong to the option, give them a special treatment
        # This is to handle cases for switching between MA tables
        if self.nresultant_select.value not in dynamic_nresultant_options:
            # Split the text to further examine
            nresultant_text_handle = str.split(self.nresultant_select.value, '(')
    
            if self.matable_select.value == 'C1_IMG_MICROLENS': 
                if int(nresultant_text_handle[0]) == 4:
                    self.nresultant_select.value = '4(Rec. Min)'
                elif int(nresultant_text_handle[0]) >= 6:
                    self.nresultant_select.value = '6(Max)' # If the input value is greater than the max, set it back to max
                else:
                    self.nresultant_select.value = nresultant_text_handle[0]                                     
            elif self.matable_select.value == 'C2A_IMG_HLWAS':
                if int(nresultant_text_handle[0]) == 4:
                    self.nresultant_select.value = '4(Rec. Min)'
                elif int(nresultant_text_handle[0]) >= 10:
                    self.nresultant_select.value = '10(Max)' # If the input value is greater than the max, set it back to max
                else:
                    self.nresultant_select.value = nresultant_text_handle[0]
            elif self.matable_select.value == 'C2B_IMG_HLWAS':
                if int(nresultant_text_handle[0]) == 4:
                    self.nresultant_select.value = '4(Rec. Min)'
                elif int(nresultant_text_handle[0]) == 13:
                    self.nresultant_select.value = '13(Max)' # If the input value is greater than the max, set it back to max   
                else:
                    self.nresultant_select.value = nresultant_text_handle[0]                         
            else:
                if int(nresultant_text_handle[0]) == 4:
                    self.nresultant_select.value = '4(Rec. Min)'
                elif int(nresultant_text_handle[0]) == 16:
                    self.nresultant_select.value = '16(Max)' # If the input value is greater than the max, set it back to max   
                else:
                    self.nresultant_select.value = nresultant_text_handle[0]                         
        
                        
        # To assign the selection to nresultant, I need to drop the (Rec. Min) and (Max) text 
        if self.nresultant_select.value in ['4(Rec. Min)', '6(Max)', '10(Max)', '13(Max)', '16(Max)']:
            new_nresultant = str.split(self.nresultant_select.value, '(')[0]
        else:
            new_nresultant = self.nresultant_select.value


        # Treat the magnitude system
        if self.magsys_button_group.active == 0:
            new_magsys = 'abmag'
        else:
            new_magsys = 'vegamag'

        # Treat the SED type
        if self.sed_type_button_group.active == 0:
            new_sedtype = 'flat_'
        elif self.sed_type_button_group.active == 1:
            new_sedtype = 'phoenix_a0v'
        elif self.sed_type_button_group.active == 2:
            new_sedtype = 'phoenix_g2v'
        elif self.sed_type_button_group.active == 3:
            new_sedtype = 'phoenix_m5v'            



        # Assign the newly selected values
        self.ma_table = new_matable
        self.nresultant = new_nresultant
        self.background = new_background

        self.mag_system = new_magsys
        self.sed_type =  new_sedtype


        # Search the grid that matches the selection
        lookup = self.lookup_grid()
        new_result = self.master_grid[lookup]
    
        # Generate the new data points
        snr = new_result.interp(magnitude = new_magnitude) 
        snr_saturated = new_result.interp(magnitude = new_magnitude) 

        # Treat the dim points first to avoid a confusion with how the saturated points are plotted
        # This is because the saturated points will be set to ymin * 1.1 in the next few lines
        # Some dim targets' SNRs are happened to be ymin * 1.1. so set them to any value 
        # just above ymin*1.1 to be replaced to 0 later
        # The value also has to be non 0 which is what Pandeia sets for the saturated sources from the calculation) 
        # This treatment is for the snr_saturated array to make them not appear in the plot as 'saturated' points
        snr_saturated = snr_saturated.where(snr_saturated != round(self.ymin*1.1, 3), round(self.ymin*1.11, 4))
        
        # Also changing SNR = ymin because ymin * 1.1 and ymin are too close in the log space and
        # it still looks like it is a saturated point in the plot (turn to the triangle)
        snr_saturated = snr_saturated.where(snr_saturated != round(self.ymin, 3), round(self.ymin*1.11, 4))

        # Unfortunately, there are also SNR = 0 for the actual dim star..
        if new_magnitude > 26:
            # Set the actual SNR=0 to nan to not get confused with the saturated onnes
            snr_saturated = snr_saturated.where(snr_saturated != 0, np.nan)

        # Create array of saturated points
        # Pandas dataframe's built-in where function 'keeps the original values where the condition is True and replaces them with 
        # NaN or another specified value where the condition is False.' 
        snr_saturated = snr_saturated.where(snr_saturated != 0, round(self.ymin*1.1, 3))  # Look for where SNR = 0 and set it to ymin*1.1
        snr_saturated = snr_saturated.where(snr_saturated <= round(self.ymin*1.1, 3), 0)  # Look for where 

        self.source.data['snr'] = snr
        self.source.data['snr_saturated'] = snr_saturated     



    def load_grid(self):

        '''
        Loads the pre-computed Pandeia grid

        Returns:
        --------
        master_grid: the loaded pre-computed Pandeia grid
        colors: color scheme for plotting

        '''

        # Load the master grid
        # master_grid = pd.read_pickle('grid_wfi.pkl')
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
        grid_name = self.ma_table + '_' + str(self.nresultant) + '_' + self.background + '_' + self.mag_system + '_' + self.sed_type
        
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
                                + '_' + self.master_grid[gp].attrs['background'] + '_' + self.master_grid[gp].attrs['mag_system'] + '_' + self.master_grid[gp].attrs['sed_type'])

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

