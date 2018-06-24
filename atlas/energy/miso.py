# -*- coding: utf-8 -*-
"""
        atlas.energy.miso
        ~~~~~~~~~~~~~~
        This file provides classes for handling MISO LMP data.
        
        :copyright: © 2018 by Veridex
        :license: MIT, see LICENSE for more details.
        
        MISO data portal:
        https://www.misoenergy.org/markets-and-operations/market-reports/
"""


import zipfile
import datetime

import pandas
import pytz

from atlas import BaseCollectEvent


class BaseMisoLmp(BaseCollectEvent):
    """This is the Super Class for all MISO LMP collector classes."""
    
    def __init__(self, **kwargs):
        BaseCollectEvent.__init__(self)
        self.rows_rejected = 0
        self.rows_accepted = 0
    
    def load_data(self, i_csv_list):
        """This method accepts a list of lists representing the csv
        file and it returns a Pandas DataFrame. 
        """
        # all times are in EPT but watch out for DST issues
        localtz = pytz.timezone('America/New_York')
        
        # find actual header row
        r = [x for x in i_csv_list if x[0] == 'Node'][0]
        # clean is the dsc file without the top few rows of fluff
        clean = i_csv_list[i_csv_list.index(r):]
        headers = [x.strip().upper().replace('HE ','') for x in clean[0]]
        
        # loop through clean and build a list of dicts
        # make EPT/UTC conversion on datetime columns
        # pivot table form wide to long format
        output = []
        # initialize a date for datetime columns
        date = datetime.datetime.strptime(self.filename[0:8], '%Y%m%d')
        for row in clean[1:]: 
            try:
                d = dict(zip(headers, 
                        [x.upper().replace('\r','') for x in row]))
                d['data'] = [{
                    'datatype':self.datatype,
                    'iso':'MISO',
                    'node':d['NODE'],
                    'node_type':d['TYPE'],
                    'dt_utc':(localtz.localize(
                            date + datetime.timedelta(hours=int(x)-1))
                            .astimezone(pytz.timezone('UTC'))),
                    'price':float(d[str(x)])
                } for x in range(1,25)]
                # add in lmp_type to dict
                for i in d['data']:
                    try:
                        i['lmp_type'] = d['VALUE']
                    except:
                        i['lmp_type'] = 'Unknown'
                output.extend(d['data'])
            except Exception, er:
                """
                No logging implemented, but this is where we would 
                handle errors from failed rows and log it.
                """
                self.rows_rejected += 1
                pass
        self.data = pandas.DataFrame(output)
        self.rows_accepted = len(self.data)
        return self.data


class MisoLmp(BaseMisoLmp):
    """This is the generic LMP Class for MISO. Right now we only 
    collect the MISO LMP data in daily increments."""
    
    def __init__(self, lmp_type='LMP', **kwargs):
        self.datatype = kwargs.get('datatype')
        self.startdate = kwargs.get('startdate')
        self.enddate = self.startdate + datetime.timedelta(days=1)
        self.lmp_type = lmp_type
        self.url = self.build_url()
        self.filename = self.url.split('/')[-1]
        
        BaseMisoLmp.__init__(self)
        
    def build_url(self):
        """This method builds the a url for the data source. It relies
        on the following attributes: self.startdate, self.datatype
        """
        meta = MisoLmp.datatype_config()
        base = 'https://docs.misoenergy.org/marketreports/'
        url = base + '{0}{1}'.format(
            self.startdate.strftime('%Y%m%d'),
            [d['url_suffix'] for d in meta if 
                d['atlas_datatype'] == self.datatype][0])
        return url
    
    @classmethod
    def datatype_config(cls):
        """This class method maps the Atlas datatype to a URL suffix."""
        config = [
            {
                'atlas_datatype':   'DALMP_EXPOST',
                'url_suffix':       '_da_expost_lmp.csv'
            },{
                'atlas_datatype':   'DALMP_EXANTE',
                'url_suffix':       '_da_exante_lmp.csv',
            },{
                'atlas_datatype':   'RTLMP_PRELIM',
                'url_suffix':       '_rt_lmp_prelim.csv'
            },{
                'atlas_datatype':   'RTLMP',
                'url_suffix':       '_rt_lmp_final.csv'
            }
        ]
        return config
