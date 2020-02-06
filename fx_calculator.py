"""
Created on Thu Feb 6th 2020
@author:Niveditha Ramayanam
"""
import numpy as np 
import pandas as pd 
import re
import requests
from bs4 import BeautifulSoup

# Define global variables
# cross-via matrix definition
# Corrected, CNYUSD is Inv and USDCNY is D
cross_via=pd.DataFrame({'/':['AUD','CAD','CNY','CZK','DKK','EUR','GBP','JPY','NOK','NZD','USD'],
              'AUD':['1:1','USD','USD','USD','USD','USD','USD','USD','USD','USD','Inv'],
              'CAD':['USD','1:1','USD','USD','USD','USD','USD','USD','USD','USD','Inv'],
              'CNY':['USD','USD','1:1','USD','USD','USD','USD','USD','USD','USD','D'],
              'CZK':['USD','USD','USD','1:1','EUR','D','USD','USD','EUR','USD','EUR'],
              'DKK':['USD','USD','USD','EUR','1:1','D','USD','USD','EUR','USD','EUR'],
              'EUR':['USD','USD','USD','Inv','Inv','1:1','USD','USD','Inv','USD','Inv'],
              'GBP':['USD','USD','USD','USD','USD','USD','1:1','USD','USD','USD','Inv'],
              'JPY':['USD','USD','USD','USD','USD','USD','USD','1:1','USD','USD','D'],
              'NOK':['USD','USD','USD','EUR','EUR','D','USD','USD','1:1','USD','EUR'],
              'NZD':['USD','USD','USD','USD','USD','USD','USD','USD','USD','1:1','Inv'],
              'USD':['D','D','Inv','EUR','EUR','D','D','Inv','EUR','D','1:1']})
cross_via.set_index("/",inplace=True)

# Exchange rates matrix definition
exchange_rates=pd.DataFrame({'BaseTerms':['AUDUSD','CADUSD','USDCNY','EURUSD','GBPUSD','NZDUSD','USDJPY','EURCZK','EURDKK','EURNOK'],'rates':[0.8317,0.8711,6.1715,1.2315,1.5683,0.7750,119.95,27.6028,7.4405,8.6651]})
exchange_rates.set_index("BaseTerms",inplace=True)

#Extract the list of known currency codes from web
def extract_known_currency_list():
	df=pd.DataFrame()
	url=requests.get("https://www.iban.com/currency-codes") # get the url 
	page=url.text 
	soup=BeautifulSoup(page,"lxml")

	# Extracting the table from the url to python and storing it as a dataframe
	table=soup.find_all('tbody')
	data=[]
	table_rows=table[0].find_all('tr')

	for tr in table_rows:
		td=tr.find_all("td")
		td=[ele.text.strip() for ele in td]
		data.append([ele for ele in td if ele])

	data=pd.DataFrame(list(data))

	d1=[]
	name=soup.find_all('table')
	name=name[0].find_all('tr')
	names=name[0].find_all('th')
	for name in names:
		d12=name.text.strip()
		d1.append(d12)
	data.columns=d1
	return data['Code'].values # we need only currency codes column

def cross_currency_loop(ccy,amount1,cross_via,exchange_rates,link_currency):
	# We use the same logic for a second loop of cross-via
	second_link=[i for i in exchange_rates.index.values if ccy in i][0]
	link_currency2=second_link.replace(ccy,'')
	if second_link[0:3]==ccy:
	    base_cross2=np.round(exchange_rates.loc[ccy+link_currency2,'rates'],4)
	else:
	    base_cross2=np.round(1/exchange_rates.loc[link_currency2+ccy,'rates'],4)

	if link_currency+link_currency2 in exchange_rates.index.values:
	    term_cross2=np.round(exchange_rates.loc[link_currency+link_currency2,'rates'],4)
	elif link_currency2+link_currency in exchange_rates.index.values:
	    term_cross2=np.round(1/exchange_rates.loc[link_currency2+link_currency,'rates'],4)
	else:
		print("Unable to find rate for %s/%s" % (ccy1, ccy2))
		user_input(known_currency)
	temp_cross=base_cross2/term_cross2
	return temp_cross


