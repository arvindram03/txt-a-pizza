from flask import Flask, request, redirect
import twilio.twiml
import urllib2
import requests
from random import randint
import difflib
from pymongo import MongoClient
client = MongoClient('0.0.0.0', 27017)
db = client['txt-a-pizza']


app = Flask(__name__)

access_token = 'UNGBIDQ7ZXEIB5IMPVI37UVPUQ773OQH'
CID_KEY = 'cid'
ORDER_INIT = "STARTED"
PENDING_APPR = "PENDING_APPR"
PENDING_LOC = "PENDING_LOC"
ORDER_MADE = "CONFIRMED"
ORDER_CANCELLED = "CANCELLED"
def get_order(user):
	return db.orders.find_one({'_id':user})

def insert_order(order):
	print order
	db.orders.delete_one({'_id':order['_id']})
	db.orders.insert_one(order)

def find_stores(zipcode):
	resp=requests.get("https://api.foursquare.com/v2/venues/search?venues/search?ll=&near=%s&limit=3&query=pizza&client_id=NCOCNJCP4O2BU520KQ2G0G0CWXLCS44ZY40VW1LWLNLGWHNY&client_secret=ASMOR1N4N4G4ZYZUQQSS1HILUC3LKODZMNPS2YMUFYAQSUXV&v=20160402" % zipcode);
	return resp.json()

def parse(query):
	resp=requests.get("https://api.wit.ai/message?v=20160402&q="+query, headers={"Authorization":"Bearer %s" % access_token});
	return resp.json()

def update_status(user, status):
	db.orders.update({'_id':user},{"$set": {'status':status}}, upsert=True)

def update_location(user, location):
	db.orders.update({'_id':user},{"$set": {'location':location}}, upsert=True)

def update_choices(user, choices):
	db.orders.update({'_id':user},{"$set": {'choices':choices}}, upsert=True)

def update_items(user, items):
	db.orders.update({'_id':user},{"$set": {'items':items}}, upsert=True)

def is_approved(action_items):
	outcomes = action_items['outcomes']
	outcome = outcomes[0]
	if outcome['intent'] == 'confirmation':
		return True
	else:
		return False	

def get_price(store_name):
	prices = ['$20.05','$24.32','$30.15','$18.95','$19.99','$22.35','$21.00','$19.75','$22.85','$21.50']
	return "\n%s: %s\n" % (store_name,prices[randint(0,9)])

def fetch_location(action_items):
	outcomes = action_items['outcomes']
	outcome = outcomes[0]
	entities = outcome['entities']
	if 'location' in entities.keys():
		values = entities['location']
		value = values[0]
		return value['value']
	return ""	

def fetch_order(action_items):
	outcomes = action_items['outcomes']
	outcome = outcomes[0]
	entities = outcome['entities']
	order = []
	
	if 'number' in entities.keys():
		values = entities['number']
		value = values[0]
		order.append(str(value['value']))
	
	if 'phrase_to_translate' in entities.keys():
		phrases = entities['phrase_to_translate']
		phrase = phrases[0]
		order.append(str(phrase['value']))

	return order

def get_names(stores):
	resp = stores['response']
	venues = resp['venues']
	names = []
	i =0
	for venue in venues:
		if i ==3:
			break
		names.append("["+str(i+1)+"] "+venue['name'])
		i += 1
	return names	
def translate_location(location):
	if location in ['home','house','office','work','dorm']:
		return "123, saved street, state, zipcode"
	else:
		return location

def handle_delivery(action_items, user, zipcode):
	user_order = get_order(user)
	if user_order['status'] == ORDER_INIT:
		order = fetch_order(action_items)
		location = fetch_location(action_items)
		location = translate_location(location)
		if len(order) == 0:
			order.append('Ooops I could not catch that, can you rephrase the order ?')
		elif location == "":
			order.append('Where do you need us to deliver?')
			# update_status(user, PENDING_LOC)
		else:
			update_items(user, fetch_order(action_items))
			update_location(user, location)
			stores = find_stores(zipcode)
			store_names = get_names(stores)
			choices = []
			for store_name in store_names:
				choices.append(get_price(store_name))

			order.extend(choices)
			order.append('\n[4] Cancel\n')	
			order.append('Which choice would you like ?')
			update_status(user, PENDING_APPR)
			update_choices(user, choices)
			
		return " ".join(order)

def find_closest_choice(choices, text):
	sim_scores = []	
	for choice in choices:
		sim_scores.append(difflib.SequenceMatcher(a=choice.lower(), b=text.lower()).ratio())

	return choices[sim_scores.index(max(sim_scores))]

def handle_confirmation(action_items, user):
	order = get_order(user)
	choices = order['choices']
	location = order['location']
	if order['status'] == PENDING_APPR:
		update_status(user, ORDER_MADE)
		user_order = fetch_order(action_items)
		items = " ".join(order['items'])
		choice = ""
		if len(user_order) == 0:
			choice = find_closest_choice(choices, action_items['_text'])
		else:	
			choice = choices[int(user_order[0])-1]
		return "ORDER: %s from %s is confirmed. Your pizza will be delivered within 30 mins at %s" % (items,choice[4:], location)
	return ""

def handle_cancellation(action_items, user):
	order = get_order(user)
	if order['status'] == PENDING_APPR:
		update_status(user,ORDER_CANCELLED)
		return "Your order is cancelled."
	return ""

def handle_takeaway(action_items, user):
	return ""

def get_action(action_items):
	outcomes = action_items['outcomes']
	outcome = outcomes[0]
	return outcome['intent']

def do(action_items, user, zipcode):
	action = get_action(action_items)
	if action == "pizza_delivery":
		return handle_delivery(action_items, user, zipcode)
	elif action == "pizza_takeaway":
		return handle_takeaway(action_items, user)
	elif action == "cancellation":	
		return handle_cancellation(action_items, user)
	else:	
		return handle_confirmation(action_items, user)
			
 
@app.route("/pizza", methods=['GET', 'POST'])
def receive_sms():
	user = request.form['From']
	sms = request.form['Body']
	order = get_order(user)
	if not order:
		insert_order({'_id':user,'status':ORDER_INIT})
	else:
		if order['status'] not in [PENDING_APPR, PENDING_LOC]:
			update_status(user, ORDER_INIT)

	from_zip = request.form['FromZip']

	print sms, from_zip
	
	action_items = parse(sms)
	print action_items
	
	msg = do(action_items, user, from_zip)
	resp = twilio.twiml.Response()	
	resp.message(msg)
	print msg
	return str(resp)
 
if __name__ == "__main__":
	app.secret_key = 'UNGBIDQ7ZXEIB5IMPVI37UVPUQ773OQH'
	app.run(debug=True)
