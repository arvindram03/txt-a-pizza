# txt-a-pizza
### AI Bot to order pizza via Text Messaging (SMS)
#### How it works ?
1. Twilio API is used to send messages to the Python app server
2. The messages are parsed into Natural Language Entities using the wit.ai API to identify the items, quantity and location to deliver.
3. The intended action(delivery/ take away/ confirmation/ cancellation) of the message is identified using a trained model which learns continuously
4. Based on the intended actions, the bot responds to the user with corresponding messages to proceed with the order.
5. Foursquare API is used to identified the nearby Pizza places based on the location of the user identified from the Twilio API. 
6. All the NLP data are unstructured JSONs and varies significantly based on different messages and orders. Therefore, MongoDB was used to perform CRUD on orders. 

#### Tech Stack
1. wit.ai
2. Twilio
3. Foursquare
4. MongoDB
5. Python Flask