def cross_currency(ccy1,amount1,ccy2,cross_via,exchange_rates):
	# The logic is to find rates for Base/Crossccy and Term/Crossccy and then BaseCrossccy/TermCrossccy gives
	# the rate for BaseTerm.
	link_currency=cross_via.loc[ccy1,ccy2]
	# Calculating - Base to intermediate currency value
	if ccy1+link_currency in exchange_rates.index.values:
		base_cross=exchange_rates.loc[ccy1+link_currency,'rates']
	elif link_currency+ccy1 in exchange_rates.index.values:
		base_cross=np.round(1/exchange_rates.loc[link_currency+ccy1,'rates'],4)
	else:
		#Base->Crossccy1->Crossccy2->Term
		base_cross=cross_currency_loop(ccy1,amount1,cross_via,exchange_rates,link_currency)

    #Calculating term to intermiediate currency value
	if ccy2+link_currency in exchange_rates.index.values:
		term_cross=exchange_rates.loc[ccy2+link_currency,'rates']
	elif link_currency+ccy2 in exchange_rates.index.values:
		term_cross=np.round(1/exchange_rates.loc[link_currency+ccy2,'rates'],4)
	else:
		#Base->Crossccy1->Crossccy2->Term
		term_cross=cross_currency_loop(ccy2,amount1,cross_via,exchange_rates,link_currency)
	return base_cross,term_cross

#function to calculate the conversions
def fxCalculator(ccy1,amount1,ccy2,cross_via,exchange_rates):
	if cross_via.loc[ccy1,ccy2]=='1:1': #Unity, the rate is always same
		converted_currency=amount1
	elif cross_via.loc[ccy1,ccy2]=='D': #Direct feed, currency can be looked up in rates table
		converted_currency=amount1 * exchange_rates.loc[ccy1+ccy2,'rates']
	elif cross_via.loc[ccy1,ccy2]=='Inv': #Inverted
		converted_currency=amount1 * np.round((1/exchange_rates.loc[ccy2+ccy1,'rates']),4)
	elif cross_via.loc[ccy1,ccy2] not in ['1:1','D','Inv']:
		base_cross,term_cross=cross_currency(ccy1,amount1,ccy2,cross_via,exchange_rates) #cross-via the currency
		converted_currency=amount1 * (base_cross/term_cross)
	else:
		converted_currency="NotFound"
	return converted_currency

def process_input(ccy1,amount1,ccy2):
	# Calling FX calculator
	if (ccy1 in cross_via.index.values) & (ccy2 in cross_via.index.values):
		converted_currency=fxCalculator(ccy1,amount1,ccy2,cross_via,exchange_rates) #calling FX calcuator

		# Displaying Output to the user
		if converted_currency=='NotFound':
			print("Unable to find rate for %s/%s" % (ccy1, ccy2))
		else:
			# Formatting the output as ther the decimal places
			format1=format2='%.2f' # To format amount in print statement as an integer or float
			precision1=precision2=2 # To round off the number
			if ccy1=='JPY': # if currency is JPY, then the precision is adjusted to 0
			    format1='%d' # Integer format
			    precision1=0 # round off to 0
			if ccy2=='JPY': # if currency is JPY, then the precision is adjusted to 0
			    format2='%d'
			    precision2=0
			print(ccy1,format1 %np.round(amount1,precision1),"=",ccy2,format2 %np.round(converted_currency,precision2))
			user_input(known_currency) # Calling user input function for next request
	else:
		print("Unable to find rate for %s/%s" % (ccy1, ccy2)) # Conversion rate not available
		user_input(known_currency) # Calling user input function for next request

def user_input(known_currency):
	# User Input 
	regexp=r'[a-zA-Z]{3}\s([+-]?([0-9]+([.][0-9]*)?|[.][0-9]+))\sIN\s[a-zA-Z]{3}$' # Regular expression to validate user input
	userInput = re.sub(' +',' ',input("Please enter input or press (/) to exit:")).strip().upper()
	if userInput=='/':
		print("Thanks for using FX Calculator")
	else:
		valid=re.match(regexp,userInput)
		if valid is None:
			print("Input should be as per the instructions")
			user_input(known_currency) # if input is not valid, asks for input again
		else:
			# Parsing the input in the format : <ccy1> <amount11> in <ccy2>" 
			ccy1=userInput.split(' ')[0] 
			amount1=float(userInput.split(' ')[1])
			ccy2=userInput.split(' ')[3]
			# Validating if the currency code is valid or not
			if (ccy1 not in known_currency) | (ccy2 not in known_currency):
				print("Please enter a valid currency")
				user_input(known_currency)# if currency code is not valid, asks for input again
			else:
				process_input(ccy1,amount1,ccy2) # Function processes input to calculate currency and formats output

#Main function
if __name__ == "__main__": 
	# User guidelines to use the application
	print("*-------**-----**---------*")
	print("WELCOME TO FX CALCULATOR")
	print("This application let's you convert an amount1 in specific currency to equivalent amount1 in another currency")
	print("Instructions")
	print("---------------")
	print("Please provide the input only in below mentioned format")
	print("Example: AUD 100.00 in USD")
	known_currency=extract_known_currency_list() #extracting list of known currency codes by webscraping
	user_input(known_currency) # Function that takes user input and validates it.

# End-Program
