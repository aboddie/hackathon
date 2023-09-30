from collections import Counter
import json
import os
import re
from typing import Counter #TODO Drop once put on webapp and use python >=3.9
from typing import Dict
from typing import List
from typing import Tuple

from flask import render_template 
from flask import request
from flask import url_for
import pandasdmx as sdmx #TODO Probably faster to use something else as I don't need Pandas
import yaml #TODO switch to ruamel.yaml maybe

from . import app
from .yaml_configuration import YAMLConfiguration


#def represent_none(self, _):
#    return self.represent_scalar('tag:yaml.org,2002:null', '')
#
#yaml.add_representer(type(None), represent_none)

@app.template_filter('to_json')
def to_json(value):
    #TODO: get rid of this if possible
    return json.dumps(value)

def list_saved_dashboads() -> List[str]:
    '''Returns a list of all saved dashboards names.'''
    return [filename[:-5] for filename in os.listdir('hackathon/static/saved_dashboards/') if filename.endswith('.yaml')]

def get_index_from_row_counter(row_list: Counter[int], row_num: int, col_num: int) -> int:
    '''Returns the index of a visual in the list of visuals given its row and column numbers.'''
    return sum([row_list[i] for i in range(0, row_num)]) + col_num - 1

def get_weight(formating: List[str]) -> str:
    '''Returns weight option from formating string, if no weight found then normal is returned.
    Note these options are extended from the hackathon specs.
    '''
    options = ["bold", "bolder", "semibold", "medium", "light", "lighter"]
    for option in formating[2:]:
        if option in options:
            return option
    return "normal"

def get_italics(formating: List[str]) -> str:
    '''Returns italic or normal depending on content of formating.'''
    if "italics" in formating[2:]:
        return 'italic'
    return "normal"

def get_alignment(formating: List[str]) -> str:
    '''Returns alignment depending on content of formating.'''
    alignemnt_lookup = {'left':'start', 'center': 'center', 'right': 'end'}
    return alignemnt_lookup.get(formating[-1], 'center')

def get_legend_location(location: str) -> str:
    '''Returns legend location.'''
    if not location:
        return 'hide'
    location_options = {'top','left','bottom','right','hide'}
    if location.lower() in location_options:
        return location.lower()
    else:
        return 'hide'

def affix_unit(text: str, unit:str, unit_location:str) -> str:
    '''Affix unit to text in location specified by unit_location.'''
    if not unit:
        return text
    try:
        unit_location = unit_location.lower()
    except AttributeError:
        return text         
    if unit_location == 'hide':
        return text
    elif unit_location == 'prefix':
        return f'{unit} {text}'
    elif unit_location == 'suffix':
        return f'{text} {unit}'
    elif unit_location == 'under':
        return f'{text}<br />{unit}'
    else:
        return text

def get_formating(text: str, unit:str = '', unit_location:str = 'hide') -> str:
    '''Converts a string with text and formating information in brackets into HTML to render string
    according to formating.
    '''
    if text is None:
        return ''
    formating = [x.strip() for x in text[text.find("[")+1:text.find("]")].lower().split(",")]
    if len (formating) > 2:
        font = formating[0]
        fontsize = formating[1]
        weight = get_weight(formating)
        italics = get_italics(formating)
        alignment = get_alignment(formating)
        text = text[:text.find("[") - 1].strip()
        if text[-1] == ',':
            text = text[:-1]
        text = affix_unit(text, unit, unit_location)
        # Note Arial is added as a fall back font
        return f"<div class='row title justify-content-{alignment} fw-{weight} fst-{italics}' style='font-size: {fontsize}px; font-family: {font}, arial;'>{text}</div>"
    else:
        text = affix_unit(text, unit, unit_location)
        return f"<div class='row title justify-content-center'>{text}</div>" 

def get_chart_type(text: str) -> Tuple[str, str]:
    '''Pulls chart type and width from text. Defaults to unsonfigured, col.'''
    text_list = [x.strip() for x in text.lower().split(",")]
    size_options = {'single': 'col-4', 'double': 'col-8', 'triple': 'col-12'}
    chart_Mapping = {'title': 'title', 'pie': 'pie', 'value': 'value', 'lines': 'line', 'bars': 'bar', 'unconfigured': 'unconfigured'}
    width = 'col-4'
    chart_type = 'unconfigured'
    for option in text_list:
        if option in size_options:
            width = size_options[option]
        if option in chart_Mapping:
            chart_type = chart_Mapping[option]
    return chart_type, width

def create_table_setup(yaml_configuration: YAMLConfiguration) -> List:
    '''Generates a table set up from a yaml configuration which is a bit easier to work with.'''
    table_setup = []
    row_list = yaml_configuration.get_row_counter()
    for i in range(min(row_list.keys()), max(row_list.keys())+ 1):
        row_viz = [pulldata(row) for row in yaml_configuration["Rows"] if row["Row"] == i]
        table_setup.append(row_viz)
    return table_setup 

