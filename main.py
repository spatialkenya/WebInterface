#############################################
##       MAIN HANDLER FILE FOR VIEWS       ##
#############################################
import datetime
import json
import logging
import os

import cgi
import config
import ee
import httplib2
import jinja2
import numpy
import webapp2

import forms
import formchecks
import processingMethods
import collectionMethods

from google.appengine.api import urlfetch
urlfetch.set_default_fetch_deadline(180000)
httplib2.Http(timeout=180000)

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
    def set_share_link(self, initial_template_values):
        shareLink = 'http://drought-monitor3.appspot.com?'
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
        tempstart = datetime.date.today()-datetime.timedelta(days=20)
        tempend = datetime.date.today()-datetime.timedelta(days=2)
        template_values = {
            'downloadURL':self.request.get('downloadURL',''),
            'mapid':self.request.get('mapid',''),
            'token':self.request.get('token',''),
            'form_error': {},
            #Variable Options
            'variable': self.request.get('variable','Gpr'),
            'product': self.request.get('product','G'),
            'statistic': self.request.get('statistic','Total'),
            'calculation': self.request.get('calculation','value'),
            'units': self.request.get('units','metric'),
            'varUnits': self.request.get('varUnits','mm'),
            #Time Options
            'minYear':self.request.get('minYear','1979'),
            'minDate':self.request.get('minDate','1979-01-01'),
            'maxDate':self.request.get('maxDate',tempend.strftime('%Y-%m-%d')),
            'maxYear':self.request.get('maxYear',tempend.strftime('%Y')),
            'dateStart': self.request.get('dateStart',tempstart.strftime('%Y-%m-%d')),
            'dateEnd': self.request.get('dateEnd',tempend.strftime('%Y-%m-%d')),
            'yearStart': self.request.get('yearStart','1979'),
            'yearEnd': self.request.get('yearEnd',tempend.strftime('%Y')),
            #Map Options
            'opacity': self.request.get('opacity',str(14*0.05)),
            'mapCenterLongLat':self.request.get('mapCenterLongLat','-112,42'),
            'NELat': self.request.get('NELat',45),
            'NELong': self.request.get('NELong',-95),
            'SWLat': self.request.get('SWLat',40),
            'SWLong': self.request.get('SWLong',-111),
            'ppost': 0,
            'state': self.request.get('state','California'),
            'domainType': self.request.get('domainType','full'),
            'layer': self.request.get('layer','none'),
            'kmlurl': self.request.get('kmlurl', ''),
            'kmloption': self.request.get('kmloption', ''),
            #Colorbar Options
            'palette': self.request.get('palette', None),
            'minColorbar': self.request.get('minColorbar', 0),
            'maxColorbar': self.request.get('maxColorbar', 400),
            'colorbarmap': self.request.get('colorbarmap', 'GnBu'),
            'colorbarsize': self.request.get('colorbarsize', '8'),
            'colorbarLabel': self.request.get('colorbarLabel', 'Total Precipitation (mm)'),
            #TimeSeries Options
            'timeSeriesCalc': self.request.get('timeSeriesCalc','days'),
            'chartType': self.request.get('chartType', 'column'),
            #PointMarker Options
            'marker_colors':['blue', 'green', 'orange', 'purple','yellow', 'pink','red'],
            'p1check': self.request.get('p1check','checked'),
            'p2check': self.request.get('p2check','checked'),
            'p3check': self.request.get('p3check','checked'),
            'p4check': self.request.get('p4check','checked'),
            'p5check': self.request.get('p5check','checked'),
            'p6check': self.request.get('p6check','checked'),
            'p7check': self.request.get('p7check','checked'),
            'p1display': self.request.get('p1display','block'),
            'p2display': self.request.get('p2display','none'),
            'p3display': self.request.get('p3display','none'),
            'p4display': self.request.get('p4display','none'),
            'p5display': self.request.get('p5display','none'),
            'p6display': self.request.get('p6display','none'),
            'p7display': self.request.get('p7display','none'),
            #Forms
            'formChartType': forms.formChartType,
            'formMonth': forms.formMonth,
            'formDay': forms.formDay,
            'formGridMetYear': forms.formGridMetYear,
            'formLandsat5Year': forms.formLandsat5Year,
	    'formLandsat8Year': forms.formLandsat8Year,
            'formModisYear': forms.formModisYear,
            'formMapZoom': forms.formMapZoom,
            'formPaletteCustomMap': forms.formPaletteCustomMap,
            'formPaletteDivMap': forms.formPaletteDivMap,
            'formPaletteSeqMap': forms.formPaletteSeqMap,
            'formPaletteSize': forms.formPaletteSize,
            'formOpacity': forms.formOpacity,
            'formUnits': forms.formUnits,
            'formCalculation': forms.formCalculation,
            'formBackground': forms.formBackground,
            'formTimeSeriesCalc': forms.formTimeSeriesCalc,
            'formVariableGrid': forms.formVariableGrid,
            'formStatistic': forms.formStatistic,
            'formLocation': forms.formLocation,
            'formVariableLandsat': forms.formVariableLandsat,
            'formVariableModis': forms.formVariableModis,
            'formStates': forms.formStates,
            'formLayers': forms.formLayers
        }
        #Conditional template values
        #Climatology start year depends in minYear of variable
        template_values['yearStartClim'] = self.request.get('yearStartClim',template_values['minYear'])
        template_values['yearEndClim'] = self.request.get('yearEndClim','2010')
        #Map zoom depends on domain type
        if template_values['domainType'] == 'full':
            mz= '5'
        elif template_values['domainType'] == 'states':
            mz= '6'
            stLong = str(forms.stateLong[template_values['state']])
            stLat = str(forms.stateLat[template_values['state']])
            template_values['mapCenterLongLat'] = stLong + ',' + stLat
        else:
            mz='4'
        template_values['mapzoom'] = self.request.get('mapzoom',mz)

        #Markers are initialized to center of map
        template_values['pointsLongLat'] = self.request.get('pointsLongLat',template_values['mapCenterLongLat'])
        template_values['p1'] = self.request.get('p1',template_values['mapCenterLongLat'])
        template_values['p2'] = self.request.get('p2',template_values['mapCenterLongLat'])
        template_values['p3'] = self.request.get('p3',template_values['mapCenterLongLat'])
        template_values['p4'] = self.request.get('p4',template_values['mapCenterLongLat'])
        template_values['p5'] = self.request.get('p5',template_values['mapCenterLongLat'])
        template_values['p6'] = self.request.get('p6',template_values['mapCenterLongLat'])
        template_values['p7'] = self.request.get('p7',template_values['mapCenterLongLat'])

        #Sharelink depends on most template variables
        template_values['shareLink'] = self.set_share_link(template_values)

        #format template values to allow for different date formats etc...
        #See format_ functions in formchecks.py
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
        #See check_ functions in formchecks.py
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

        #special check for climatology years
        err = formchecks.check_climatologyyears(template_values['yearStartClim'],template_values['yearEndClim'],
              template_values['domainType'])
        if err:
                fieldID = 'yearStartClim'
                return fieldID,err

        #special check for date range >365 when climatology is needed
        #(someday when we fix this.. we can delete this)
        err = formchecks.check_dateMoreThanYear(template_values['dateStart'],template_values['dateEnd'],
              template_values['calculation'],template_values['domainType'])
        if err:
                fieldID = 'dateCheckMoreThanYear'
                return fieldID,err

        return fieldID,err
    #############################################
    ##      GET                                ##
    #############################################
    def get(self):
        ppost=0
        ee.Initialize(config.EE_CREDENTIALS, config.EE_URL)
	ee.data.setDeadline(180000);

        #initialize forms
        #self.set_form_params()
        template_values = self.set_initial_template_values()

        #Check user input for errors:
        fieldID,input_err = self.check_user_input(template_values)
        if not input_err:
            if self.request.arguments():
                #Update template values with mapid or time series data
                if template_values['domainType'] == 'full':
                    template_values = processingMethods.get_images(template_values)
                elif template_values['domainType'] == 'points':
                    template_values = processingMethods.get_time_series(template_values)
                #elif template_values['domainType'] == 'rectangle':
                #    template_values = processingMethods.get_images(template_values)
                #elif template_values['domainType'] == 'singlemappoint':
                #    template_values = processingMethods.get_images(template_values)
                #else: #error

        else:
            template_values['form_error'] = {fieldID:input_err}

        template = JINJA_ENVIRONMENT.get_template('droughttool.php')
        self.response.out.write(template.render(template_values))
    #############################################
    ##      POST                                ##
    #############################################
    def post(self):
        ee.Initialize(config.EE_CREDENTIALS, config.EE_URL)
	ee.data.setDeadline(180000);

        #self.set_form_params()
        template_values = self.set_initial_template_values()
        #Check user input for errors:
        fieldID,input_err = self.check_user_input(template_values)
        if not input_err:
            #Override ppost default
            template_values['ppost'] = 1
            #Update template values with mapid or time series data
            if template_values['domainType'] == 'full':
                template_values = processingMethods.get_images(template_values)
            elif template_values['domainType'] == 'points':
                template_values = processingMethods.get_time_series(template_values)
            elif template_values['domainType'] == 'rectangle':
                template_values = processingMethods.get_images(template_values)
        else:
            #write error message to html
            template_values['form_error'] = {fieldID:input_err}
        template = JINJA_ENVIRONMENT.get_template('droughttool.php')
        self.response.out.write(template.render(template_values))


