#############################################
##       MAIN HANDLER FILE FOR VIEWS       ##
#############################################
import os
import cgi
import config
import ee
import jinja2
import webapp2
import datetime
import numpy
import json
import httplib2

import forms
import collectionMethods
from google.appengine.api import urlfetch
urlfetch.set_default_fetch_deadline(60)
httplib2.Http(timeout=15)

#############################################
##       SET DIRECTORY FOR PAGES          ##
#############################################
template_dir = os.path.join(os.path.dirname(__file__),'templates')
JINJA_ENVIRONMENT= jinja2.Environment(autoescape=True,
    loader=jinja2.FileSystemLoader(template_dir))

#############################################
##       DROUGHT TOOL PAGE                 ##
#############################################
class DroughtTool(webapp2.RequestHandler):
    def set_form_params(self):
        #sets form  parameters
        self.ppost = 0
        self.form_error = {}
        self.opacity = self.request.get('opacity',str(14*0.05))
        self.variable = self.request.get('variable','Gpr')
        self.minYear = self.request.get('minYear','1979')
        self.domainType = self.request.get('domainType','full')
        self.state = self.request.get('state','California')
        self.anomOrValue = self.request.get('anomOrValue','value')
        self.timeSeriesCalc = self.request.get('timeSeriesCalc','days')
        self.background = self.request.get('background','nowhitebackground')
        self.layer = self.request.get('layer','none')

        self.mapid = self.request.get('mapid','')
        self.token = self.request.get('token','')
        self.mapCenterLongLat = self.request.get('mapCenterLongLat','-112,42')

	tempstart = datetime.date.today()-datetime.timedelta(days=30)
	tempend = datetime.date.today()-datetime.timedelta(days=2)
	#tempstart = datetime.date.today()-datetime.timedelta(days=60)
	#tempend = datetime.date.today()-datetime.timedelta(days=30)
        self.dateStart = self.request.get('dateStart',tempstart.strftime('%Y-%m-%d'))
        self.dateEnd = self.request.get('dateEnd',tempend.strftime('%Y-%m-%d'))
        self.dayStart = self.request.get('dayStart','1')
        self.dayEnd = self.request.get('dayEnd','31')
        self.monthStart = self.request.get('monthStart',tempstart.strftime('%mm'));
        self.monthEnd = self.request.get('monthEnd',tempend.strftime('%mm'));
        self.yearStart = self.request.get('yearStart','1979');
        self.yearEnd = self.request.get('yearEnd','2015');

        self.pointsLongLat = self.request.get('pointsLongLat',self.mapCenterLongLat)

        self.opacity = self.request.get('opacity',str(14*0.05))
        self.units = self.request.get('units','metric')
        self.NELat = self.request.get('NELat',45)
        self.NELong= self.request.get('NELong',-95)
        self.SWLat= self.request.get('SWLat',40)
        self.SWLong= self.request.get('SWLong',-111)
        self.kmloption = self.request.get('kmloption', '')
        self.kmlurl = self.request.get('kmlurl', '')

        self.minColorbar = self.request.get('minColorbar', None)
        self.maxColorbar = self.request.get('maxColorbar', None)
        self.palette = self.request.get('palette', None)
        self.colorbarmap = self.request.get('colorbarmap', 'GnBu')
        self.colorbarsize = self.request.get('colorbarsize', '8')
        #Points/markers
        #Long,Lat inputs
        self.p1 = self.request.get('p1',self.mapCenterLongLat);
        self.p2 = self.request.get('p2',self.mapCenterLongLat);
        self.p3 = self.request.get('p3',self.mapCenterLongLat);
        self.p4 = self.request.get('p4',self.mapCenterLongLat);
        self.p5 = self.request.get('p5',self.mapCenterLongLat);
        self.p6 = self.request.get('p6',self.mapCenterLongLat);
        self.p7 = self.request.get('p7',self.mapCenterLongLat);
        #checkboxes and displays
        self.p1check =self.request.get('p1check','checked');self.p2check=self.request.get('p2check','checked')
        self.p3check =self.request.get('p3check','checked');self.p4check=self.request.get('p4check','checked')
        self.p5check =self.request.get('p5check','checked');self.p6check=self.request.get('p6check','checked')
        self.p7check =self.request.get('p7check','checked')
        self.p1display =self.request.get('p1display','block');self.p2display=self.request.get('p2display','none')
        self.p3display =self.request.get('p3display','none');self.p4display=self.request.get('p4display','none')
        self.p5display =self.request.get('p5display','none');self.p6display=self.request.get('p6display','none')
        self.p7display =self.request.get('p7display','none');
        self.marker_colors = ['blue', 'green', 'orange', 'purple',\
        'yellow', 'pink','red']

	if(self.domainType=='full'):
            mz= '5';
        elif(self.domainType=='states'):
            mz= '6';
	    self.mapCenterLongLat = str(forms.stateLong[self.state])+','+str(forms.stateLat[self.state]);
	else:
	    mz='4';
        self.mapzoom = self.request.get('mapzoom',mz)

        if self.minColorbar is None and self.maxColorbar is None:
            self.colorbarmap,self.colorbarsize,self.minColorbar,self.maxColorbar,self.colorbarLabel=collectionMethods.get_colorbar(self.variable,self.anomOrValue,self.units)

    def set_share_link(self, initial_template_values):
        shareLink = 'drought-monitor2.appspot.com?'
        for key, val in initial_template_values.iteritems():
            if str(key[0:4]) == 'form':
                continue
            if key == 'ppost':continue
            param_str = str(key) + '=' + str(val)
            if shareLink[-1] =='?':
                shareLink+=param_str
            else:
                shareLink+='&' + param_str
        return shareLink

    def set_initial_template_values(self):
        template_values = {
            'mapid':self.mapid,
            'token':self.token,
            'form_error': self.form_error,
            'opacity': self.opacity,
            'units': self.units,
            'pointsLongLat':self.pointsLongLat,
            'mapCenterLongLat':self.mapCenterLongLat,
            'NELat': self.NELat,
            'NELong': self.NELong,
            'SWLat': self.SWLat,
            'SWLong': self.SWLong,
            'ppost': self.ppost,
            'mapzoom': self.mapzoom,
            'variable': self.variable,
            'minYear':self.minYear,
            'state': self.state,
            'domainType': self.domainType,
            'anomOrValue': self.anomOrValue,
            'background': self.background,
            'layer': self.layer,
            'timeSeriesCalc': self.timeSeriesCalc,
            'dateStart': self.dateStart,
            'dateEnd': self.dateEnd,
            'formMonth': forms.formMonth,
            'formDay': forms.formDay,
            'formYear': forms.formYear,
            'formMapZoom': forms.formMapZoom,
            'formPaletteDivMap': forms.formPaletteDivMap,
            'formPaletteSeqMap': forms.formPaletteSeqMap,
            'formPaletteSize': forms.formPaletteSize,
            'formOpacity': forms.formOpacity,
            'formUnits': forms.formUnits,
            'formAnomOrValue': forms.formAnomOrValue,
            'formBackground': forms.formBackground,
            'formTimeSeriesCalc': forms.formTimeSeriesCalc,
            'formVariableGrid': forms.formVariableGrid,
            'formLocation': forms.formLocation,
            'formVariableLandsat': forms.formVariableLandsat,
            'formVariableModis': forms.formVariableModis,
            'formStates': forms.formStates,
            'formLayers': forms.formLayers,
            'kmlurl': self.kmlurl,
            'kmloption': self.kmloption,
            'palette': self.palette,
            'minColorbar': self.minColorbar,
            'maxColorbar': self.maxColorbar,
            'colorbarmap': self.colorbarmap,
            'colorbarsize': self.colorbarsize,
            'marker_colors':self.marker_colors,
            'p1':self.p1,
            'p2':self.p2,
            'p3':self.p3,
            'p4':self.p4,
            'p5':self.p5,
            'p6':self.p6,
            'p7':self.p7,
            'p1check':self.p1check,
            'p2check':self.p2check,
            'p3check':self.p3check,
            'p4check':self.p4check,
            'p5check':self.p5check,
            'p6check':self.p6check,
            'p7check':self.p7check,
            'p1display':self.p1display,
            'p2display':self.p2display,
            'p3display':self.p3display,
            'p4display':self.p4display,
            'p5display':self.p5display,
            'p6display':self.p6display,
            'p7display':self.p7display
        }
        if self.colorbarmap:
            template_values['colorbarmap']= self.colorbarmap
        if self.colorbarsize:
            template_values['colorbarsize']= self.colorbarsize
        if self.palette:
            template_values['palette']= self.palette
        if self.minColorbar:
            template_values['minColorbar']= self.minColorbar
        if self.maxColorbar:
            template_values['maxColorbar']= self.maxColorbar
        template_values['shareLink'] = self.set_share_link(template_values)
        if self.minColorbar:
            template_values['minColorbar'] = self.minColorbar
        if self.maxColorbar:
            template_values['maxColorbar'] = self.maxColorbar
        if self.kmlurl:
            template_values['kmlurl'] = self.kmlurl
        if self.kmloption:
            template_values['kmloption'] = self.kmloption
        #format template values to allow for different date formats etc...
        #See format_ functions in forms.py
        formatted_template_values = {}
        for key, val in template_values.iteritems():
            format_function_name = 'format_' + key
            try:
                format_function = getattr(forms,format_function_name)
            except:
                format_function = None

            if format_function:
                formatted_template_values[key] = format_function(val)
            else:
                formatted_template_values[key] = val
        return formatted_template_values

    def check_user_input(self, template_values):
        #Checks for errors in user input
        #See check_ functions in forms.py
        #At first error encountered, spits out error message and exits
        err = None; fieldID = None
        for key, val in template_values.iteritems():
            #do not check form items
            if key[0:4] == 'form':
                continue
            check_function_name = 'check_' + key
            try:
                #See if a check function exists in forms.py
                #If so, executed to check for form errors
                check_function = getattr(forms,check_function_name)
            except:
                continue
            err = check_function(val)
            if err:
                fieldID = key
                return fieldID,err
        return fieldID,err
    #############################################
    ##      GET                                ##
    #############################################
    def get(self):
        ppost=0
        ee.Initialize(config.EE_CREDENTIALS, config.EE_URL)

        #initialize forms
        self.set_form_params()
        template_values = self.set_initial_template_values()

        #Check user input for errors:
        fieldID,input_err = self.check_user_input(template_values)
        if not input_err:
            if self.request.arguments():
                #Update template values with mapid or time series data
                if self.domainType != 'points':
                    template_values = collectionMethods.get_images(template_values)
                else:
                    template_values = collectionMethods.get_time_series(template_values)
        else:
            template_values['form_error'] = {fieldID:input_err}

        template = JINJA_ENVIRONMENT.get_template('droughttool.php')
        self.response.out.write(template.render(template_values))
    #############################################
    ##      POST                                ##
    #############################################
    def post(self):
        ee.Initialize(config.EE_CREDENTIALS, config.EE_URL)
        self.set_form_params()
        template_values = self.set_initial_template_values()
        #Check user input for errors:
        fieldID,input_err = self.check_user_input(template_values)
        if not input_err:
            #Override ppost default
            template_values['ppost'] = 1
            #Update template values with mapid or time series data
            if self.domainType != 'points':
                template_values = collectionMethods.get_images(template_values)
            else:
                template_values = collectionMethods.get_time_series(template_values)
        else:
            #write error message to html
            template_values['form_error'] = {fieldID:input_err}
        template = JINJA_ENVIRONMENT.get_template('droughttool.php')
        self.response.out.write(template.render(template_values))

#############################################
##       URL MAPPING                        ##
#############################################
app = webapp2.WSGIApplication(
    [
    ('/', DroughtTool),
],
debug=True)