def pulldata(viz):
    #if there is data
    if (viz['DATA'] is not None) and (viz['DATA'] != 'None'):
        try:
            url = viz['DATA']
            req = sdmx.Request()
            myfile = req.get(url=url)
            dataflows = sdmx.to_pandas(myfile)
            p = re.compile(r"{\$(.*)}")
            for key, value in viz.items():
                if key == 'DATA':
                    viz[key] = dataflows.values.tolist()
                elif key in ['xAxisConcept','yAxisConcept', 'legendConcept']:
                    try:
                        code = dataflows.keys().get_level_values(str(value)).to_list()
                        viz[key] = code
                        #TODO: code to name use dsd and pull (Pandasdmx doesn't seem to pull either URNs or local representations from the sample file, should probably switch to something else)
                    except:
                        viz[key] = [value]
                else:
                    try:
                        if re.search(p, value):
                            lookupvalue = re.search(p, value).group(1)
                            code = dataflows.keys().get_level_values(lookupvalue).to_list()[0]
                            viz[key] = re.sub(f"{{\$({lookupvalue})}}", code, value)
                            #TODO: code to name use dsd and pull
                    except:
                        pass
        except:
            viz['DATA'] = [0]
    viz['chartType'], viz['width'] = get_chart_type(viz['chartType'])
    viz['TitleFormated'] = get_formating(viz.get('Title',None), unit=viz.get('Unit',None), unit_location=viz.get('unitLoc','Hide'))
    viz['SubtitleFormated'] = get_formating(viz.get('Subtitle',None))
    viz['NoteFormated'] = get_formating(viz.get('Note',None))
    viz['legendLoc'] = get_legend_location(viz.get('legendLoc',None))
    return viz


@app.route("/",methods = ['GET', 'POST'])
@app.route("/home", methods = ['GET', 'POST'])
def home():
    if request.method == 'GET':
        return render_template('editdashboard.html', configuration = '', table_setup = [], saved_dashboards = list_saved_dashboads())
    elif request.method == 'POST':
        yaml_configuration = yaml.safe_load(request.form['Configuration'])
        if not yaml_configuration:
            yaml_configuration = {"DashID": "ExampleCL", "Rows": list()} 
        configuration = YAMLConfiguration(yaml_configuration)

        if request.form['form'] == 'Update Layout':
            new_row_list = Counter()
            for i in range(request.form.get('num_of_rows', 0, type=int)):
                new_row_list[i] = request.form.get(f'num_of_col_row{i + 1}', 0, type=int)
            configuration.update_configuration(new_row_list)
        elif request.form['form'] == 'Update Visual':
            # Copy form data to dict:
            viz_configuration = dict(request.form)
            # Drop keys not needed in viz:
            viz_configuration.pop('Configuration', None)
            col_num = int(viz_configuration.get('viz_col_num', 0))
            viz_configuration.pop('viz_col_num', None)
            # Align elements to YAML specs
            for k, v in viz_configuration.items():
                if v == '':
                   viz_configuration[k] = None 
            viz_configuration['Row'] = int(viz_configuration.get('Row', 0)) - 1
            viz_configuration['chartType'] = viz_configuration['chartType'].upper()
            # Updata yaml_configuration
            row_list = configuration.get_row_counter()
            index_value = get_index_from_row_counter(row_list, viz_configuration['Row'], col_num)
            configuration["Rows"][index_value] = viz_configuration
        elif request.form['form'] == 'Update Configuration':
            pass
        elif request.form['form'] == 'Save Configuration':
            dashid = configuration['DashID']
            with open(f'hackathon/static/saved_dashboards/{dashid}.yaml','w') as yamlfile:
                #TODO yaml.dump is pulling off quotes and dropping duplicate visuals
                yaml.Dumper.ignore_aliases = lambda *args : True
                configuration_dump = yaml.dump(configuration.data, sort_keys=False)


        #TODO yaml.dump is pulling off quotes and dropping duplicate visuals
        yaml.Dumper.ignore_aliases = lambda *args : True
        configuration_dump = yaml.dump(configuration.data, sort_keys=False)
        #TODO Pull data should only pull updated data (Updated layout don't pull data, Updated visual, pull data only on that visual, updated configuration pull all data)
        table_setup = create_table_setup(configuration)
        return render_template('editdashboard.html', configuration = configuration_dump, table_setup = table_setup, saved_dashboards = list_saved_dashboads())

@app.route('/view/<dashid>')
def viewdashboard(dashid):
    try:
        with open(f'hackathon/static/saved_dashboards/{dashid}.yaml','r') as yamlfile:
            yaml_configuration = yaml.safe_load(yamlfile) 
    except FileNotFoundError:
        return render_template('viewdashboard.html', table_setup = [], saved_dashboards = list_saved_dashboads())
    configuration = YAMLConfiguration(yaml_configuration)
    table_setup = create_table_setup(configuration)
    return render_template('viewdashboard.html', table_setup = table_setup, saved_dashboards = list_saved_dashboads())
