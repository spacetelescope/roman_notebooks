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
        self.ymin = 1e-2  # Setting the y-axis min and max for plotting
        self.ymax = 1e3
        self.ma_table = 'im_120_8'  #'im_135_8'
        # self.nresultant = 5
        self.background = 'hlwas-medium_field1_medium'
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

        # background_options = ['hlwas-medium_field1', 'hlwas-medium_field2',
        #                       'hlwas-wide_field1', 'hlwas-wide_field2', 'hlwas-wide_field3', 'hlwas-wide_field4',
        #                       'gbtds_mid_5stripe', 'hltds']
        # background_options = ['hlwas-medium_field1 & high', 'hlwas-medium_field1 & medium', 'hlwas-medium_field1 & low',
        #                       'hlwas-medium_field2 & high', 'hlwas-medium_field2 & medium', 'hlwas-medium_field2 & low',
        #                       'hlwas-wide_field1 & high','hlwas-wide_field1 & medium','hlwas-wide_field1 & low',
        #                       'hlwas-wide_field2 & high','hlwas-wide_field2 & medium','hlwas-wide_field2 & low',
        #                       'hlwas-wide_field3 & high','hlwas-wide_field3 & medium','hlwas-wide_field3 & low',
        #                       'hlwas-wide_field4 & high','hlwas-wide_field4 & medium','hlwas-wide_field4 & low',
        #                       'gbtds_mid_5stripe & high','gbtds_mid_5stripe & medium','gbtds_mid_5stripe & low',
        #                       'hltds & medium']       
        background_options = ['hlwas-medium_field1',
                              'hlwas-medium_field2', 
                              'hlwas-wide_field1',
                              'hlwas-wide_field2',
                              'hlwas-wide_field3',
                              'hlwas-wide_field4',
                              'gbtds_mid_5stripe',
                              'hltds']     
        # background_options = ['minzodi & benchmark']
        self.background_select = Select(title='Background', options=background_options, value='hlwas-medium_field1')
        
        # background_level_options = ['high', 'medium', 'low']
        # background_level_options = ['medium']
        # self.background_level_select = Select(title='Background Level', options=background_level_options, value='medium')

        # matable_options = ['C1_IMG_MICROLENS', 'C2A_IMG_HLWAS', 'C2B_IMG_HLWAS', 'C2C_IMG_HLWAS', 'C2D_IMG_HLWAS', 'C2E_IMG_HLWAS', 'C2F_IMG_HLWAS', 'C2G_IMG_HLWAS', 'C2H_IMG_HLWAS'] # 'defocus_mod', 'defocus_lrg'
        matable_options = ['im_60_6_s', 'im_66_6', 'im_76_7_s', 'im_85_7', 'im_95_7', 'im_101_7', 'im_107_7',
                           'im_107_8_s', 'im_120_8', 'im_135_8', 'im_152_9', 'im_171_10', 'im_193_11', 'im_193_14_s',
                           'im_225_13', 'im_250_14', 'im_284_14', 'im_294_16', 'im_307_16', 'im_360_16', 'im_409_16',
                           'im_420_16', 'im_460_16', 'im_500_16', 'im_550_16', 'im_600_16', 'im_650_16', 'im_700_16', 
                           'im_750_16', 'im_800_16', 'im_900_16', 'im_950_16', 'im_1000_16']
        self.matable_select = Select(title='MA Table (obs mode_exp time_# of resultants)', options=matable_options, value='im_120_8')
        
        # nresultant_options = ['2', '3', '4(Rec. Min)', '5', '6', '7', '8', '9', '10(Max)']    
        # self.nresultant_select = Select(title='# of Resultant', options=nresultant_options, value= '5')

        # for w1 in [self.magnitude_slider, self.background_select, self.matable_select, self.nresultant_select]:
        for w1 in [self.magnitude_slider, self.background_select, self.matable_select]:
            w1.on_change('value', self.update_data)

        for w2 in [self.magsys_button_group, self.sed_type_button_group]:
            w2.on_change('active', self.update_data)
        
        # Set up layouts and add to document
        label_magsys = Div(text='Input Magnitude Type')
        label_sedtype = Div(text='Spectrum Type')
        widgets = column(column(label_magsys, self.magsys_button_group), 
                         column(label_sedtype, self.sed_type_button_group), 
                         self.magnitude_slider, self.background_select, self.matable_select) # self.magnitude_slider, self.background_select, self.matable_select, self.nresultant_select        

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

        # Update the background level option based on the background selection
        if self.background_select.value == 'hltds':
            dynamic_background_level_options = ['medium']
        else:
            dynamic_background_level_options = ['high', 'medium', 'low']

        # New background level selection
        # self.background_level_select.options = dynamic_background_level_options

        # Now merge the background and level selection
        # Insert '_' to match the formatting
        if (self.background_select.value == 'hlwas-medium_field1'):
            new_background = 'hlwas-medium_field1_medium'        
        elif (self.background_select.value == 'hlwas-medium_field2'):
            new_background = 'hlwas-medium_field2_medium'        
        elif (self.background_select.value == 'hlwas-wide_field1'):
            new_background = 'hlwas-wide_field1_medium'      
        elif (self.background_select.value == 'hlwas-wide_field2'):
            new_background = 'hlwas-wide_field2_medium'      
        elif (self.background_select.value == 'hlwas-wide_field3'):
            new_background = 'hlwas-wide_field3_medium'      
        elif (self.background_select.value == 'hlwas-wide_field4'):
            new_background = 'hlwas-wide_field4_medium'      
        elif (self.background_select.value == 'gbtds_mid_5stripe'):
            new_background = 'gbtds_mid_5stripe_medium'      
        elif (self.background_select.value == 'hltds'):
            new_background = 'hltds_medium'            
        else:
            new_background = self.background_select.value
            
        # New MA table selection    
        new_matable = self.matable_select.value

        # Update the nresultant select option based on the MA table selection
        # This is just to show the max resultant (not the truncation)
        if self.matable_select.value in ['im_60_6_s','im_66_6']:
            dynamic_nresultant_options = '5'  
        elif self.matable_select.value in ['im_76_7_s', 'im_85_7', 'im_95_7', 'im_101_7', 'im_107_7']:
            dynamic_nresultant_options = '6'        
        elif self.matable_select.value in ['im_107_8_s', 'im_120_8', 'im_135_8']:
            dynamic_nresultant_options = '7' 
        elif self.matable_select.value in ['im_152_9']:
            dynamic_nresultant_options = '8' 
        elif self.matable_select.value in ['im_171_10']:
            dynamic_nresultant_options = '9' 
        elif self.matable_select.value in ['im_193_11']:
            dynamic_nresultant_options = '10' 
        elif self.matable_select.value in ['im_225_13']:
            dynamic_nresultant_options = '12' 
        elif self.matable_select.value in ['im_193_14_s', 'im_250_14', 'im_284_14']:
            dynamic_nresultant_options = '13' 
        elif self.matable_select.value in ['im_294_16', 'im_307_16', 'im_360_16', 'im_409_16', 'im_420_16', 
                                           'im_460_16', 'im_500_16', 'im_550_16', 'im_600_16', 'im_650_16', 'im_700_16', 
                                           'im_750_16', 'im_800_16', 'im_900_16', 'im_950_16', 'im_1000_16']:
            dynamic_nresultant_options = '15' 

        # New # of resultant selection
        # self.nresultant_select.options = dynamic_nresultant_options
        new_nresultant = dynamic_nresultant_options  # self.nresultant_select.value

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
        self.sed_type = new_sedtype

        # Search the grid that matches the selection
        lookup = self.lookup_grid()
        new_result = self.master_grid[lookup]
    
        # Generate the new data points
        snr = new_result.interp(magnitude=new_magnitude) 
        snr_saturated = new_result.interp(magnitude=new_magnitude) 

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
        # grid_name = self.ma_table + '_' + str(self.nresultant) + '_' + self.background + '_' + self.mag_system + '_' + self.sed_type
        grid_name = self.ma_table + '_'  + self.background + '_' + self.mag_system + '_' + self.sed_type

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
            grid_properties.append(self.master_grid[gp].attrs['ma_table']['name'] + 
                                   '_' + self.master_grid[gp].attrs['background'] + 
                                   '_' + self.master_grid[gp].attrs['mag_system'] + 
                                   '_' + self.master_grid[gp].attrs['sed_type'])

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