#############################################
##      FUNCTIONAL TESTS                   ##
#############################################
class testURLs(webapp2.RequestHandler):
    #from urllib.request import Reqest, urlopen
    #from urllib.error import URLError
     #import urllib.request
     #import urllib.error

    def get(self):

	#Here's my plan
	#get the initial template_values
        ppost=0
        ee.Initialize(config.EE_CREDENTIALS, config.EE_URL)

	#get the current shareLink URL
        #dT=DroughtTool()
        #template_values = dT.set_initial_template_values()
        #shareLink = template_values['shareLink']
        #shareLink='http://drought-monitor3.appspot.com?state=California&kmloption=&p6display=none&chartType=column&marker_colors=['blue', 'green', 'orange', 'purple', 'yellow', 'pink', 'red']&SWLat=40&p3=-112,42&p2=-112,42&p1=-112,42&p7=-112,42&p6=-112,42&p5=-112,42&p4=-112,42&opacity=0.7&p7check=checked&pointsLongLat=&statistic=Total&SWLong=-111&palette=f7fcf0,e0f3db,ccebc5,a8ddb5,7bccc4,4eb3d3,2b8cbe,08589e&downloadURL=&maxYear=2015&varUnits=mm&p4check=checked&units=metric&colorbarmap=GnBu&yearEnd=2015&p5display=none&yearStart=1979&p2check=checked&layer=none&colorbarLabel=Total Precipitation (mm)&minColorbar=0&minYear=1979&NELat=45&mapCenterLongLat=-112,42&mapid=&timeSeriesCalc=days&maxDate=2015-02-25&dateEnd=2015-02-25&colorbarsize=8&token=&dateStart=2015-02-07&p1display=block&p3check=checked&maxColorbar=400&mapzoom=5&NELong=-95&p4display=none&domainType=full&p1check=checked&kmlurl=&p5check=checked&product=G&calculation=value&minDate=1979-01-01&variable=Gpr&p6check=checked&yearStartClim=1979&p3display=none&p7display=none&yearEndClim=2010&p2display=none'

	#loop over a set of variables that are input into shareLink from the current forms in forms.py
        #for variable in forms.formVariableGrid:
       	#	var = variable[0]
	#	find and replace the variables in shareLink
        #        sL_new = shareLink.replace(/mapzoom=\d+/m,'variable=' + var);
	#	#test the shareLink
        #	req=Request(shareLink)
        #	try:
        #    	    response=urlopen(req)
	#	except URLError as e:
        #    	    errorCode = e.code
        #    	#print(e.reason)
        #	else:
        #    		#everything is fine

	#see if get a 404 error or not
	#print a line on the webpage showing the variable tested and the status of the test (fail/success)
        #if errorCode ==404:
        #   errorMesssage = 'failed'
        #else:
        #   errorMessage = 'success'
        errorMessage = 'success'
	errorMessage = shareLink

	template_values ={'errorMessage':errorMessage,
		}
	template = JINJA_ENVIRONMENT.get_template('testURL.php')
        self.response.out.write(template.render(template_values))

#############################################
##       URL MAPPING                        ##
#############################################
app = webapp2.WSGIApplication(
    [
    ('/', DroughtTool),
    ('/testURLs',testURLs ),
],
debug=True)
